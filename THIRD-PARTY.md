# Third-party components

What this project redistributes, and under what terms.

Each licence below was **read from the upstream repository's own licence file**,
not from memory. Source and date are recorded so the claim can be re-checked.
Retrieved 2026-09-20.

| Component | Licence | Verified from |
|---|---|---|
| Mindustry | **GPL-3.0** | <https://raw.githubusercontent.com/Anuken/Mindustry/master/LICENSE> |
| Arc | **Apache-2.0** | <https://raw.githubusercontent.com/Anuken/Arc/master/LICENSE> |
| SDL3 | **Zlib** | <https://raw.githubusercontent.com/libsdl-org/SDL/main/LICENSE.txt> |
| LWJGL | **BSD-3-Clause** | <https://raw.githubusercontent.com/LWJGL/lwjgl3/master/LICENSE.md> |
| OpenJDK 21 | **GPL-2.0 with Classpath Exception** | <https://raw.githubusercontent.com/openjdk/jdk/master/LICENSE> — GPL v2 text plus an explicit `"CLASSPATH" EXCEPTION TO THE GPL` section |

## Why this project is GPL-3.0

⚠️ **Ark Launcher does not redistribute Mindustry** (2026-10-01): the launcher
ships without a game, and the player supplies their own jar. That removes two of
the three reasons this section used to give — **but it does not change the
licence.** The argument, with the dead parts marked:

- ~~the game jar is packaged into the same artifact as the launcher~~ — **no
  longer true**; this build carries no game jar at all;
- ~~a HAP is a single installable unit, not a directory of independent programs~~
  — still true of the HAP, but there is no longer a second work for it to be
  combined *with*, so the point has nothing to do;
- **the launcher exists to run Mindustry and does nothing else** — unchanged.

⭐ The surviving point is the one that was always doing the real work, and
shipping the game separately does not touch it. This is not a general-purpose
launcher that happens to support Mindustry: its entry class
(`mindustry/desktop/DesktopLauncher`), its class-path shape, its patch jar, its
mod-directory layout and its version readout are all Mindustry's. A work written
specifically to run another work is a derivative of it.

⇒ **This repository stays GPL-3.0.** What changed is the *distribution*
obligation, not the licence — see the Mindustry section below.

Choosing GPL-3.0 deliberately is also the cheapest option: for a project that is
open anyway it costs nothing, and it removes the question entirely.

**Compatibility check.** Every component still shipped permits this combination:

| Component | Compatible with GPL-3.0? |
|---|---|
| Arc (Apache-2.0) | Yes. Apache-2.0 is compatible with GPL-3 — note it is *not* compatible with GPL-2, which is why the version matters |
| SDL3 (Zlib) | Yes, permissive |
| LWJGL (BSD-3) | Yes, permissive |
| OpenJDK 21 (GPL-2 + Classpath Exception) | Yes, **because of the Classpath Exception**, which explicitly permits linking the library with independent modules and distributing the resulting executable under terms of the user's choice |

Two different GPL versions appear in this stack — v3 for Mindustry, v2 for
OpenJDK — and they are not interchangeable. The JDK side only works out because
of the exception.

> This is a reading of the licence texts, not legal advice. The texts were
> fetched and read (sources above) rather than recalled, but if the distinction
> matters commercially, have someone qualified check it.

## Third-party files are not relicensed

The GPL-3.0 above covers this project. It does not relicense the third-party
files vendored inside it:

- `entry/src/main/cpp/SDL/` — Zlib-licensed SDL3, with local modifications.
  Zlib condition 2 requires that altered versions be **plainly marked as such**
  and not misrepresented as the original, so do not describe this tree as plain
  SDL3.
- Vendored Arc sources referenced by `scripts/` — Apache-2.0, unchanged in
  licence by being built against.
- The LWJGL payload — BSD-3-Clause.

Each keeps its own terms; they merely have to be compatible with GPL-3.0, and
they are.

## Obligations that apply to this project

### Mindustry — GPL-3.0

⛔ **Not redistributed. Changed 2026-10-01.** Earlier builds packaged an upstream
release jar at `entry/libs/arm64-v8a/game/mindustry.so` (the `.so` name was a
packaging requirement, not a modification). Ark Launcher ships without it: the
player points the launcher at a jar of their own.

Three things enforce that, so it is a property of the build rather than an
intention:

