#!/bin/bash
# 构建 probe mod jar -- 用来回答一个问题的产物：
#   运行时从 mod jar 里加载的类，能否在这个启动器的
#   JVM 下被定义并执行？
#
# 为什么它要针对游戏 jar 构建
#   Mindustry 在加载时检查 mod 的父类是否来自与
#   mindustry.mod.Mod 相同的类加载器，不一致就拒绝该 mod
#   ("This mod/plugin has loaded Mindustry dependencies from its own class
#   loader..."). 因此 mindustry.jar 必须是 COMPILE-time 依赖，绝不能
#   进入产物内部。这就是为什么 classpath 传给 javac，
#   而 jar 只由 class 文件组装 -- 从不来自 classpath。
#
# 输出：tools/probe-mod/out/probe-mod.jar
#
# 用法：
#   bash tools/probe-mod/build.sh

set -o pipefail
cd "$(dirname "$0")/../.." || exit 1

JDK="${ARK_JDK:-C:/Program Files/Java/jdk-17}"
JAVAC="$JDK/bin/javac.exe"
JAR="$JDK/bin/jar.exe"
GAME_JAR="payload-src/mindustry-1.0.jar"
SRC="tools/probe-mod/ProbeMod.java"
OUT="tools/probe-mod/out"
CLASSES="$OUT/classes"

[ -f "$JAVAC" ] || { echo "!! javac not found: $JAVAC  (set ARK_JDK)" >&2; exit 1; }
[ -f "$JAR" ]   || { echo "!! jar not found: $JAR" >&2; exit 1; }
[ -f "$GAME_JAR" ] || { echo "!! game jar not found: $GAME_JAR" >&2; exit 1; }

rm -rf "$OUT"
mkdir -p "$CLASSES"

echo "=== compiling (against the game jar, so this must match its bytecode level) ==="
# 游戏是 Java 17（class file major 61）。--release 17 让 probe 保持
# 同一级别；更高的级别会在加载时被拒绝，且没有有用的报错。
"$JAVAC" --release 17 -cp "$GAME_JAR" -d "$CLASSES" "$SRC" || exit 1
echo "   ok"

echo
echo "=== packaging ==="
cp tools/probe-mod/mod.json "$CLASSES/mod.json"
"$JAR" --create --file "$OUT/probe-mod.jar" -C "$CLASSES" . || exit 1

echo
echo "=== the built artifact ==="
"$JAR" --list --file "$OUT/probe-mod.jar" | sed 's/^/   /'
echo
echo "   $OUT/probe-mod.jar   $(stat -c%s "$OUT/probe-mod.jar") B"
echo "   sha256 $(sha256sum "$OUT/probe-mod.jar" | cut -d' ' -f1)"

# ---------------------------------------------------------------------------
# 门禁：产物绝不能包含任何 Mindustry 类。
#
# javac 的 classpath 上带着游戏 jar，之后很容易犯一个错，
# 就是把这脚本 "简化" 成把 classpath 打包进 jar。
# 游戏会指名拒绝这样的 mod，但它是在设备上 RUNTIME 拒绝的，
# 发现这一点要花一次构建和 171 MB 的安装。不如在这里就检查。
# ---------------------------------------------------------------------------
echo
if "$JAR" --list --file "$OUT/probe-mod.jar" | grep -qE '^(mindustry|arc|rhino)/'; then
    echo "!! the probe jar contains game classes -- the game will refuse it:" >&2
    "$JAR" --list --file "$OUT/probe-mod.jar" | grep -E '^(mindustry|arc|rhino)/' | head -5 >&2
    exit 1
fi
echo "   gate: no game classes bundled"

# ---------------------------------------------------------------------------
# 它不再往 bundle 里装任何东西，这就是本次改动。
#
# 它曾把 jar 复制到 entry/libs/arm64-v8a/probe/probe-mod.jar.so，
# 再由 ArkTS（Index.ets 里的 seedProbeMod）在每次启动时把它复制进
# 游戏的 mods 目录。两部分都已移除：
#
#   * 播种是每次启动时的无条件覆盖，所以在游戏里删掉
#     probe-mod.jar 它会自己回来 -- 与文件夹扫描和
#     悬浮球的导入行同样的缺陷，三者一起被移除。
#   * 既然没东西把它复制出去，装进 libs/ 只会让每个 HAP 多带 1.2 KB
#     无用的 jar。
#
# 构建本身仍可用且仍会对结果设门禁，所以这依然是
# 关于 probe 如何制作的说明。现在要用的话，手工把下面这个 jar 复制进
# 游戏的 mods 目录（通过游戏自带的导入按钮），或者
# 如果确实还想要自动投放，就从 git 历史里恢复播种
# 逻辑。
#
# ⚠️ 不要重新加回复制到 libs/ 的逻辑，而不先决定当
#    玩家删掉 mod 时该怎么办。旧答案是 "它会回来"，
#    整个导入器就是为这个答案被移除的。
# ---------------------------------------------------------------------------
echo
echo "   built -> $OUT/probe-mod.jar"
echo "   (not installed into the bundle; see the note above)"
