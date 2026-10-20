"""
images.py
---------
WHY THIS FILE EXISTS:
    "Each recipe should have an image by default." Recipes get their picture from one of three places:
      1. Built-in recipes -> a bundled picture in assets/recipe_images/<uid>.jpg
         (stored in the database as "asset:<uid>.jpg", so it works on any device and any folder).
      2. Recipes that came from the server but whose picture isn't bundled -> downloaded once
         into a cache folder (see api_client.py) and then also available offline.
      3. User recipes -> their own photo, or, if they didn't add one, a soft-coloured picture
         generated here by make_default_image().
    resolve_image() turns whatever is stored into a real file path the UI can display.
"""

import hashlib                        # turns a name into a stable number (to pick a colour)
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Folder that contains this file's parent project: .../FridgeChef
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")                 # bundled with the app
RECIPE_IMAGES_DIR = os.path.join(ASSETS_DIR, "recipe_images")   # default recipe pictures
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")                   # tab / profile icons
AVATARS_DIR = os.path.join(ASSETS_DIR, "avatars")               # profile pictures to choose from (4.7.1)
# The avatars a user can pick (file assets/avatars/<name>.png, made by tools/make_assets.py avatars).
AVATARS = ("chef", "cat", "panda", "fox", "bear", "rabbit", "robot", "cupcake")


def avatar_path(name):
    """File of the avatar called `name`, or None (no avatar chosen yet, or the file is missing)."""
    path = os.path.join(AVATARS_DIR, f"{name}.png") if name in AVATARS else None   # only known names
    return path if path and os.path.exists(path) else None


# Set by the app at start-up: where downloaded server images are kept.
_cache_dir = None

# Soft pastel colour pairs (top colour, bottom colour) for generated pictures.
SOFT_GRADIENTS = [
    ((255, 228, 214), (255, 200, 180)),   # peach
    ((222, 240, 224), (190, 225, 196)),   # sage
    ((226, 234, 250), (196, 212, 242)),   # sky
    ((250, 236, 205), (244, 214, 160)),   # butter
    ((240, 226, 246), (220, 200, 236)),   # lavender
    ((214, 240, 238), (180, 224, 220)),   # mint
]


def set_cache_dir(path):
    """Tell this module where downloaded images live (called once by main.py / the API client)."""
    global _cache_dir                     # 'global' lets us change the module-level variable
    _cache_dir = path
    os.makedirs(path, exist_ok=True)


def cache_dir():
    return _cache_dir


# The container pictures of the Fridge tab (jar, bottle, ...), version 4.5. For each one,
# assets/icons/containers.json (written by tools/make_assets.py) holds, in pixels (y = 0 at the TOP):
#   size  - width and height of the picture
#   label - (left, top, right, bottom) of the cream sticker where the app writes the item's name
# Because the app reads this file, replacing a picture (see assets/icons/custom/README.txt) just works.
def _load_container_art():
    import json                                          # local import: only needed here
    with open(os.path.join(ICONS_DIR, "containers.json"), encoding="utf-8") as f:
        return json.load(f)


CONTAINER_ART = _load_container_art()


def icon(name):
    """Full path of a bundled icon, e.g. icon('fire') -> .../assets/icons/fire.png"""
    return os.path.join(ICONS_DIR, f"{name}.png")


THUMBS_DIR = os.path.join(RECIPE_IMAGES_DIR, "thumbs")     # 256 px copies for lists (made by tools/make_assets.py)


def resolve_image(image_path, small=False):
    """Return a file path that exists for the stored image value, or None.

    small=True prefers the 256 px thumbnail of a built-in picture: lists show pictures at about
    90 x 90, so loading the 800 x 800 original there only wastes time and memory (version 4.0.1).
    """
    if not image_path:
        return None
    if image_path.startswith("asset:"):                       # built-in / server picture
        name = image_path[len("asset:"):]
        if small and os.path.exists(os.path.join(THUMBS_DIR, name)):
            return os.path.join(THUMBS_DIR, name)               # the small copy
        for folder in (RECIPE_IMAGES_DIR, _cache_dir):          # bundled first, then downloaded
            if folder and os.path.exists(os.path.join(folder, name)):
                return os.path.join(folder, name)
        return None                                             # not available (yet)
    return image_path if os.path.exists(image_path) else None   # user photo on this device


