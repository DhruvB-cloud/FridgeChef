r"""
tools/make_assets.py
--------------------
WHY THIS FILE EXISTS:
    This DEVELOPER tool makes the app's pictures: the fridge container pictures, the small icons
    (tab bar, headers, Profile tab), the launcher icon, the wood / leather / background textures
    and the rounded button shapes. Emoji pictures come from Google's Noto Emoji 2D set (downloaded),
    with the Windows emoji font (Segoe UI Emoji) as a fallback - so run it on Windows. The output
    files are committed in the assets/ folder and bundled with the app; this script is NOT part of
    the app itself.

RUN (from the FridgeChef folder):   .\.venv\Scripts\python tools\make_assets.py
ONLY THE FRIDGE CONTAINER PICTURES: .\.venv\Scripts\python tools\make_assets.py containers
ONLY THE WOOD / LEATHER TEXTURES:  .\.venv\Scripts\python tools\make_assets.py textures
ONLY THE SMALL ICONS + APP ICON:    .\.venv\Scripts\python tools\make_assets.py icons
(The recipe PHOTOS come from Wikimedia Commons - see tools/fetch_recipe_photos.py.)
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFilter, ImageFont   # noqa: E402

from app.images import ICONS_DIR, gradient                     # noqa: E402

EMOJI_FONT = "seguiemj.ttf"          # Windows colour emoji font

# Small icons used by the UI: file name -> emoji.
ICONS = {
    "tab_fridge": "\U0001F966",      # broccoli
    "tab_recipes": "\U0001F372",     # pot of food
    "tab_cookbook": "\U0001F4D6",    # open book
    "tab_calendar": "\U0001F4C5",    # calendar
    "tab_profile": "\U0001F9D1\u200D\U0001F373",   # cook (person + frying pan = a chef)
    "fire": "\U0001F525",            # streak flame
    "trophy": "\U0001F3C6",          # longest streak
    "star": "⭐",                # favourite dish
    "plate": "\U0001F37D",           # meals cooked / empty states
    "muscle": "\U0001F4AA",          # protein
    "grain": "\U0001F33E",           # carbs
    "bolt": "⚡",                # calories
    "timer": "⏱",               # preparation time
    "heart": "\U0001F496",           # sparkling heart - the "love" easter egg
    "party": "\U0001F389",           # party popper - the "Yay, you cooked!" message
    "camera": "\U0001F4F7",          # camera - add a photo of your dish
}


# Version 4.7: every emoji picture (fridge containers, tab bar, Profile icons, app icon) comes from
# Google's free Noto Emoji set - clean 2D pictures (Apache licence, assets/icons/NOTO_LICENSE.txt).
# A failed download falls back to the Windows colour emoji font.
NOTO_URL = "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/2D/png/512/emoji_u{0}.png"
_NOTO_CACHE = {}                                         # emoji -> downloaded picture (each fetched once)


def noto_code(char):
    """The file-name code of an emoji: '\U0001F9D1\u200D\U0001F373' (cook) -> '1f9d1_200d_1f373'.
    (U+FE0F, the invisible 'show as emoji' mark, is not part of Noto's file names.)"""
    return "_".join(f"{ord(c):x}" for c in char if ord(c) != 0xFE0F)


def download_noto(char):
    """Download the 512 x 512 Noto 2D picture of one emoji (or raise OSError)."""
    import io, ssl, urllib.request
    import certifi                                         # trusted certificates for HTTPS
    if char not in _NOTO_CACHE:
        context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(NOTO_URL.format(noto_code(char)), context=context, timeout=30) as answer:
            _NOTO_CACHE[char] = Image.open(io.BytesIO(answer.read())).convert("RGBA")
    return _NOTO_CACHE[char].copy()


def emoji_image(char, size):
    """One emoji as a transparent RGBA image, cropped tightly and scaled to fit `size` x `size`."""
    try:
        glyph = download_noto(char)
        glyph = glyph.crop(glyph.getchannel("A").getbbox())              # cut away the empty border
        scale = size / max(glyph.size)                                   # fit inside size x size
        return glyph.resize((max(1, round(glyph.width * scale)), max(1, round(glyph.height * scale))),
                            Image.LANCZOS)
    except OSError as error:
        print(f"  (could not download Noto {noto_code(char)}: {error} - using the emoji font)")
    font = ImageFont.truetype(EMOJI_FONT, 256)
    canvas = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).text((40, 40), char, font=font, embedded_color=True)
    box = canvas.getbbox()                                # tight box around the visible pixels
    if not box:
        raise ValueError(f"Emoji {char!r} not available in {EMOJI_FONT}")
    glyph = canvas.crop(box)
    glyph.thumbnail((size, size), Image.LANCZOS)          # fit inside size x size
    return glyph


