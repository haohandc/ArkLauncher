#!/bin/bash
# 构建 AppGallery 的 .app，并声明可执行内存权限。
#
# 为什么需要它
#   ohos.permission.kernel.ALLOW_WRITABLE_CODE_MEMORY 是 JVM 的 JIT 所必需的，
#   在某些设备上如此 -- 见 RELEASE-MAINTENANCE.md 2.11。实测：一台 HarmonyOS 6.1.1
#   (API 24) 设备拒绝 mmap(RWX)，errno=22，launcher 完全走不过
#   JNI_CreateJavaVM，应用装得上却起不来。
#
#   它不能无条件写进 src/main/module.json5，因为一个普通
#   (debug) profile 无法授予受限权限：声明它会让
#   本地安装失败，报 "install failed due to grant request permissions
#   failed"，本项目已经踩过一次 -- 见 deploy.sh 开头。
#
#   所以它只由本脚本为 store 产物声明，随后再移除；
#   hvigor 没有按 product 区分的 module.json5：它自己的
#   getJsonProfilePath() 对每个 TARGET 的 source-set 根目录只解析一个文件，所以
#   按 product 的 manifest 意味着整个源码树要再拷一份。
#
# ⚠️ 顺序很重要
#   在 AppGallery Connect 里 ACL 已获批、且 Release profile 已重新生成
#   带上它之前，不要运行本脚本。一个声明了受限权限、其 profile 却
#   无法授予该权限的包是装不上的 -- 所以
#   提前运行只会让 store 构建更糟，而不是更好。
#
# 它保证什么
#   1. 除非 module.json5 处于已知干净状态，否则拒绝启动，这样
#      上一次在注入中途被杀掉的情况会被检出，而不是在其之上继续构建。
#   2. module.json5 在每一条退出路径上都会恢复，且恢复结果用哈希
#      校验 -- 不是假设。trap 在第一次写入之前就装好。
#   3. 构建产物会被打开并检查其中的权限。注入一个
#      文件并指望它进了包，和信任一份构建日志是同一个错误；
#      真正被上传的是那个包。
#
# 用法：
#   bash scripts/make_store_app.sh tablet
#
# ⚠️⚠️ 没有 phone 模式，而不做 phone 模式正是要点。
#
# 曾经写过一个 phone 模式，现在有意删掉了。它会产出一个
# 不声明任何可执行内存权限、且只面向 phone 的包，
# 并指望 JVM 以解释模式运行。2026-09-22 实测 -- 见
# RELEASE-MAINTENANCE.md 2.13b -- 那个包不可能工作：
#
#   在设备绑定的 RELEASE profile 且没有可执行内存 ACL 时，launcher
#   探测该能力，拿到 -1，强制 -Xint，然后死在
#   JNI_CreateJavaVM 里，之后再无任何输出。解释器仍然需要
#   可执行内存：HotSpot 在去看字节码要怎么运行之前，
#   就已经建好了启动桩。
#
# ⇒ 手机无法被授予该 ACL（该策略覆盖 tablet 和 PC/2in1），而
#   解释模式兜底也救不了它，所以一个手机 store 包会
#   装得上却永远起不来 -- 最糟糕的一种提交。手机改由
#   SELF-SIGNED 构建服务，那里的 debug profile 会临时解锁所有
#   权限，JIT 因此可用。那条路线有文档记录；它不是本脚本
#   产出的包。
#
# ⚠️ 而且 module.json5 的 deviceTypes 里仍列着 "phone" -- 同样是有意为之。
#    deviceTypes 在安装时就会被强制检查，不只是在列表展示时，所以从
#    manifest 里去掉 "phone" 会让自签名构建在手机上也无法安装，
#    从而毁掉手机唯一的路线。收窄应该放在
#    这里，构建期：这一层才决定 STORE 提供什么。
#
# 可执行内存权限是通过一个受限（ACL）应用授予的，
# 其支持的设备是 "tablet and PC/2in1"。本构建
# 声明了它并面向 tablet + 2in1。用户已与华为确认，一个
# Release Profile 就能覆盖它，且 AppGallery 按 deviceTypes 过滤 -- 这就是
# 为什么 deviceTypes 要在这里重写，而不是沿用工具链模板的
# ["phone","tablet","2in1","tv"]。"tv" 被去掉：本项目从未测过
# TV，而声明一个未测试的平台是一种主张，不是默认值。
#
# MODE 参数仍然必填，不给默认值。它是这个包唯一明说
# 自己声称哪些平台的地方，不应该让一个默认值
# 来回答这个问题。
#
# 输出：dist/store/MindustryArk-<mode>.app

