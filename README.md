# Ark Launcher

[English](README.en.md) | **简体中文**

⭐ **上游仓库是 [Mindustry Ark](https://github.com/haohandc/MindustryArk)。**
Ark Launcher 是它的一个分支，**把游戏本体去掉之后剩下的那部分 —— 一个纯启动器**。

Mindustry Ark 做的是：在 **HarmonyOS / OpenHarmony** 上用自建启动器跑 Mindustry ——
内嵌一套 JDK、从 native 代码创建 JVM、把一个真正的 SDL3 窗口交给游戏，不套任何现成的模拟层。
**Ark Launcher 把这些全部保留，唯独不随包分发游戏。**

> **非官方项目。** 与 Mindustry 项目及 Anuken 无隶属关系，未获其认可或支持。
> 详见 [THIRD-PARTY.md](THIRD-PARTY.md)。

---

## 与上游的差异

**只有两条。**

### ① 不打包游戏本体 ⭐ 这是全部重点

| | [Mindustry Ark](https://github.com/haohandc/MindustryArk) | **Ark Launcher** |
|---|---|---|
| 包内的游戏 jar | `libs/arm64-v8a/game/mindustry.so`（实测 **84.8 MB**） | ⛔ **没有** |
| 游戏从哪来 | 随包分发 | **玩家自己提供** |
| 产物大小 | **262.4 MB** | **177.7 MB** |
| 全新安装首次启动 | 直接进游戏 | **进启动器界面，等你去放 jar** |

⭐ **两个体积都是实测的未签名 HAP**（同一棵源码树、`product=default`、`buildMode=debug`）。

⚠️ **差额 84.7 MB ≈ 游戏 jar 的 84.8 MB** —— 少掉的正好是游戏，不是别的东西被顺手砍了。
（上游 `v1.1.0.1` 与 Ark Launcher `v2.0.0.1`，均取自各自 `entry/build/default/outputs/default/`。）

⇒ ⚠️ **第一次打开会停在启动器界面**，因为此刻一个 jar 都没有。这是设计如此，不是故障：
把 Mindustry 的 `.jar` 放进界面显示的那个文件夹 → 点「重新扫描」→ 选中它 → 点「启动游戏」。

⭐ **三处守着这条，所以它不是一句承诺：**

| 位置 | 做什么 |
|---|---|
| `scripts/prep_game.py` | 职责已**反转**：从「把游戏复制进去」变成「**保证那里没有游戏**」，`--check` 发现残留就报错 |
| `scripts/verify_hap.py` 第 6 段 | 产物里**出现**游戏 jar ⇒ 退出码 1 ⇒ 构建中止。⭐ **阴性对照已跑**：把一个假 jar 塞进真产物，得到 `RESULT: FAIL` / 退出码 **1** |
| `scripts/make_payload_zip.py` | 载荷包里不再要求它 |

⚠️ **`entry/libs/` 是被 gitignore 的**，一次旧构建留下的残留会被 hvigor **无声地打进包**
（它只按 `.so` 后缀复制，从不看内容）—— 这正是为什么上面第一条是一个脚本、而不是「记得删掉」。

### ② 换了名字

| | Mindustry Ark | **Ark Launcher** |
|---|---|---|
| 应用名 | Mindustry Ark | **Ark Launcher** |
| 包名 | `com.haohandc.mindustryark` | **`com.haohandc.arklauncher`** |
| 应用图标 | 炮塔 + 灰色装甲底板（带四个螺栓） | **只有那门炮塔** |

⭐ **版本号不在这张表里 —— 它不是一项差异。** Ark Launcher 只做减法、自身没有新功能，
所以**版本跟着上游走，两边同号**：上游 bump，它跟着 bump。
（当前上游是 `1.1.0.1`、本仓库是 `2.0.0.1`；上游会走到同一个号。）

⚠️ **包名不同 ⇒ 沙箱不同 ⇒ 存档、模组、设置【不共通】。**
两个应用可以并存在同一台设备上，各自独立。

### 其余完全一致

包括「在界面上挑一个 jar」那套东西 —— ⚠️ **上游也有**（上游提交 `b4f1a2b`）。
Ark Launcher 的差异是**把游戏拿掉**，不是加了什么功能。

---

## 开始使用

**你需要自备一个 Mindustry 的 `.jar`。** 启动器**不判断版本**，只是把 jar 放进 classpath。

⚠️ 但**我替不了你验证**：上游跑通过的是 `v8 Build 160.5`（上游 `RELEASE.md:16` 记的内嵌版本；
`docs/BUILDING.md:58` 实测同一份补丁 jar 同时驱动 `160.4` 与 `160.5`）。而
**Ark Launcher 自己这条「放 jar → 启动」的路还没上过真机** —— 见下面的「未验证」。

装上之后：

1. 打开应用 → 落在启动器界面
2. 界面上会显示一个文件夹路径（在「下载」里，本应用自己的目录下）
3. 用任何文件管理器，把 `.jar` 拷进那个文件夹
4. 回到应用，点「重新扫描」→ 列表里会出现它 → 点选它
5. 点「启动游戏」

⭐ **全新安装的第一次打开就会正确列出你的 jar** —— 这一点实测过（见「未验证」）。
📌 更早的构建上不是这样：那时第一次会显示一句「还没读到文件夹」，**重启一次**才好。
原因是那个文件夹建得比界面读得晚，**已修**。

⚠️ **但你的 jar 不会因为重装而丢。** 【实测】卸载再安装之后，放进那个文件夹的两个 jar
**原样还在**（连文件日期都没变）—— 重装清的是**应用自己的数据**，不是 Downloads 里的那个
文件夹。

之后每次启动都直接进游戏。想换一个 jar：**悬浮球 →「启动器」**。

⚠️ **界面里还有一个「仍然尝试启动」** —— 它是逃生门：万一某台设备上判定出错，
它让你绕过去直接进游戏，而不是被永远关在启动器里。

---

## 设备与系统要求

⭐ **哪些设备能跑**：**鸿蒙 7 / API 26 及以上**，**平板和手机都行**，自签名安装即可全速运行。

全速依赖应用拿到「可执行内存」—— 从 API 26 起，系统会为**调试** profile 自动申请受支持的
ACL 权限，手机上同样有效；**这也是应用商店里没有手机包的原因**（**release** 签名永远拿不到）。
⚠️ **鸿蒙 5 / 6** 没有自动授予机制，自签名安装**未验证**。

⚠️ 设备支持这件事是**上游**验证的（MatePad Pro 12.2" 2025 平板、Mate 80 Pro 手机）。
**Ark Launcher 本身的「没有游戏」那部分还没在真机上跑过** —— 见下面的「未验证」。

---

## 把游戏跑起来之后

以下都是**上游 Mindustry Ark 已验证**的运行时行为，Ark Launcher 原样继承
（它跑的是同一套启动器、同一个 jar 来源）：

| 项目 | 状态 |
|---|---|
| JVM 启动 | 可用 —— 但启动器**必须**传 `-XX:UseSVE=0`，否则 JIT 会生成本设备无法执行的 SVE 指令，进程直接 SIGILL |
| 图形 | OpenGL ES，经 SDL3 |
| 音频 | OHAudio，经自编的 `libarcarm64.so`（含 SDL3 后端） |
| 触屏 | 可用，**含双指捏合缩放** |
| 键盘 | 可用（物理键盘；WASD 与 ESC）。往游戏输入框里打字用**带输入法的弹出式输入框** |
| 鼠标 / 手柄 | 鼠标可用；手柄**未测试** |
| 存档导入导出 | 走「下载」里的应用文件夹往返 |
| 模组 | 用**游戏自带的「导入模组」按钮**导入 —— 唯一入口，不用重启 |
| 桌面 / 移动模式 | 可切换，但**需要重启应用** |
| 网络 / 联机 | 平台层面已通（`socket` / `epoll` / DNS / TCP / TLS / HTTP 全部实测）。局域网、公网服务器搜索、本机开服三项均实测。⚠️ 但还没打完过一局真实对局 |

详细清单与实测证据见 [docs/LIMITATIONS.md](docs/LIMITATIONS.md)。

### ⚠️ 未验证

- ⚠️ **「没有游戏」这条路径只走到了【列出 jar】。** 【实测】全新安装 → 启动器界面 →
  放 jar → **重启后正确列出两个 jar** —— 这四步走通了。
  **还差最后一步：选中某个 jar → 点「启动游戏」→ 游戏真的起来。** 那需要两次点击。
- ✅ **首次启动那个竞态已修，并实测验证**。它原本是这样：放 jar 的文件夹由
  `ensureModFolder()` 创建，那是**异步**的（mkdir 或弹选择器）；而 `decideStartup()`
  紧接着**同步**把界面切到启动器，启动器界面的 `aboutToAppear` 也**同步**读那个状态文件
  （`gameJarDir` → `readModFolder`）—— 于是读到了还没有的东西。
  ⚠️ **这个路径过去不可能被走到**（那时包里总有游戏，判定从不落到启动器界面），
  **是阉割把它暴露出来的**。
  ⇒ 修法：`Index.ets` 里加 `folderSettled`，在 `ensureModFolder()` 的 `.then()` **末尾**
  翻成 true，作为 `@Prop @Watch` 传给启动器界面重读一次。
  ⭐ **【实测】全新安装的第一次启动（没重启、没点任何东西）→ 两个 jar 都正确列出。**
  ⚠️ 刻意**不**让别人去做阻塞式等待：选择器那条路可能永远不返回，界面就永远不出来 ——
  本项目为「门关上了却没有开的路径」付过代价，不重犯。
- ✅ **一条原本担心的「更坏情况」没有发生**：项目里记着平台可能拒绝在 Download 里建目录
  （平板上 `EPERM`）—— 本次实测**这条路是通的**，文件夹在第一次启动时就建好了
  （状态文件 61 字节，只有路径行）。那份记录至少在这台设备 + 这个版本上已经过时。

---

## 下载与安装

⚠️ **本仓库目前没有 Releases 产物** —— 请从源码构建，或直接用
[上游](https://github.com/haohandc/MindustryArk/releases)的成果。

构建出来的 HAP 是**未签名**的，装不上。两种办法：

**① 用安装工具（不需要开发环境，推荐）**

| 工具 | 说明 |
|---|---|
| [小白调试助手](https://github.com/likuai2010/auto-installer/releases/latest) | 免费的跨平台鸿蒙调试工具，**签名 + 安装一步到位** |
| [HoKit](https://github.com/yabi-zzh/HoKit/releases/latest) | **一键重签名**、设备投屏、性能监控、文件管理。支持 Windows / macOS / Linux |

**② 用 DevEco Studio 自己签名**

用 DevEco Studio 打开本项目 → **File → Project Structure → Signing Configs →
Automatically generate signature** → `bash deploy.sh`。

更细的说明、以及**什么绝不能发布**，见 [RELEASE.md](RELEASE.md)。

---

## 从源码构建

```bash
# 1) 解开载荷包（JDK / LWJGL / Arc natives / 补丁 jar）到 entry/libs/
unzip -o ArkLauncher-<版本>-payload.zip

# 2) 关键一步：确保包里没有游戏
python scripts/prep_game.py --check    # 有残留会报错
python scripts/prep_game.py            # 清掉它

# 3) 构建
bash build.sh assembleHap --mode module -p product=default -p buildMode=debug --no-daemon
```

⚠️ 第 2 步不是可选的：**载荷包里带着游戏 jar**（它是为上游做的），直接构建会被
`verify_hap.py` 拦下。这正是那道闸门存在的意义 —— 见上面「与上游的差异」。

---

## 文档

**`docs/` 下的文件是双语的 —— 中文段在前、英文段在后，在同一个文件里。**

⚠️ **这些文档大多是从上游继承的**，描述的还是「带游戏的完整体」。凡是提到
「随包的游戏」「内嵌的 Mindustry」，在 Ark Launcher 上都**不成立** —— 以本 README 为准。

| 文档 | 什么时候看 |
|---|---|
| **[docs/FAQ.md](docs/FAQ.md)** | 有具体疑问，先看这里 |
| **[docs/LIMITATIONS.md](docs/LIMITATIONS.md)** | 想报 bug 之前，先确认是不是已知行为 |
| **[docs/BUILDING.md](docs/BUILDING.md)** | 要自己从源码构建 |
| **[docs/PERMISSIONS.md](docs/PERMISSIONS.md)** | 想知道这应用要什么权限 |
| **[PRIVACY.md](PRIVACY.md)** | 想知道它收集什么数据（答案：什么都不收集）|
| **[docs/LAYOUT.md](docs/LAYOUT.md)** | 刚克隆下来，不知道东西在哪 |
| [RELEASE.md](RELEASE.md) | 下载了构建，想知道该下哪个、怎么装 |
| [RELEASE-MAINTENANCE.md](RELEASE-MAINTENANCE.md) | 要发下一个版本 |
| [THIRD-PARTY.md](THIRD-PARTY.md) | 要审计许可证 |
| [payload-src/README.md](payload-src/README.md) | 在凑构建的输入 |

---

## 许可证

**GPL-3.0** —— 见 [LICENSE](LICENSE)。

Copyright (C) 2026 Haohandc and contributors.

⭐ **许可证来自上游**：这一族项目是 Mindustry 的衍生作品（启动器就是为运行它而写的，
入口类、classpath 形状、补丁 jar 都是 Mindustry 的），所以**整个是 GPL-3.0**。

⚠️ **但 Ark Launcher 【不再分发】Mindustry 本体**，所以 GPL-3.0 §6 那条
「随二进制提供对应源码」的义务，对 Mindustry 那一半**没有对象可施加**。
本项目自己的源码仍然要随发布提供 —— 这个仓库就是它。
详细论证见 [THIRD-PARTY.md](THIRD-PARTY.md)。

**特别注意**：衍生作品也必须以 GPL-3.0 分发，所以**不能**基于本项目做闭源产品。

---

## 致谢

- [**Mindustry Ark**](https://github.com/haohandc/MindustryArk) —— ⭐ **本项目的上游**，
  整个启动器、平台适配与文档都来自它
- [**Mindustry**](https://github.com/Anuken/Mindustry) —— Anuken 开发，游戏本体。
  ⛔ **不随本仓库分发**，但本启动器是为运行它而写的
- [**Arc**](https://github.com/Anuken/Arc) —— Anuken 开发的游戏框架；平台补丁装在独立 jar 里
- [**SDL3**](https://github.com/libsdl-org/SDL) —— 窗口 / 输入 / 音频层
- [**LWJGL**](https://github.com/LWJGL/lwjgl3) —— OpenGL 与 SDL 的 JNI 绑定
- [**OpenJDK 21**](https://github.com/openjdk/jdk) —— 运行时

各组件许可证与再分发条款见 [THIRD-PARTY.md](THIRD-PARTY.md)。

本仓库大部分代码、文档和文字由 AI 辅助完成（Claude via Cherry Studio，模型 deepseek-flash v4.1）。
