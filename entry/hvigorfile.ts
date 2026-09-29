import { hapTasks } from '@ohos/hvigor-ohos-plugin';
import { execFileSync } from 'node:child_process';
import * as path from 'node:path';
import { hvigor } from '@ohos/hvigor';

// Python 解释器：解析方式与 build.sh / deploy.sh / scripts/config.py 一致 ——
// 先看 ARK_PYTHON，再退到 PATH 上的 "python"。
// 这里原本写死的是一条绝对路径，带着某个用户的目录，等于让这个
// 已提交的文件在别的机器上必然是错的；而本文件正是跑产物闸门的地方，
// 路径一错，构建会以一个指向闸门、而不是指向路径的报错失败。
// ⚠️ 兜底必须是 "python"，不能是 "python3"：本机上 "python3" 解析到
// 另一个 Python 版本，不是这个项目一直在用的那个。
//
// ⚠️⚠️ ARK_PYTHON 只在带 --no-daemon 时可靠。实测（2026-09-29）：
//   bash build.sh assembleHap --no-daemon   + 一个不存在的 ARK_PYTHON
//       -> 构建失败，并打出本文件下面那条 "cannot run ..." 提示
//   bash build.sh assembleHap（走守护进程）+ 同一个坏值
//       -> 构建通过，ARK_PYTHON 被静默忽略，退回 PATH 上的 python
//   hvigor 守护进程在启动时捕获环境变量，之后从 shell 里设的值进不去。
//   所以真正兜住"换一台机器"的是下面那个 PATH 兜底，ARK_PYTHON 只是
//   方便；而"我明明设了它却没生效"这种静默取错值，靠下面那条日志暴露。
const PYTHON = process.env.ARK_PYTHON || 'python';

function verifyArtifact() {
  return {
    pluginId: 'mindustryark-verify-artifact',
    apply(node) {
      const assemble = node.getTaskByName('assembleHap');
      if (!assemble) {
        console.error('[ARK] assembleHap not found -- verification gate NOT installed');
        throw new Error('verification gate NOT installed');
      }

      const projectRoot = path.dirname(node.getNodePath());
      const script = path.join(projectRoot, 'scripts', 'verify_hap.py');

      assemble.afterRun(() => {
        const product = hvigor.getParameter().getExtParam('product') ?? 'default';
        console.log(`[ARK] verifying artifact (product=${product}, python=${PYTHON}) ...`);
        try {
          execFileSync(PYTHON, [script], {
            env: { ...process.env, ARK_PRODUCT: product },
            stdio: 'inherit',
          });
        } catch (e) {
          // ENOENT 说明解释器本身不存在，而不是脚本报了错。
          // 那种情况下抛出去的原始错误只说 "spawn python ENOENT"，
          // 不告诉你该改哪个变量。
          if ((e as { code?: string } | null)?.code === 'ENOENT') {
            console.error(`[ARK] cannot run "${PYTHON}" -- put python on PATH, or set ARK_PYTHON to its full path`);
          }
          throw e;
        }
        console.log('[ARK] verification PASS');
      });

      console.log('[ARK] artifact verification gate attached');
    },
  };
}

export default {
  system: hapTasks,
  plugins: [verifyArtifact()],
};