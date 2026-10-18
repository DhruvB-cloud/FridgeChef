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


def _paper_label(d, s, box, outline=(232, 214, 186, 255)):
    """The cream paper label the item's name is written on."""
    d.rounded_rectangle(s(*box), radius=40, fill=(255, 248, 232, 255), outline=outline, width=12)


def make_jar_icon():
    """A wide glass jar with a golden lid (pickles, rice, onions, spices...)."""
    big, d, s = _icon_canvas("jar")
    d.rounded_rectangle(s(30, 66, 270, 244), radius=180, fill=(224, 240, 250, 255),
                        outline=(160, 196, 222, 255), width=20)                 # glass body
    d.rectangle(s(76, 54, 224, 72), fill=(206, 226, 240, 255))                  # neck of the jar
    d.rounded_rectangle(s(64, 16, 236, 58), radius=40, fill=(242, 184, 75, 255))   # lid
    for x in range(88, 230, 28):                                                # ridges on the lid
        d.line(s(x, 22, x, 52), fill=(214, 152, 52, 255), width=16)
    d.rounded_rectangle(s(40, 82, 50, 228), radius=20, fill=(255, 255, 255, 200))   # shine
    _paper_label(d, s, _label_box("jar"))
    _finish_icon(big, "jar", s(30, 228, 270, 256))


def make_bottle_icon():
    """A brown glass bottle with a red cap (sauces, oil, milk, water...)."""
    big, d, s = _icon_canvas("bottle")
    glass, dark = (205, 128, 62, 255), (172, 100, 44, 255)                       # amber glass
    d.rounded_rectangle(s(30, 112, 170, 290), radius=110, fill=glass)            # body
    d.polygon([tuple(s(80, 70)), tuple(s(120, 70)), tuple(s(170, 136)), tuple(s(30, 136))],
              fill=glass)                                                       # sloping shoulders
    d.rectangle(s(80, 36, 120, 80), fill=glass)                                 # neck
    d.rounded_rectangle(s(74, 6, 126, 40), radius=30, fill=(214, 92, 80, 255))  # cap
    d.rectangle(s(74, 32, 126, 40), fill=(186, 70, 62, 255))                    # cap's lower ring
    d.rounded_rectangle(s(42, 118, 54, 146), radius=20, fill=(255, 255, 255, 120))   # shine
    l, t, r, b = _label_box("bottle")
    d.rectangle(s(l, t, r, b), fill=(255, 248, 232, 255))                       # label around the body
    d.line(s(l, t, r, t), fill=dark, width=12)                                  # label edges
    d.line(s(l, b, r, b), fill=dark, width=12)
    _finish_icon(big, "bottle", s(30, 276, 170, 300))


def make_dish_icon():
    """A bowl of food under a clear lid (leftovers, cooked rice, curries...)."""
    big, d, s = _icon_canvas("dish")
    d.chord(s(64, 36, 236, 204), 180, 360, fill=(214, 234, 250, 170),
            outline=(150, 190, 222, 255), width=16)                             # clear, slightly blue dome lid
    d.ellipse(s(138, 24, 162, 44), fill=(150, 190, 222, 255))                   # knob on the lid
    d.ellipse(s(40, 104, 260, 140), fill=(226, 140, 72, 255))                   # food (curry colour)
    for x, y in ((96, 112), (140, 108), (186, 118), (120, 124), (210, 110)):   # green garnish
        d.ellipse(s(x, y, x + 14, y + 10), fill=(110, 170, 90, 255))
    # The bowl: the lower half of an ellipse, with a peach stripe painted inside its shape.
    bowl = Image.new("L", big.size, 0)
    ImageDraw.Draw(bowl).chord(s(20, 8, 280, 248), 0, 180, fill=255)            # bowl outline as a mask
    body = Image.new("RGBA", big.size, (255, 250, 242, 255))                    # cream china
    ImageDraw.Draw(body).rectangle(s(0, 222, 300, 232), fill=(245, 168, 135, 255))   # peach stripe
    big.paste(body, (0, 0), bowl)
    d.line(s(20, 128, 280, 128), fill=(236, 224, 210, 255), width=16)           # bowl rim
    _paper_label(d, s, _label_box("dish"))
    _finish_icon(big, "dish", s(60, 230, 240, 256))


def make_container_icons():
    """The three pictures a fridge item can be shown as, plus their 'expired' (mouldy) versions."""
    make_jar_icon()
    make_bottle_icon()
    make_dish_icon()
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
