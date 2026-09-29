"""
Build the app icon from the user's hand-made source, not from the game atlas.

WHY THIS IS NOT PART OF make_app_icon.py
    That script's job is to DERIVE an icon: it reads the game's sprite atlas,
    checks the atlas by sha1, crops the `arc` frame and paints a gradient behind
    it. This one cannot derive anything -- the artwork is hand-made and lives as
    a 64x64 PNG, so there is no atlas, no frame rect and no gradient constant.
    Folding it in would mean one script with two unrelated truths in it, and the
    atlas gate would start failing for reasons that have nothing to do with
    either icon. Keeping them apart also keeps the old set reproducible: run
    make_app_icon.py and the previous icon comes back.

THE SOURCE
    assets/icon_64.png -- 64x64, opaque content in a 52x52 SQUARE at (6,6)-(57,57),
    the rest transparent. The transparent border is the source file's margin, not
    part of the design; it is cropped away here, and that is the point of this
    script rather than drawing the icon on a 64x64 canvas as-is.

    The file name follows the game's own convention for its icon -- the jar ships
    `icons/icon_64.png` -- so name_size is the pattern: a bigger or smaller
    original would be icon_128.png and so on.

    ⚠️ WHERE THE OTHER REVISIONS LIVE. This one is in the repository, which is why
    the script now works on a fresh clone. The earlier revisions are NOT: they are
    working files in MindustryArkDocs/icon-candidates/handoff/, outside the
    checkout. They are icon.png, icon2.png, icon3.png and icon4.png -- the same
    shape as each other, differing mainly in colour (icon3 and icon4 differ in
    1094 of 4096 pixels and are otherwise identical), so grabbing the wrong one is
    an easy and quiet mistake. That is what SOURCE_SHA256 is for; it stays
    meaningful even now that the file is versioned, because replacing the artwork
    is a normal-looking edit.

THE SCALE, AND WHY IT IS 19
    52 x 19 = 988, so the artwork is scaled up by an integer and NEAREST keeps
    every source pixel exactly 19x19. 1024/52 does not divide, so scaling 52
    straight to 1024 would make some pixels 19 wide and others 20 -- visible as
    uneven banding on a pixel-art icon. 988 leaves 18px (1.8%) of margin, which
    is deliberate: filling a masked icon edge to edge means the system's mask
    clips the outermost row of pixels instead of the background showing through.

THE TWO LAYERS
    background.png  the flat outer blue, sampled from the artwork's own outer
                    band -- (161,197,239), the most common colour there. This
                    matters because the artwork's blue is NOT flat: the band runs
                    (158,193,234) to (168,205,249), so a wrong sample shows up as
                    a visible seam where the mask crops.
    foreground.png  the artwork itself, transparent border cropped, at 19x,
                    centred.

    The smaller sizes are COMPOSITES (background + foreground flattened) because
    that is what startIcon.png and app_icon.png are. They are resized with
    LANCZOS, not NEAREST: at 41px the source's 19x pixels are sub-pixel, and
    nearest-neighbour would drop rows irregularly. The previous icon set made the
    same distinction.

⚠️ Dependency: Pillow, which is not installed globally.
    uv run --with pillow python scripts/make_handmade_icon.py
    uv run --with pillow python scripts/make_handmade_icon.py --check
"""
import io
import os
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("!! Pillow is required:  uv run --with pillow python " + os.path.basename(__file__))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 手工原画，放在仓库里，这样脚本在全新 clone 上也能跑。
# 它以前会去读 MindustryArkDocs，那是刻意不做版本管理的同级目录，
# 结果就是别人谁也没法复现这个图标。
SOURCE = os.path.join(PROJECT_ROOT, "assets", "icon_64.png")

SOURCE_SHA256 = "35bc7bd8092c3c6ca19fe0aeabd99a8798126a90be7e2fe70493fc39d53e2539"

