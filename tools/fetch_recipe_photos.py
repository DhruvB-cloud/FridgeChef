r"""
tools/fetch_recipe_photos.py
----------------------------
WHY THIS FILE EXISTS:
    "Replace the recipe pictures with actual food images from the web." Photos found on random
    websites belong to whoever took them, and this project is public on GitHub - so we only use
    photos from Wikimedia Commons (the free photo library behind Wikipedia) whose licence allows
    anyone to reuse them: public domain, CC0, CC BY or CC BY-SA. Those licences ask for ONE thing
    in return: credit the photographer. The tool therefore also writes
    assets/recipe_images/credits.json, and the app shows "Photo: <name> - <licence>" on each recipe.

    This is a DEVELOPER tool (like make_assets.py), not part of the app.

HOW TO USE IT (from the FridgeChef folder):
    1. Find candidates and make a contact sheet to look at:
           .\.venv\Scripts\python tools\fetch_recipe_photos.py search
       -> F:\Temp\recipe-photos\<recipe>.jpg  (numbered candidates for each recipe)
    2. Write the chosen file name of each recipe into tools/recipe_photos.json
    3. Download the chosen photos, crop them square and write the credits:
           .\.venv\Scripts\python tools\fetch_recipe_photos.py fetch

    VERSION 5.0 (80 more recipes):
           .\.venv\Scripts\python tools\fetch_recipe_photos.py auto
       picks the FIRST suitable photo for every recipe that has no choice yet, adds it to
       recipe_photos.json and makes review sheets (F:\Temp\recipe-photos\review-*.jpg). Bad picks
       can then be replaced by hand in recipe_photos.json before running "fetch".
       "fetch" only downloads photos that are missing. The first 21 recipes' photos are bundled in
       the APK (assets/recipe_images); the newer ones go to assets/catalog_photos, which phones
       download from GitHub Pages instead (keeps the APK small).
"""

import html                                        # turns "&amp;" back into "&"
import io                                          # treat downloaded bytes like a file
import json                                        # read / write the .json files
import os
import re                                          # strip HTML tags from the photographer's name
import ssl                                         # secure (HTTPS) connections...
import sys
import urllib.parse                                # build web addresses safely
import urllib.request                              # download from the web

import certifi                                     # ...with an up-to-date list of trusted certificates
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.images import CATALOG_PHOTOS_DIR, RECIPE_IMAGES_DIR   # noqa: E402  where recipe pictures live
from app.seed_recipes import SEED_RECIPES          # noqa: E402  the built-in recipes

API = "https://commons.wikimedia.org/w/api.php"    # Wikimedia Commons' public search API
# Wikimedia asks every program to say who it is (no e-mail needed: the project page is enough).
HEADERS = {"User-Agent": "FridgeChefAssetTool/1.0 (https://github.com/DhruvB-cloud/FridgeChef)"}
CHOICES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recipe_photos.json")
CREDITS = os.path.join(RECIPE_IMAGES_DIR, "credits.json")
SHEETS_DIR = r"F:\Temp\recipe-photos"             # contact sheets for choosing (on F:, never C:)
SIZE = 800                                         # the app's recipe pictures are 800 x 800
ALLOWED = ("cc0", "public domain", "pd", "cc by", "cc-by")   # licences we may reuse (lower case)

# What to search for, per recipe (plain dish names find the best photos).
SEARCH = {
    "masala-omelette": "masala omelette", "vegetable-poha": "poha", "jeera-rice": "jeera rice",
    "dal-tadka": "dal tadka", "cucumber-raita": "cucumber raita", "paneer-bhurji": "paneer bhurji",
    "chicken-curry": "chicken curry", "aloo-tikki": "aloo tikki", "vegetable-pulao": "vegetable pulao",
    "hummus": "hummus", "shakshuka": "shakshuka", "fattoush-salad": "fattoush",
    "chicken-shawarma-bowl": "chicken shawarma plate", "mujaddara": "mujaddara",
    "scrambled-eggs-on-toast": "scrambled eggs toast", "porridge-with-fruit": "porridge fruit",
    "jacket-potato-with-beans": "jacket potato beans", "tomato-soup": "tomato soup",
    "fruit-yogurt-bowl": "yogurt fruit bowl", "cottage-pie": "cottage pie",
    "cheese-toastie": "cheese toastie",
}


