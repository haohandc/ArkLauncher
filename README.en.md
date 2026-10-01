# Ark Launcher

**English** | [简体中文](README.md)

⭐ **The upstream repository is [Mindustry Ark](https://github.com/haohandc/MindustryArk).**
Ark Launcher is a fork of it — **what is left after the game was taken out: a launcher, and nothing else.**

Mindustry Ark runs **Mindustry** on **HarmonyOS / OpenHarmony** with a self-built launcher:
it embeds a JDK, creates a JVM from native code, and hands the game a real SDL3 window,
without wrapping any existing emulation layer.
**Ark Launcher keeps all of that and simply does not ship the game.**

> **Unofficial.** Not affiliated with, endorsed by, or supported by the Mindustry
> project or Anuken. See [THIRD-PARTY.md](THIRD-PARTY.md).

---

## What differs from upstream

**Two things.**

### ① It does not bundle the game ⭐ this is the whole point

| | [Mindustry Ark](https://github.com/haohandc/MindustryArk) | **Ark Launcher** |
|---|---|---|
| Game jar in the package | `libs/arm64-v8a/game/mindustry.so` (measured: **84.8 MB**) | ⛔ **none** |
| Where the game comes from | shipped with the package | **the player supplies it** |
| Artifact size | **262.4 MB** | **177.7 MB** |
| First launch after a fresh install | straight into the game | **the launcher screen, waiting for you to add a jar** |

⭐ **Both sizes are measured unsigned HAPs** — same source tree, `product=default`, `buildMode=debug`.

⚠️ **The difference, 84.7 MB, equals the game jar's 84.8 MB** — what went away is the game,
not something else that got trimmed along with it.
(Upstream `v1.1.0.1` and Ark Launcher `v2.0.0.1`, each from its own
`entry/build/default/outputs/default/`.)

⇒ ⚠️ **The first launch stops at the launcher screen**, because at that moment there is no jar at all.
That is by design, not a fault: put Mindustry's `.jar` into the folder the screen shows you →
tap **Rescan** → select it → tap **Launch Game**.

⭐ **Three places hold this line, so it is not a promise:**

| Where | What it does |
|---|---|
| `scripts/prep_game.py` | Its job is now **inverted**: from "copy the game in" to "**make sure no game is there**". `--check` fails if one is |
| `scripts/verify_hap.py` §6 | A game jar **present** in the artifact ⇒ exit code 1 ⇒ the build aborts. ⭐ **Negative control run**: a dummy jar was planted in the real artifact, giving `RESULT: FAIL` / exit **1** |
| `scripts/make_payload_zip.py` | The payload zip no longer requires it |

⚠️ **`entry/libs/` is gitignored.** A leftover from an old build gets packed **silently** —
hvigor copies anything ending in `.so` and never looks inside. That is exactly why the first
item above is a script and not a note to remember.

### ② It was renamed

| | Mindustry Ark | **Ark Launcher** |
|---|---|---|
| App name | Mindustry Ark | **Ark Launcher** |
| Bundle name | `com.haohandc.mindustryark` | **`com.haohandc.arklauncher`** |
| App icon | the turret on a grey armoured plate, four bolts | **the turret on its own** |

⭐ **The version number is deliberately not in that table — it is not a difference.**
Ark Launcher only subtracts and adds no features of its own, so **its version tracks upstream's,
and the two stay on the same number**: upstream bumps, this follows.
(Right now upstream is `1.1.0.1` and this repository is `2.0.0.1`; upstream is going to the
same number.)

⚠️ **A different bundle name means a different sandbox — saves, mods and settings are
【not shared】.** The two apps can sit side by side on one device, fully independent.

### Everything else is the same

Including the jar picker itself — ⚠️ **upstream has that too** (upstream commit `b4f1a2b`).
Ark Launcher's difference is **that the game is gone**, not that a feature was added.

---

## Getting started

**You need to supply a Mindustry `.jar` yourself.**

- The upstream official release will do — the launcher **makes no version judgement**, it just
  puts the jar on the class path
- [upstream docs] Upstream `1.1.0.1` embeds exactly this: **`v8 Build 160.5`**
  (upstream `RELEASE.md:16`)
- [measurement, upstream] `docs/BUILDING.md:58`: **the same patch jar drives both `160.4`
  and `160.5`**
- [measured] The jar currently in upstream's working tree calls itself
  `number=8` / `build=160.5` / `type=official`
- ⚠️ But all of the above was run **on upstream**. **Ark Launcher's own
  "add a jar → launch" path has not been tested** — see "Unverified" below

Once installed:

1. Open the app → you land on the launcher screen
2. The screen shows a folder path (under Downloads, in this app's own directory)
3. Using any file manager, copy your `.jar` into that folder
4. Back in the app, tap **Rescan** → it appears in the list → select it
5. Tap **Launch Game**

⭐ **On a fresh install the very first launch lists your jars correctly** — that was measured
(see "Unverified"). 📌 It did not on earlier builds: the first launch reported that the folder
had not been read yet, and one restart cleared it. The cause was the folder being created later
than the screen read it. **Fixed.**

⚠️ **Your jars do not disappear when the app is reinstalled.** [measured] After an uninstall and
reinstall, both jars in that folder were **still there, with their original timestamps** —
reinstalling wipes the **app's own data**, not the folder under Downloads.

After that, every launch goes straight into the game. To switch jars: **floating ball →「Launcher」**.

⚠️ **There is also a「Try launching anyway」button.** It is an escape hatch: should the
detection go wrong on some device, it lets you bypass it and get into the game rather than
being locked out of it forever.

---

## Devices and requirements

⭐ **What can run it**: **HarmonyOS 7 / API 26 or later**, a **tablet or a phone**;
install it self-signed and it runs at full speed either way.

Full speed depends on the app getting anonymous executable memory. From API 26 the system
supplies the relevant ACL to a **debug** profile automatically — on a phone as well as a
tablet — which is also **why there is no phone package in the store**: a store (**release**)
signature never gets it.
⚠️ **HarmonyOS 5 / 6** have no automatic grant; a self-signed install there is **untested**.

⚠️ The device support above was verified **upstream**
(HUAWEI MatePad Pro 12.2" 2025 tablet, HUAWEI Mate 80 Pro phone).
**Ark Launcher's "no game" path itself has not been run on a device** — see below.

---

## Once the game is running

All of the following are **upstream-verified** runtime behaviour, inherited unchanged
(it is the same launcher and the same jar):

| Area | State |
|---|---|
| JVM startup | Works — the launcher **must** pass `-XX:UseSVE=0`. Without it the JIT emits SVE instructions this device cannot execute and the process dies with SIGILL |
| Graphics | OpenGL ES via SDL3 |
| Audio | OHAudio, through a self-built `libarcarm64.so` with an SDL3 backend |
| Touch | Works, including two-finger pinch zoom |
| Keyboard | Works (physical keyboard; WASD and ESC). Typing into game text fields uses an on-screen field with full input-method support |
| Gamepad / mouse | Mouse works. Gamepad untested |
| Save import/export | Via the app's folder in Downloads |
| Mods | Import them with the **game's own "import mod" button** — the only way in, and it needs no restart |
| Desktop/mobile mode switch | Switches, but needs an app restart |
| Networking / multiplayer | **The platform side works** — `socket`, `epoll`, DNS, TCP, TLS and HTTP all measured working. **LAN, public-server search and hosting on the device have each been tested.** ⚠️ **But a full multiplayer match has not been played through** |

The full list, with the evidence behind each line, is in [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

### ⚠️ Unverified

- ⚠️ **The "no game" path has only been walked as far as *listing the jars*.** [measured]
  Fresh install → launcher screen → add a jar → **restart, and both jars are listed correctly.**
  Those four steps work. **The last step is missing: select a jar → tap Launch Game → the game
  actually starts.** That takes two taps.
- ✅ **That first-launch race is fixed, and the fix was measured.** It used to work like this:
  the folder you drop jars into is created by `ensureModFolder()`, which is **async** (a mkdir,
  or a picker that waits for a person); `decideStartup()` then runs **synchronously** and flips
  the UI to the launcher, whose own `aboutToAppear` reads **the state file that folder writes**
  (`gameJarDir` → `readModFolder`) synchronously too — so it read something that did not exist yet.
  ⚠️ **This path could not be reached before** (a game always shipped, so the decision never
  landed on the launcher screen) — **the excision is what exposed it.**
  ⇒ The fix: `Index.ets` gained `folderSettled`, set at the **end** of `ensureModFolder()`'s
  `.then()`, passed down as `@Prop @Watch` so the launcher screen re-reads once.
  ⭐ **[measured] Fresh install, first launch, nothing tapped → both jars listed correctly.**
  ⚠️ A blocking wait was deliberately refused: on the picker route the answer may never come,
  and the screen would then never appear. This project has paid for a gate with no way out.
- ✅ **A "worse case" this project was worried about did not happen.** It had recorded that the
  platform may refuse to create a directory under Downloads (`EPERM` on tablets). **This
  measurement found that route working** — the folder was created on the very first launch
  (the state file is 61 bytes, a path line and nothing else). That record is out of date, at
  least for this device and this build.

---

## How to download and install

⚠️ **This repository currently has no Releases artifacts.** Build from source, or use
what [upstream](https://github.com/haohandc/MindustryArk/releases) publishes.

A built HAP is **unsigned** and will not install. Two ways around that:

**① An installer tool (no dev environment needed, recommended)**

| Tool | What it does |
|---|---|
| [小白调试助手 (Auto-Installer)](https://github.com/likuai2010/auto-installer/releases/latest) | Free cross-platform HarmonyOS debugging tool — **signing and installing in one step** |
| [HoKit](https://github.com/yabi-zzh/HoKit/releases/latest) | **One-click re-signing**, device mirroring, perf monitoring, file management. Windows / macOS / Linux |

**② Sign it yourself with DevEco Studio**

Open the project, **File → Project Structure → Signing Configs → Automatically
generate signature**, then `bash deploy.sh`.

More detail, including what must **not** be published, is in [RELEASE.md](RELEASE.md).

---

## Building from source

```bash
# 1) Unpack the payload (JDK / LWJGL / Arc natives / patch jar) into entry/libs/
unzip -o ArkLauncher-<version>-payload.zip

# 2) The important step: make sure no game is in there
python scripts/prep_game.py --check    # fails if a leftover is present
python scripts/prep_game.py            # removes it

# 3) Build
bash build.sh assembleHap --mode module -p product=default -p buildMode=debug --no-daemon
```

⚠️ Step 2 is not optional: **the payload zip carries the game jar** (it was made for upstream),
so a build straight from it is stopped by `verify_hap.py`. That gate is the point — see
"What differs from upstream" above.

---

## Documentation

**The files under `docs/` are bilingual — Chinese section first, then English, in the same file.**

⚠️ **Most of them are inherited from upstream** and still describe the "complete" app that
ships the game. Wherever they mention "the bundled game" or "the embedded Mindustry", that is
**not true of Ark Launcher** — this README takes precedence.

| Document | Open it when |
|---|---|
| **[docs/FAQ.md](docs/FAQ.md)** | You have a specific question — start here |
| **[docs/LIMITATIONS.md](docs/LIMITATIONS.md)** | Before reporting a bug: is this known? |
| **[docs/BUILDING.md](docs/BUILDING.md)** | You want to build it from source |
| **[docs/PERMISSIONS.md](docs/PERMISSIONS.md)** | You want to know what it asks for |
| **[PRIVACY.md](PRIVACY.md)** | You want to know what data it collects (answer: none) |
| **[docs/LAYOUT.md](docs/LAYOUT.md)** | You just cloned it and can't find things |
| [RELEASE.md](RELEASE.md) | You downloaded a build: which file, how to install, what's verified |
| [RELEASE-MAINTENANCE.md](RELEASE-MAINTENANCE.md) | You're cutting a release |
| [THIRD-PARTY.md](THIRD-PARTY.md) | You're auditing licences |
| [payload-src/README.md](payload-src/README.md) | You're assembling the build's inputs |

---

## Licence

**GPL-3.0** — see [LICENSE](LICENSE).

Copyright (C) 2026 Haohandc and contributors.

⭐ **The licence comes from upstream.** This family of projects is a derivative work of
Mindustry — the launcher exists in order to run it, and its entry point, class-path shape and
patch jar are all Mindustry's — so the whole thing is **GPL-3.0**.

⚠️ **But Ark Launcher no longer distributes Mindustry itself**, so GPL-3.0 §6's
"provide the corresponding source alongside the binary" obligation has **nothing to attach to**
on the Mindustry half. This project's own source still has to travel with its releases —
this repository is it.
The full argument is in [THIRD-PARTY.md](THIRD-PARTY.md).

**Note in particular**: derivative works must also be distributed under GPL-3.0, so
this **cannot** be used as the basis of a closed-source product.

---

## Credits

- [**Mindustry Ark**](https://github.com/haohandc/MindustryArk) — ⭐ **this project's upstream**;
  the entire launcher, the platform work and the documentation come from it
- [**Mindustry**](https://github.com/Anuken/Mindustry) — by Anuken, the game.
  ⛔ **Not distributed by this repository**, but this launcher exists in order to run it
- [**Arc**](https://github.com/Anuken/Arc) — by Anuken, the game framework; the platform patches
  ship **in a separate jar**, not written into the game
- [**SDL3**](https://github.com/libsdl-org/SDL) — the windowing / input / audio layer
- [**LWJGL**](https://github.com/LWJGL/lwjgl3) — the JNI bindings for OpenGL and SDL
- [**OpenJDK 21**](https://github.com/openjdk/jdk) — the runtime

Licensing and redistribution terms for each are in [THIRD-PARTY.md](THIRD-PARTY.md).

Most of the code, phrases and documents in this repository were written with AI assistance
(Claude via Cherry Studio, model deepseek-flash v4.1).
