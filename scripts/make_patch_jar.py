# -*- coding: utf-8 -*-
r"""Package our patched Arc classes into a jar the launcher puts FIRST on the class path.

WHY THIS EXISTS
    Until now our Arc changes were applied by rewriting the game jar in place
    (patch_mindustry.py). That works, but it means every upstream release has to
    be re-opened and re-written, and it leaves no way to tell "our classes" from
    "upstream's" once the jar is built.

    Measured 2026-09-28: a jar placed ahead of the game jar on -Djava.class.path
    shadows same-named classes in it. That was verified on the device, not just
    on a desktop JVM -- an arc/util/Log stand-in in the leading jar is what the
    game actually loaded (NoSuchFieldError for a member only the real Log has).

    So the patch becomes a separate artifact and the game jar stays pristine.

WHAT GOES IN
    Exactly the classes build_arc_patch.py compiled, and nothing else:

        arc/graphics/gl/GLVersion.class          from arcbuild/core
        arc/graphics/gl/GLVersion$GlType.class   from arcbuild/core
        arc/graphics/gl/Shader.class             from arcbuild/core
        arc/backend/sdl/*.class                  from arcbuild/sdl3

    The list is not written out by hand. It is derived from the same two sources
    patch_mindustry.py uses, so the two cannot drift apart.

WHY THE FILE IS NAMED .so
    hvigor only copies names ending in ".so" from entry/libs/ into the HAP, and
    the content is never inspected. The game jar itself ships as
    libs/arm64-v8a/game/mindustry.so for the same reason. A jar is not an ELF
    either, so it takes the same road.

DETERMINISM
    Entry timestamps are fixed, so the same inputs produce the same bytes. This
    project has twice shipped an artifact that was not the one it thought it was,
    and a hash that moves on every run cannot be used as an anchor.

Usage:  python make_patch_jar.py [--check]
        --check  report what would be packed and verify the inputs; write nothing
"""

import argparse
import hashlib
import os
import struct
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

ARCBUILD = os.path.join(config.TMP, "arcbuild")

# arc-core 这一半。就是 patch_mindustry.py 在 SINGLE 里列的那三个名字。
CORE_CLASSES = [
    "arc/graphics/gl/GLVersion.class",
    "arc/graphics/gl/GLVersion$GlType.class",
    "arc/graphics/gl/Shader.class",
]
# backend 这一半 —— 整个目录，因为它是 SDL2 backend 的即插即用替代品，
# 而不是一组零散的改动。
SDK_DIR_SRC = os.path.join(ARCBUILD, "sdl3", "arc", "backend", "sdl")
SDK_DIR_DEST = "arc/backend/sdl/"

# 启动器查找它的位置。与 launcher.c 里的 PATCH_JAR 保持一致。
OUT_DIR = os.path.join(config.PROJECT_ROOT, "entry", "libs", "arm64-v8a", "patchjar")
OUT_JAR = os.path.join(OUT_DIR, "arcpatch.so")

# backend 是作为【整个目录】被替换的，而不是一份被改文件的清单 ——
# patch_mindustry.py 自己的注释就写着 "目录替换（backend-sdl3 整体覆盖 backend-sdl）"。
# backend 十二个源文件里有十个是我们的（七个改动，三个新增），
# 只包含被改文件的补丁并不等价：我们的 SdlApplication 会读一个
# 只有我们的 SdlConfig 声明的字段，所以只发其中一个、不发另一个
# 会在运行时抛 NoSuchFieldError。2026-09-28 在真机上实测。
#
# 所以集合就是 build_arc_patch.py 编译进 sdl3 的全部内容 —— 每一个类，
# 包括那些我们从未碰过源码、
# 但因为同属一个模块而被重新编译的类。
SDK_MIN_EXPECTED = 20

# 新代码里有、上游没有。这里作为最后一道关卡检查，防止用过期 class 文件
# 构建出的 jar 被悄悄发出去 —— build_arc_patch
# 也查同样的标记，但它查的是自己编译出来的东西，不是我们打包的东西。
MARKERS = {
    "arc/graphics/gl/GLVersion.class": [b"(Ljava/lang/CharSequence;)Z"],
    "arc/graphics/gl/Shader.class": [b"GLVersion$GlType"],
    "arc/backend/sdl/SdlApplication.class": [b"arc.sdl.glEs", b"arc.sdl.mobile"],
    "arc/backend/sdl/SdlInput.class": [b"MAX_TOUCH_POINTERS", b"pointerJustDown",
                                       b"syncMouseToFinger"],
    "arc/backend/sdl/SdlFiles.class": [b"arc.sdl.chooserPath", b"chooserPath"],
    # 2026-09-28 加入：真机构建正好在这个类上失败 ——
    # 我们的 SdlApplication 会读 config.appName，而只有【我们的】SdlConfig 声明了它。
    # 上游的 SdlConfig 没有这个字段，所以这个名字本身就是标记。
    "arc/backend/sdl/SdlConfig.class": [b"appName"],
    # 有三个类只存在于我们的 backend、上游完全没有，所以它们
    # 出现在 jar 里本身就是检查 —— 没有标记可查。
    # 在这里点名，是为了让"不查"是个决定，而不是疏忽。
    #   arc/backend/sdl/GLBootstrap.class
    #   arc/backend/sdl/GLDiag.class
    #   arc/backend/sdl/GLDispatchFix.class
}
# 必须出现在 jar 里、但自身不带任何标记的类。
MUST_EXIST = [
    "arc/backend/sdl/GLBootstrap.class",
    "arc/backend/sdl/GLDiag.class",
    "arc/backend/sdl/GLDispatchFix.class",
]

