# -*- coding: utf-8 -*-
r"""Does the version gate actually fail when it should?

    python scripts/test_version_gate.py

WHY A TEST FOR A CHECK
    verify_hap.py's first step compares the file name, the artifactName, the
    versionName and the versionCode, because those four live in four files that
    get edited at different times. That check is only worth having if it is
    known to reject a bad package -- and this project has already shipped one
    "gate" that printed OK unconditionally, because a pipeline's exit status was
    being thrown away before it was read.

    So: build minimal packages holding nothing but pack.info, tamper with one
    field at a time, and run the real gate function over each.

    The first run failed its own good case and the fault was in this file, not
    in the gate: the harness wrote every package under a scratch name and passed
    the intended name separately, and the gate compares the file's actual name.
    Worth recording, because "the check is broken" and "my test is broken" look
    identical from the output.

WHEN TO RUN IT
    After touching the version fields, and after touching that gate.
"""
# 版本关卡的负面测试。
#
# 构造最小的 .hap 文件（只含 pack.info 的 zip），篡改
# 版本字段，然后对每一个运行 verify_hap.py 里真正的关卡
# 函数。从未被证明会失败的关卡还不能算
# 关卡 -- 这个项目已经发布过一个总是打印 OK 的检查，
# 因为流水线的退出状态被丢弃了。
import io
import json
import os
import sys
import zipfile

# 由本文件自身的位置推导，而非写死。它以前是指向某个
# 特定 checkout 的字面绝对路径，而这是这里其他所有脚本都
# 刻意避免的一件事 -- 它们全都经由 config.py 路由，
# 后者的路径是可被 ARK_* 覆盖的默认值。那个字面量意味着
# 在其他任何地方 checkout 都会以令人困惑的 ImportError 失败，而且仓库
# 无缘无故带着一个属于某台机器的路径。
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
os.chdir(HERE)

import config
import verify_hap

GOOD = {
    "summary": {"app": {"version": {"name": config.APP_VERSION,
                                    "code": config.VERSION_CODE}}},
    "packages": [{"name": config.ARTIFACT_NAME}],
}


def make_hap(path, info):
    """Write a minimal package AT the given path.

    The path's basename is part of what the gate checks, so the file has to
    actually carry the name under test -- writing it under a scratch name and
    passing the intended one separately made the good case fail, which was the
    harness being wrong rather than the gate.
    """
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("pack.info", json.dumps(info))
    return path


def run_case(label, filename, patch, expect_fail):
    info = json.loads(json.dumps(GOOD))          # 深拷贝
    patch(info)
    p = make_hap(os.path.join(os.environ["TEMP"], filename), info)
    ok = [True]
    print("--- %s" % label)
    print("    expecting: %s" % ("FAIL" if expect_fail else "PASS"))
    verify_hap.check_version_matches_name(p, ok)
    got = not ok[0]
    verdict = "as expected" if got == expect_fail else "*** WRONG ***"
    print("    result   : %s   %s" % ("FAIL" if got else "PASS", verdict))
    os.remove(p)
    return got == expect_fail


base = config.ARTIFACT_NAME
cases = [
    ("good", base + "-unsigned.hap", lambda i: None, False),
    ("wrong-code",
     base + "-unsigned.hap",
     lambda i: i["summary"]["app"]["version"].__setitem__("code", 1000000),
     True),
    ("code-is-final-release-value",
     base + "-unsigned.hap",
     lambda i: i["summary"]["app"]["version"].__setitem__(
         "code", config.version_code_for("0.1.0")),
     True),
    ("wrong-versionName",
     base + "-unsigned.hap",
     lambda i: i["summary"]["app"]["version"].__setitem__("name", "0.1.0-beta2"),
     True),
    ("wrong-artifactName",
     base + "-unsigned.hap",
     lambda i: i["packages"][0].__setitem__("name", "MindustryArk-v9.9.9"),
     True),
    ("file-name-mismatch",
     "MindustryArk-v1.0.0-unsigned.hap",
     lambda i: None,
     True),
    ("unexpected-artifact-name",
     base + "-signed.hap",
     lambda i: None,
     True),
]

results = [run_case(*c) for c in cases]
print()
print("negative test: %d/%d as expected" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
