"""
config.py
---------
WHY THIS FILE EXISTS:
    One place for the addresses the app downloads from.

    Version 4.7.1: there is no recipe SERVER any more. The recipe catalogue is a plain file on
    GitHub Pages (published by .github/workflows/publish-catalog.yml), and all matching happens on
    the phone (see app/catalog.py). These addresses are public on purpose - they only serve the
    same recipes that are already inside the app, and contain no account or project details.
"""

SITE_URL = "https://dhruvb-cloud.github.io/FridgeChef"   # the GitHub Pages site of this repository
CATALOG_URL = f"{SITE_URL}/catalog.json"                 # the recipes + their version
IMAGES_URL = f"{SITE_URL}/images"                        # the recipe pictures

REQUEST_TIMEOUT_SECONDS = 8                # give up after this and keep using the saved recipes
