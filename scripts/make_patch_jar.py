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

# The arc-core half. Same three names patch_mindustry.py lists in SINGLE.
CORE_CLASSES = [
    "arc/graphics/gl/GLVersion.class",
    "arc/graphics/gl/GLVersion$GlType.class",
    "arc/graphics/gl/Shader.class",
]
# The backend half -- a whole directory, because it is a drop-in replacement for
# the SDL2 backend rather than a set of individual edits.
SDK_DIR_SRC = os.path.join(ARCBUILD, "sdl3", "arc", "backend", "sdl")
SDK_DIR_DEST = "arc/backend/sdl/"

# Where the launcher looks for it. Mirrors PATCH_JAR in launcher.c.
OUT_DIR = os.path.join(config.PROJECT_ROOT, "entry", "libs", "arm64-v8a", "patchjar")
OUT_JAR = os.path.join(OUT_DIR, "arcpatch.so")

# The backend is replaced as a WHOLE DIRECTORY, not as a list of edited files --
# patch_mindustry.py's own note says "目录替换（backend-sdl3 整体覆盖 backend-sdl）".
# Ten of the backend's twelve sources are ours (seven modified, three new), and
# a patch containing only the edited ones is not equivalent: our SdlApplication
# reads a field that only our SdlConfig declares, so shipping one without the
# other fails at runtime with NoSuchFieldError. Measured on a device, 2026-09-28.
#
# So the set is whatever build_arc_patch.py compiled into sdl3 -- every class,
# including the ones whose source we never touched but which are recompiled
# because they are in the same module.
SDK_MIN_EXPECTED = 20

# Present in the new code, absent from upstream. Checked here as a last gate so a
# jar built from stale class files cannot be shipped silently -- build_arc_patch
# checks the same markers, but it checks what it compiled, not what we packed.
MARKERS = {
    "arc/graphics/gl/GLVersion.class": [b"(Ljava/lang/CharSequence;)Z"],
    "arc/graphics/gl/Shader.class": [b"GLVersion$GlType"],
    "arc/backend/sdl/SdlApplication.class": [b"arc.sdl.glEs", b"arc.sdl.mobile"],
    "arc/backend/sdl/SdlInput.class": [b"MAX_TOUCH_POINTERS", b"pointerJustDown",
                                       b"syncMouseToFinger"],
    "arc/backend/sdl/SdlFiles.class": [b"arc.sdl.chooserPath", b"chooserPath"],
    # Added 2026-09-28 after the device build that failed on exactly this class:
    # our SdlApplication reads config.appName, and only OUR SdlConfig declares it.
    # Upstream's SdlConfig has no such field, so the name is a marker.
    "arc/backend/sdl/SdlConfig.class": [b"appName"],
    # Three classes exist in our backend and not in upstream's at all, so their
    # presence in the jar is itself the check -- there is no marker to look for.
    # Named here so the omission is a decision rather than an oversight.
    #   arc/backend/sdl/GLBootstrap.class
    #   arc/backend/sdl/GLDiag.class
    #   arc/backend/sdl/GLDispatchFix.class
}
# Classes that must be in the jar but carry no marker of their own.
MUST_EXIST = [
    "arc/backend/sdl/GLBootstrap.class",
    "arc/backend/sdl/GLDiag.class",
    "arc/backend/sdl/GLDispatchFix.class",
]

# Java 17. The game jar's classes are major 61 and the embedded JVM is 21, so
# anything else here is a build accident rather than a preference.
WANT_MAJOR = 61

# Fixed, so the same inputs give the same jar. 1980-01-01 is the earliest a DOS
# timestamp can express and is what reproducible-build tooling conventionally uses.
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
    # A floor, not an equality: the number moves when Arc gains or loses a class,
    # and pinning it exactly would make a legitimate upstream change look like a
    # build failure. What it catches is the failure that actually happened -- a
    # directory that had been narrowed down to three edited files.
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

    # Gate 1: every class is Java 17 bytecode. A class compiled for the wrong
    # release only fails on the device, and it fails as a version error that says
    # nothing about which step produced it.
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

    # Gate 2: the markers. This is what separates "built from the patched sources"
    # from "built from whatever was on disk".
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

    # Gate 3: the classes that exist only in our backend. A marker check cannot
    # cover these -- they are new, so there is nothing to compare against.
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
    # Write to a temporary name and move into place, so a failure part-way cannot
    # leave a truncated jar where the launcher will find it.
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

    # Read the jar back and check what actually landed, rather than trusting the
    # write. Same reason verify_hap.py re-reads the HAP.
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
