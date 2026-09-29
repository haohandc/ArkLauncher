# -*- coding: utf-8 -*-
r"""Recompile the patched Arc classes that go into the game jar.

WHY THIS IS A SCRIPT WITH GATES
    patch_mindustry.py replaces arc/backend/sdl/** in the game jar with whatever
    is sitting in %TEMP%\arcbuild\sdl3. Nothing checks that those class files were
    built from the sources that are on disk now -- so editing Arc and forgetting
    to rebuild produces a jar that looks updated and is not. That is the same
    shape of failure as the library that was "rebuilt" without being re-linked,
    and the jar's hash would not catch it either, because the hash is taken after
    the fact.

    So: the source is checked for the change, the compile is required to succeed,
    and the produced class is checked for the property name that only the new
    code contains.

TWO PHASES, AND WHY THE SECOND ONE EXISTS (added 2026-09-28)
    This script now compiles BOTH modules of the patch:

        arc-core            GLVersion, GLVersion$GlType, Shader  -> arcbuild/core
        backend-sdl3        SdlApplication, SdlInput, SdlFiles   -> arcbuild/sdl3

    Until this change only the second phase existed. patch_mindustry.py expects
    the arc-core three in arcbuild/core and reads them as an INPUT, but nothing
    wrote them: the directory had been populated by hand and was later found
    empty, which meant the patch could not be rebuilt at all. The sources were
    intact and did carry the changes, so the gap was purely the missing compile.

    arc-core goes first because the backend compile puts arcbuild/core on its
    class path.

    Both phases gate twice, and the two gates are different in kind:
      * source gates, against the SOURCE TEXT of the change
      * class gates, against the COMPILED BYTES
    For the SDL3 classes the marker happens to be a string literal, which exists
    in both places, so one marker served both gates. That is not true in general
    -- GLVersion's marker is a method descriptor, which javac writes and the
    source never contains -- so the two are kept separate here.

Usage:  python build_arc_patch.py
"""

import os
import shutil
import struct
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

# 编译所用的 Arc 源码检出目录（ARK_ARC_SRC）。下面这三个
# 类是本项目唯一修改的 Arc 文件。
ARC = config.ARC_SRC
SRC = os.path.join(ARC, "backends", "backend-sdl3", "src",
                   "arc", "backend", "sdl", "SdlApplication.java")
# 触摸/捏合补丁在这里。同一轮运行会重新编译它，门禁方式
# 相同 -- 见 MARKER3/MARKER4，以及关于为什么一个标记
# 对一个会被反复编辑的文件不够用的说明。
SRC_INPUT = os.path.join(ARC, "backends", "backend-sdl3", "src",
                         "arc", "backend", "sdl", "SdlInput.java")
# 把文件浏览器的根目录与游戏数据目录解耦，使 "import
# save" 能打开玩家真正放得下文件的地方。
SRC_FILES = os.path.join(ARC, "backends", "backend-sdl3", "src",
                         "arc", "backend", "sdl", "SdlFiles.java")
SRC_ROOT = os.path.join(ARC, "backends", "backend-sdl3", "src")
CORE_ROOT = os.path.join(ARC, "arc-core", "src")


def backend_sources():
    """Every .java in the SDL3 backend, not just the three named above.

    ⚠️ 2026-09-28. This is the fix for a failure that took a device build to
    find: the patch has to be the WHOLE recompiled backend, not three files.

    patch_mindustry.py replaces arc/backend/sdl/ as a DIRECTORY -- its own
    comment says "目录替换（backend-sdl3 整体覆盖 backend-sdl）". So whatever is
    in arcbuild/sdl3 goes in, and the game jar's copies of those names are
    replaced whether or not we edited the matching source.

    Ten of the backend's twelve sources are ours (seven modified, three new:
    GLBootstrap, GLDiag, GLDispatchFix). Compiling only SdlApplication/SdlInput/
    SdlFiles produced a patch jar missing SdlConfig and the GL classes, and the
    device died with:

        NoSuchFieldError: Class arc.backend.sdl.SdlConfig does not have member
        field 'java.lang.String appName'

    because our SdlApplication reads a field that only OUR SdlConfig declares.
    The install filter below had narrowed to three prefixes while the directory
    it feeds is consumed as a whole.
    """
    out = []
    for dp, _d, fs in os.walk(SRC_ROOT):
        for f in sorted(fs):
            if f.endswith(".java"):
                out.append(os.path.join(dp, f))
    return sorted(out)

