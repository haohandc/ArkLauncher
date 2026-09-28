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

# The checkout of Arc's sources that gets compiled from (ARK_ARC_SRC). The three
# classes below are the only Arc files this project modifies.
ARC = config.ARC_SRC
SRC = os.path.join(ARC, "backends", "backend-sdl3", "src",
                   "arc", "backend", "sdl", "SdlApplication.java")
# The touch/pinch patch lives here. Recompiled by the same run, and gated the
# same way -- see MARKER3/MARKER4 and the note about why one marker is not
# enough for a file that gets edited over time.
SRC_INPUT = os.path.join(ARC, "backends", "backend-sdl3", "src",
                         "arc", "backend", "sdl", "SdlInput.java")
# Decouples the file browser's root from the game's data directory, so "import
# save" can open somewhere the player can actually put a file.
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

# The LWJGL jars, needed on the compile class path because Arc's SDL3 backend
# references org.lwjgl.* -- same directory prep_lwjgl.py ships from.
LWJGL = config.LWJGL_SRC
ARCBUILD = os.path.join(config.TMP, "arcbuild")
OUT_SDL3 = os.path.join(ARCBUILD, "sdl3", "arc", "backend", "sdl")

JAVAC = config.JAVAC

# Present in the new code, absent from the old. Checking the compiled class for it
# is what distinguishes "recompiled" from "the previous class files are still
# sitting there".
MARKER = b"arc.sdl.glEs"
# Both properties must be in the compiled class. Checking one would pass while the
# other edit was never picked up, which is the failure this whole script exists to
# prevent -- and they are edited at different times, so "recompiled since the last
# change I remember" is not a safe assumption.
MARKER2 = b"arc.sdl.mobile"

# Present in the new SdlInput code, absent from the old (which ignored
# SDL_EVENT_FINGER_* entirely and answered every pointer query with pointer 0).
# These are field names, so they land in the class constant pool through the
# field references the new methods make.
MARKER3 = b"MAX_TOUCH_POINTERS"
MARKER4 = b"pointerJustDown"
# Added later than the two above, and gated separately for that reason: those two
# were already present in both the source and the previously-shipped class, so
# they cannot tell a rebuilt SdlInput.class from a stale one. This one can -- it
# is a method name introduced by the hover-follows-touch fix, so it exists only in
# a class compiled from the source as it stands now.
MARKER7 = b"syncMouseToFinger"

# Present in the new SdlFiles code, absent from the old (the browser root used
# to be inseparable from the game data path).
MARKER5 = b"arc.sdl.chooserPath"
MARKER6 = b"chooserPath"

# ---------------------------------------------------------------------------
# arc-core: the two classes patched in the core module (not the SDL3 backend).
#
# ⚠️ Added 2026-09-28. Until this change NOTHING in this repository produced
# these three class files -- patch_mindustry.py expects them in arcbuild/core
# and treats that directory as an INPUT, but no script wrote it. The directory
# was populated by hand, once, and then lost; when this was investigated the
# directory was empty and the classes could not be rebuilt at all.
#
# That is the same shape of gap as the un-reproducible libarcarm64.so, except
# this one is fixable: the sources are on disk, and the changes in them are
# real (checked against upstream below).
# ---------------------------------------------------------------------------
SRC_GLVERSION = os.path.join(ARC, "arc-core", "src",
                             "arc", "graphics", "gl", "GLVersion.java")
SRC_SHADER = os.path.join(ARC, "arc-core", "src",
                          "arc", "graphics", "gl", "Shader.java")
OUT_CORE = os.path.join(ARCBUILD, "core")

# Present in the new GLVersion code, absent from the old. The patch adds
#     if(versionString != null && versionString.contains("OpenGL ES")) ...
# against the old first line, which only tested appType == android -- so the
# call it introduces is the marker. It is the String.contains descriptor rather
# than the literal "OpenGL ES" because that literal is already in the upstream
# class (its version parsing uses it), which would make it prove nothing.
MARKER8 = b"(Ljava/lang/CharSequence;)Z"
# Present in the new Shader code, absent from the old: the import of GLVersion
# and the switch from app-type to GL-flavour means Shader.class now REFERENCES
# GLVersion$GlType, which the upstream class does not.
MARKER9 = b"GLVersion$GlType"

# ⚠️ SOURCE markers are a DIFFERENT thing from the class markers above, and this
# is where that distinction had to be made explicit.
#
# The markers above are checked against the COMPILED BYTES. The three SDL3
# markers happen to be string literals, which exist in the source and in the
# bytes alike, so one marker served both gates and the difference never showed.
# MARKER8 is a method descriptor: it is written by javac and appears NOWHERE in
# the source. Feeding it to the source gate fails every time -- which is exactly
# what happened the first time this was run.
#
# So the source gate gets its own markers, taken from the source text of the
# change itself.
SRC_MARK_GLVERSION = b"!= null && versionString.contains"
SRC_MARK_SHADER = b"glType == GlType.GLES"

# GLVersion$GlType carries no behaviour change -- it is recompiled because it
# sits next to GLVersion, not because we edited it. There is therefore no marker
# that could tell our copy from the upstream one, and it is checked for the
# bytecode version alone. Saying so here is the point: a marker would have to be
# invented, and an invented marker on an unchanged class proves nothing.
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

    # Shader.java references org.lwjgl.opengl.*, so the LWJGL jars are needed even
    # though this is the core module.
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

        # Same two-part gate as the backend: bytecode major, then a marker that
        # only the patched source produces. GLVersion$GlType is checked for the
        # major version only -- see the note on CORE_PRODUCES.
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

        # Clear only the three files this step owns. Wiping the directory would
        # also delete anything else a future step puts there, and the whole point
        # of this function is that the directory has an owner now.
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

    # Verify from the installed copy, not from the temporary one.
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
    # Each source is checked for its own markers, against its own contents. A
    # marker found in the wrong file would prove nothing, which is why these are
    # paired up rather than pooled into one list.
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

    # arc-core first: the SDL3 compile below puts ARCBUILD/core on its class path,
    # so it has to exist and be current before that compile runs.
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

        # Both classes are read back from what javac actually wrote, with their
        # own markers. Bytecode major 61 (Java 17) is checked per class, because
        # a class compiled for the wrong release would only fail on the device.
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

        # Clear stale .class files first. patch_mindustry.py takes this directory
        # WHOLE, so a class left behind by an earlier run -- or by a class we have
        # since removed -- would be packed as if it were current.
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

        # The directory is consumed as a whole by patch_mindustry.py, so what
        # lands there has to be exactly what was compiled -- no leftovers, no
        # silent drops. A count alone would not catch a swap.
        landed = set(f for f in os.listdir(OUT_SDL3) if f.endswith(".class"))
        if landed != set(compiled):
            print("FAIL installed set != compiled set")
            print("   extra: %s" % sorted(landed - set(compiled)))
            print("   missing: %s" % sorted(set(compiled) - landed))
            return 1
        print("installed set == compiled set (%d files)" % len(landed))

    # Verify from the installed copy, not from the temporary one.
    for name in PRODUCES:
        p = os.path.join(OUT_SDL3, name)
        if not os.path.isfile(p):
            print("FAIL %s was not installed" % name)
            return 1
    for cls, marker in (("SdlApplication.class", MARKER), ("SdlInput.class", MARKER3),  # MARKER7 checked above; this late pass is a second, independent read
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