def _get(params=None, url=API):
    """Download `url` (with ?params) and return the raw bytes."""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers=HEADERS)
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, context=context, timeout=60) as answer:
        return answer.read()


def _plain(text):
    """'<a href="...">Jane Doe</a>' -> 'Jane Doe' (the API gives names as HTML)."""
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def candidates(query, limit=8):
    """Photos on Commons for `query` that we are allowed to reuse, best first."""
    data = json.loads(_get({
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,   # 6 = files
        "gsrsearch": f"filetype:bitmap {query}", "gsrlimit": 30,
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1000,
    }))
    found = []
    for page in sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0)):
        info = page["imageinfo"][0]
        meta = info.get("extmetadata", {})
        licence = _plain(meta.get("LicenseShortName", {}).get("value", ""))
        if not licence.lower().startswith(ALLOWED):                # not free to reuse: skip
            continue
        if info["mime"] != "image/jpeg" or min(info["width"], info["height"]) < 700:   # photos, big enough
            continue
        if not 0.66 < info["width"] / info["height"] < 1.8:         # not too tall / too wide to crop
            continue
        found.append({"file": page["title"], "thumb": info["thumburl"], "licence": licence,
                      "licence_url": meta.get("LicenseUrl", {}).get("value", ""),
                      "author": _plain(meta.get("Artist", {}).get("value", "")) or "Unknown",
                      "page": info["descriptionurl"]})
        if len(found) == limit:
            break
    return found