# LWJGL 的 jar，编译类路径需要它们，因为 Arc 的 SDL3 后端
# 引用了 org.lwjgl.* -- 与 prep_lwjgl.py 发布的是同一目录。
LWJGL = config.LWJGL_SRC
ARCBUILD = os.path.join(config.TMP, "arcbuild")
OUT_SDL3 = os.path.join(ARCBUILD, "sdl3", "arc", "backend", "sdl")

JAVAC = config.JAVAC

# 新代码里有，旧代码里没有。在编译产物里检查它，才能区分
# "已重新编译" 与 "之前的 class 文件还
# 原样躺在那"。
MARKER = b"arc.sdl.glEs"
# 两个属性都必须出现在编译产物里。只查一个可能通过，而另一处
# 修改根本没被带进去，这正是整个脚本要防止的失败 -- 而且它们
# 是不同时间改的，所以 "自上次我记得的修改以来已重新编译"
# 不是一个安全的假设。
MARKER2 = b"arc.sdl.mobile"

# 新 SdlInput 代码里有，旧代码里没有（旧代码完全忽略
# SDL_EVENT_FINGER_*，并且对所有指针查询都回答指针 0）。
# 这些是字段名，会通过新方法产生的字段引用
# 进入类的常量池。
MARKER3 = b"MAX_TOUCH_POINTERS"
MARKER4 = b"pointerJustDown"
# 比上面两个加得更晚，因此单独设门禁：那两个在源码和之前发布的
# class 里都已存在，所以无法区分重新构建的 SdlInput.class 和过期的。
# 这个可以 -- 它是 hover 跟随触摸修复引入的方法名，因此只存在于
# 由当前状态的源码编译出来的
# class 里。
MARKER7 = b"syncMouseToFinger"

# 新 SdlFiles 代码里有，旧代码里没有（浏览器根目录以前
# 与游戏数据路径不可分割）。
MARKER5 = b"arc.sdl.chooserPath"
MARKER6 = b"chooserPath"

# ---------------------------------------------------------------------------
# arc-core：核心模块（不是 SDL3 后端）中被修补的两个类。
#
# ⚠️ 2026-09-28 添加。在此改动之前，本仓库中没有任何东西会产出
# 这三个 class 文件 -- patch_mindustry.py 期望它们位于 arcbuild/core
# 并把该目录当作 INPUT，但没有脚本写它。该目录曾被人手工
# 填充过一次，随后丢失；调查此事时该目录是空的，
# 这些类根本无法重新构建。
#
# 这与不可复现的 libarcarm64.so 是同一种缺口，只是
# 这个可以修：源码在磁盘上，其中的改动是
# 真实的（下面会与上游比对）。
# ---------------------------------------------------------------------------
SRC_GLVERSION = os.path.join(ARC, "arc-core", "src",
                             "arc", "graphics", "gl", "GLVersion.java")
SRC_SHADER = os.path.join(ARC, "arc-core", "src",
                          "arc", "graphics", "gl", "Shader.java")
OUT_CORE = os.path.join(ARCBUILD, "core")

