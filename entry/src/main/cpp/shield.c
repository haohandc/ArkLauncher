// [B]
// 创建于 2026/9/27。
//
// Node API 的支持并不完整。若遇到「找不到接口」的编译错误，
// 请包含 "napi/native_api.h"。
//

/* [A]
 * 在任何【需要可执行内存】的东西启动【之前】，先问平台：它是否处于坚盾守护模式。
 *
 * 为什么需要它
 *   坚盾模式禁止申请匿名可执行内存。而 HotSpot 在去考虑「字节码怎么执行」之前，
 *   就已经在构建它的启动 stub 了，所以解释执行要的内存和 JIT 一样多 —— 没有退路，
 *   应用根本起不来。诚实的做法是把这件事说出来，而不是在第一帧就死掉。
 *
 * 为什么用 dlopen，而不是链接这个 Kit
 *   链接期依赖会写成一个硬 DT_NEEDED。不附带该 Kit 的设备，就会因此连本库都加载
 *   不起来；而「Kit 不可用」不该把应用拖死。
 *
 * 为什么返回字符串，而不是布尔
 *   布尔版把「库没找到」「符号没找到」「不在坚盾模式」统统答成了 false。这是三件
 *   不同的事，而只有最后一件是【答案】——前两件是【知识的缺口】。把缺口压成答案，
 *   就会让「一个从不触发的门」和「门查过了、什么都没查到」变得无法区分，而这里
 *   恰恰发生过这件事，代价是好几天。
 *
 *   所以返回值是：'on' / 'off' / 'no-lib: <dlerror>' / 'no-sym: <dlerror>' / 'mode=<N>'。
 *   只有 'on' 才表示处于坚盾。其余都不是「设备受限」的证据，调用方不能在没有证据
 *   的情况下拒绝启动。
 */
#include <node_api.h>
#include <stdio.h>
#include <dlfcn.h>
#include <DeviceSecurityKit/device_security_mode.h>

static napi_value ShieldDiagnosis(napi_env env, napi_callback_info info)
{
    char text[256];

    void *lib = dlopen("libdevice_security_mode.z.so", RTLD_LAZY);
    if (lib == NULL) {
        const char *why = dlerror();
        snprintf(text, sizeof(text), "no-lib: %s", why ? why : "(no dlerror text)");
    } else {
        DSM_DeviceSecurityMode (*get_mode)(void) =
            (DSM_DeviceSecurityMode (*)(void)) dlsym(lib, "HMS_DSM_GetDeviceSecurityMode");
        if (get_mode == NULL) {
            const char *why = dlerror();
            snprintf(text, sizeof(text), "no-sym: %s", why ? why : "(no dlerror text)");
        } else {
            const DSM_DeviceSecurityMode mode = get_mode();
            if (mode == DSM_SECURE_SHIELD_MODE) {
                snprintf(text, sizeof(text), "on");
            } else if (mode == DSM_NORMAL_MODE) {
                snprintf(text, sizeof(text), "off");
            } else {
                /* [A] 这是头文件没有命名的枚举值。不要把它读成 "off"。 */
                snprintf(text, sizeof(text), "mode=%d", (int)mode);
            }
        }
        /* [A] 故意【不】dlclose() —— 该库在整个进程生命周期内保持映射，
         * 这样后续调用不会因为重新加载而拿到一个不同的答案。 */
    }

    napi_value result;
    napi_create_string_utf8(env, text, NAPI_AUTO_LENGTH, &result);
    return result;
}


static napi_value Init(napi_env env, napi_value exports)
{
    napi_property_descriptor desc[] = {
        { "shieldDiagnosis", NULL, ShieldDiagnosis, NULL, NULL, NULL, napi_default, NULL },
    };
    napi_define_properties(env, exports, sizeof(desc) / sizeof(desc[0]), desc);
    return exports;
}

static napi_module shield_module = {
    .nm_version = 1,
    .nm_flags = 0,
    .nm_filename = NULL,
    .nm_register_func = Init,
    .nm_modname = "shield",
    .nm_priv = ((void*)0),
    .reserved = { 0 },
};

void __attribute__((constructor)) RegisterShieldModule(void)
{
    napi_module_register(&shield_module);
}