_CREDITS = None                                                # loaded on first use


def photo_credit(image_path):
    """Who took a built-in recipe photo, e.g. {"author": "Jane", "licence": "CC BY-SA 4.0",
    "source": "https://commons.wikimedia.org/...", ...} - or None (own photos, drawings).

    The photos come from Wikimedia Commons; their free licences ask us to credit the photographer.
    tools/fetch_recipe_photos.py writes the credits into assets/recipe_images/credits.json."""
    global _CREDITS
    if _CREDITS is None:
        import json                                            # local import: only needed here
        try:
            with open(os.path.join(RECIPE_IMAGES_DIR, "credits.json"), encoding="utf-8") as f:
                _CREDITS = json.load(f)
        except (OSError, ValueError):                          # missing / broken file: no credits
            _CREDITS = {}
    name = asset_name(image_path)
    return _CREDITS.get(name[:-4]) if name and name.endswith(".jpg") else None


def asset_name(image_path):
    """'asset:dal-tadka.jpg' -> 'dal-tadka.jpg' (None for user photos)."""
    if image_path and image_path.startswith("asset:"):
        return image_path[len("asset:"):]
    return None


def _font(size):
    """Bold font for the initials (same search order as recipe_card.py)."""
    candidates = []
    try:
        import kivy
        candidates.append(os.path.join(os.path.dirname(kivy.__file__), "data", "fonts", "Roboto-Bold.ttf"))
    except ImportError:
        pass
    for path in candidates + ["arialbd.ttf", "DejaVuSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def gradient(size, top, bottom):
    """A vertical colour gradient image - the soft background of every generated picture."""
    w, h = size
    img = Image.new("RGB", (1, h))                              # 1 pixel wide, h tall...
    for y in range(h):
        t = y / max(h - 1, 1)                                   # 0.0 at the top, 1.0 at the bottom
        img.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img.resize((w, h))                                   # ...then stretched sideways (fast)


def make_default_image(name, out_path, size=800):
    """Draw a soft placeholder picture: pastel gradient, a plate, and the dish's initials."""
    # Pick the colour from the name, so the same dish always gets the same colour.
    index = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16) % len(SOFT_GRADIENTS)
    top, bottom = SOFT_GRADIENTS[index]
    img = gradient((size, size), top, bottom)
    # Soft shadow under the plate: a blurred dark circle.
    shadow = Image.new("L", (size, size), 0)
    ImageDraw.Draw(shadow).ellipse([size * 0.2, size * 0.24, size * 0.8, size * 0.84], fill=70)
    shadow = shadow.filter(ImageFilter.GaussianBlur(size // 30))
    img.paste((0, 0, 0), (0, 0), shadow.point(lambda v: v // 2))   # paste black through the mask
    draw = ImageDraw.Draw(img)
    draw.ellipse([size * 0.2, size * 0.2, size * 0.8, size * 0.8], fill=(255, 255, 255))    # plate
    draw.ellipse([size * 0.27, size * 0.27, size * 0.73, size * 0.73], fill=bottom)         # food
    initials = "".join(word[0] for word in name.split()[:2]).upper() or "?"
    font = _font(size // 5)
    box = draw.textbbox((0, 0), initials, font=font)            # measure the text
    draw.text(((size - (box[2] - box[0])) / 2 - box[0], (size - (box[3] - box[1])) / 2 - box[1]),
              initials, font=font, fill=(255, 255, 255))
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    img.save(out_path, "JPEG", quality=88)
    return out_path