- `scripts/prep_game.py` now **removes** that path instead of filling it;
- `scripts/verify_hap.py` §6 **fails the build** if a game jar is present in the
  artifact — verified by putting one there on purpose and watching it fail;
- `scripts/make_payload_zip.py` no longer requires it in the payload.

**What that changes.** GPL-3.0 §6 obliges whoever distributes a binary to make
the corresponding source available to its recipients. Distributing no Mindustry
binary means **there is no Mindustry source obligation to discharge** — the old
clause about pointing at upstream has nothing left to attach to.

**What it does not change.** The licence of this repository, which is still
GPL-3.0 (see above), and the attribution and non-affiliation notes at the end.

⚠️ **If a build ever puts the game back, every obligation in this section returns
with it.** That is not a formality: a HAP containing the game *is* a distribution
of it, exactly as before. The path that used to document which parts of the jar
were modified — the `mindustry/**` / `arc/**` table — is in this file's git
history, and it becomes live again the moment the jar does.

**Corresponding source for this project** is still required, and this repository
is it. The build scripts are part of it, because they are what produce the
artifact.

### Arc — Apache-2.0

**Arc's source is modified by this project.** `scripts/build_arc_patch.py`
recompiles three classes from patched sources and `scripts/patch_mindustry.py`
writes them into the jar:

| Class | What was changed |
|---|---|
| `arc/backend/sdl/SdlApplication.java` | GL context profile and mobile-mode flag read from system properties |
| `arc/backend/sdl/SdlInput.java` | Touch pointer handling: finger events, per-pointer state |
| `arc/backend/sdl/SdlFiles.java` | File-browser root separated from the game data path |

Apache-2.0 §4(b) requires modified files to carry prominent notices stating that
they were changed, and §4(a)/(c) require the licence and attribution notices to
be retained. The patch scripts are what actually produce those files, so the
provenance is reproducible even though the compiled classes are what ship.

### SDL3 — Zlib

**SDL3's source is modified by this project** (OpenHarmony input, windowing and
audio paths under `entry/src/main/cpp/SDL/`).

Zlib's conditions require that (1) the origin not be misrepresented, (2) **altered
source versions be plainly marked as such** and not passed off as the original,
and (3) the notice not be removed. Point 2 is the one to keep an eye on: this
repository ships a modified SDL tree, so **do not describe it as plain SDL3**.
The modifications are confined to the OpenHarmony backend directories.

### OpenJDK 21 — GPL-2.0 with Classpath Exception

The embedded runtime is redistributed. The Classpath Exception is what permits
linking and shipping it alongside a work under other terms; without it this
project's combination would be a GPL-2.0 work as a whole.

Note that this is GPL **v2**, unlike Mindustry's v3 — two different GPL versions
are involved here, and they are not interchangeable.

### LWJGL — BSD-3-Clause

Redistributed as jars and natives. Retain the copyright notice, the list of
conditions and the disclaimer, and do not use the "Lightweight Java Game
Library" name to endorse this project.

**Provenance**, because it is not obvious from the files: the LWJGL 3.4.2 set
this project ships was not compiled here. It was taken from a prebuilt
HarmonyOS application that runs this game, which is what makes it a known-good
pair for this platform — the jars and the natives are version-checked against
each other by `prep_lwjgl.py`, and every file is pinned by SHA-1 there. They are
LWJGL's own released binaries; what the other application contributed is the
evidence that they work here, not a modification.

## Not in this repository

Neither the payload nor the inputs it is assembled from are committed (see
`.gitignore`): the Mindustry jar, the JDK, and the LWJGL and Arc natives. They
are supplied by whoever builds the project — `payload-src/README.md` says which
files and where they come from — or shipped as Release assets.

That reduces the size of the repository but does **not** remove any of the
obligations above: **a Release asset is redistribution too**, so a published HAP
or payload zip carries every licence and source obligation listed here exactly as
a clone would. `RELEASE.md` covers what may be published at all.

## Attribution

- Mindustry and Arc, by **Anuken** — <https://github.com/Anuken/Mindustry>,
  <https://github.com/Anuken/Arc>
- SDL3 — <https://github.com/libsdl-org/SDL>
- LWJGL — <https://www.lwjgl.org/>
- OpenJDK — <https://openjdk.org/>

## This project is unofficial

Not affiliated with, endorsed by, or supported by any of the projects above.
"Mindustry" refers to the upstream game and is used only to say what this
launcher runs.
