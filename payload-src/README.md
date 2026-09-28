# payload-src — the build's inputs

Everything the `prep_*.py` scripts consume lives here. **Nothing in this
directory is committed** (see `.gitignore`), because all of it is either large,
reproducible, or both. This file is committed: it is the list of what has to be
present, and the hashes each file must have.

Two directories in this repository start with `payload` and they are not the
same thing:

| Directory | What | Committed |
|---|---|---|
| `payload-src/` (here) | The **inputs**: jars, JDK pieces, LWJGL set | no |
| `entry/libs/` | The **output**: what the scripts assemble and hvigor packs | no |

`scripts/config.py` is what points the scripts at this directory, and every path
below can be pointed somewhere else instead — see the `ARK_*` variables in that
file. Run `python scripts/config.py` to print the resolved paths and whether
each one is present.

## What goes here

```
payload-src/
├── Mindustry.jar                 the upstream release jar, unmodified  <- SHIPPED AS-IS
├── Mindustry-160.4.jar           the previous upstream release, kept for reference
├── mindustry-1.0.jar             DERIVED (retired): upstream + Arc patches
├── mindustry-1.0-audio.jar       DERIVED: the upstream natives + OURS   <- read for the natives
├── lwjgl-ohos/
│   ├── lwjgl.jar                 LWJGL 3.4.2 Java half
│   ├── lwjgl-opengl.jar
│   ├── lwjgl-sdl.jar
│   ├── liblwjgl.so               LWJGL 3.4.2 native half
│   └── liblwjgl_opengl.so
└── jdk21slim/
    └── lib/
        ├── libcxxabi_shim.so     shipped as-is; verify_hap.py pins its SHA-1
        └── server/libjvm.so      the JVM that gets patched and shipped
```

The three `mindustry-*.jar` files are **derived**, so you do not need to supply
them: drop `Mindustry.jar` in and run the chain in `README.md`. They live here
rather than in a scratch directory so that the chain — patch, repack, variant —
can be re-run in place without anything being copied by hand between stages.

`jdk21slim` is the one thing here that is neither upstream nor reproducible from
this repository: it is an OpenJDK 21 build for OpenHarmony (musl / aarch64)
whose `lib/` and `conf/` have been trimmed to a runtime. A desktop JDK will not
do. It travels in the payload release.

## Where each file comes from

| File | Source |
|---|---|
| `Mindustry.jar` | ⭐ **The official release, and the file that ships.** Download `Mindustry.jar` from the upstream GitHub releases; `prep_game.py` pins it by SHA-1, so a wrong build is refused rather than packed |
| `lwjgl-ohos/` | LWJGL 3.4.2 for this platform. The copy used here was collected from a prebuilt HarmonyOS application that runs this game, which makes it a known-good set — but any 3.4.2 pair will do, and `prep_lwjgl.py` refuses to mix versions |
| `jdk21slim/` | The payload release (see `RELEASE.md`) |
| `mindustry-1.0.jar` | **retired** — the upstream jar with our Arc classes written into it. Nothing reads it any more |
| `mindustry-1.0-audio.jar` | The jar that carries **our** Arc natives. `prep_arc.py` extracts them from it into the bundle. ⚠️ **Not the shipped game jar** — see the naming note below |

### ⚠️ Two jars used to be called `Mindustry.jar` and `GAME_JAR`, and that was wrong

Until 2026-09-29 `config.GAME_JAR` pointed at `mindustry-1.0-audio.jar` while
`config.UPSTREAM_JAR` pointed at `Mindustry.jar`, and the first of those reads as
"the game jar" when it is not: what ships in the game slot is `Mindustry.jar`.
The one that carries our natives has been renamed `NATIVES_JAR`, and it is a
different file. Changing where it points would put upstream's audio-less
`libarcarm64.so` into the bundle.

## Why the hashes matter

Every script checks its input's SHA-1 before writing anything, and
`verify_hap.py` re-checks the result inside the built package. This is not
ceremony: this project has twice shipped an artifact that was not the one it
thought it was — once by re-running an upstream stage and forgetting a
downstream one, once by reusing a stale library — and in both cases the build
reported success.

⭐ Since 2026-09-29 the anchor is an **upstream** artifact rather than our own
multi-stage output, which makes it a stronger statement than it used to be. It
appears in two places that must be changed together:

- `scripts/prep_game.py` — `SRC_SHA1`
- `scripts/verify_hap.py` — `WANT_GAME`

`prep_game.py` fails loudly if they disagree. A version bump means changing both,
plus this file.

## What does NOT need to be here

`entry/libs/arm64-v8a/jdk21/conf/`, `jdk21/lib/classlist`, `jdk21/lib/jfr/` and
`jdk21/lib/jexec` are not inputs — they are part of the JDK tree that gets
copied to `entry/libs/`, and hvigor drops them during packaging because their
names do not end in `.so`. None of them is read by `libjvm` at runtime; the two
files that *are* opened by name are handled explicitly by `prep_jdklib.py`.