set -o pipefail
cd "$(dirname "$0")/.." || exit 1
export MSYS_NO_PATHCONV=1

MODE="${1:-}"
case "$MODE" in
    tablet) WANT_PERM=yes; WANT_DEVICES='["tablet", "2in1"]' ;;
    phone)
        # 显式写出来，这样回答就是解释而不是用法
        # 报错。输入 "phone" 的人不是打错字 -- 他们要的是
        # 本项目决定不构建的那个包，而单独一句 "usage: tablet"
        # 读起来会像这个参数只是没被识别。
        echo "!! there is no phone mode, and that is a decision rather than an omission." >&2
        echo "!! A phone store package would install and never start: the ACL covers" >&2
        echo "!! tablet and PC/2in1 only, and the interpreted fallback does not rescue a" >&2
        echo "!! device that was refused executable memory. Phones are served by the" >&2
        echo "!! self-signed build. See the header of this file, and" >&2
        echo "!! RELEASE-MAINTENANCE.md 2.13b." >&2
        exit 2
        ;;
    *)
        echo "usage: bash scripts/make_store_app.sh tablet" >&2
        echo >&2
        echo "  tablet  tablet + 2in1, WITH the executable-memory ACL (JIT)" >&2
        echo >&2
        echo "The mode is required: it is where the package says out loud which" >&2
        echo "platforms it claims, and a default should not be allowed to answer that." >&2
        exit 2
        ;;
esac

PY=("${ARK_PYTHON:-python}")
MODJSON="entry/src/main/module.json5"
PERM="ohos.permission.kernel.ALLOW_WRITABLE_CODE_MEMORY"
BUILT_APP="build/outputs/release/MindustryArk-release-signed.app"
OUTDIR="dist/store"
OUTAPP="$OUTDIR/MindustryArk-$MODE.app"
BACKUP="${TEMP:-/tmp}/module.json5.pre-store"

echo "############ store build: mode = $MODE ############"
echo "   permission $PERM: $([ "$WANT_PERM" = yes ] && echo INJECTED || echo absent)"
echo "   deviceTypes: $WANT_DEVICES"

# ---------------------------------------------------------------------------
# 恢复，先装好，在一切写入之前
#   在写入之后才装的 trap 只能保护比它更晚发生的失败。
#   真正要命的失败就是写入本身。
# ---------------------------------------------------------------------------
restore() {
    rc=$?
    if [ -f "$BACKUP" ]; then
        "${PY[@]}" - "$MODJSON" "$BACKUP" <<'PYEOF'
import hashlib, io, os, shutil, sys
path, b = sys.argv[1], sys.argv[2]
want = io.open(b + ".sha256").read().strip()
shutil.copyfile(b, path)
got = hashlib.sha256(open(path, "rb").read()).hexdigest()
print("   restored %s  (sha256 %s%s)"
      % (path, got[:16], "" if got == want else "  *** MISMATCH, expected %s ***" % want[:16]))
PYEOF
    fi
    exit $rc
}
trap restore EXIT

# ---------------------------------------------------------------------------
# 闸门：FORCE_COMPAT_MODE 必须为 false。
#
# 该常量会在每一台设备上强制 -Xint，它存在的唯一目的是测量
# 解释器在并不需要它的硬件上要付出多少代价。如果它被留着没关，
# 而 store 包又是从这个工作树构建的，那每个用户拿到的都会是
# 解释模式跑的游戏，设备上却没有任何东西会说明原因。
#
# 这里选择检查而不是信任，因为"记得改回去"正是那种
# 一直有效、直到它失效为止的指示。
# ---------------------------------------------------------------------------
FORCE_LINE="$(grep -nE '^const FORCE_COMPAT_MODE' entry/src/main/ets/pages/Index.ets || true)"
case "$FORCE_LINE" in
    *"= false"*) : ;;
    "")  echo "!! could not find FORCE_COMPAT_MODE in Index.ets -- refusing to build" >&2
         exit 1 ;;
    *)   echo "!! FORCE_COMPAT_MODE is not false:" >&2
         echo "!!   $FORCE_LINE" >&2
         echo "!! that forces interpreted mode on every device. Set it back to false" >&2
         echo "!! before building anything that could ship." >&2
         exit 1 ;;
