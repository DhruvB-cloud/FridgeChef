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
ONLY THE FRIDGE CONTAINER PICTURES: .\.venv\Scripts\python tools\make_assets.py containers
ONLY THE WOOD / LEATHER TEXTURES:  .\.venv\Scripts\python tools\make_assets.py textures
ONLY THE SMALL ICONS + APP ICON:    .\.venv\Scripts\python tools\make_assets.py icons
ONLY THE RECIPE PICTURES:           .\.venv\Scripts\python tools\make_assets.py recipes
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


# Version 4.6: the small icons (tab bar, headers, Profile tab...) use Microsoft's Fluent Emoji 3D
# pictures - the same glossy 3D style as the fridge containers. icon name -> Fluent emoji name.
# (An icon missing here, or a failed download, falls back to the Windows emoji font above.)
FLUENT_ICONS = {
    "tab_fridge": "Broccoli", "tab_recipes": "Pot of food", "tab_cookbook": "Open book",
    "tab_calendar": "Calendar", "tab_profile": "Cook",          # a chef, not just a person
    "fire": "Fire", "trophy": "Trophy", "star": "Star", "plate": "Fork and knife with plate",
    "muscle": "Flexed biceps", "grain": "Sheaf of rice", "bolt": "High voltage", "timer": "Stopwatch",
    "heart": "Sparkling heart", "party": "Party popper", "camera": "Camera",
}


# Version 4.6: every emoji the recipe pictures use, and its Fluent Emoji 3D name, so the recipe
# pictures are drawn with the same glossy 3D food as the rest of the app.
FLUENT_FOOD = {
    "\U0001F373": "Cooking", "\U0001F9C5": "Onion", "\U0001F345": "Tomato", "\U0001F336": "Hot pepper",
    "\U0001F35A": "Cooked rice", "\U0001F95C": "Peanuts", "\U0001F34B": "Lemon", "\U0001F954": "Potato",
    "\U0001F9C8": "Butter", "\U0001F33F": "Herb", "\U0001F372": "Pot of food", "\U0001F9C4": "Garlic",
    "\U0001F952": "Cucumber", "\U0001F963": "Bowl with spoon", "\U0001F958": "Shallow pan of food",
    "\U0001F9C0": "Cheese wedge", "\U0001FAD1": "Bell pepper", "\U0001F35B": "Curry rice",
    "\U0001F357": "Poultry leg", "\U0001F955": "Carrot", "\U0001F33D": "Ear of corn", "\U0001F9C6": "Falafel",
    "\U0001FAD2": "Olive", "\U0001F957": "Green salad", "\U0001F32F": "Burrito", "\U0001F35E": "Bread",
    "\U0001F34C": "Banana", "\U0001F36F": "Honey pot", "\U0001FAD8": "Beans", "\U0001F34E": "Red apple",
    "\U0001F95B": "Glass of milk", "\U0001F967": "Pie", "\U0001F969": "Cut of meat", "\U0001F96A": "Sandwich",
    "\U0001F37D": "Fork and knife with plate",
}
_FLUENT_CACHE = {}                                       # name -> downloaded picture (each fetched once)


def emoji_image(char, size):
    """One emoji as a transparent RGBA image, cropped tightly and scaled to fit `size`.

    Food emojis come from Fluent Emoji 3D (see FLUENT_FOOD); anything else - or a failed
    download - is drawn with the Windows colour emoji font, as before."""
    name = FLUENT_FOOD.get(char)
    if name:
        try:
            if name not in _FLUENT_CACHE:
                _FLUENT_CACHE[name] = _download_fluent(name)
            glyph = _FLUENT_CACHE[name].copy()
            glyph = glyph.crop(glyph.getchannel("A").getbbox())          # cut away the empty border
            scale = size / max(glyph.size)                               # fit inside size x size
            return glyph.resize((max(1, round(glyph.width * scale)), max(1, round(glyph.height * scale))),
                                Image.LANCZOS)
        except OSError as error:
            print(f"  (could not download {name}: {error} - using the emoji font)")
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


