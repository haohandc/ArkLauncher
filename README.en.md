# Ark Launcher

**English** | [简体中文](README.md)

⭐ **The upstream repository is [Mindustry Ark](https://github.com/haohandc/MindustryArk).**
Ark Launcher is a fork of it — **what is left after the game was taken out.**

> **Unofficial.** Not affiliated with, endorsed by, or supported by the Mindustry
> project or Anuken. See [THIRD-PARTY.md](THIRD-PARTY.md).

---

## What differs from upstream: two things

### ① The package carries no game

| | [Mindustry Ark](https://github.com/haohandc/MindustryArk) | **Ark Launcher** |
|---|---|---|
| Game jar in the package | `libs/arm64-v8a/game/mindustry.so` (84.8 MB) | **none** |
| Where the game comes from | shipped with the package | **the player supplies it** |
| Artifact size | 262.4 MB | **177.7 MB** |

⇒ **The first launch stops at the launcher screen**, because at that moment there is no jar at
all. Put Mindustry's `.jar` into the folder the screen shows you, pull the list down to refresh,
select it, then tap Launch Game.

⭐ **Three places hold this line, so it is not a promise:**

| Where | What it does |
|---|---|
| `scripts/prep_game.py` | Its job is now **inverted**: from "copy the game in" to "**make sure no game is there**" |
| `scripts/verify_hap.py` §6 | A game jar **present** in the artifact ⇒ exit code 1 ⇒ the build aborts |
| `scripts/make_payload_zip.py` | The payload zip no longer requires it |

### ② It was renamed

| | Mindustry Ark | **Ark Launcher** |
|---|---|---|
| App name | Mindustry Ark | **Ark Launcher** |
| Bundle name | `com.haohandc.mindustryark` | **`com.haohandc.arklauncher`** |
| App icon | the turret on a grey armoured plate | **the turret on its own** |

⚠️ **A different bundle name means a different sandbox — saves, mods and settings are not
shared.** The two apps can sit side by side on one device.

⭐ **The version number is deliberately not in that table** — it is not a difference. Ark
Launcher only subtracts and adds no features of its own, so **its version tracks upstream's and
the two stay on the same number** (both are `1.2.0.1` now).

**Everything else is the same**, including the jar picker itself — upstream has that too.
Ark Launcher's difference is **that the game is gone**, not that a feature was added.

---

## For everything else, read upstream's README

Usage, device requirements, known limitations, how to build, licence and credits — **all of it
is taken from upstream**, and the two run the same code:

⭐ **[Mindustry Ark's README (English)](https://github.com/haohandc/MindustryArk/blob/master/README.en.md)**
⭐ **[Mindustry Ark's README (中文)](https://github.com/haohandc/MindustryArk#readme)**

⚠️ **One exception**: wherever upstream's README mentions "the bundled game" or "the embedded
Mindustry", that is **not true here** — this page's "What differs" section takes precedence.

---

## Licence

**GPL-3.0** — see [LICENSE](LICENSE). Copyright (C) 2026 Haohandc and contributors.

⭐ **The licence comes from upstream**: this family of projects is a derivative work of
Mindustry, so the whole thing is GPL-3.0.
⚠️ **But this repository distributes no copy of Mindustry itself**, so GPL-3.0 §6's obligation
has nothing to attach to on that half. The full argument is in [THIRD-PARTY.md](THIRD-PARTY.md).