def make_round_shape(out_path, size, radius, fill=(255, 255, 255), ring=None, ring_width=0):
    """A white rounded square used as a stretchable ('9-slice') background by the UI.

    Kivy multiplies these pixels by the widget's background_color, so ONE white image gives
    rounded buttons in any colour. Drawn 4x larger and shrunk, which smooths the curved edges.
    """
    s = 4                                                 # supersampling factor for smooth corners
    big = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle([0, 0, size * s - 1, size * s - 1], radius=radius * s, fill=fill + (255,))
    if ring:                                              # focus ring for text inputs
        d.rounded_rectangle([0, 0, size * s - 1, size * s - 1], radius=radius * s,
                            outline=ring + (255,), width=ring_width * s)
    big.resize((size, size), Image.LANCZOS).save(out_path, "PNG")


def make_ui_shapes():
    ui_dir = os.path.join(os.path.dirname(ICONS_DIR), "ui")
    os.makedirs(ui_dir, exist_ok=True)
    make_round_shape(os.path.join(ui_dir, "round.png"), 64, 22)                          # buttons
    make_round_shape(os.path.join(ui_dir, "round_pressed.png"), 64, 22, fill=(222, 222, 222))
    make_round_shape(os.path.join(ui_dir, "round_focus.png"), 64, 22, ring=(122, 178, 132), ring_width=3)
    make_round_shape(os.path.join(ui_dir, "round_big.png"), 96, 34)                      # popups
    print("ui shapes ->", ui_dir)


