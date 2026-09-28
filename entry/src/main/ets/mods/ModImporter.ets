/* [A]
 * 应用在 Downloads 里的文件夹 —— 而且它已经【不再是】导入器了。
 *
 * ⚠️ 在把任何东西加回来之前，先读这一段。
 *
 * 这个文件过去是干什么的，以及为什么那些东西现在一样都不在这里
 *   它本来有三个职责，而这三个都会由应用【自作主张】地往游戏的 mods 目录里塞文件：
 *
 *     pickMods()       悬浮球的「导入模组」那一行：系统选择器、复制
 *     scanModFolder()  每次启动：把这个 Downloads 文件夹里的任何东西都复制过去
 *     seedProbeMod()   每次启动：无条件种下 probe-mod.jar
 *                      （那个住在 Index.ets 里）
 *
 *   中间那个才是造成损害的那个。它只在 mods 目录里已经存在一个大小相同的文件时才跳过，
 *   所以在游戏里【删掉一个 mod】—— 也就等于把它从沙箱里删掉 —— 下一次启动就会把它带回来，
 *   永远如此。没有办法让一个 mod 保持被删掉的状态，因为 Downloads 里的那份副本
 *   比游戏里的任何一次删除都活得更久。
 *
 *   它还和存档撞车。同一个文件夹正是游戏自己的文件浏览器打开的根目录
 *   （-Darc.sdl.chooserPath），存档导出为 .zip，而扫描又把 .zip 当作 mod 接受 ——
 *   所以放在这里的一个存档就会被当成 mod 一样被扫进 mods 目录。
 *
 *   ⇒ 这三个都在用户的指示下【移除了】。现在这个应用里没有任何东西会写进 mods 目录。
 *     唯一会这么做的只有游戏本身：当玩家使用游戏自己的导入按钮时 —— 那按构造就是手动的，
 *     不需要我们写任何代码。
 *
 * 为什么游戏自己的按钮就足够了
 *   它在这里能用，已在设备上确认过。这个文件更早的一个修订版正是建立在相反的说法上，
 *   而它是怎么走到那一步的值得保留下来：那些测量全都是真的 ——
 *
 *       Platform.showFileChooser 的默认实现会抛
 *           throw new IllegalArgumentException("Not implemented on this platform!")
 *       实现它的那个后端会加载 libarc-filedialogsarm64.so，也就是
 *       tinyfiledialogs（zenity/kdialog/popen），链接 glibc，加载不起来
 *
 *   —— 而由它们得出的结论是错的。从 jar 里读到：`showFileChooser` 只被 DesktopLauncher
 *   引用，而拥有导入按钮的 ModsDialog 用的是 mindustry/ui/FileChooser，也就是游戏【自己】的
 *   游戏内浏览器，纯 Java 跑在 Arc 的 Fi 之上。这条路径上没有任何东西会走到那个抛异常的默认实现。
 *   「真实的测量被拼装成一个错误的结论」是这个项目不得不一再重新学习的失败模式；
 *   见 RELEASE-MAINTENANCE.md 的 2.10。
 *
 * 还剩下什么，以及它为什么仍然存在
 *   文件夹本身。它每次启动都会被创建，它的路径会被发布到 native 侧，因为：
 *
 *     - 游戏的文件浏览器在那里打开，这才让「import mod」以及存档的导入/导出
 *       落在玩家真正够得着的地方。没有它，浏览器会在沙箱内部打开，
 *       看不到玩家放进 Downloads 的任何东西。
 *
 *   ⇒ 所以丢在这里的 mod 仍然可用 —— 只不过必须在游戏的浏览器里【手动挑中】它，
 *     而不是被自动拿走。在设备上实测：这个文件夹在文件管理器里显示为
 *     Download/<bundle name>/，而 user_dirs.txt 把它的路径记为 `mods=`。
 *
 * ⚠️ 名字没有跟上。文件、函数以及磁盘上的状态文件都还叫 mod_folder / ensureModFolder，
 *   而这个东西现在已经是浏览器的根目录了。改名意味着要动桥接格式以及每一处引用它的注释，
 *   那比这次纠正本身值得的改动要大；诚实的记录就是这一段。
 */