# 新 GLVersion 代码里有，旧代码里没有。补丁新增了
#     if(versionString != null && versionString.contains("OpenGL ES")) ...
# 对应旧代码的第一行，旧行只判断了 appType == android -- 所以它
# 引入的调用就是标记。用 String.contains 的描述符而不是
# 字面量 "OpenGL ES"，是因为该字面量在上游 class 里
# 已经存在（其版本解析会用到它），那样什么都证明不了。
MARKER8 = b"(Ljava/lang/CharSequence;)Z"
# 新 Shader 代码里有，旧代码里没有：对 GLVersion 的 import
# 以及从 app 类型改为按 GL 版本判断，意味着 Shader.class 现在会引用
# GLVersion$GlType，而上游 class 不会。
MARKER9 = b"GLVersion$GlType"

# ⚠️ SOURCE 标记与上面的 class 标记是 DIFFERENT 的东西，这里
# 必须把这一区分讲明确。
#
# 上面的标记是拿 COMPILED BYTES 来检查的。那三个 SDL3
# 标记恰好是字符串字面量，源码和字节里都有，
# 所以一个标记同时服务两道门禁，差异从未显现。
# MARKER8 是方法描述符：它由 javac 写出，在源码里 NOWHERE
# 都不出现。把它喂给源码门禁每次都会失败 -- 这正是
# 第一次运行这个脚本时发生的事。
#
# 所以源码门禁有自己的一套标记，取自改动本身的
# 源码文本。
SRC_MARK_GLVERSION = b"!= null && versionString.contains"
SRC_MARK_SHADER = b"glType == GlType.GLES"

# GLVersion$GlType 没有行为变化 -- 重新编译它是因为它
# 挨着 GLVersion，不是因为我们改了它。因此没有标记
# 能区分我们的副本和上游的副本，它只检查
# 字节码版本。在这里说明这一点才是关键：标记只能
# 凭空发明，而给未改动的类发明标记什么都证明不了。
CORE_PRODUCES = ["arc/graphics/gl/GLVersion.class",
                 "arc/graphics/gl/GLVersion$GlType.class",
                 "arc/graphics/gl/Shader.class"]

PRODUCES = ["SdlApplication.class",
            "SdlApplication$SdlError.class",
            "SdlApplication$1.class",
            "SdlInput.class"]


