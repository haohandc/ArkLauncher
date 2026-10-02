# Ark Launcher

**English** | [简体中文](README.md)

> [!IMPORTANT]
> **This repository is archived and read-only. Development moved to the
> [`lite` branch of `MindustryArk`](https://github.com/haohandc/MindustryArk/tree/lite).**
>
> Why: Ark Launcher and Mindustry Ark differ in **exactly one thing — whether the
> package carries the game** — and keeping them as two repositories meant
> **syncing every upstream change by hand**. That cost was real; the thing it
> bought was "not having to flip a switch". As two branches of one repository,
> **`launcher.c` and every ArkTS source file are byte-identical across both**,
> and the difference is a single line in
> [`scripts/config.py`](https://github.com/haohandc/MindustryArk/blob/lite/scripts/config.py)
> (`SHIPS_GAME = False`) plus the app name, the icons and the docs.
>
> ⭐ **Everything this page describes still holds on `lite`** — no game in the
> package, bundle name `com.haohandc.arklauncher`, app name `Ark Launcher`.
> ⚠️ The **version number has caught up with upstream**: this repository is the
> snapshot from upstream's `1.2.0.1`, while `lite` is now on the same number as
> upstream, **`1.3.0.1`** — i.e. it also has the save manager, version isolation
> and the rest of what upstream added since.
>
> ⇒ **For downloads, issues and building, go to
> [MindustryArk](https://github.com/haohandc/MindustryArk).** This repository no
> longer takes changes.

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
the two stay on the same number.** (This repository is the snapshot from upstream's
`1.2.0.1`; the [`lite` branch](https://github.com/haohandc/MindustryArk/tree/lite) is on `1.3.0.1`.)

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