import { bundleManager, common } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { fileIo as fs, picker, fileUri, Environment } from '@kit.CoreFileKit';

const DOMAIN = 0x0000;
const TAG = 'MindustryLauncher';

/* [C]
 * 玩家所选文件夹的 URI 存在哪里。
 *
 * 是 URI，不是路径。DOWNLOAD 模式发出来的那份权限是【跟着】URI 走的，
 * 所以把路径写下来、以后再用它重新打开，那就是另一回事了 —— 它只是碰巧
 * 指向同一个目录，而且不携带那份授权。
 */
/* [A]
 * 文件夹在哪里，形式是路径加上一个可选的 URI。
 *
 * 【首行永远是路径】，这样 user_dirs.txt 桥接就能取走第一行，而不必知道后面的内容。
 *
 * 有 URI 的时候就把它留着，因为权限是跟着它走的：在手机上，这个文件夹只能通过
 * 选择器交回来的那份授权才够得着，光有一个路径只会指向同一个目录，
 * 却不携带读它的权利。在平板上没有 URI，路径就够了 ——
 * 那条路走的是平台自己的 Download 目录。
 */
interface ModFolder {
  path: string;
  uri: string;
}

/** [B] 读取已存储的文件夹位置；如果还没有，就返回一对空值。 */
function readModFolder(statePath: string): ModFolder {
  const none: ModFolder = { path: '', uri: '' };
  try {
    if (!fs.accessSync(statePath)) {
      return none;
    }
    const lines: Array<string> = fs.readTextSync(statePath).split('\n');
    const path: string = lines.length > 0 ? lines[0].trim() : '';
    const uri: string = lines.length > 1 ? lines[1].trim() : '';
    if (path === '') {
      return none;
    }
    return { path: path, uri: uri };
  } catch (e) {
    const err = e as BusinessError;
    hilog.warn(DOMAIN, TAG, 'mods: reading the stored folder failed: %{public}s',
               err.message);
    return none;
  }
}

/** [A]
 * 文件夹的路径；如果没有，就是 ''。
 *
 * 之所以导出，是因为 user_dirs.txt 桥接要的正好就是这个，而不该被迫知道这个文件的格式。
 * 它过去读的是 URI，再用 fileUri 解析 —— 一旦路径被直接存下来，那种做法就不再对了，
 * 正是那种会逐渐跑偏的重复知识。
 *
 * ⚠️ 这是剩下的唯一一个导出，而现在正是它让存档的导入/导出能工作：EntryAbility
 * 把它写进桥接，launcher 把它作为 -Darc.sdl.chooserPath 传下去，
 * 游戏的浏览器就在那里打开。
 */
export function modFolderPath(statePath: string): string {
  return readModFolder(statePath).path;
}

function writeModFolder(statePath: string, folder: ModFolder): void {
  const text: string = folder.uri === ''
    ? folder.path + '\n'
    : folder.path + '\n' + folder.uri + '\n';
  const f: fs.File = fs.openSync(statePath,
    fs.OpenMode.CREATE | fs.OpenMode.TRUNC | fs.OpenMode.READ_WRITE);
  try {
    fs.writeSync(f.fd, text);
  } finally {
    fs.closeSync(f);
  }
}

/* [A]
 * 到达这个文件夹的两条路，按值得尝试的顺序排列。
 *
 * ⚠️ 路径排在前面，这是测量结果，不是偏好。在手机上、对 DOWNLOAD 模式刚给我们
 * 建好的那个文件夹实测：
 *
 *     /storage/Users/currentUser/Download/<bundle>        能正常列出
 *     file://docs/storage/Users/currentUser/Download/...  "No such file or directory"
 *
 * URI 不是 fs.listFileSync 能直接接受的东西 —— 指南是用 new fileUri.FileUri(uri).path
 * 来解析它的，上面那个路径正是这么来的。所以路径才是可用的形式，URI 是回退，
 * 留给那种文件夹靠授权（而不是靠路径本身）才够得着的设备。
 *
 * 更早的一个修订版先试 URI，它能用仅仅是因为第二次尝试把它救了回来 ——
 * 而且这么做的时候每次启动都会记一条失败日志。
 */
