/*
 * libjvm.so -- 一个 ANCHOR（锚），不是 JVM。
 *
 * 为什么存在这个
 *   每个挨着 libjvm.so 的 JDK 库（libjava、libnet、libnio、libjimage……）
 *   都在裸名 "libjvm.so" 上声明 DT_NEEDED。动态链接器
 *   靠在它的库路径里搜索来满足这个需求，而那些路径只包含 HAP 的
 *   扁平 native-lib 目录 —— 不包含真正的 libjvm.so 所在的
 *   子目录：
 *
 *       真正的 libjvm.so : <bundle>/libs/arm64/jdk21/lib/server/libjvm.so
 *       搜索路径         : <bundle>/libs/arm64/
 *
 *   ……而它不能被挪到搜索路径上，因为 HotSpot 通过剥掉
 *   libjvm.so 自身路径的三段分量来推导 java.home，然后
 *   要求 "<java.home>/lib/<module image>" 存在：
 *
 *       <bundle>/libs/arm64/jdk21/lib/server/libjvm.so
 *                                ^^^^^^^ lib/server -> lib -> jdk21 = java.home
 *
 *   于是这两个要求把方向拽向相反的两边，而这个极小的库
 *   就是折中：它待在搜索路径【上】，好让 "libjvm.so" 能解析出来，
 *   而它除了存在什么都不做。其它 JDK 库真正想要的符号
 *   来自【真正的】 libjvm.so，本应用会先用 RTLD_GLOBAL
 *   把它加载起来，让它在全局符号作用域中可见。
 *
 *   没有任何东西直接链接这个目标文件；应用总是用完整路径
 *   dlopen() 真正的那个。
 *
 * ⚠️「仅限 ASCII」这条规则已于 2026-09-28 被实测推翻：穷举 182 个
 * 非 ASCII 字符紧贴注释结束符全部正常闭合，且用项目真实编译命令编过。
 * 撤销它的提交是 db403e5。本文件写中文注释没有问题。
 */

/* 导出一个符号，让本文件是结构合法的共享对象，
 * 且动态符号表非空（链接器更满意，也给了我们一个
 * 可以 dlsym 的东西，用来证明加载到的是哪一个） */
__attribute__((visibility("default")))
int libjvm_anchor_present(void)
{
    return 0x4a564d;   /* "JVM" */
}
