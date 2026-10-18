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
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFilter, ImageFont   # noqa: E402

from app.images import ICONS_DIR, RECIPE_IMAGES_DIR, gradient   # noqa: E402
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


def _icon_canvas(size):
    """A transparent square, 4x bigger than the final icon (shrinking it later smooths the edges)."""
    big = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    return big, ImageDraw.Draw(big), size * 4 / 256          # k: scale factor for a 256-unit design


def _finish_icon(big, size, out_path, shadow_box):
    """Add a soft shadow under the drawing, shrink to `size` and save."""
    shadow = soft_shadow(big.size, shadow_box, 10 * big.size[0] / 256, 70)   # blurred ellipse
    base = Image.new("RGBA", big.size, (0, 0, 0, 0))
    base.paste((20, 40, 70, 255), (0, 0), shadow)              # dark blue-grey shadow...
    base.alpha_composite(big)                                  # ...with the drawing on top
    base.resize((size, size), Image.LANCZOS).save(out_path, "PNG")


def make_jar_icon(out_path, size=256):
    """A glass jar with a golden lid and a cream label (pickles, rice, spices...)."""
    big, d, k = _icon_canvas(size)
    s = lambda *v: [round(x * k) for x in v]                   # design units (0-256) -> pixels
    d.rounded_rectangle(s(44, 76, 212, 238), radius=round(36 * k), fill=(224, 240, 250, 255),
                        outline=(160, 196, 222, 255), width=round(5 * k))       # glass body
    d.rectangle(s(70, 64, 186, 82), fill=(206, 226, 240, 255))                  # neck of the jar
    d.rounded_rectangle(s(58, 26, 198, 66), radius=round(10 * k), fill=(242, 184, 75, 255))   # lid
    for x in (84, 110, 136, 162):                                               # ridges on the lid
        d.line(s(x, 32, x, 60), fill=(214, 152, 52, 255), width=round(4 * k))
    d.rounded_rectangle(s(62, 120, 194, 196), radius=round(10 * k), fill=(255, 248, 232, 255),
                        outline=(232, 214, 186, 255), width=round(3 * k))       # paper label
    d.rounded_rectangle(s(56, 92, 70, 222), radius=round(7 * k), fill=(255, 255, 255, 190))   # shine
    _finish_icon(big, size, out_path, s(40, 222, 216, 252))


def make_bottle_icon(out_path, size=256):
    """A brown glass bottle with a red cap and a label (sauces, oil, milk, water...)."""
    big, d, k = _icon_canvas(size)
    s = lambda *v: [round(x * k) for x in v]
    glass, dark = (205, 128, 62, 255), (172, 100, 44, 255)                       # amber glass
    d.rounded_rectangle(s(80, 100, 176, 244), radius=round(26 * k), fill=glass)  # body
    d.polygon([tuple(s(112, 56)), tuple(s(144, 56)), tuple(s(176, 118)), tuple(s(80, 118))],
              fill=glass)                                                       # sloping shoulders
    d.rectangle(s(112, 36, 144, 70), fill=glass)                                # neck
    d.rounded_rectangle(s(106, 10, 150, 42), radius=round(8 * k), fill=(214, 92, 80, 255))   # cap
    d.rectangle(s(106, 34, 150, 42), fill=(186, 70, 62, 255))                   # cap's lower ring
    d.rounded_rectangle(s(92, 108, 104, 232), radius=round(6 * k), fill=(255, 255, 255, 120))  # shine (under the label)
    d.rectangle(s(80, 140, 176, 204), fill=(255, 248, 232, 255))                # paper label
    d.line(s(80, 140, 176, 140), fill=dark, width=round(3 * k))                 # label edges
    d.line(s(80, 204, 176, 204), fill=dark, width=round(3 * k))
    _finish_icon(big, size, out_path, s(78, 230, 178, 254))


def make_dish_icon(out_path, size=256):
    """A bowl of food under a clear lid (leftovers, cooked rice, curries...)."""
    big, d, k = _icon_canvas(size)
    s = lambda *v: [round(x * k) for x in v]
    d.chord(s(48, 52, 208, 196), 180, 360, fill=(214, 234, 250, 170),
            outline=(150, 190, 222, 255), width=round(4 * k))                   # clear, slightly blue dome lid
    d.ellipse(s(116, 40, 140, 60), fill=(150, 190, 222, 255))                   # knob on the lid
    d.ellipse(s(40, 106, 216, 146), fill=(226, 140, 72, 255))                   # food (curry colour)
    for x, y in ((88, 116), (128, 112), (160, 122), (108, 128)):                # green garnish
        d.ellipse(s(x, y, x + 12, y + 9), fill=(110, 170, 90, 255))
    # The bowl: the lower half of an ellipse, with a peach stripe painted inside its shape.
    bowl = Image.new("L", big.size, 0)
    ImageDraw.Draw(bowl).chord(s(28, 30, 228, 230), 0, 180, fill=255)           # bowl outline as a mask
    body = Image.new("RGBA", big.size, (255, 250, 242, 255))                    # cream china
    ImageDraw.Draw(body).rectangle(s(0, 160, 256, 178), fill=(245, 168, 135, 255))   # peach stripe
    big.paste(body, (0, 0), bowl)
    d.line(s(28, 130, 228, 130), fill=(236, 224, 210, 255), width=round(4 * k))      # bowl rim
    _finish_icon(big, size, out_path, s(50, 214, 206, 242))


def make_container_icons():
    """The three pictures a fridge item can be shown as (chosen in the Add item form)."""
    make_jar_icon(os.path.join(ICONS_DIR, "container_jar.png"))
    make_bottle_icon(os.path.join(ICONS_DIR, "container_bottle.png"))
    make_dish_icon(os.path.join(ICONS_DIR, "container_dish.png"))
    print("container icons -> assets/icons/container_*.png")


if __name__ == "__main__":
    if sys.argv[1:] == ["containers"]:            # "make_assets.py containers" = only redraw these 3
        make_container_icons()
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
    make_ui_shapes()
    make_app_icon(os.path.join(os.path.dirname(ICONS_DIR), "app_icon.png"))   # assets/app_icon.png
    print("app icon -> assets/app_icon.png")
