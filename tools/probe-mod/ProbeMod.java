package probe;

import mindustry.mod.Mod;

/**
 * 能【证明】加载器可用性的最小 mod。
 *
 * 为什么存在这个
 *   Mindustry 的 mod 支持从没在这个平台上跑起来过，而眼下悬着的
 *   问题很窄：从 mod jar 里在运行时加载的类，能否在这个 JVM 下
 *   被定义并执行？mod 的其它一切 —— 目录扫描、内容解析器、
 *   生命周期 —— 都是 Mindustry 原装的。
 *
 * 为什么是打日志，而不是添加内容
 *   本项目对这件事已经有规矩：「出现在 mod 列表里」
 *   与「它真的生效了」不是一回事。一行日志不可能
 *   由本类体执行之外的任何东西产生，所以它同时证明了两件事：
 *   这个类被定义了，且它的生命周期方法被调用了。
 *   只是出现在列表里的 mod，两样都证明不了。
 *
 *   两个标记刻意区分开，这样即使只拿到一半结果也仍有
 *   信息量：init() 在内容加载之前跑，loadContent() 在加载过程中跑。
 *   只见到第一个，就意味着类加载能工作、而内容阶段
 *   不能。
 *
 * 刻意保持纯 ASCII：本项目已经被 clang 在中文 Windows 控制台上
 * 把源文件按 GBK 解码坑过两次。javac 不是 clang，但
 * 没理由非得亲自撞一次才信。
 */
public class ProbeMod extends Mod {

    @Override
    public void init() {
        System.out.println("[probe-mod] MARKER-INIT-RAN");
    }

    @Override
    public void loadContent() {
        System.out.println("[probe-mod] MARKER-LOADCONTENT-RAN");
    }
}
