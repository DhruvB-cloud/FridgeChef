"""
export_catalog.py
-----------------
WHY THIS FILE EXISTS (version 4.7.1 - replaces the Cloud Run recipe server):
    Builds the folder that GitHub Pages publishes:
        site/catalog.json        every built-in recipe + a "version" fingerprint
        site/images/<file>.jpg   their pictures (+ site/images/thumbs/<file>.jpg, small copies for lists)
        site/index.html          a tiny page, so the address shows something in a browser
    The app downloads catalog.json once a day (app/catalog.py) and matches recipes on the phone.

    Run by .github/workflows/publish-catalog.yml on every push to main that changes the recipes.
    By hand:   .venv\\Scripts\\python tools\\export_catalog.py      (writes the "site" folder)
"""

import json
import os
import shutil                        # copy picture files
import sys
from datetime import datetime, timezone

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../FridgeChef
sys.path.insert(0, PROJECT_DIR)      # so "import app..." works when run as a script

from app.api_schema import recipe_to_dict          # noqa: E402  Recipe -> JSON-friendly dict
from app.catalog import fingerprint                # noqa: E402  the same version maths as the app
from app.images import CATALOG_PHOTOS_DIR, RECIPE_IMAGES_DIR   # noqa: E402  where the photos are
from app.seed_recipes import SEED_RECIPES          # noqa: E402  the master recipe list

OUT_DIR = os.path.join(PROJECT_DIR, "site")        # what GitHub Pages serves (git-ignored)


def main():
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)                     # start clean, so deleted pictures disappear too
    os.makedirs(os.path.join(OUT_DIR, "images", "thumbs"))
    recipes = [recipe_to_dict(r) for r in SEED_RECIPES]
    for r in recipes:                              # copy every picture (and its thumbnail) the recipes mention
        if r["image"]:
            folder = next(f for f in (RECIPE_IMAGES_DIR, CATALOG_PHOTOS_DIR)   # bundled or 5.0 photo
                          if os.path.exists(os.path.join(f, r["image"])))
            shutil.copy2(os.path.join(folder, r["image"]), os.path.join(OUT_DIR, "images"))
            shutil.copy2(os.path.join(folder, "thumbs", r["image"]), os.path.join(OUT_DIR, "images", "thumbs"))
    catalog = {"version": fingerprint(recipes),    # changes only when a recipe changes
               "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "count": len(recipes), "recipes": recipes}
    with open(os.path.join(OUT_DIR, "catalog.json"), "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write("<!doctype html><meta charset=utf-8><title>FridgeChef recipes</title>"
                f"<p>FridgeChef recipe catalogue: {len(recipes)} recipes. "
                "<a href=catalog.json>catalog.json</a></p>")
    print(f"Exported {len(recipes)} recipes (version {catalog['version']}) to {OUT_DIR}")


if __name__ == "__main__":
    main()