def build_core():
    """Compile the patched arc-core classes into ARCBUILD/core.

    Runs FIRST, because the SDL3 backend compile below puts ARCBUILD/core on its
    class path.

    ARCBUILD/core is deliberately absent from this compile's OWN class path: it
    is the thing being rebuilt, and leaving it there would let a stale copy
    satisfy javac. The Arc classes these two files depend on are reached through
    -sourcepath instead, and -implicit:none keeps javac from writing them out --
    only the three classes we actually patch land in the output.
    """
    for path, markers in ((SRC_GLVERSION, (SRC_MARK_GLVERSION,)),
                          (SRC_SHADER, (SRC_MARK_SHADER,))):
        if not os.path.isfile(path):
            print("FAIL missing %s" % path)
            return 1
        src_text = open(path, encoding="utf-8", errors="replace").read()
        for marker in markers:
            name = marker.decode()
            if name not in src_text:
                print("FAIL %s does not contain the change (%s)."
                      % (os.path.basename(path), name))
                print("     Edit it first.")
                return 1
            print("%s carries the change: %s" % (os.path.basename(path), name))

    # Shader.java 引用了 org.lwjgl.opengl.*，所以即使这是核心
    # 模块也需要 LWJGL 的 jar。
    jars = [os.path.join(LWJGL, f) for f in sorted(os.listdir(LWJGL))
            if f.endswith(".jar")]

    with tempfile.TemporaryDirectory() as tmp:
        cmd = [JAVAC, "--release", "17", "-nowarn", "-implicit:none",
               "-encoding", "UTF-8",
               "-sourcepath", CORE_ROOT,
               "-d", tmp]
        if jars:
            cmd += ["-cp", os.pathsep.join(jars)]
        cmd += [SRC_GLVERSION, SRC_SHADER]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print("FAIL javac (arc-core)")
            print(r.stdout)
            print(r.stderr)
            return 1
        out = (r.stdout or "") + (r.stderr or "")
        if out.strip():
            print(out)

        # 与后端相同的两段式门禁：先字节码主版本，再查只有打过补丁的
        # 源码才会产出的标记。GLVersion$GlType 只检查
        # 主版本 -- 见 CORE_PRODUCES 处的说明。
        for cls, markers in (("GLVersion.class", (MARKER8,)),
                             ("GLVersion$GlType.class", ()),
                             ("Shader.class", (MARKER9,))):
            produced = os.path.join(tmp, "arc", "graphics", "gl", cls)
            if not os.path.isfile(produced):
                print("FAIL javac produced no %s" % cls)
                return 1
            blob = open(produced, "rb").read()
            major = struct.unpack(">H", blob[6:8])[0]
            if major != 61:
                print("FAIL %s bytecode major is %d, the jar's classes are 61"
                      % (cls, major))
                return 1
            for marker in markers:
                if marker not in blob:
                    print("FAIL the compiled %s does not contain %r" % (cls, marker))
                    return 1
            print("compiled: %s major=61%s"
                  % (cls, "" if not markers else
                     ", contains " + ", ".join(repr(m.decode()) for m in markers)))

        # 只清理本步骤自己拥有的三个文件。清空目录还会
        # 删掉未来步骤放在那里的其他东西，而本函数的全部
        # 意义就在于这个目录现在有主了。
        for rel in CORE_PRODUCES:
            stale = os.path.join(OUT_CORE, rel.replace("/", os.sep))
            if os.path.isfile(stale):
                os.remove(stale)
        installed = 0
        for rel in CORE_PRODUCES:
            src_p = os.path.join(tmp, rel.replace("/", os.sep))
            dst_p = os.path.join(OUT_CORE, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst_p), exist_ok=True)
            shutil.copyfile(src_p, dst_p)
            installed += 1
        print("installed %d class file(s) into %s" % (installed, OUT_CORE))

    # 从安装后的副本校验，而不是从临时副本。
    for rel, markers in (("arc/graphics/gl/GLVersion.class", (MARKER8,)),
                         ("arc/graphics/gl/GLVersion$GlType.class", ()),
                         ("arc/graphics/gl/Shader.class", (MARKER9,))):
        p = os.path.join(OUT_CORE, rel.replace("/", os.sep))
        if not os.path.isfile(p):
            print("FAIL %s was not installed" % rel)
            return 1
        blob = open(p, "rb").read()
        for marker in markers:
            if marker not in blob:
                print("FAIL the installed %s lost %r" % (rel, marker))
                return 1
    print("installed core copies verified")
    return 0