# Java 17。游戏 jar 的类 major 是 61，内嵌 JVM 是 21，所以
# 这里出现别的值只能是构建事故，而不是偏好。
WANT_MAJOR = 61

# 固定值，让同样的输入产出同样的 jar。1980-01-01 是 DOS 时间戳能表达的
# 最早时间，也是可复现构建工具惯用的取值。
FIXED_DATE = (1980, 1, 1, 0, 0, 0)


def collect():
    """Return {entry_name: absolute_source_path}, or raise with what is missing."""
    out = {}
    for rel in CORE_CLASSES:
        src = os.path.join(ARCBUILD, "core", rel.replace("/", os.sep))
        if not os.path.isfile(src):
            raise SystemExit("缺少文件: %s（先跑 build_arc_patch.py）" % src)
        out[rel] = src
    if not os.path.isdir(SDK_DIR_SRC):
        raise SystemExit("缺少目录: %s（先跑 build_arc_patch.py）" % SDK_DIR_SRC)
    n = 0
    for fn in sorted(os.listdir(SDK_DIR_SRC)):
        if fn.endswith(".class"):
            out[SDK_DIR_DEST + fn] = os.path.join(SDK_DIR_SRC, fn)
            n += 1
    if n == 0:
        raise SystemExit("目录里没有 .class: %s" % SDK_DIR_SRC)
    # 这是下限，不是相等判定：Arc 增删类时这个数字会变，
    # 把它钉死会把一次正常的上游变更显得像构建失败。
    # 它真正要抓的是实际发生过的那次失败 ——
    # 一个被压缩成三个改动文件的目录。
    if n < SDK_MIN_EXPECTED:
        raise SystemExit("只找到 %d 个 backend 类，少于 %d —— 目录像是被截断了。"
                         "backend-sdl3 是【整个】被替换的，先跑 build_arc_patch.py"
                         % (n, SDK_MIN_EXPECTED))
    return out


def sha1_of(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report only; write nothing")
    args = ap.parse_args()

    entries = collect()
    print("要打包的类 = %d 个" % len(entries))

    # 关卡 1：每个类都是 Java 17 字节码。编译到错误 release 的类
    # 只会在真机上失败，而且报出来的是一个版本错误，
    # 完全看不出是哪个步骤产生的。
    bad = []
    for name in sorted(entries):
        blob = open(entries[name], "rb").read()
        if len(blob) < 8 or blob[:4] != b"\xca\xfe\xba\xbe":
            bad.append("%s 不是 class 文件" % name)
            continue
        major = struct.unpack(">H", blob[6:8])[0]
        if major != WANT_MAJOR:
            bad.append("%s 的字节码 major 是 %d，应为 %d" % (name, major, WANT_MAJOR))
    if bad:
        print("FAIL:")
        for b in bad:
            print("   " + b)
        return 1
    print("字节码版本：全部 major=%d OK" % WANT_MAJOR)

    # 关卡 2：标记。这是用来区分"从打过补丁的源码构建"和
    # "从磁盘上随便什么东西构建"的。
    for name, markers in MARKERS.items():
        if name not in entries:
            print("FAIL 标记清单里的 %s 不在要打包的集合中" % name)
            return 1
        blob = open(entries[name], "rb").read()
        for m in markers:
            if m not in blob:
                print("FAIL %s 里没有 %r" % (name, m))
                return 1
    print("改动标记：%d 个类逐个命中 OK" % len(MARKERS))

    # 关卡 3：只存在于我们 backend 的类。标记检查覆盖不到这些 ——
    # 它们是新增的，没有可比对的东西。
    for name in MUST_EXIST:
        if name not in entries:
            print("FAIL %s 不在要打包的集合中（我们的 backend 应该比上游多这三个类）" % name)
            return 1
    print("新增类：%d 个都在 OK" % len(MUST_EXIST))

    if args.check:
        print()
        for name in sorted(entries):
            print("   %-46s %8d B  %s" % (name, os.path.getsize(entries[name]),
                                          sha1_of(entries[name])[:12]))
        print()
        print("--check：未写文件")
        return 0

    os.makedirs(OUT_DIR, exist_ok=True)
    # 先写到临时名字再移到位，这样中途失败不会留下一个被截断的 jar
    # 躺在启动器能找到的地方。
    tmp_jar = OUT_JAR + ".tmp"
    if os.path.exists(tmp_jar):
        os.remove(tmp_jar)
    with zipfile.ZipFile(tmp_jar, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(entries):
            zi = zipfile.ZipInfo(name, date_time=FIXED_DATE)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with open(entries[name], "rb") as f:
                z.writestr(zi, f.read())

    # 把 jar 读回来、检查实际落盘的内容，而不是相信写入成功。
    # 与 verify_hap.py 重新读取 HAP 是同样的理由。
    with zipfile.ZipFile(tmp_jar) as z:
        got = sorted(z.namelist())
    want = sorted(entries)
    if got != want:
        print("FAIL 包内条目与预期不符")
        print("   多出: %s" % sorted(set(got) - set(want)))
        print("   缺少: %s" % sorted(set(want) - set(got)))
        os.remove(tmp_jar)
        return 1
    with zipfile.ZipFile(tmp_jar) as z:
        for name, markers in MARKERS.items():
            blob = z.read(name)
            for m in markers:
                if m not in blob:
                    print("FAIL 包内 %s 丢了标记 %r" % (name, m))
                    os.remove(tmp_jar)
                    return 1

    os.replace(tmp_jar, OUT_JAR)
    size = os.path.getsize(OUT_JAR)
    print()
    print("输出   = %s" % OUT_JAR)
    print("条目   = %d" % len(want))
    print("字节   = %d" % size)
    print("sha1   = %s" % sha1_of(OUT_JAR))
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