esac
echo "   gate: FORCE_COMPAT_MODE = false"

# ---------------------------------------------------------------------------
# 1. 前置检查、备份、注入
# ---------------------------------------------------------------------------
"${PY[@]}" - "$MODJSON" "$PERM" "$BACKUP" "$WANT_PERM" "$WANT_DEVICES" "$MODE" <<'PYEOF' || exit 1
import hashlib, io, os, re, sys
path, perm, backup, want_perm, want_devices, mode = sys.argv[1:7]
src = io.open(path, encoding="utf-8").read()

# ⚠️ 匹配声明本身，而不是名字。module.json5 有意在注释里
# 提到这个权限 -- 就是解释它为何缺席的那段 --
# 所以子串判断在干净的工作树上也会说"已声明"并拒绝
# 运行。实测：裸名字出现一次（第 36 行，在注释里），
# 而 '"name": "<perm>"' 出现零次。
DECL = '"name": "%s"' % perm
if DECL in src:
    print("!! %s ALREADY declares %s." % (path, perm))
    print("!! Either a previous run died before restoring it, or it was added by")
    print("!! hand. Restore it (git checkout -- %s) before running this --" % path)
    print("!! otherwise the backup below would capture the WRONG 'original'.")
    sys.exit(1)

io.open(backup, "w", encoding="utf-8", newline="").write(src)
digest = hashlib.sha256(src.encode("utf-8")).hexdigest()
io.open(backup + ".sha256", "w").write(digest)
print("   original saved: sha256 %s" % digest[:16])

# ⚠️ 锚点是那个数组，不是某条权限条目。
#
# 以前是插在 READ_WRITE_DOWNLOAD_DIRECTORY 条目之前，那样很方便，
# 因为那条目存在，而且明确不是注释。
# 那也是个陷阱：任何删除或重命名该权限的改动都会
# 在最糟的时刻把本脚本一起带走 -- 那时 ACL 刚刚
# 获批，而 store 构建正是你想产出的东西。
#
# 数组本身是结构性的。增删权限时它不会动，而如果
# 它没了，那 module.json5 就不再是 manifest，
# 这时大声失败才是正确答案。
m = re.search(r'"requestPermissions"\s*:\s*\[', src)
if not m:
    print("!! could not find the requestPermissions array in %s" % path)
    print("!! this script injects INTO that array; without it there is nowhere to")
    print("!! put the permission, and the manifest is not what this expects.")
    sys.exit(1)
after = m.end()

# 缩进取自数组的第一条条目，这样注入的文本会和
# 已有内容对齐。空数组时回退到 manifest 惯用的六个
# 空格。
nm = re.search(r'\n([ \t]+)\S', src[after:])
indent = nm.group(1) if nm else '      '

NEW = (indent + "// STORE BUILD ONLY -- injected by scripts/make_store_app.sh and removed\n"
       + indent + "// again on exit. See RELEASE-MAINTENANCE.md 2.11 for why this cannot be\n"
       + indent + "// declared unconditionally. Never commit a module.json5 containing this.\n"
       + indent + "// The ACL's supported devices are tablet and PC/2in1, which is why the\n"
       + indent + "// package this script produces claims those and nothing else.\n"
       + indent + '{ "name": "%s", "reason": "$string:perm_reason_CODE_MEMORY", '
                  # 是 `always`，而不是 `inuse`。JVM 的 JIT 从进程启动那一刻
                  # 到进程退出的全程都需要这块内存，而哪个 ability 在前台
                  # 跟这件事毫无关系。它还必须在形式上 MATCH
                  # 那份 AGC ACL 申请，在那边时机被设为 always -- 一个包的
                  # usedScene 与它自己的 ACL 申请给出的答案不一致，
                  # 就是一处不值得发布出去的不一致。
                  '"usedScene": { "abilities": [ "EntryAbility" ], "when": "always" } },\n' % perm)