def main():
    # 每个源码都用各自的标记、对照各自的内容来检查。在错误的
    # 文件里找到的标记什么都证明不了，所以这里是配对使用
    # 而不是汇总到一个列表里。
    for path, markers in ((SRC, (MARKER, MARKER2)), (SRC_INPUT, (MARKER3, MARKER4, MARKER7)),
                          (SRC_FILES, (MARKER5, MARKER6))):
        if not os.path.isfile(path):
            print("FAIL missing %s" % path)
            return 1
        src_text = open(path, encoding="utf-8", errors="replace").read()
        for marker in markers:
            name = marker.decode()
            if name not in src_text:
                print("FAIL %s does not contain the change (%s)."
                      % (os.path.basename(path), name))
                print("     Edit it first.")
                return 1
            print("%s carries the change: %s" % (os.path.basename(path), name))

    # 先 arc-core：下面的 SDL3 编译会把 ARCBUILD/core 放进类路径，
    # 所以它必须先存在且是最新的，那次编译才能跑。
    core_rc = build_core()
    if core_rc != 0:
        return core_rc

    jars = [os.path.join(LWJGL, f) for f in sorted(os.listdir(LWJGL))
            if f.endswith(".jar")]
    cp = os.pathsep.join([os.path.join(ARCBUILD, "core"),
                          os.path.join(ARCBUILD, "sdl3")] + jars)

    with tempfile.TemporaryDirectory() as tmp:
        srcs = backend_sources()
        if not srcs:
            print("FAIL no .java under %s" % SRC_ROOT)
            return 1
        print("backend sources = %d" % len(srcs))
        cmd = [JAVAC, "--release", "17", "-nowarn", "-implicit:none",
               "-encoding", "UTF-8",
               "-cp", cp,
               "-sourcepath", os.pathsep.join([SRC_ROOT, CORE_ROOT]),
               "-d", tmp] + srcs
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print("FAIL javac")
            print(r.stdout)
            print(r.stderr)
            return 1
        out = (r.stdout or "") + (r.stderr or "")
        if out.strip():
            print(out)

        # 两个类都从 javac 实际写出的内容读回，并用各自的标记。
        # 每个类都检查字节码主版本 61（Java 17），因为按错误
        # 版本编译的类只会在设备上失败。
        for cls, markers in (("SdlApplication.class", (MARKER, MARKER2)),
                             ("SdlInput.class", (MARKER3, MARKER4, MARKER7)),
                             ("SdlFiles.class", (MARKER5, MARKER6))):
            produced = os.path.join(tmp, "arc", "backend", "sdl", cls)
            if not os.path.isfile(produced):
                print("FAIL javac produced no %s" % cls)
                return 1
            blob = open(produced, "rb").read()
            major = struct.unpack(">H", blob[6:8])[0]
            if major != 61:
                print("FAIL %s bytecode major is %d, the jar's classes are 61"
                      % (cls, major))
                return 1
            for marker in markers:
                if marker not in blob:
                    print("FAIL the compiled %s does not contain %r" % (cls, marker))
                    return 1
            print("compiled: %s major=61, contains %s"
                  % (cls, ", ".join(repr(m.decode()) for m in markers)))

        # 先清理过期的 .class 文件。patch_mindustry.py 会把这个目录
        # 整体打包，所以早先运行残留的、或我们后来删除的
        # 类，会被当成最新的打进去。
        os.makedirs(OUT_SDL3, exist_ok=True)
        removed = 0
        for f in os.listdir(OUT_SDL3):
            if f.endswith(".class"):
                os.remove(os.path.join(OUT_SDL3, f))
                removed += 1
        if removed:
            print("cleared %d stale class file(s) from %s" % (removed, OUT_SDL3))

        compiled = {}
        for dp, _d, fs in os.walk(os.path.join(tmp, "arc", "backend", "sdl")):
            for f in fs:
                if f.endswith(".class"):
                    compiled[f] = os.path.join(dp, f)
        for f, src_p in compiled.items():
            shutil.copyfile(src_p, os.path.join(OUT_SDL3, f))
        print("installed %d class file(s) into %s" % (len(compiled), OUT_SDL3))

        # 该目录被 patch_mindustry.py 整体消费，所以落到那里的
        # 必须恰好是编译出来的内容 -- 没有残留、没有
        # 静默丢失。只看数量抓不住调包。
        landed = set(f for f in os.listdir(OUT_SDL3) if f.endswith(".class"))
        if landed != set(compiled):
            print("FAIL installed set != compiled set")
            print("   extra: %s" % sorted(landed - set(compiled)))
            print("   missing: %s" % sorted(set(compiled) - landed))
            return 1
        print("installed set == compiled set (%d files)" % len(landed))

    # 从安装后的副本校验，而不是从临时副本。
    for name in PRODUCES:
        p = os.path.join(OUT_SDL3, name)
        if not os.path.isfile(p):
            print("FAIL %s was not installed" % name)
            return 1
    for cls, marker in (("SdlApplication.class", MARKER), ("SdlInput.class", MARKER3),  # MARKER7 上面已检查；这次迟到的扫描是第二次独立读取
                        ("SdlFiles.class", MARKER5)):
        installed_blob = open(os.path.join(OUT_SDL3, cls), "rb").read()
        if marker not in installed_blob:
            print("FAIL the installed %s lost the marker" % cls)
            return 1
    print("installed copies verified")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
