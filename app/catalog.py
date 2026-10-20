"""
catalog.py
----------
WHY THIS FILE EXISTS (version 4.7.1 - replaces the Cloud Run server and api_client.py):
    The recipe catalogue is published as plain files on GitHub Pages:
        https://dhruvb-cloud.github.io/FridgeChef/catalog.json      the recipes (+ a version)
        https://dhruvb-cloud.github.io/FridgeChef/images/<file>     their pictures
    (made by tools/export_catalog.py and .github/workflows/publish-catalog.yml).

    The phone checks catalog.json at most ONCE A DAY, saves new / changed recipes in its own
    database and downloads pictures it doesn't have yet. All matching, filtering and sorting
    happens on the phone (app/recipe_engine.py) - exactly like the old offline mode.

    Why (QA report, point 15): a server that computes an answer for every request costs money per
    request, so anyone could run up the bill by flooding it. Static files cost nothing per request,
    GitHub serves them for free, and there is no server left to attack.

    Uses only Python's built-in urllib, so nothing extra is needed on the phone.
"""

import hashlib                       # sha256: the catalogue's version is a fingerprint of its content
import json                          # catalog.json -> Python dicts
import os
import re                            # checks picture file names
import ssl                           # HTTPS: checks the website's certificate
import threading                     # download without freezing the screen
import time                          # monotonic(): wait a while after a failed check
import urllib.error
import urllib.request                # Python's built-in HTTP client
from datetime import date

from app.api_schema import recipe_from_dict
from app.config import CATALOG_URL, IMAGES_URL, REQUEST_TIMEOUT_SECONDS
from app.images import cache_dir, resolve_image

MAX_CATALOG_BYTES = 2 * 1024 * 1024  # a sane catalogue is ~100 KB; refuse anything absurd
MAX_IMAGE_BYTES = 2 * 1024 * 1024    # recipe pictures are ~150 KB
SAFE_IMAGE_NAME = re.compile(r"[a-z0-9-]{1,80}\.jpg")   # e.g. "dal-tadka.jpg" - nothing like "../x"
CHECKED_ON = "catalog_checked_on"    # settings key: the day of the last SUCCESSFUL check
VERSION = "catalog_version"          # settings key: fingerprint of the catalogue we have
RETRY_AFTER_SECONDS = 15 * 60        # after a failed check (e.g. offline), wait before trying again
_state = {"running": False, "failed_at": None}   # one check at a time; when the last one failed


def _ssl_context():
    """Trusted certificates for HTTPS. Python on Android can't find the system's list, so we use
    the `certifi` package (bundled via buildozer.spec) whenever it is installed."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:                                   # e.g. a minimal PC setup
        return ssl.create_default_context()


SSL_CONTEXT = _ssl_context()                              # created once, reused for every download


class CatalogError(Exception):
    """Any problem getting the catalogue (offline, website down, damaged file...)."""


def fingerprint(recipe_dicts):
    """A short text that changes whenever any recipe changes (used as the catalogue's version)."""
    text = json.dumps(recipe_dicts, sort_keys=True, ensure_ascii=False)   # same data -> same text
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _download(url, limit):
    """GET `url` and return its bytes; refuse answers bigger than `limit` bytes."""
    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS, context=SSL_CONTEXT) as answer:
            data = answer.read(limit + 1)                 # one byte more than allowed...
    except (urllib.error.URLError, OSError, ValueError) as error:   # offline / timeout / bad address
        raise CatalogError(f"download failed: {getattr(error, 'reason', error)}") from error
    if len(data) > limit:                                 # ...so a too-big answer is noticed
        raise CatalogError("download too large")
    return data


def fetch_catalog():
    """Download and check catalog.json. Returns (version, [Recipe, ...]). Raises CatalogError."""
    try:
        body = json.loads(_download(CATALOG_URL, MAX_CATALOG_BYTES).decode("utf-8"))
    except ValueError as error:                           # not JSON / not UTF-8
        raise CatalogError("the catalogue is damaged") from error
    if not isinstance(body, dict) or not isinstance(body.get("recipes"), list):
        raise CatalogError("the catalogue has an unexpected format")
    recipes = []
    for item in body["recipes"]:
        try:
            recipe = recipe_from_dict(item)               # dict -> Recipe (raises on missing fields)
        except (KeyError, TypeError, ValueError):
            continue                                      # skip one broken entry, keep the rest
        name = (recipe.image_path or "")[len("asset:"):]
        if recipe.image_path and not SAFE_IMAGE_NAME.fullmatch(name):   # e.g. "../../secret"
            recipe.image_path = None                      # ignore it -> the default picture is used
        if recipe.uid and recipe.name:
            recipes.append(recipe)
    return str(body.get("version", "")), recipes


def download_missing_images(recipes):
    """Fetch pictures that are neither bundled in the app nor cached yet (runs in the background)."""
    folder = cache_dir()
    if not folder:
        return
    for recipe in recipes:
        path = recipe.image_path or ""
        name = path[len("asset:"):] if path.startswith("asset:") else ""
        if not SAFE_IMAGE_NAME.fullmatch(name) or resolve_image(path) is not None:
            continue                                      # odd name, or we already have it
        try:
            data = _download(f"{IMAGES_URL}/{name}", MAX_IMAGE_BYTES)
        except CatalogError:
            continue                                      # no picture -> a placeholder colour is shown
        with open(os.path.join(folder, name), "wb") as out:
            out.write(data)


def sync_if_due(db, on_done, force=False):
    """Check the catalogue at most once a day, in the background.

    on_done(changed, ok) is called ON A BACKGROUND THREAD with ok=False when the check failed, and
    changed=True when new recipes are waiting - the caller must hop to the UI thread (Kivy:
    Clock.schedule_once) and call apply_catalog() there, because SQLite may only be used by the
    thread that opened it.
    Returns False (and does nothing) when today's check already succeeded.
    """
    if not force and db.get_setting(CHECKED_ON) == date.today().isoformat():
        return False                                      # already up to date today
    if _state["running"]:                                 # a check is already on its way (4.7.1:
        return True                                       # the log showed two at once) - don't start another
    failed_at = _state["failed_at"]
    if not force and failed_at is not None and time.monotonic() - failed_at < RETRY_AFTER_SECONDS:
        on_done(None, False)                              # failed a moment ago: stay "Offline" for now
        return True
    known = db.get_setting(VERSION)
    _state["running"] = True

    def work():
        try:
            version, recipes = fetch_catalog()
            download_missing_images(recipes)              # pictures first, so new cards look right
        except CatalogError as error:
            print(f"[FridgeChef] Catalogue check failed ({error}) - using the saved recipes")
            _state.update(running=False, failed_at=time.monotonic())
            on_done(None, False)
            return
        _state.update(running=False, failed_at=None)
        on_done((version, recipes) if version != known else None, True)
    threading.Thread(target=work, daemon=True).start()    # daemon: never keeps the app alive
    return True


def apply_catalog(db, update):
    """Save a downloaded catalogue into the database (UI thread only). update = (version, recipes)."""
    if update:
        version, recipes = update
        for recipe in recipes:
            db.upsert_catalog_recipe(recipe, commit=False)   # update by uid, or add if new
        db.commit()
        db.set_setting(VERSION, version)
    db.set_setting(CHECKED_ON, date.today().isoformat())  # no new check until tomorrow
