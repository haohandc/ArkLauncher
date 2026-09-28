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
#include <sys/mman.h>
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

/* [A]
 * 这个进程【现在】能不能拿到匿名可执行内存？
 *
 * 为什么这才是决定性问题，而「坚盾开不开」不是
 *   2026-09-28 实测：同一个包启动两次，两份日志逐行相同，唯一差别就在这个探测 ——
 *   探测为 42 时 JVM 建成、游戏跑起来了；探测为 -1 时 JNI_CreateJavaVM 从未返回，
 *   进程凭空消失，没有错误码、也没有 faultlog。坚盾模式只是「拿不到可执行内存」的
 *   【一种】成因，不是唯一一种 —— 实测坚盾【关着】的启动也出现过 -1。所以要问的
 *   是那个覆盖全部成因的问题，而不是只覆盖一种成因的那个。
 *
 * 为什么不干脆「去问 launcher」
 *   launcher 自己的探测跑在 main() 里，而 main() 只有在 XComponent 存在之后才会跑 ——
 *   可 XComponent 建不建，正是这里要决定的事。到那时进程已经无可挽回了。这个问题
 *   必须在那之前就能回答。
 *
 * 为什么用了 munmap，而 launcher 的探测没有
 *   launcher.c 的 probe_exec_mem() 是故意不释放映射、且每次都打日志的，所以它
 *   绝不能放进循环里调用。这一个会在每次启动、每次按「重试」时都调用，所以它
 *   映射、然后释放。
 *
 * ⚠️ 为什么【不】把机器码写进去再执行它（第一版是这样，已改掉）
 *   第一版往那块内存里写了一条 AArch64 指令「mov w0,#42; ret」并调用它，只在
 *   返回 42 时才判为可用。那一步不带来任何额外覆盖，却引入一个真实的崩溃风险：
 *   本探针跑在 aboutToAppear，此时 launcher.c 的信号处理器【还没装上】（那是
 *   main() 里的事，而 main() 这时根本还没跑）。mmap 成功但执行出错的话，这个
 *   探针会自己把应用打死，连提示都来不及显示 —— 正是它要防的那件事。
 *
 *   额外的覆盖确实是零：本项目实测过，拿不到时 mmap(RWX) 直接失败（errno=22），
 *   所以 mmap 这一步就是完整信号。（见 FACT.md 的「匿名可执行内存的内核边界」。）
 *
 * ⭐ 这个写法与 AMCL 的 detectJitSupport() 一致（amcl-src：jvm/jvm_launcher.cpp）。
 *   它同样是「只 mmap、就 munmap」，不执行；而它的执行型探测留在 jvmInit 那条
 *   兜底上 —— 与本项目把执行型探测留在 launcher.c 里的结构相同。
 *   前置闸门用不会崩的那种，执行型探测放在它该在的位置。
 */
static napi_value ProbeExecMemory(napi_env env, napi_callback_info info)
{
    bool ok = false;

    void *p = mmap(NULL, 4096,
                   PROT_READ | PROT_WRITE | PROT_EXEC,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p != MAP_FAILED) {
        ok = true;
        munmap(p, 4096);
    }

    napi_value result;
    napi_get_boolean(env, ok, &result);
    return result;
}

static napi_value Init(napi_env env, napi_value exports)
{
    napi_property_descriptor desc[] = {
        { "shieldDiagnosis", NULL, ShieldDiagnosis, NULL, NULL, NULL, napi_default, NULL },
        { "probeExecMemory", NULL, ProbeExecMemory, NULL, NULL, NULL, napi_default, NULL },
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