# 插成第一条而不是最后一条：一个写成 `[]` 的数组，
# 它的收尾方括号紧跟在 `[` 之后，而插成第一条的处理
# 对空数组和有内容的数组都是一样的。
out = src[:after] + "\n" + NEW + src[after:] if want_perm == "yes" else src

# --- deviceTypes，两种模式下都会重写 --------------------------------
#
# manifest 出厂时带的是工具链模板的值 ["phone","tablet","2in1",
# "tv"]，那是一个起点而不是一个决定。每个模式把它收窄到
# 该包自己的用途，而 "tv" 两边都去掉：这里没有任何东西
# 在 TV 上跑过，而声明一个平台就是一份承诺。
#
# 用户已确认 AppGallery 按它过滤，所以这个切分正是让
# 手机用户不会被提供 tablet 包的东西 -- 对他们来说那会是
# *更糟* 的那个，因为他们无法被授予它期望的 ACL。
dm = re.search(r'"deviceTypes"\s*:\s*\[[^\]]*\]', out)
if not dm:
    print("!! no deviceTypes array in %s" % path)
    print("!! without it a package declares no platform, and the split between the")
    print("!! two store builds has nowhere to live.")
    sys.exit(1)
out = out[:dm.start()] + '"deviceTypes": %s' % want_devices + out[dm.end():]
print("   deviceTypes -> %s" % want_devices)

# 对写入本身做的廉价检查，在它落盘之前。下面的构建
# 闸门检查的是产物；这一条在备份还新鲜的时候
# 抓出被改坏的编辑。
decl = ('"name": "%s"' % perm) in out
if not decl:
    print("!! the injection produced a file without the permission in it")
    sys.exit(1)

io.open(path, "w", encoding="utf-8", newline="\n").write(out)
print("   %s" % ("injected %s" % perm if want_perm == "yes"
                else "no permission injected (phone mode)"))
PYEOF

# ---------------------------------------------------------------------------
# 2. 构建
# ---------------------------------------------------------------------------
echo
echo "############ building the store .app ############"
bash build.sh assembleApp --mode project -p product=release -p buildMode=release --no-daemon > /tmp/store_app.log 2>&1
if [ $? -ne 0 ] || ! grep -q "BUILD SUCCESSFUL" /tmp/store_app.log; then
    grep -Ei "BUILD (SUCCESSFUL|FAILED)" /tmp/store_app.log | head -1
    echo "!! build failed -- tail of the log:" >&2
    tail -25 /tmp/store_app.log >&2
    exit 1
fi
grep -Ei "BUILD (SUCCESSFUL|FAILED)" /tmp/store_app.log | head -1

# ---------------------------------------------------------------------------
# 2b. 以带模式名的名字另存一份
#
# hvigor 每个 product 只写一个固定路径，所以构建第二个模式会
# 覆盖第一个 -- 而这两个包只靠一个在文件列表里看不见的
# 权限来区分。在这里改名意味着两者可以同时存在，
# 文件名也能说明哪个是哪个。
#
# 是拷贝不是移动：下面的闸门要读 $BUILT_APP，闸门失败时应该
# 让构建树保持 hvigor 留下的样子。
# ---------------------------------------------------------------------------
echo
echo "############ keeping the artifact as MindustryArk-$MODE.app ############"
if [ ! -f "$BUILT_APP" ]; then
    echo "!! the build reported success but there is no .app at $BUILT_APP" >&2
    echo "!! do not go looking for an older one -- that is how a stale package gets" >&2
    echo "!! uploaded. Check the build log above." >&2
    exit 1
fi
mkdir -p "$OUTDIR"
cp -f "$BUILT_APP" "$OUTAPP"
echo "   $OUTAPP"