# ⚠️ 裁剪为何偏移一个像素，以及为何它看起来像 bug
#
#     原画的不透明区域是 (6,6)-(57,57)，即 52x52，其几何
#     中心是 31.5。但里面画的内容并不以它为居中：按四个
#     螺栓量，它们的镜像轴在 32.5 —— 整整偏右、偏下
#     一个像素。用户看到结果后说“螺栓不再对称了”，
#     他说得对：在设备上这偏移在 1024 时是 19px，在图标实际
#     绘制的 64px 下约一个像素。
#
#     裁 (6,6,58,58) 会保留这个误差。裁 (7,7,59,59) 则把
#     窗口中心正好落在画面的轴上 —— 残差 0.00px —— 代价是
#     右侧和底部各多出一条透明像素列/行，因为窗口现在
#     越过了不透明区域一个像素。那一条在 1024 时是 19px，
#     而且正好在系统遮罩会裁掉的位置，所以视觉上没有代价。
#
#     按螺栓镜像轴实测两种偏移：
#         crop (6,6,58,58)  轴 26.50，52 窗口内（中心 25.5）  偏 +1.00
#         crop (7,7,59,59)  轴 25.50                              偏  0.00
#
#     ⚠️ 这是原画本身的属性，不是脚本的问题：icon2 和 icon3
#     也有同样的 +1 偏移。如果以后重画原画、让画面
#     在自身边界内居中，这个裁剪必须改回 (6,6,58,58) ——
#     否则就会引入它本就是要消除的那个误差。

CROP = (7, 7, 59, 59)     # 52x52 —— 为何不是 (6,6,58,58)，见下方注释
CANVAS = 1024
UPSCALE = 19              # 整数：52 x 19 = 988
MARGIN = (CANVAS - 52 * UPSCALE) // 2      # 18

# 原画自身的外圈蓝，实测得出（外圈里最常用的颜色）。
BACKGROUND = (161, 197, 239, 255)

# 背景层上的一条深色边。
#
# 为什么非要它不可
#     原画是 52x52 的正方形，系统会在上面套自己的圆角遮罩。
#     遮罩的角在方形内弯的地方，背景就会露出来 —— 而背景
#     原本是平铺的浅蓝，于是看起来就像四个浅色楔形从
#     深灰图标里戳出来。用户的原话：大尺寸下看起来
#     不对。把背景层的边缘涂成深色，正好填掉
#     那些楔形，遮罩的弧线又把这条边变成围绕图标的
#     连续轮廓。
#
# 为什么是 19，为什么是这个颜色
#     19 是放大倍数，所以边框正好一个源像素宽 ——
#     与原画绘制所用单位一致，这样它与画作一致，
#     而不是与画布一致。颜色取自原画自己的螺栓
#     颜色 (64,64,73)，实测得出，这样两处深色是相同而不是
#     仅仅相近。
#
# 把 WIDTH 设为 0 即可恢复之前的平铺背景。
EDGE_COLOR = (64, 64, 73, 255)
#
# ⚠️ 先试的是 19 —— 一个源像素 —— 用户反馈“根本
# 看不见”。他说得对，原因值得记下来：这是一个
# 1024px 的资源，实际显示在约 64px，所以 19px 在屏幕上
# 是 19/1024*64 = 1.2px，而且就在遮罩会吃掉的最边上。
# 这个宽度是看着 250px 预览选出来的，而图标从不会
# 以那个尺寸出现。比较边框宽度要在 64px 下比，不是在预览尺寸下。
EDGE_WIDTH = 0            # 关闭 —— 用户 2026-09-25 决定：不要边框，只用原画

