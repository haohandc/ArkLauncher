# Ark Launcher

[English](README.en.md) | **简体中文**

⭐ **上游仓库是 [Mindustry Ark](https://github.com/haohandc/MindustryArk)。**
Ark Launcher 是它的一个分支 —— **把游戏本体去掉之后剩下的那部分**。

> **非官方项目。** 与 Mindustry 项目及 Anuken 无隶属关系，未获其认可或支持。
> 详见 [THIRD-PARTY.md](THIRD-PARTY.md)。

---

## 与上游的差异：只有两条

### ① 包里没有游戏本体

| | [Mindustry Ark](https://github.com/haohandc/MindustryArk) | **Ark Launcher** |
|---|---|---|
| 包内的游戏 jar | `libs/arm64-v8a/game/mindustry.so`（84.8 MB） | **没有** |
| 游戏从哪来 | 随包分发 | **玩家自己提供** |
| 产物大小 | 262.4 MB | **177.7 MB** |

⇒ **第一次打开会停在启动器界面**，因为此刻一个 jar 都没有。把 Mindustry 的 `.jar` 放进
界面显示的那个文件夹，在列表上下拉刷新，选中它，再点「启动游戏」。

⭐ **三处守着这条，所以它不是一句承诺：**

| 位置 | 做什么 |
|---|---|
| `scripts/prep_game.py` | 职责已**反转**：从「把游戏复制进去」变成「**保证那里没有游戏**」 |
| `scripts/verify_hap.py` 第 6 段 | 产物里**出现**游戏 jar ⇒ 退出码 1 ⇒ 构建中止 |
| `scripts/make_payload_zip.py` | 载荷包里不再要求它 |

### ② 换了名字

| | Mindustry Ark | **Ark Launcher** |
|---|---|---|
| 应用名 | Mindustry Ark | **Ark Launcher** |
| 包名 | `com.haohandc.mindustryark` | **`com.haohandc.arklauncher`** |
| 应用图标 | 炮塔 + 灰色装甲底板 | **只有那门炮塔** |

⚠️ **包名不同 ⇒ 沙箱不同 ⇒ 存档、模组、设置不共通。** 两个应用可以并存在同一台设备上。

⭐ **版本号不在这张表里** —— 它不是一项差异。Ark Launcher 只做减法、自身没有新功能，
所以**版本跟着上游走，两边同号**（现在都是 `1.2.0.1`）。

**其余全部与上游相同**，包括「在界面上挑一个 jar」那套东西 —— 上游也有。
Ark Launcher 的差异是**把游戏拿掉**，不是加了什么功能。

---

## 其他一切，看上游的 README

用法、设备要求、已知限制、构建方式、许可证与致谢 —— **全部以上游为准**，
两边的代码是同一套：

⭐ **[Mindustry Ark 的 README（中文）](https://github.com/haohandc/MindustryArk#readme)**
⭐ **[Mindustry Ark 的 README（English）](https://github.com/haohandc/MindustryArk/blob/master/README.en.md)**

⚠️ **唯一一处例外**：上游 README 里凡是提到「随包的游戏」「内嵌的 Mindustry」的地方，
在这个仓库上都**不成立** —— 以本页「与上游的差异」为准。

---

## 许可证

**GPL-3.0** —— 见 [LICENSE](LICENSE)。Copyright (C) 2026 Haohandc and contributors.

⭐ **许可证来自上游**：这一族项目是 Mindustry 的衍生作品，所以整个是 GPL-3.0。
⚠️ **但本仓库不分发 Mindustry 本体**，所以 GPL-3.0 §6 的义务对那一半没有对象可施加。
详细论证见 [THIRD-PARTY.md](THIRD-PARTY.md)。