# ---------------------------------------------------------------------------
# 2c. 签名到底有没有真的被附加？
#
# 结尾的消息告诉读者这个文件是 release 签名的。那是一个关于
# 签名的主张，而签名不是 zip 条目 -- HarmonyOS 把它附加在
# 归档之后 -- 所以列出 .app 的内容两条路都证明不了什么。
# 实测如此，这也是本检查存在的原因：脚本里原本没有任何
# 地方验证它。
#
# hvigor 会把两个变体并排产出，而带签名那个大出的部分
# 正好是签名块（实测：153,246,249 vs 153,231,519 = +14,730 B）。
# 两者一比，主张就变成了实测。
#
# 如果签名配置缺失或错误，hvigor 仍然会成功，并且仍然
# 写出一个叫 "-signed" 的文件 -- 这正是本检查要抓的失败。
# ---------------------------------------------------------------------------
UNSIGNED_APP="${BUILT_APP%-signed.app}-unsigned.app"
if [ -f "$UNSIGNED_APP" ]; then
    SZ_SIGNED=$(wc -c < "$BUILT_APP")
    SZ_UNSIGNED=$(wc -c < "$UNSIGNED_APP")
    if [ "$SZ_SIGNED" -le "$SZ_UNSIGNED" ]; then
        echo "!! '$BUILT_APP' is NOT LARGER than the unsigned variant:" >&2
        echo "!!   signed   $SZ_SIGNED B" >&2
        echo "!!   unsigned $SZ_UNSIGNED B" >&2
        echo "!! The file is named -signed but no signature was appended, which means" >&2
        echo "!! the release signingConfig did not take effect. Check the 'release'" >&2
        echo "!! entry in the root build-profile.json5 (it is skip-worktree, so it is" >&2
        echo "!! not in git and cannot be reviewed by 'git diff'). Do not upload." >&2
        exit 1
    fi
    echo "   signature present: +$((SZ_SIGNED - SZ_UNSIGNED)) B over the unsigned variant"
else
    echo "   (no -unsigned variant to compare against; the signature is not verified)" >&2
fi

# ---------------------------------------------------------------------------
# 3. 闸门 -- 包才是被上传的东西，所以要检查包
#
# 两条不变式，其中第一条现在是要命的那条：
#
#   1. deviceTypes 恰好是 tablet + 2in1。正是它让 store 不会
#      把应用提供给手机，而这正是 phone 模式被删掉的全部理由：
#      这个应用在手机上装了也起不来。一个意外带上 "phone" 的包
#      会被提供给它服务不了的设备。
#   2. ACL 权限确实被声明了。没有它就没有 JIT，安装后
#      永远起不来 -- 从外面看是静默的。唯一的证据是 launcher
#      有没有打日志 "executable memory works (probe=42)"。
# ---------------------------------------------------------------------------
echo
echo "############ gate: the ARTIFACT has the shape mode=$MODE requires ############"
"${PY[@]}" - "$BUILT_APP" "$PERM" "$WANT_PERM" "$WANT_DEVICES" "$MODE" <<'PYEOF'
import hashlib, io, json, os, re, sys, zipfile
app, perm, want_perm, want_devices, mode = sys.argv[1:6]
if not os.path.exists(app):
    sys.exit("!! no .app at %s" % app)
z = zipfile.ZipFile(app)
inner = [n for n in z.namelist() if n.endswith(".hap")]
if not inner:
    sys.exit("!! the .app contains no .hap")
h = zipfile.ZipFile(io.BytesIO(z.read(inner[0])))
mod = json.loads(h.read("module.json").decode())["module"]
names = [p["name"] for p in mod.get("requestPermissions", [])]
print("   declared permissions: %s" % names)
print("   deviceTypes: %s" % mod.get("deviceTypes"))

# ---------------------------------------------------------------------------
# 检查项。
#
# 1. deviceTypes 与本构建声称的一致，最先检查，因为它决定
#    这个包会被提供给谁。这里出现 "phone" 意味着 store 会把一个
#    应用提供给跑不动它的设备。
#
# 2. 权限存在。它缺席时的那种失败，看起来像一台慢
#    平板，而不是一个坏包。
#
# 3. module.json5 在未注释行上声明的每一个权限，都在
#    包里。这是通用不变式 -- manifest 被改成某种
#    包不反映的样子 -- 与单模式版本相比未变。
#    它正是当初抓住那个旧陷阱的东西：注入被锚定在一条
#    后来被删掉的权限条目上。
# ---------------------------------------------------------------------------
expected = json.loads(want_devices)
actual = mod.get("deviceTypes") or []
if sorted(actual) != sorted(expected):
    sys.exit("!! mode=%s expects deviceTypes %s but the package declares %s -- do not upload"
             % (mode, expected, actual))