def make_recipe_pictures():
    """The picture of every built-in recipe (800 px) plus a 256 px copy for lists."""
    os.makedirs(os.path.join(RECIPE_IMAGES_DIR, "thumbs"), exist_ok=True)
    for recipe in SEED_RECIPES:
        full = os.path.join(RECIPE_IMAGES_DIR, f"{recipe.uid}.jpg")
        make_recipe_image(recipe, full)
        thumb = Image.open(full)                                  # a 256 px copy for list rows
        thumb.thumbnail((256, 256), Image.LANCZOS)
        thumb.save(os.path.join(RECIPE_IMAGES_DIR, "thumbs", f"{recipe.uid}.jpg"), "JPEG", quality=85)
        print("recipe image:", recipe.uid)


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
    the 3D pot of food (version 4.6; the emoji font is used if the download fails)."""
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
    try:
        pot = _download_fluent("Pot of food")              # the 3D pot of food on the plate
        pot = pot.crop(pot.getchannel("A").getbbox())
        pot.thumbnail((int(size * 0.5), int(size * 0.5)), Image.LANCZOS)
    except OSError:
        pot = emoji_image("\U0001F372", int(size * 0.46))   # fallback: the emoji font
    icon.alpha_composite(pot, ((size - pot.width) // 2, (size - pot.height) // 2))
    icon.save(out_path, "PNG")


def make_icon(name, char, out_path, size=128):
    """One small square icon: the Fluent 3D picture if there is one, else the emoji `char`."""
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glyph, source = None, "emoji font"
    if name in FLUENT_ICONS:
        try:
            glyph = _download_fluent(FLUENT_ICONS[name])
            glyph = glyph.crop(glyph.getchannel("A").getbbox())     # cut away the empty border
            glyph.thumbnail((int(size * 0.92), int(size * 0.92)), Image.LANCZOS)   # fit, keep the shape
            source = "Fluent 3D"
        except OSError as error:                                   # no internet: use the emoji font
            print(f"  (could not download {FLUENT_ICONS[name]}: {error})")
    if glyph is None:
        glyph = emoji_image(char, int(size * 0.86))
    icon.alpha_composite(glyph, ((size - glyph.width) // 2, (size - glyph.height) // 2))   # centred
    icon.save(out_path, "PNG")
    print(f"icon: {name:13} ({source})")


# ----------------------------------------------------------------------------------------------
# FRIDGE CONTAINER PICTURES (version 4.5)
# ----------------------------------------------------------------------------------------------
# Each container (jar, bottle, ...) is a 3D picture. It comes from, in this order:
#   1. YOUR OWN picture, if you put one in  assets/icons/custom/<kind>.png  (e.g. custom/jar.png)
#   2. otherwise Microsoft's free "Fluent Emoji 3D" set (MIT licence, see assets/icons/FLUENT_LICENSE.txt)
# The tool trims the empty space around the picture, saves it as assets/icons/container_<kind>.png,
# makes the mouldy "expired" version, and writes assets/icons/containers.json - the picture sizes
# and where the app puts the cream name sticker. The app reads that file, so new pictures just work.
FLUENT_URL = "https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/{0}/3D/{1}_3d.png"
CUSTOM_DIR = os.path.join(ICONS_DIR, "custom")           # drop your own <kind>.png files here

# kind -> (Fluent emoji name, where the name sticker goes as fractions of the picture:
#          centre x, centre y (from the top), width, height)
CONTAINER_SOURCES = {
    "jar": ("Jar", (0.50, 0.55, 0.74, 0.27)),
    "bottle": ("Sake", (0.50, 0.66, 0.80, 0.24)),            # only the bottle - the cup is cut away
    "dish": ("Curry rice", (0.50, 0.78, 0.62, 0.27)),
    "carton": ("Beverage box", (0.47, 0.64, 0.74, 0.24)),
    "can": ("Canned food", (0.50, 0.52, 0.78, 0.27)),
    "tub": ("Bowl with spoon", (0.50, 0.74, 0.64, 0.27)),
    "box": ("Bento box", (0.50, 0.76, 0.60, 0.27)),
    "basket": ("Basket", (0.50, 0.76, 0.60, 0.25)),
    "pot": ("Pot of food", (0.50, 0.78, 0.54, 0.24)),
    "glass": ("Glass of milk", (0.50, 0.60, 0.68, 0.22)),
    "greens": ("Leafy green", (0.50, 0.62, 0.66, 0.24)),
    "takeout": ("Takeout box", (0.50, 0.70, 0.60, 0.24)),
}


def _download_fluent(name):
    """Download one Fluent Emoji 3D picture (256 x 256 PNG) and return it as an image."""
    import io, ssl, urllib.parse, urllib.request
    import certifi                                         # trusted certificates for HTTPS
    folder, file = urllib.parse.quote(name), name.lower().replace(" ", "_")
    context = ssl.create_default_context(cafile=certifi.where())
    urls = [FLUENT_URL.format(folder, file),                                    # most pictures
            FLUENT_URL.replace("/3D/", "/Default/3D/").format(folder, file).replace("_3d.png", "_3d_default.png")]
    for url in urls:                                       # people / hands: the "Default" skin-tone folder
        try:
            with urllib.request.urlopen(url, context=context, timeout=30) as answer:
                return Image.open(io.BytesIO(answer.read())).convert("RGBA")
        except urllib.error.HTTPError:                     # 404 = not in this folder: try the next one
            continue
    raise OSError(f"no Fluent 3D picture called {name!r}")


def _only_the_bottle(img):
    """The Fluent 'sake' picture is a bottle WITH a small cup in front of it. Keep only the bottle:
    cut off the left part, and repaint the corner the cup hid with the bottle's own left-side shade."""
    img = img.crop((108, 0, img.width, img.height))        # the bottle starts at x = 108
    px, centre = img.load(), 67                            # the bottle's middle (measured)
    alpha = img.getchannel("A")
    bottom = max(y for y in range(img.height) if alpha.getpixel((centre, y)) > 128)
    for y in range(150, img.height):                       # the cup covered the rows from y = 150 down
        for x in range(centre):
            mirror = px[2 * centre - x, y]                 # the bottle is symmetric: its outline...
            r, g, b, _ = px[x, 149]                        # ...and the colour just above the cup
            shade = 0.96 if y >= bottom - 10 else 1        # slightly darker at the very bottom
            px[x, y] = (int(r * shade), int(g * shade), int(b * shade), mirror[3])
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
    for kind, (fluent_name, (cx, cy, fw, fh)) in CONTAINER_SOURCES.items():
        custom = os.path.join(CUSTOM_DIR, f"{kind}.png")
        if os.path.exists(custom):                         # 1. your own picture wins
            img, source = Image.open(custom).convert("RGBA"), "custom"
        else:                                              # 2. the Fluent 3D picture
            img, source = _download_fluent(fluent_name), "Fluent 3D"
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
    if sys.argv[1:] == ["textures"]:              # "make_assets.py textures" = only the wood + leather
        make_textures()
        sys.exit()
    if sys.argv[1:] == ["recipes"]:               # "make_assets.py recipes" = only the recipe pictures
        make_recipe_pictures()
        sys.exit()
    if sys.argv[1:] == ["icons"]:                 # "make_assets.py icons" = only the small icons + app icon
        for name, char in ICONS.items():
            make_icon(name, char, os.path.join(ICONS_DIR, f"{name}.png"))
        make_app_icon(os.path.join(os.path.dirname(ICONS_DIR), "app_icon.png"))
        sys.exit()
    os.makedirs(RECIPE_IMAGES_DIR, exist_ok=True)
    os.makedirs(ICONS_DIR, exist_ok=True)
    os.makedirs(os.path.join(RECIPE_IMAGES_DIR, "thumbs"), exist_ok=True)
    make_recipe_pictures()
    for name, char in ICONS.items():
        make_icon(name, char, os.path.join(ICONS_DIR, f"{name}.png"))
    make_container_icons()
    make_textures()
    make_ui_shapes()
    make_app_icon(os.path.join(os.path.dirname(ICONS_DIR), "app_icon.png"))   # assets/app_icon.png
    print("app icon -> assets/app_icon.png")
