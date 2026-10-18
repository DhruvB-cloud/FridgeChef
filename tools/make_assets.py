r"""
tools/make_assets.py
--------------------
WHY THIS FILE EXISTS:
    "Each recipe should have an image by default." This DEVELOPER tool draws a soft, illustrated
    picture for every built-in recipe (pastel background, a plate, the dish and a few ingredients)
    plus the small icons used by the tab bar and the Profile tab.

    It uses the colourful emoji font that ships with Windows 10/11 (Segoe UI Emoji), so run it on
    Windows. The output PNG/JPG files are committed in the assets/ folder and bundled with the app,
    so phones never need the font - this script is NOT part of the app itself.

RUN (from the FridgeChef folder):   .\.venv\Scripts\python tools\make_assets.py
ONLY THE JAR / BOTTLE / DISH ICONS: .\.venv\Scripts\python tools\make_assets.py containers
ONLY THE WOOD / LEATHER TEXTURES:  .\.venv\Scripts\python tools\make_assets.py textures
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFilter, ImageFont   # noqa: E402

from app.images import CONTAINER_ART, ICONS_DIR, RECIPE_IMAGES_DIR, gradient   # noqa: E402
from app.seed_recipes import SEED_RECIPES                       # noqa: E402

EMOJI_FONT = "seguiemj.ttf"          # Windows colour emoji font
SIZE = 800                           # recipe pictures are 800 x 800 pixels

# Main dish emoji + up to three garnish emojis for every built-in recipe (by uid).
ART = {
    "masala-omelette": ("\U0001F373", "\U0001F9C5\U0001F345\U0001F336"),
    "vegetable-poha": ("\U0001F35A", "\U0001F95C\U0001F34B\U0001F954"),
    "jeera-rice": ("\U0001F35A", "\U0001F9C8\U0001F33F"),
    "dal-tadka": ("\U0001F372", "\U0001F9C4\U0001F345\U0001F33F"),
    "cucumber-raita": ("\U0001F952", "\U0001F963\U0001F33F"),
    "paneer-bhurji": ("\U0001F958", "\U0001F9C0\U0001FAD1\U0001F9C5"),
    "chicken-curry": ("\U0001F35B", "\U0001F357\U0001F9C5\U0001F336"),
    "aloo-tikki": ("\U0001F954", "\U0001F33F\U0001F336"),
    "vegetable-pulao": ("\U0001F35A", "\U0001F955\U0001F9C5\U0001F33D"),
    "hummus": ("\U0001F963", "\U0001F9C6\U0001F34B\U0001FAD2"),
    "shakshuka": ("\U0001F958", "\U0001F373\U0001F345\U0001FAD1"),
    "fattoush-salad": ("\U0001F957", "\U0001F952\U0001F345\U0001F34B"),
    "chicken-shawarma-bowl": ("\U0001F32F", "\U0001F357\U0001F35A\U0001F952"),
    "mujaddara": ("\U0001F372", "\U0001F9C5\U0001F35A"),
    "scrambled-eggs-on-toast": ("\U0001F35E", "\U0001F373\U0001F9C8"),
    "porridge-with-fruit": ("\U0001F963", "\U0001F34C\U0001F36F"),
    "jacket-potato-with-beans": ("\U0001F954", "\U0001FAD8\U0001F9C0\U0001F9C8"),
    "tomato-soup": ("\U0001F963", "\U0001F345\U0001F9C4\U0001F33F"),
    "fruit-yogurt-bowl": ("\U0001F34E", "\U0001F34C\U0001F36F\U0001F95B"),
    "cottage-pie": ("\U0001F967", "\U0001F954\U0001F955\U0001F969"),
    "cheese-toastie": ("\U0001F96A", "\U0001F9C0\U0001F345"),
}

# Soft background colours per cuisine: (top, bottom).
CUISINE_COLORS = {
    "Indian": ((255, 236, 218), (252, 205, 170)),    # warm peach / saffron
    "Arabic": ((246, 238, 220), (222, 214, 172)),    # sand / soft olive
    "English": ((228, 236, 250), (205, 212, 240)),   # sky / lavender
}

# Small icons used by the UI: file name -> emoji.
ICONS = {
    "tab_fridge": "\U0001F966",      # broccoli
    "tab_recipes": "\U0001F372",     # pot of food
    "tab_cookbook": "\U0001F4D6",    # open book
    "tab_calendar": "\U0001F4C5",    # calendar
    "tab_profile": "\U0001F9D1",     # person
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


def emoji_image(char, size):
    """Render one emoji as a transparent RGBA image, cropped tightly and scaled to `size`."""
    font = ImageFont.truetype(EMOJI_FONT, 256)
    canvas = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).text((40, 40), char, font=font, embedded_color=True)
    box = canvas.getbbox()                                # tight box around the visible pixels
    if not box:
        raise ValueError(f"Emoji {char!r} not available in {EMOJI_FONT}")
    glyph = canvas.crop(box)
    glyph.thumbnail((size, size), Image.LANCZOS)          # fit inside size x size
    return glyph


def soft_shadow(size, box, blur, alpha):
    """A blurred ellipse used as a soft drop shadow."""
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse(box, fill=alpha)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def make_recipe_image(recipe, out_path):
    rng = random.Random(recipe.uid)                       # same "random" layout every run
    top, bottom = CUISINE_COLORS.get(recipe.cuisine, CUISINE_COLORS["English"])
    img = gradient((SIZE, SIZE), top, bottom).convert("RGBA")

    # Decorative soft bubbles in the background.
    bubbles = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bubbles)
    for _ in range(7):
        r = rng.randint(40, 130)
        x, y = rng.randint(0, SIZE), rng.randint(0, SIZE)
        bd.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 55))
    img = Image.alpha_composite(img, bubbles.filter(ImageFilter.GaussianBlur(6)))

    # Plate: shadow, white disc, faint inner rim.
    shadow = soft_shadow((SIZE, SIZE), [150, 190, 650, 690], 28, 90)
    img.paste((90, 70, 50, 255), (0, 0), shadow)
    d = ImageDraw.Draw(img)
    d.ellipse([140, 140, 660, 660], fill=(255, 255, 255, 255))
    d.ellipse([185, 185, 615, 615], outline=(240, 236, 230, 255), width=6)

    main, garnish = ART.get(recipe.uid, ("\U0001F37D", ""))
    hero = emoji_image(main, 340)
    img.alpha_composite(hero, ((SIZE - hero.width) // 2, (SIZE - hero.height) // 2))

    # Garnishes around the plate, slightly rotated for a hand-placed look.
    spots = [(70, 70), (590, 90), (600, 590), (80, 600)]
    rng.shuffle(spots)
    for char, (x, y) in zip(garnish, spots):
        g = emoji_image(char, 130).rotate(rng.randint(-25, 25), expand=True, resample=Image.BICUBIC)
        img.alpha_composite(g, (x, y))

    img.convert("RGB").save(out_path, "JPEG", quality=88)


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
    """The launcher icon on the phone's home screen: a sage-green rounded square with a pot of food."""
    s = 4                                                   # draw 4x bigger, then shrink = smooth edges
    big = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    bg = gradient((size * s, size * s), (150, 200, 158), (95, 160, 108)).convert("RGBA")   # light -> darker sage
    mask = Image.new("L", bg.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, bg.width - 1, bg.height - 1], radius=size * s // 5, fill=255)
    big.paste(bg, (0, 0), mask)                             # rounded green square
    plate = int(size * s * 0.66)                            # white plate in the middle
    off = (size * s - plate) // 2
    ImageDraw.Draw(big).ellipse([off, off, off + plate, off + plate], fill=(255, 255, 255, 255))
    icon = big.resize((size, size), Image.LANCZOS)
    pot = emoji_image("\U0001F372", int(size * 0.46))       # the pot-of-food emoji on the plate
    icon.alpha_composite(pot, ((size - pot.width) // 2, (size - pot.height) // 2))
    icon.save(out_path, "PNG")


def make_icon(char, out_path, size=128):
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glyph = emoji_image(char, int(size * 0.86))
    icon.alpha_composite(glyph, ((size - glyph.width) // 2, (size - glyph.height) // 2))
    icon.save(out_path, "PNG")


def _icon_canvas(kind):
    """A transparent canvas 4x bigger than the final picture (shrinking it later smooths the edges).

    Returns (image, drawer, s): s() turns design units (see CONTAINER_ART) into canvas pixels.
    """
    w, h = CONTAINER_ART[kind]["size"]
    big = Image.new("RGBA", (w * 4, h * 4), (0, 0, 0, 0))
    return big, ImageDraw.Draw(big), lambda *v: [round(x * 4) for x in v]


def _label_box(kind):
    """Where the cream name label goes (the app writes the item's name on it)."""
    return CONTAINER_ART[kind]["label"]


def _gone_bad(img, kind):
    """The 'expired' look: tint the whole picture green and sprinkle darker mould spots on it.

    No spots on the label, so the item's name stays readable.
    """
    rgba = img.copy()
    green = Image.new("RGBA", img.size, (118, 176, 78, 255))          # mouldy green
    tinted = Image.blend(rgba, green, 0.55)                            # 55 % green over the colours
    spots = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(spots)
    rng = random.Random(kind)                                          # same spots every run
    left, top, right, bottom = _label_box(kind)
    placed = 0
    while placed < 12:
        r = rng.randint(img.width // 40, img.width // 18)
        x, y = rng.randint(0, img.width), rng.randint(img.height // 6, img.height)
        if left - r < x < right + r and top - r < y < bottom + r:     # would touch the label: skip
            continue
        placed += 1
        d.ellipse([x - r, y - r, x + r, y + r], fill=(70, 120, 50, 170))
    tinted = Image.alpha_composite(tinted, spots)
    tinted.putalpha(img.getchannel("A"))                               # keep the original outline
    return tinted


def _finish_icon(big, kind, shadow_box):
    """Add a soft shadow, shrink to the final size and save the normal + the expired picture."""
    shadow = soft_shadow(big.size, shadow_box, 40, 70)                 # blurred ellipse under it
    base = Image.new("RGBA", big.size, (0, 0, 0, 0))
    base.paste((20, 40, 70, 255), (0, 0), shadow)                      # dark blue-grey shadow...
    base.alpha_composite(big)                                          # ...with the drawing on top
    final = base.resize(CONTAINER_ART[kind]["size"], Image.LANCZOS)
    final.save(os.path.join(ICONS_DIR, f"container_{kind}.png"), "PNG")
    _gone_bad(final, kind).save(os.path.join(ICONS_DIR, f"container_{kind}_expired.png"), "PNG")


def _gradient(size, stops, horizontal=False):
    """An RGBA picture filled with a colour gradient through `stops` = [(position 0-1, RGBA), ...].
    horizontal=True runs left -> right (round things: dark edges, bright highlight = 3D)."""
    w, h = size
    n = w if horizontal else h
    strip = Image.new("RGBA", (n, 1))
    px = strip.load()
    for i in range(n):
        t = i / max(n - 1, 1)
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if t <= p1 or p1 == stops[-1][0]:
                k = (t - p0) / (p1 - p0) if p1 > p0 else 0
                px[i, 0] = tuple(int(a + (b - a) * min(max(k, 0), 1)) for a, b in zip(c0, c1))
                break
    if horizontal:
        return strip.resize((w, h), Image.NEAREST)
    return strip.resize((h, 1)).transpose(Image.ROTATE_270).resize((w, h), Image.NEAREST)


class _Filled:
    """Wraps an ImageDraw so every shape is FILLED (Pillow otherwise draws only the outline)."""

    def __init__(self, draw):
        self.draw = draw

    def __getattr__(self, name):
        method = getattr(self.draw, name)
        return lambda *args, **kwargs: method(*args, **{"fill": 255, **kwargs})


def _shape(big, draw, fill):
    """Paint `fill` (a gradient picture) inside the shape that `draw(ImageDraw)` draws."""
    mask = Image.new("L", big.size, 0)
    draw(_Filled(ImageDraw.Draw(mask)))
    layer = Image.new("RGBA", big.size, (0, 0, 0, 0))
    layer.paste(fill, (0, 0), mask)
    big.alpha_composite(layer)


def _mix(c, other, k):
    """Blend colour c towards `other` by k (0-1). Works on RGB or RGBA tuples."""
    return tuple(int(a + (b - a) * k) for a, b in zip(c, other))


def _round(c, alpha=255):
    """Gradient stops that make a flat colour look round (cylinder): dark edge, bright highlight."""
    c = tuple(c[:3]) + (alpha,)
    dark, light = _mix(c, (0, 0, 0, alpha), 0.28), _mix(c, (255, 255, 255, alpha), 0.45)
    return [(0, dark), (0.16, light), (0.42, c), (0.85, _mix(c, (0, 0, 0, alpha), 0.12)), (1, dark)]


def _label(big, s, box, accent=None):
    """The cream name label (the app writes the item's name on it), softly shaded."""
    _shape(big, lambda d: d.rounded_rectangle(s(*box), radius=36),
           _gradient(big.size, [(0, (255, 252, 243, 255)), (1, (243, 233, 212, 255))]))
    d = ImageDraw.Draw(big)
    l, t, r, b = box
    d.rounded_rectangle(s(*box), radius=36, outline=(225, 208, 178, 255), width=6)
    if accent:                                            # two thin coloured stripes, like printing
        d.line(s(l + 8, t + 7, r - 8, t + 7), fill=accent, width=8)
        d.line(s(l + 8, b - 7, r - 8, b - 7), fill=accent, width=8)


def _shine(big, s, box, alpha=150, radius=24):
    """A soft white reflection (glossy plastic / glass)."""
    layer = Image.new("RGBA", big.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(s(*box), radius=radius, fill=(255, 255, 255, alpha))
    big.alpha_composite(layer.filter(ImageFilter.GaussianBlur(3)))


def make_jar_icon():
    """A glass jar with a golden lid (pickles, rice, onions, spices...)."""
    big, d, s = _icon_canvas("jar")
    _shape(big, lambda d: d.rounded_rectangle(s(30, 64, 270, 244), radius=200),
           _gradient(big.size, _round((206, 232, 248), 240), horizontal=True))           # glass body
    d.rounded_rectangle(s(30, 64, 270, 244), radius=200, outline=(150, 192, 222, 255), width=14)
    _shape(big, lambda d: d.rectangle(s(76, 50, 224, 70)),
           _gradient(big.size, _round((186, 214, 234)), horizontal=True))                 # neck
    _shape(big, lambda d: d.rounded_rectangle(s(58, 12, 242, 56), radius=48),
           _gradient(big.size, _round((247, 186, 64)), horizontal=True))                  # golden lid
    for x in range(84, 230, 22):                                                        # lid ridges
        d.line(s(x, 18, x, 50), fill=(212, 146, 40, 150), width=8)
    _shine(big, s, (44, 84, 58, 226), 170)
    _shine(big, s, (74, 18, 130, 26), 140, radius=12)
    _label(big, s, _label_box("jar"))
    _finish_icon(big, "jar", s(30, 228, 270, 256))


def make_bottle_icon():
    """A glass bottle with a red cap (sauces, oil, water...)."""
    big, d, s = _icon_canvas("bottle")
    body = lambda d: (d.rounded_rectangle(s(30, 110, 170, 292), radius=150),
                      d.polygon([tuple(s(82, 62)), tuple(s(118, 62)), tuple(s(170, 130)), tuple(s(30, 130))]),
                      d.rectangle(s(82, 32, 118, 80)))
    _shape(big, body, _gradient(big.size, _round((206, 116, 52)), horizontal=True))      # amber glass
    _shape(big, lambda d: d.rounded_rectangle(s(74, 4, 126, 40), radius=28),
           _gradient(big.size, _round((232, 80, 70)), horizontal=True))                   # cap
    d.rectangle(s(74, 32, 126, 40), fill=(180, 56, 52, 255))
    _shine(big, s, (42, 120, 54, 284), 120)
    _label(big, s, _label_box("bottle"), accent=(226, 86, 72, 255))
    _finish_icon(big, "bottle", s(30, 276, 170, 300))


def make_dish_icon():
    """A bowl of food under a clear lid (leftovers, cooked rice, curries...)."""
    big, d, s = _icon_canvas("dish")
    _shape(big, lambda d: d.chord(s(62, 34, 238, 206), 180, 360),
           _gradient(big.size, [(0, (232, 245, 255, 190)), (1, (190, 220, 246, 130))]))   # clear dome
    d.chord(s(62, 34, 238, 206), 180, 360, outline=(150, 192, 224, 255), width=12)
    _shape(big, lambda d: d.ellipse(s(136, 20, 164, 44)),
           _gradient(big.size, _round((168, 196, 220)), horizontal=True))                 # knob
    _shape(big, lambda d: d.ellipse(s(38, 102, 262, 142)),
           _gradient(big.size, [(0, (246, 168, 86, 255)), (1, (208, 112, 52, 255))]))    # curry
    for x, y in ((92, 112), (138, 106), (186, 116), (118, 124), (214, 110)):           # garnish
        d.ellipse(s(x, y, x + 16, y + 11), fill=(96, 168, 86, 255))
    _shape(big, lambda d: d.chord(s(20, 8, 280, 248), 0, 180),
           _gradient(big.size, [(0, (255, 255, 255, 255)), (0.5, (255, 255, 255, 255)),
                                (1, (232, 222, 210, 255))]))                              # china bowl
    _shape(big, lambda d: d.chord(s(20, 8, 280, 248), 0, 180),
           _gradient(big.size, [(0, (0, 0, 0, 0)), (0.85, (0, 0, 0, 0)), (0.86, (64, 168, 160, 255)),
                                (0.9, (64, 168, 160, 255)), (0.91, (0, 0, 0, 0)), (1, (0, 0, 0, 0))]))   # teal stripe
    d.line(s(22, 128, 278, 128), fill=(236, 226, 212, 255), width=14)                  # rim
    _shine(big, s, (92, 54, 150, 64), 160, radius=10)
    _label(big, s, _label_box("dish"))
    _finish_icon(big, "dish", s(60, 232, 240, 256))


def make_carton_icon():
    """A milk / juice carton with a folded top."""
    big, d, s = _icon_canvas("carton")
    _shape(big, lambda d: d.rounded_rectangle(s(34, 94, 166, 290), radius=40),
           _gradient(big.size, _round((250, 250, 252)), horizontal=True))                 # white box
    _shape(big, lambda d: d.polygon([tuple(s(34, 96)), tuple(s(100, 40)), tuple(s(166, 96))]),
           _gradient(big.size, _round((86, 156, 236)), horizontal=True))                  # blue roof
    _shape(big, lambda d: d.rounded_rectangle(s(84, 16, 116, 50), radius=12),
           _gradient(big.size, _round((86, 156, 236)), horizontal=True))                  # top fin
    _shape(big, lambda d: d.rectangle(s(34, 96, 166, 132)),
           _gradient(big.size, _round((86, 156, 236)), horizontal=True))                  # blue band
    _shine(big, s, (44, 140, 54, 280), 130)
    _label(big, s, _label_box("carton"), accent=(86, 156, 236, 255))
    _finish_icon(big, "carton", s(34, 276, 166, 300))


def make_can_icon():
    """A tin can (beans, tomatoes, coconut milk...)."""
    big, d, s = _icon_canvas("can")
    _shape(big, lambda d: d.rounded_rectangle(s(20, 34, 200, 236), radius=28),
           _gradient(big.size, _round((206, 212, 220)), horizontal=True))                 # steel body
    _shape(big, lambda d: d.rectangle(s(20, 60, 200, 212)),
           _gradient(big.size, _round((222, 72, 72)), horizontal=True))                   # red print
    _shape(big, lambda d: d.ellipse(s(20, 18, 200, 50)),
           _gradient(big.size, [(0, (238, 242, 246, 255)), (1, (178, 186, 196, 255))]))  # lid
    d.ellipse(s(34, 24, 186, 44), outline=(160, 168, 180, 255), width=8)
    for y in (60, 212):                                                                 # rims
        d.line(s(20, y, 200, y), fill=(160, 168, 180, 255), width=10)
    _shine(big, s, (32, 66, 42, 206), 110)
    _label(big, s, _label_box("can"))
    _finish_icon(big, "can", s(20, 222, 200, 256))


def make_tub_icon():
    """A plastic tub with a lid (curd, yogurt, butter, ice cream...)."""
    big, d, s = _icon_canvas("tub")
    _shape(big, lambda d: d.polygon([tuple(s(40, 64)), tuple(s(260, 64)), tuple(s(240, 210)), tuple(s(60, 210))]),
           _gradient(big.size, _round((252, 250, 246)), horizontal=True))                 # white tub
    d.line(s(60, 210, 240, 210), fill=(214, 206, 196, 255), width=10)
    _shape(big, lambda d: d.rounded_rectangle(s(26, 36, 274, 70), radius=40),
           _gradient(big.size, _round((84, 198, 170)), horizontal=True))                  # mint lid
    _shine(big, s, (58, 42, 160, 50), 150, radius=10)
    _shine(big, s, (54, 80, 66, 196), 120)
    _label(big, s, _label_box("tub"), accent=(84, 198, 170, 255))
    _finish_icon(big, "tub", s(56, 202, 244, 230))


def make_box_icon():
    """A glass food box with a snap-on lid (meal prep, cut fruit, takeaway...)."""
    big, d, s = _icon_canvas("box")
    _shape(big, lambda d: d.rounded_rectangle(s(24, 70, 276, 204), radius=110),
           _gradient(big.size, _round((214, 236, 250), 230), horizontal=True))            # glass box
    _shape(big, lambda d: d.rounded_rectangle(s(36, 150, 264, 196), radius=70),
           _gradient(big.size, [(0, (252, 240, 210, 255)), (1, (236, 214, 170, 255))]))  # rice inside
    for x in (60, 110, 196, 236):                                                       # peas / greens
        d.ellipse(s(x, 158, x + 18, 172), fill=(104, 174, 92, 255))
    d.rounded_rectangle(s(24, 70, 276, 204), radius=110, outline=(150, 192, 222, 255), width=12)
    _shape(big, lambda d: d.rounded_rectangle(s(14, 44, 286, 80), radius=50),
           _gradient(big.size, _round((112, 136, 232)), horizontal=True))                 # violet lid
    for x in (34, 246):                                                                 # the snap clips
        _shape(big, lambda d, x=x: d.rounded_rectangle(s(x, 66, x + 20, 100), radius=20),
               _gradient(big.size, _round((92, 112, 208)), horizontal=True))
    _shine(big, s, (60, 50, 170, 58), 150, radius=10)
    _label(big, s, _label_box("box"))
    _finish_icon(big, "box", s(24, 196, 276, 220))


def make_basket_icon():
    """A wooden crate of fresh vegetables (onions, tomatoes, potatoes, greens...)."""
    big, d, s = _icon_canvas("basket")
    veg = [((40, 54, 116, 130), (236, 76, 64)),       # tomato
           ((96, 30, 176, 110), (96, 176, 84)),       # broccoli / greens
           ((150, 50, 222, 122), (154, 98, 196)),     # aubergine / onion
           ((196, 60, 262, 126), (246, 156, 52))]     # orange / carrot
    for box, color in veg:                                                              # round, shiny veg
        _shape(big, lambda d, b=box: d.ellipse(s(*b)), _gradient(big.size, _round(color), horizontal=True))
    d.ellipse(s(64, 62, 80, 74), fill=(255, 255, 255, 170))
    d.line(s(78, 54, 84, 40), fill=(80, 150, 70, 255), width=12)                       # tomato stalk
    _shape(big, lambda d: d.rounded_rectangle(s(22, 98, 278, 230), radius=40),
           _gradient(big.size, [(0, (214, 160, 102, 255)), (1, (170, 112, 62, 255))]))    # wooden crate
    for y in (124, 176):                                                                # slats
        d.line(s(26, y, 274, y), fill=(150, 98, 54, 255), width=8)
    d.rounded_rectangle(s(22, 98, 278, 230), radius=40, outline=(146, 94, 50, 255), width=10)
    _label(big, s, _label_box("basket"))
    _finish_icon(big, "basket", s(22, 218, 278, 240))


def make_container_icons():
    """Every picture a fridge item can be shown as, plus their 'expired' (mouldy) versions."""
    for make in (make_jar_icon, make_bottle_icon, make_dish_icon, make_carton_icon, make_can_icon,
                 make_tub_icon, make_box_icon, make_basket_icon):
        make()
    print("container icons -> assets/icons/container_*.png")


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
    if sys.argv[1:] == ["containers"]:            # "make_assets.py containers" = only redraw these 3
        make_container_icons()
        sys.exit()
    if sys.argv[1:] == ["textures"]:              # "make_assets.py textures" = only the wood + leather
        make_textures()
        sys.exit()
    os.makedirs(RECIPE_IMAGES_DIR, exist_ok=True)
    os.makedirs(ICONS_DIR, exist_ok=True)
    os.makedirs(os.path.join(RECIPE_IMAGES_DIR, "thumbs"), exist_ok=True)
    for recipe in SEED_RECIPES:
        full = os.path.join(RECIPE_IMAGES_DIR, f"{recipe.uid}.jpg")
        make_recipe_image(recipe, full)
        thumb = Image.open(full)                                  # a 256 px copy for list rows
        thumb.thumbnail((256, 256), Image.LANCZOS)
        thumb.save(os.path.join(RECIPE_IMAGES_DIR, "thumbs", f"{recipe.uid}.jpg"), "JPEG", quality=85)
        print("recipe image:", recipe.uid)
    for name, char in ICONS.items():
        make_icon(char, os.path.join(ICONS_DIR, f"{name}.png"))
        print("icon:", name)
    make_container_icons()
    make_textures()
    make_ui_shapes()
    make_app_icon(os.path.join(os.path.dirname(ICONS_DIR), "app_icon.png"))   # assets/app_icon.png
    print("app icon -> assets/app_icon.png")