function listTargets(folder: ModFolder): Array<string> {
  const targets: Array<string> = [];
  if (folder.path !== '') {
    targets.push(folder.path);
  }
  if (folder.uri !== '') {
    targets.push(folder.uri);
  }
  return targets;
}

/** [B] 当文件夹存在、且本应用能读它时为 true。 */
function modFolderUsable(folder: ModFolder): boolean {
  if (folder.path === '' && folder.uri === '') {
    return false;
  }
  for (const target of listTargets(folder)) {
    try {
      fs.listFileSync(target);
      return true;
    } catch (e) {
      /* [B] 试下一个目标 */
    }
  }
  return false;
}

/** [A]
 * 在 Downloads 里创建应用的文件夹，用这台设备支持的那一条路线。
 *
 * 两条是互补的 —— 实测如此，也正是为什么单独任何一条都不够：
 *
 *   平台 Download 目录             getUserDownloadDir() 在平板上可用，
 *                                 在手机上抛异常
 *   DOWNLOAD 模式选择器            在手机上可用，在平板上失败，
 *                                 失败码 13900042
 *
 * 路线 A 走平台自己的 Download 目录，平板能报出来，手机不能。注意这个 API 只返回【路径】——
 * 它根本不检查任何权限（文档自己说的），所以真正算数的是 mkdir 是否会以 EPERM 失败，
 * 而不是这个调用是否成功。
 *
 * 路线 B 是 DOWNLOAD 模式下的选择器：不需要权限、没有 UI，而且它自己会创建
 * Download/<bundle name>/。它返回一个 URI，而授权是跟着那个 URI 走的，
 * 这就是为什么 URI 会和路径一起存下来。
 *
 * 该模式有文档记录的行为，也正是为什么这至少是在手机上能走通的那条路线
 * （官方 save-user-file.md，DOWNLOAD 模式）：
 *
 *     模式特点
 *       * 自动创建在 Download/包名/ 目录。
 *       * 跳过文件选择界面直接保存。
 *       * 返回的 URI 已具备持久化权限，用户可在该 URI 下创建文件。
 *
 * 返回文件夹；如果两条路线都不成，就返回一对空值。
 */