def make_app_icon(out_path, size=512):
    """The launcher icon on the phone's home screen: an emerald rounded square, a white plate and
    the 2D pot of food (version 4.7)."""
    s = 4                                                   # draw 4x bigger, then shrink = smooth edges
    big = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    bg = gradient((size * s, size * s), (84, 199, 133), (26, 140, 107)).convert("RGBA")   # light -> deep emerald
    mask = Image.new("L", bg.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, bg.width - 1, bg.height - 1], radius=size * s // 5, fill=255)
    big.paste(bg, (0, 0), mask)                             # rounded green square
    plate = int(size * s * 0.66)                            # white plate in the middle
    off = (size * s - plate) // 2
    ImageDraw.Draw(big).ellipse([off, off, off + plate, off + plate], fill=(255, 255, 255, 255))
    icon = big.resize((size, size), Image.LANCZOS)
    pot = emoji_image("\U0001F372", int(size * 0.5))         # the pot of food on the plate
    icon.alpha_composite(pot, ((size - pot.width) // 2, (size - pot.height) // 2))
    icon.save(out_path, "PNG")


def blank_calendar(icon):
    """Paint over the "July" and "17" on the Noto calendar and draw a small grid of days instead.

    (Version 4.7.1: Dhruv asked for no specific date on the Calendar icon.) The positions are
    fractions of the icon size, measured on the Noto picture, so this works at any size.
    """
    from PIL import ImageDraw                      # Pillow's simple shape-drawing tool
    w, h = icon.size
    draw = ImageDraw.Draw(icon)
    red = icon.getpixel((w // 2, int(h * 0.08)))   # the header's red, taken from the picture itself
    page = icon.getpixel((w // 2, int(h * 0.42)))  # the page's off-white, just under the header
    draw.rectangle((w * 0.25, h * 0.11, w * 0.72, h * 0.37), fill=red)    # hide "July"
    draw.rectangle((w * 0.20, h * 0.44, w * 0.80, h * 0.88), fill=page)   # hide "17"
    cols, rows = 4, 3                              # a 4 x 3 grid of little day squares
    left, top, right, bottom = w * 0.22, h * 0.48, w * 0.78, h * 0.85     # the area they fill
    cell_w, cell_h = (right - left) / cols, (bottom - top) / rows        # room for one day
    gap = w * 0.035                                # space between the squares
    for r in range(rows):
        for c in range(cols):
            x0, y0 = left + c * cell_w + gap / 2, top + r * cell_h + gap / 2   # top-left of this day
            draw.rounded_rectangle((x0, y0, x0 + cell_w - gap, y0 + cell_h - gap),
                                   radius=w * 0.02, fill=(208, 208, 208, 255))   # soft grey day
    return icon


# Version 4.7.1: the avatars a new user picks from (the names must match app.images.AVATARS).
AVATAR_EMOJI = {
    "chef": "\U0001F9D1‍\U0001F373",   # cook
    "cat": "\U0001F431",                     # cat face
    "panda": "\U0001F43C",                   # panda
    "fox": "\U0001F98A",                     # fox
    "bear": "\U0001F43B",                    # bear
    "rabbit": "\U0001F430",                  # rabbit face
    "robot": "\U0001F916",                   # robot
    "cupcake": "\U0001F9C1",                 # cupcake
}


def make_avatars(size=256):
    """Save every avatar as assets/avatars/<name>.png (Noto 2D, 256 x 256, transparent)."""
    from app.images import AVATARS, AVATARS_DIR    # the app's list - so both always agree
    assert set(AVATAR_EMOJI) == set(AVATARS), "AVATAR_EMOJI and app.images.AVATARS differ"
    os.makedirs(AVATARS_DIR, exist_ok=True)        # create assets/avatars the first time
    for name in AVATARS:
        make_icon(name, AVATAR_EMOJI[name], os.path.join(AVATARS_DIR, f"{name}.png"), size=size)


def make_icon(name, char, out_path, size=128):
    """One small square icon: the emoji `char`, centred (Noto 2D, see emoji_image)."""
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glyph = emoji_image(char, int(size * 0.9))
    icon.alpha_composite(glyph, ((size - glyph.width) // 2, (size - glyph.height) // 2))   # centred
    if name == "tab_calendar":                     # 4.7.1: no fixed date ("July 17") on the icon
        icon = blank_calendar(icon)
    icon.save(out_path, "PNG")
    print("icon:", name)


# ----------------------------------------------------------------------------------------------
# FRIDGE CONTAINER PICTURES (version 4.7: 2D)
# ----------------------------------------------------------------------------------------------
# Each container (jar, bottle, ...) is a picture. It comes from, in this order:
#   1. YOUR OWN picture, if you put one in  assets/icons/custom/<kind>.png  (e.g. custom/jar.png)
#   2. otherwise Google's free Noto Emoji 2D set (Apache licence, see assets/icons/NOTO_LICENSE.txt)
# The tool trims the empty space around the picture, saves it as assets/icons/container_<kind>.png,
# makes the mouldy "expired" version, and writes assets/icons/containers.json - the picture sizes
# and where the app puts the cream name sticker. The app reads that file, so new pictures just work.
CUSTOM_DIR = os.path.join(ICONS_DIR, "custom")           # drop your own <kind>.png files here

# kind -> (emoji, where the name sticker goes as fractions of the picture:
#          centre x, centre y (from the top), width, height)
CONTAINER_SOURCES = {
    "jar": ("\U0001FAD9", (0.50, 0.58, 0.80, 0.26)),
    "bottle": ("\U0001F376", (0.50, 0.68, 0.84, 0.24)),       # only the bottle - the cup is cut away
    "dish": ("\U0001F35B", (0.50, 0.74, 0.62, 0.26)),
    "carton": ("\U0001F9C3", (0.50, 0.66, 0.72, 0.22)),
    "can": ("\U0001F96B", (0.50, 0.58, 0.80, 0.26)),
    "tub": ("\U0001F963", (0.50, 0.70, 0.62, 0.26)),
    "box": ("\U0001F371", (0.50, 0.62, 0.62, 0.26)),
    "basket": ("\U0001F9FA", (0.50, 0.70, 0.60, 0.25)),
    "pot": ("\U0001F372", (0.50, 0.74, 0.54, 0.24)),
    "glass": ("\U0001F95B", (0.50, 0.62, 0.66, 0.22)),
    "greens": ("\U0001F96C", (0.50, 0.62, 0.64, 0.22)),
    "takeout": ("\U0001F961", (0.50, 0.70, 0.60, 0.22)),
}


def _only_the_bottle(img):
    """The 'sake' picture is a bottle WITH a small cup in front of it, on the left. Keep only the
    bottle (it is symmetric, so its right half tells us its shape):
      1. the bottle's middle = the middle of its neck (the top quarter shows only the neck),
      2. its left edge = the right edge mirrored around that middle,
      3. the cup's top = the highest point left of the bottle,
      4. below that, repaint the left half: the bottle's own colour from just above the cup,
         with the outline of the mirrored right half."""
    img = img.crop(img.getchannel("A").getbbox())
    alpha, w, h = img.getchannel("A"), img.width, img.height
    neck = [x for x in range(w) if any(alpha.getpixel((x, y)) > 128 for y in range(0, h // 4, 4))]
    centre = (min(neck) + max(neck)) // 2                  # 1. the middle of the neck
    left = max(0, 2 * centre - (w - 1))                    # 2. mirror of the right edge
    cup_top = min(y for y in range(h) for x in range(0, left, 3) if alpha.getpixel((x, y)) > 128)   # 3.
    img = img.crop((left, 0, w, h))                        # drop everything left of the bottle
    px, centre = img.load(), centre - left
    for y in range(cup_top - 2, img.height):               # 4. repaint where the cup was
        for x in range(centre):
            r, g, b, _ = px[x, cup_top - 4]                # colour just above the cup...
            px[x, y] = (r, g, b, px[2 * centre - x, y][3])  # ...with the mirrored outline
    return img


def _trim(img, pad=0.04):
    """Cut away the empty transparent border, then leave a small even margin."""
    img = img.crop(img.getchannel("A").getbbox())
    m = int(max(img.size) * pad)
    framed = Image.new("RGBA", (img.width + 2 * m, img.height + 2 * m), (0, 0, 0, 0))
    framed.alpha_composite(img, (m, m))
    return framed


def _gone_bad(img, label_box, seed):
    """The 'expired' look: tint the whole picture green and sprinkle darker mould spots on it.
    No spots on the name sticker, so the item's name stays readable."""
    green = Image.new("RGBA", img.size, (118, 176, 78, 255))          # mouldy green
    tinted = Image.blend(img, green, 0.5)                              # half green over the colours
    spots = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(spots)
    rng = random.Random(seed)                                          # same spots every run
    left, top, right, bottom = label_box
    placed = 0
    while placed < 12:
        r = rng.randint(img.width // 40, img.width // 18)
        x, y = rng.randint(0, img.width), rng.randint(img.height // 6, img.height)
        if left - r < x < right + r and top - r < y < bottom + r:     # would touch the sticker: skip
            continue
        placed += 1
        d.ellipse([x - r, y - r, x + r, y + r], fill=(60, 110, 45, 150))
    tinted = Image.alpha_composite(tinted, spots)
    tinted.putalpha(img.getchannel("A"))                               # keep the original outline
    return tinted


def make_container_icons():
    """Make every container picture (+ expired version) and assets/icons/containers.json."""
    import json
    art = {}
    for kind, (char, (cx, cy, fw, fh)) in CONTAINER_SOURCES.items():
        custom = os.path.join(CUSTOM_DIR, f"{kind}.png")
        if os.path.exists(custom):                         # 1. your own picture wins
            img, source = Image.open(custom).convert("RGBA"), "custom"
        else:                                              # 2. the Noto 2D picture
            img, source = download_noto(char), "Noto 2D"
            if kind == "bottle":
                img = _only_the_bottle(img)
        img = _trim(img)
        if max(img.size) > 320:                            # big custom pictures: shrink (keeps the app small)
            img.thumbnail((320, 320), Image.LANCZOS)
        w, h = img.size
        label = [round((cx - fw / 2) * w), round((cy - fh / 2) * h),     # left, top,
                 round((cx + fw / 2) * w), round((cy + fh / 2) * h)]     # right, bottom (y = 0 at the top)
        img.save(os.path.join(ICONS_DIR, f"container_{kind}.png"), "PNG")
        _gone_bad(img, label, kind).save(os.path.join(ICONS_DIR, f"container_{kind}_expired.png"), "PNG")
        art[kind] = {"size": [w, h], "label": label}
        print(f"container {kind:8} {w}x{h}  ({source})")
    with open(os.path.join(ICONS_DIR, "containers.json"), "w", encoding="utf-8") as f:
        json.dump(art, f, indent=2)                        # the app reads sizes + sticker spots from here


def _streaks(size, rows, sigma, seed):
    """Grey noise stretched tall: random dots squeezed into `rows` lines, then pulled to full
    height - which turns them into long vertical streaks, like the grain of wood."""
    random.seed(seed)                                     # effect_noise uses Python's random numbers
    w, h = size
    noise = Image.effect_noise((w, rows), sigma)          # grey noise, mostly mid-grey
    return noise.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(1))


def make_oak_texture(out_path, size=(768, 1280)):
    """Light oak planks for the Recipes 'kitchen counter'."""
    from PIL import ImageChops, ImageOps
    w, h = size
    grain = ImageChops.add(_streaks(size, 10, 40, 1), _streaks(size, 60, 25, 2), scale=2)   # broad + fine grain
    wood = ImageOps.colorize(ImageOps.autocontrast(grain, cutoff=2),
                             black=(190, 144, 98), white=(224, 188, 140))   # dark -> light oak (soft contrast)
    d = ImageDraw.Draw(wood)
    plank = w // 4                                        # four planks across
    rng = random.Random(3)
    for i in range(4):
        shade = rng.randint(-10, 10)                      # each plank a slightly different tone
        overlay = Image.new("RGB", (plank, h), (128 + shade,) * 3)
        part = wood.crop((i * plank, 0, (i + 1) * plank, h))
        wood.paste(ImageChops.overlay(part, overlay), (i * plank, 0))
        if i:
            d.line([(i * plank, 0), (i * plank, h)], fill=(140, 98, 60), width=3)   # seam between planks
    wood.save(out_path, "JPEG", quality=88)


def make_leather_texture(out_path, size=(512, 768)):
    """Brown leather for the Cookbook cover."""
    from PIL import ImageOps
    random.seed(4)
    grain = Image.effect_noise(size, 30).filter(ImageFilter.GaussianBlur(1.2))
    leather = ImageOps.colorize(ImageOps.autocontrast(grain, cutoff=1),
                                black=(92, 46, 34), white=(140, 76, 56))
    leather.save(out_path, "JPEG", quality=88)


def make_app_background(out_path, size=(540, 1170)):
    """The soft, colourful app background: big blurred colour blobs on warm cream (a 'mesh gradient')."""
    w, h = size
    img = Image.new("RGB", size, (250, 245, 238))
    blobs = Image.new("RGB", size, (250, 245, 238))
    d = ImageDraw.Draw(blobs)
    for (cx, cy, r, color) in ((0.10, 0.08, 0.45, (255, 214, 190)),    # peach, top left
                               (0.95, 0.22, 0.40, (205, 236, 214)),    # mint, top right
                               (0.15, 0.60, 0.42, (255, 238, 196)),    # butter, middle left
                               (0.90, 0.85, 0.48, (222, 214, 250)),    # lavender, bottom right
                               (0.30, 1.00, 0.35, (255, 220, 214))):   # rose, bottom
        x, y, rr = cx * w, cy * h, r * w
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=color)
    img = Image.blend(img, blobs.filter(ImageFilter.GaussianBlur(w * 0.16)), 0.85)   # very soft edges
    img.save(out_path, "JPEG", quality=90)


def make_textures():
    ui_dir = os.path.join(os.path.dirname(ICONS_DIR), "ui")
    make_oak_texture(os.path.join(ui_dir, "oak.jpg"))
    make_leather_texture(os.path.join(ui_dir, "leather.jpg"))
    make_app_background(os.path.join(ui_dir, "app_bg.jpg"))
    print("textures -> assets/ui/oak.jpg, leather.jpg, app_bg.jpg")


if __name__ == "__main__":
    if sys.argv[1:] == ["containers"]:            # "make_assets.py containers" = only the fridge container pictures
        make_container_icons()
        sys.exit()
    if sys.argv[1:] == ["avatars"]:               # "make_assets.py avatars" = only the profile avatars
        make_avatars()
        sys.exit()
    if sys.argv[1:] == ["textures"]:              # "make_assets.py textures" = only the wood + leather
        make_textures()
        sys.exit()
    if sys.argv[1:] == ["icons"]:                 # "make_assets.py icons" = only the small icons + app icon
        for name, char in ICONS.items():
            make_icon(name, char, os.path.join(ICONS_DIR, f"{name}.png"))
        make_app_icon(os.path.join(os.path.dirname(ICONS_DIR), "app_icon.png"))
        sys.exit()
    os.makedirs(ICONS_DIR, exist_ok=True)
    for name, char in ICONS.items():
        make_icon(name, char, os.path.join(ICONS_DIR, f"{name}.png"))
    make_container_icons()
    make_textures()
    make_ui_shapes()
    make_app_icon(os.path.join(os.path.dirname(ICONS_DIR), "app_icon.png"))   # assets/app_icon.png
    print("app icon -> assets/app_icon.png")