def search():
    """Step 1: a numbered contact sheet of candidate photos for every recipe (to pick from)."""
    os.makedirs(SHEETS_DIR, exist_ok=True)
    font = ImageFont.truetype(os.path.join(os.path.dirname(RECIPE_IMAGES_DIR), "fonts", "Poppins-SemiBold.ttf"), 22)
    everything = {}
    for uid, query in SEARCH.items():
        found = candidates(query)
        everything[uid] = found
        sheet = Image.new("RGB", (4 * 260, 2 * 290), "white")
        d = ImageDraw.Draw(sheet)
        for i, c in enumerate(found):
            photo = Image.open(io.BytesIO(_get(url=c["thumb"]))).convert("RGB")
            photo.thumbnail((250, 250))
            x, y = (i % 4) * 260 + 5, (i // 4) * 290 + 5
            sheet.paste(photo, (x, y))
            d.text((x, y + 252), f"{i}: {c['licence']}", font=font, fill="black")
        sheet.save(os.path.join(SHEETS_DIR, f"{uid}.jpg"), quality=85)
        print(f"{uid:26} {len(found)} candidates")
    with open(os.path.join(SHEETS_DIR, "candidates.json"), "w", encoding="utf-8") as f:
        json.dump(everything, f, indent=2)


def _square(photo, focus_y=0.5):
    """Crop the middle square out of a photo and make it SIZE x SIZE."""
    w, h = photo.size
    side = min(w, h)
    left = (w - side) // 2
    top = int((h - side) * focus_y)                # focus_y: 0 = keep the top, 1 = keep the bottom
    return photo.crop((left, top, left + side, top + side)).resize((SIZE, SIZE), Image.LANCZOS)


BUNDLED = {r.uid for r in SEED_RECIPES[:21]}       # the first 21 recipes' photos live inside the APK


def folder_for(uid):
    """assets/recipe_images for the 21 bundled photos, assets/catalog_photos for the rest."""
    return RECIPE_IMAGES_DIR if uid in BUNDLED else CATALOG_PHOTOS_DIR


def auto():
    """5.0: choose the first suitable photo for every recipe without a choice, and make review sheets."""
    with open(CHOICES, encoding="utf-8") as f:
        choices = json.load(f)
    os.makedirs(SHEETS_DIR, exist_ok=True)
    font = ImageFont.truetype(os.path.join(os.path.dirname(RECIPE_IMAGES_DIR), "fonts", "Poppins-SemiBold.ttf"), 16)
    picked = []
    for recipe in SEED_RECIPES:
        if recipe.uid in choices:
            continue
        found = candidates(SEARCH.get(recipe.uid, recipe.name), limit=1)
        if not found:
            print(f"{recipe.uid:30} NO free photo found - choose one by hand")
            continue
        choices[recipe.uid] = {"file": found[0]["file"], "focus_y": 0.5}
        picked.append((recipe.uid, found[0]))
        print(f"{recipe.uid:30} {found[0]['file'][:60]}")
    with open(CHOICES, "w", encoding="utf-8") as f:
        json.dump(choices, f, indent=2, ensure_ascii=False)
    for n in range(0, len(picked), 20):                # review sheets: 20 photos each (5 x 4)
        sheet = Image.new("RGB", (5 * 230, 4 * 250), "white")
        d = ImageDraw.Draw(sheet)
        for i, (uid, c) in enumerate(picked[n:n + 20]):
            photo = Image.open(io.BytesIO(_get(url=c["thumb"]))).convert("RGB")
            photo.thumbnail((220, 220))
            x, y = (i % 5) * 230 + 5, (i // 5) * 250 + 5
            sheet.paste(photo, (x, y))
            d.text((x, y + 222), uid[:26], font=font, fill="black")
        sheet.save(os.path.join(SHEETS_DIR, f"review-{n // 20 + 1}.jpg"), quality=85)


def fetch():
    """Step 3: download the chosen photos that are missing, crop them square, save picture + thumbnail.

    Credits are ADDED to assets/recipe_images/credits.json (one file for all photos - the app reads it).
    """
    with open(CHOICES, encoding="utf-8") as f:
        choices = json.load(f)                     # uid -> {"file": "File:....jpg", "focus_y": 0.5}
    credits = {}
    if os.path.exists(CREDITS):
        with open(CREDITS, encoding="utf-8") as f:
            credits = json.load(f)                 # keep the credits we already have
    for uid, choice in choices.items():
        folder = folder_for(uid)
        if os.path.exists(os.path.join(folder, f"{uid}.jpg")) and uid in credits:
            continue                               # already downloaded
        os.makedirs(os.path.join(folder, "thumbs"), exist_ok=True)
        data = json.loads(_get({"action": "query", "format": "json", "titles": choice["file"],
                                "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 1200}))
        info = next(iter(data["query"]["pages"].values()))["imageinfo"][0]
        meta = info.get("extmetadata", {})
        photo = Image.open(io.BytesIO(_get(url=info["thumburl"]))).convert("RGB")
        picture = _square(photo, choice.get("focus_y", 0.5))
        picture.save(os.path.join(folder, f"{uid}.jpg"), "JPEG", quality=86)
        thumb = picture.copy()
        thumb.thumbnail((256, 256), Image.LANCZOS)   # the small copy for lists
        thumb.save(os.path.join(folder, "thumbs", f"{uid}.jpg"), "JPEG", quality=85)
        artist = _plain(meta.get("Artist", {}).get("value", ""))
        author = artist.splitlines()[0].strip() if artist else ""   # first line = the name (no notes)
        credits[uid] = {"author": author or "Unknown",
                        "licence": _plain(meta.get("LicenseShortName", {}).get("value", "")),
                        "licence_url": meta.get("LicenseUrl", {}).get("value", ""),
                        "source": info["descriptionurl"], "file": choice["file"]}
        print(f"{uid:26} {credits[uid]['licence']:14} {credits[uid]['author'][:40]}")
    with open(CREDITS, "w", encoding="utf-8") as f:
        json.dump(credits, f, indent=2, ensure_ascii=False)   # read by the app (recipe page credit line)


if __name__ == "__main__":
    {"search": search, "fetch": fetch, "auto": auto}[sys.argv[1] if len(sys.argv) > 1 else "search"]()