async function createModFolder(ctx: common.UIAbilityContext): Promise<ModFolder> {
  const none: ModFolder = { path: '', uri: '' };

  /* [A]
   * A. 平台自己的 Download 目录 + 我们自己的子目录。
   *
   * 如果它已经在那儿，就什么都不做 —— 从第二次启动起这就是常态 ——
   * 这个检查正是让「被手动删掉了」这件事可恢复的原因。
   */
  try {
    const base: string = Environment.getUserDownloadDir();
    /* [A]
     * 与下面的 mkdir 分开上报。「the platform Download directory is unusable」
     * 这句话涵盖了三种不同的失败 —— API 不受支持、目录够不着、以及写入被拒 ——
     * 而它们含义各不相同。在平板上实测：API 是【有应答】的（它返回
     * /storage/Users/currentUser/Download），而写入被以 EPERM 拒绝，
     * 这和手机上的 "no such api" 不是同一个问题。
     */
    if (base !== '') {
      let name: string = '';
      try {
        const info: bundleManager.BundleInfo = await bundleManager.getBundleInfoForSelf(
          bundleManager.BundleFlag.GET_BUNDLE_INFO_DEFAULT);
        name = info.name;
      } catch (e) {
        const err = e as BusinessError;
        hilog.warn(DOMAIN, TAG, 'mods: no bundle name (%{public}s)', err.message);
      }
      if (name !== '') {
        const dir: string = base + '/' + name;
        let present: boolean = false;
        try {
          present = fs.accessSync(dir);
        } catch (e) {
          const err = e as BusinessError;
          hilog.info(DOMAIN, TAG, 'mods: %{public}s not statable (%{public}s)',
                     dir, err.message);
        }
        if (!present) {
          try {
            fs.mkdirSync(dir, true);
            hilog.info(DOMAIN, TAG, 'mods: created %{public}s', dir);
          } catch (e) {
            const err = e as BusinessError;
            /* [A] 用 INFO，不用 warn。在权限被拒的设备上 —— 本项目拥有的每一台设备都是如此 ——
             * 这是预期结果，不是问题：下面那条选择器路线不需要权限，活儿由它来干。
             * 这里打一条 warning 会在每次启动时虚报狼来了。 */
            hilog.info(DOMAIN, TAG, 'mods: cannot create %{public}s (%{public}s)',
                       dir, err.message);
          }
        }
        const folder: ModFolder = { path: dir, uri: '' };
        if (modFolderUsable(folder)) {
          return folder;
        }
        hilog.info(DOMAIN, TAG, 'mods: %{public}s exists but is not listable', dir);
      }
    }
  } catch (e) {
    const err = e as BusinessError;
    hilog.info(DOMAIN, TAG, 'mods: platform Download directory unusable (%{public}s)',
               err.message);
  }

  /* [B] B. DOWNLOAD 模式下的选择器。 */
  const options: picker.DocumentSaveOptions = new picker.DocumentSaveOptions();
  options.pickerMode = picker.DocumentPickerMode.DOWNLOAD;
  try {
    const view: picker.DocumentViewPicker = new picker.DocumentViewPicker(ctx);
    const uris: Array<string> = await view.save(options);
    if (uris !== undefined && uris.length > 0 && uris[0] !== '') {
      const uri: string = uris[0];
      let path: string = '';
      try {
        path = new fileUri.FileUri(uri).path;
      } catch (e) {
        hilog.warn(DOMAIN, TAG, 'mods: could not resolve %{public}s to a path', uri);
      }
      const folder: ModFolder = { path: path, uri: uri };
      if (modFolderUsable(folder)) {
        hilog.info(DOMAIN, TAG, 'mods: DOWNLOAD mode gave %{public}s', path);
        return folder;
      }
      hilog.warn(DOMAIN, TAG, 'mods: DOWNLOAD mode returned %{public}s, not listable', uri);
    } else {
      hilog.info(DOMAIN, TAG, 'mods: DOWNLOAD mode returned nothing');
    }
  } catch (e) {
    const err = e as BusinessError;
    hilog.error(DOMAIN, TAG, 'mods: DOWNLOAD mode failed: %{public}s (code=%{public}d)',
                err.message, err.code);
  }

  return none;
}

/** [A]
 * 确保这个文件夹存在，每次启动都如此。
 *
 * ⚠️ 它是去【检查】，不是只靠【记住】。更早的一个修订版把文件夹的位置存了一次，
 * 然后就永远信任它，结果玩家删掉的文件夹 —— 或者因为那台设备的路线失败而从未被创建的文件夹 ——
 * 就一直是没了的状态，功能则悄无声息地什么都不做。来自设备的反馈：
 * 「它应该每次启动都检查，缺了就重建，像其他应用那样」。这话是对的，
 * 而且它也是唯一能在卸载后幸存的行为 —— 卸载会把文件夹和授权一并带走。
 *
 * ⚠️ 而且它不再扫描了。它过去以调用 scanModFolder() 结尾，而正是那个调用让被删掉的 mod
 * 复活；见文件头。现在没有任何东西会读这个文件夹的内容。不要把那个加回来，
 * 除非你先想清楚：当玩家在游戏里删掉一个 mod 时应该发生什么 ——
 * 旧答案是「它会回来」，而这就是那个功能被删掉的原因。
 */
export async function ensureModFolder(ctx: common.UIAbilityContext,
                                    statePath: string): Promise<void> {
  const existing: ModFolder = readModFolder(statePath);
  if (modFolderUsable(existing)) {
    return;
  }
  if (existing.path !== '' || existing.uri !== '') {
    hilog.info(DOMAIN, TAG, 'mods: %{public}s is gone -- recreating it', existing.path);
  }

  const folder: ModFolder = await createModFolder(ctx);
  if (folder.path === '' && folder.uri === '') {
    hilog.warn(DOMAIN, TAG,
               'mods: could not create the folder in Downloads on this device -- '
               + 'the game\'s file browser will open inside the sandbox instead');
    return;
  }
  try {
    writeModFolder(statePath, folder);
  } catch (e) {
    const err = e as BusinessError;
    hilog.error(DOMAIN, TAG, 'mods: storing the folder failed: %{public}s', err.message);
  }
}
