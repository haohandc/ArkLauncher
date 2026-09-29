#!/bin/bash
# 从 git-bash 运行 hvigor。
#
# 为什么需要这个脚本
#   hvigorw.bat 所在路径含空格，直接从 git-bash 调用它
#   总在引号上翻车 -- "路径里带空格" 这件事
#   已经让本项目返工好几轮。所以：直接调用 node 和 hvigorw.js，
#   参数以 ARRAY 传递，这是 bash 可靠处理
#   含空格路径的唯一方式。
#
# 路径
#   可覆盖，这样换一台机器不必改本文件。
#   scripts/config.py 读取同样的变量，所以一次导出两边都生效。
#
#     ARK_DEVECO_STUDIO   默认：E:/Program Files/DevEco Studio
#     DEVECO_SDK_HOME     默认：$ARK_DEVECO_STUDIO/sdk
#     ARK_NODE, ARK_HVIGOR
#
# 用法：
#   bash build.sh assembleHap --mode module -p product=default -p buildMode=debug --no-daemon
set -o pipefail

cd "$(dirname "$0")" || exit 1

STUDIO="${ARK_DEVECO_STUDIO:-E:/Program Files/DevEco Studio}"
export DEVECO_SDK_HOME="${DEVECO_SDK_HOME:-$STUDIO/sdk}"

# 用数组而不是普通字符串：未加引号的 $VAR 若装着 "E:/Program Files/..."
# 会被词分割，命令失败，空管道看起来就像
# 合法的 "没有匹配" 结果，而不是一个错误。
NODE=("${ARK_NODE:-$STUDIO/tools/node/node.exe}")
HVI=("${ARK_HVIGOR:-$STUDIO/tools/hvigor/bin/hvigorw.js}")

if [ ! -f "${NODE[0]}" ]; then echo "node not found: ${NODE[0]}" >&2; exit 1; fi
if [ ! -f "${HVI[0]}" ]; then echo "hvigorw.js not found: ${HVI[0]}" >&2; exit 1; fi

exec "${NODE[@]}" "${HVI[@]}" "$@"