# name -> (size, 是否为平铺背景, 是否为原画层)
# 照抄现有图标集：AppScope 带分层的那一对和六个
# 密度档，entry/ 带自己那份分层对加上 startIcon。
OUTPUTS = [
    ("AppScope/resources/base/media/background.png", 1024, "background"),
    ("AppScope/resources/base/media/foreground.png", 1024, "foreground"),
    ("entry/src/main/resources/base/media/background.png", 1024, "background"),
    ("entry/src/main/resources/base/media/foreground.png", 1024, "foreground"),
    ("entry/src/main/resources/base/media/startIcon.png", 144, "composite"),
    ("AppScope/resources/phone-sdpi/media/app_icon.png", 41, "composite"),
    ("AppScope/resources/phone-mdpi/media/app_icon.png", 54, "composite"),
    ("AppScope/resources/phone-ldpi/media/app_icon.png", 81, "composite"),
    ("AppScope/resources/phone-xldpi/media/app_icon.png", 108, "composite"),
    ("AppScope/resources/phone-xxldpi/media/app_icon.png", 162, "composite"),
    ("AppScope/resources/phone-xxxldpi/media/app_icon.png", 216, "composite"),
]


def sha256f(path):
    import hashlib
    h = hashlib.sha256()
    with io.open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def build_layers():
    """Return (background, foreground) at 1024, built from the source artwork."""
    if not os.path.isfile(SOURCE):
        sys.exit("!! source artwork not found:\n   %s\n"
                 "   Expected in the repository at assets/icon_64.png." % SOURCE)

    # 校验卡的是字节，不是路径：这个原画的早期修订版
    # 形状相同、主要只是颜色不同，所以光看路径
    # 发现不了拿错文件。
    got = sha256f(SOURCE)
    if SOURCE_SHA256 and got != SOURCE_SHA256:
        sys.exit("!! the source artwork changed\n"
                 "   expected sha256 %s\n   actual   sha256 %s\n"
                 "   If the artwork was edited on purpose, update SOURCE_SHA256 "
                 "in this file -- do not just delete the check." % (SOURCE_SHA256, got))

    src = Image.open(SOURCE).convert("RGBA")
    if src.size != (64, 64):
        sys.exit("!! unexpected source size %s -- expected 64x64" % (src.size,))

    art = src.crop(CROP)                                   # 52x52
    fg = art.resize((52 * UPSCALE, 52 * UPSCALE), Image.NEAREST)
    fg_layer = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    fg_layer.alpha_composite(fg, (MARGIN, MARGIN))

    bg_layer = Image.new("RGBA", (CANVAS, CANVAS), BACKGROUND)
    if EDGE_WIDTH > 0:
        # 普通矩形描边，不是圆角：背景本身不能
        # 自带形状。这是一个内缩的边框，在设备上把它
        # 弄圆的是系统的遮罩。
        ImageDraw.Draw(bg_layer).rectangle(
            [0, 0, CANVAS - 1, CANVAS - 1], outline=EDGE_COLOR, width=EDGE_WIDTH)
    return bg_layer, fg_layer


def main():
    check = "--check" in sys.argv
    bg_layer, fg_layer = build_layers()

    composite = bg_layer.copy()
    composite.alpha_composite(fg_layer)

    # 原画底边比色带的其余部分略浅一点；合成整个方形
    # 意味着这会在小尺寸上显示成一条淡淡的
    # 线。这里没什么可做的 —— 记下来是为了万一它在
    # 设备上可见，原因已知。
    for rel, size, kind in OUTPUTS:
        full = os.path.join(PROJECT_ROOT, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        if kind == "background":
            im = bg_layer if size == CANVAS else bg_layer.resize((size, size), Image.LANCZOS)
        elif kind == "foreground":
            im = fg_layer if size == CANVAS else fg_layer.resize((size, size), Image.LANCZOS)
        else:
            im = composite if size == CANVAS else composite.resize((size, size), Image.LANCZOS)
        print("   %-56s %4dx%-5d %s" % (rel, size, size, "check" if check else "written"))
        if not check:
            im.save(full)

    print()
    print("   background  flat %s (the artwork's own outer band)" % (BACKGROUND[:3],))
    print("   foreground  %s cropped to 52x52, upscaled %dx (NEAREST), margin %dpx"
          % (CROP, UPSCALE, MARGIN))
    print("   composite   background + foreground, resized LANCZOS for the small sizes")
    if check:
        print("\n   --check: nothing written")


if __name__ == "__main__":
    main()