has = perm in names
if not has:
    sys.exit("!! THE PACKAGE IS MISSING THE INJECTED PERMISSION: %s -- do not upload. "
             "Without it there is no JIT, and the app installs and does not start." % perm)
print("   ok: deviceTypes %s, permission declared" % sorted(actual))

# 脚本开头已经 cd 到项目根目录，所以这里本来就是正确的
# 基准 -- 从 .app 所在目录去算 "../.." 跳转层数，正是第一版把
# 深度算错一层的原因。
manifest = "entry/src/main/module.json5"
declared = []
if os.path.exists(manifest):
    for line in io.open(manifest, encoding="utf-8"):
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        # 特意锚定在 "ohos.permission." 上。一个裸的 `"name": "..."` 也会
        # 匹配模块名、ability 名和 extension 名 --
        # 实测，它们在第一版里全都命中了，会被报告成
        # "declared but missing from the package"，从而让构建
        # 因为三个根本不是权限的东西而失败。
        for nm in re.findall(r'"name"\s*:\s*"(ohos\.permission\.[^"]+)"', stripped):
            if nm not in declared:
                declared.append(nm)
    # 被注入的那个不在 module.json5 里 -- 它是本脚本在写盘途中
    # 加进去的，而且只在 tablet 模式下，所以这里不算"已声明"。
    absent = [p for p in declared if p not in names]
    print("   module.json5 declares %d, package carries %d" % (len(declared), len(names)))
    if absent:
        sys.exit("!! DECLARED IN THE MANIFEST BUT NOT IN THE PACKAGE: %s -- do not upload"
                 % absent)
else:
    print("   (module.json5 not found at %s -- skipped the manifest cross-check)" % manifest)
v = json.loads(z.read("pack.info").decode())["summary"]["app"]["version"]
print()
print("   %s" % os.path.basename(app))
print("   versionName %s   versionCode %s" % (v["name"], v["code"]))
print("   size %d B" % os.path.getsize(app))
print("   sha256 %s" % hashlib.sha256(open(app, "rb").read()).hexdigest())
PYEOF
GATE_RC=$?

# ---------------------------------------------------------------------------
# 4. 把 manifest 放回去，并说明这件事
#
# EXIT 上的 trap 会做这件事，但消息很重要：看到构建成功的
# 读者需要知道工作树是否干净，因为他们接下来可能要做的事
# 是 `git diff` 或者再跑一次构建。
# ---------------------------------------------------------------------------
echo
if [ -f "$BACKUP" ]; then
    echo "   manifest restored (the trap will do it again on exit; that is harmless)"
fi

echo
if [ "$GATE_RC" -eq 0 ]; then
    echo "############ OK -- upload this file ############"
    echo "   $OUTAPP"
    echo
    echo "   tablet + 2in1, WITH the executable-memory ACL."
    echo "   Needs the Release Profile that carries that ACL entry."
    echo "   Phones are deliberately NOT covered: the ACL cannot reach them and the"
    echo "   interpreted fallback does not save them, so a phone package would install"
    echo "   and never start. Self-signed installs are how phones are served."
    echo
    echo "   Signed with the RELEASE certificate, so it cannot be sideloaded and"
    echo "   cannot be tested on your own hardware. Same constraint as 2.10/2.11."
    echo "   ⚠️ Which means the ACL is UNVERIFIED until it is in the store: if the"
    echo "   grant does not take effect the app still runs, just interpreted -- so a"
    echo "   failed ACL looks like a slow tablet and nothing else. The launcher log"
    echo "   line to look for is 'executable memory works (probe=42)'."
else
    echo "############ GATE FAILED -- do not upload ############" >&2
fi
exit $GATE_RC
