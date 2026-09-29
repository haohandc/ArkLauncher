package com.haohandc.launcher;

/**
 * 替启动器加载一个库，发起者是一个由应用类加载器
 * 自己所拥有的类。
 *
 * 这个类为什么存在
 *
 * Runtime.load0() 挑选一个原生库所注册到的加载器，
 * 方式如下：
 *
 *     ClassLoader loader = (fromClass == null) ? null : fromClass.getClassLoader();
 *     NativeLibraries libs = libsFor(loader);
 *
 * 而 System.load() 从调用者栈帧取得 fromClass，因为它
 * 带有 @CallerSensitive 注解。
 *
 * 启动器通过 JNI 调用它，而 JNI 调用没有 Java 调用者栈帧。所以
 * fromClass 出来是 null，库被注册到 BOOTSTRAP（引导）
 * 加载器（null）上，于是应用加载器加载的每个类都找不到
 * 它的 native 方法 —— 即便库本身毫无错误地加载了：
 *
 *     java.lang.UnsatisfiedLinkError:
 *         'int arc.util.NativeUtils.setEnv(java.lang.String, java.lang.String, boolean)'
 *         at arc.util.NativeUtils.setEnv(Native Method)
 *         at arc.backend.sdl.SdlApplication.init(SdlApplication.java:125)
 *
 * 那条消息的两半都是真的，在把加载器考虑进来之前它们看起来
 * 自相矛盾：库确实已加载，只是并非为那些需要它的
 * 类加载。
 *
 * 从这里调用 System.load 就能修好，因为本类由与该游戏相同的
 * 应用类加载器加载，于是库落在同一个
 * 位置，符号得以解析。
 *
 * 保持独立成 jar，而不是注入游戏 jar，这样游戏
 * jar 就仍是那个经过验证的、原封不动的产物。
 */
public final class NativeLoader {

    private NativeLoader() {
    }

    /** System.load，以本类作为调用者，这样加载器才是对的那个。 */
    public static void load(String absolutePath) {
        System.load(absolutePath);
    }

    /**
     * 告诉 Arc 某个原生库已加载，好让它自己的加载器不再尝试。
     *
     * SharedLibraryLoader.setLoaded 是 public static 的，而 load(String)
     * 对一个已被标记的名字会立即返回。以反射方式触达，
     * 因为本 jar 刻意不对游戏保留任何编译期依赖。
     */
    public static void markLoaded(String name) throws Exception {
        Class.forName("arc.util.SharedLibraryLoader")
             .getMethod("setLoaded", String.class)
             .invoke(null, name);
    }
}
