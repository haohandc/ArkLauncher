# -*- coding: utf-8 -*-
r"""Keep the HAP's library area free of any game jar.

⚠️ 这个脚本的职责在 2026-10-01 **反转**了。它过去把游戏 jar【复制】进
entry/libs/arm64-v8a/game/；现在它保证那里【没有】游戏 jar，并在发现
残留时把它清掉。Ark Launcher 是启动器，游戏本体由玩家自己提供。

WHY THIS IS STILL A SCRIPT, AND NOT SIMPLY A DELETED FILE
    entry/libs/ 是 gitignore 的工作区目录（见 .gitignore 里那段说明），
    而一次**旧构建**会在 entry/libs/arm64-v8a/game/ 留下一个 87 MB 的
    mindustry.so。

    hvigor 只按【文件名以 .so 结尾】决定要不要把它拷进 HAP，从不检查
    内容 —— 所以那个残留会**原样进包**，而构建**不会报任何错**。

    ⇒ 必须有人主动清掉它。这个脚本就是那个人。
    ⇒ 反过来说：删掉这个脚本，等于删掉「残留会被清掉」这件事本身。

    ⚠️ 而且「没人会再去复制它」并不构成保证 —— 那是在赌没有人重跑旧
    的构建链。产物侧的断言在 verify_hap.py 第 6 段，它要求这个文件
    【不存在】；两者是同一件事的两道锁。

WHY THE OLD JAR LIVED UNDER A *.so NAME, AND ONE LEVEL DOWN（历史，留着）
    hvigor 只搬运文件名以 ".so" 结尾的东西，内容从不检查。一个 jar
    按内容被 JVM 当作 class-path 条目打开，所以后缀对它不可见。
    libs/arm64-v8a/ 顶层的名字是平台当作原生库对待的那些，而 jar 不是
    一个；放到下面一层，正好与 module image 已经待的位置一致。

    ⚠️ 那段历史仍然有用：**新的东西也不要放回顶层**，理由相同。

Usage:  python prep_game.py [--check]
        --check  verify only; do not remove
"""

import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

PROJECT_ROOT = config.PROJECT_ROOT

GAME_JAR = os.path.join(PROJECT_ROOT,
                        "entry", "libs", "arm64-v8a", "game", "mindustry.so")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    if not os.path.isfile(GAME_JAR):
        print("game jar : absent, as intended")
        print("           %s" % GAME_JAR)
        return 0

    if a.check:
        print("FAIL a game jar is present: %s" % GAME_JAR)
        print("     %d bytes. This build must not ship one."
              % os.path.getsize(GAME_JAR))
        print("     Remove it: python scripts/prep_game.py")
        return 1

    size = os.path.getsize(GAME_JAR)
    os.remove(GAME_JAR)
    print("game jar : removed, %d bytes" % size)
    print("           %s" % GAME_JAR)
    print("           Ark Launcher ships no game; the player supplies one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
