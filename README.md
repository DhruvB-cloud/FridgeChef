# FridgeChef

FridgeChef is a kitchen app. You tell it what's in your fridge and cupboard (with quantities and expiry dates) and which cooking machines you own. It then:

- shows which recipes you can cook, for **1 person** by default;
- recommends dishes for the current meal time;
- warns you about food that expires today;
- subtracts the ingredients you used once you finish cooking.

It also keeps a **cooking calendar**, a Duolingo-style **streak** and your **favourite dish**. You can add your own recipes with photos and share any recipe as an image card.

It has two parts:

| Part | Technology | Runs on |
|---|---|---|
| **The app** (`main.py`, `app/`) | Python + **Kivy** | Android phone, or Windows/macOS/Linux for development |
| **The recipe catalogue** (`catalog.json` + pictures) | Plain files made by `tools/export_catalog.py` | GitHub Pages (free), published by a GitHub Action |

All recipe matching, filtering and sorting happens **on the phone**. Once a day the app downloads the published catalogue and saves new or changed recipes; without internet it simply keeps using the recipes it already has. Everything you enter is always stored on the device.

> **Version 4.7.1:** the app used to call a recipe server on Google Cloud Run for every visit to the Recipes tab. A server like that costs money per request, so anyone could run up the bill by flooding it. It was replaced by the static catalogue: nothing runs per request, there is nothing to attack, and it costs nothing.

---

## 1. Running it on your PC

```powershell
cd F:\Projects\FridgeChef
py -3.13 -m venv .venv                 # Kivy does not support Python 3.14 yet - use 3.13
.\.venv\Scripts\activate
pip install -r requirements.txt
$env:KIVY_HOME = "F:\DevCache\kivy"    # keep Kivy's settings and logs on F: (it uses C: by default)
.\.venv\Scripts\python main.py         # opens a phone-sized window
```

On a PC the app keeps its database and photos in `local_data/` inside the project (git-ignored), never in `C:\Users\...\AppData`. The status chip on the Recipes tab shows **Up to date** after the daily catalogue check succeeded and **Offline** when it couldn't reach the catalogue (the saved recipes keep working).

**Run the automated tests** (logic, input rules, database upgrade, streaks, suggestions, catalogue):
```powershell
.\.venv\Scripts\python -m unittest discover tests -v
```

> **VS Code tip:** if the editor underlines `kivy` imports, press `Ctrl+Shift+P` → *Python: Select Interpreter* → choose `.venv\Scripts\python.exe`.

## 2. Using it on your phone

**Let GitHub build the APK.** Every push that changes the app (`main.py`, `app/`, `assets/`, `buildozer.spec`) runs [.github/workflows/build-apk.yml](.github/workflows/build-apk.yml) on GitHub's free Linux computers. To get the APK:
1. Open the repository on GitHub → **Actions** tab → the newest **Build Android APK** run.
2. When it shows a green tick, scroll down to **Artifacts** → download **FridgeChef-apk** (a zip with the `.apk` inside).
3. To publish a public download for friends, push a version tag: `git tag -a v4.7.1 -m "..."` then `git push origin v4.7.1`. The APK is then attached to a **Release** (and the App Hub shows it).

**Building on your own Linux/WSL machine instead:**
```bash
pip install buildozer cython
sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev
cd /mnt/f/Projects/FridgeChef
buildozer android debug          # the APK appears in ./bin/
```

---

## 3. The recipe catalogue

| Address | What it is |
|---|---|
| `https://dhruvb-cloud.github.io/FridgeChef/catalog.json` | `{"version": "...", "count": 21, "recipes": [...]}` |
| `https://dhruvb-cloud.github.io/FridgeChef/images/<file>` | A recipe picture (the app downloads any it doesn't already have) |

- **Made by** `tools/export_catalog.py` from `app/seed_recipes.py` and `assets/recipe_images/`; **published by** [.github/workflows/publish-catalog.yml](.github/workflows/publish-catalog.yml) whenever those change on `main`. One-time setup: GitHub → Settings → Pages → Source: **GitHub Actions**.
- **The version** is a fingerprint of the recipes (`catalog.fingerprint`), so the app only saves recipes when something really changed.
- **Downloaded by** `app/catalog.py`: at most once a day, in a background thread, with size limits (2 MB) and checks on every recipe and picture name.

---

## 4. How each requirement is implemented

| Requirement | Where |
|---|---|
| Fridge items / groceries with quantity, unit and expiry | `app/ui/pantry_screen.py` → `app/database.py`; "Where is it?" = **Fridge** or **Outside** |
| **Dates as dd-mm-yyyy, picked from dropdowns** | `app/ui/date_picker.py` (Day / Month / Year) and `app/dates.py` |
| **Easter egg: adding "love"** | `app/ui/easter_egg.py`: a heart animation plays, and nothing is added |
| **Input rules** (names, quantities, times) | `app/validation.py`; enforced while typing (`SoftInput(rule=...)`) and again on Save |
| Type-ahead dropdown for ingredient names ("oni" → Onion) | `app/ui/autocomplete.py` + `app/ingredient_catalog.py`; picking a suggestion also fills in the usual unit and category |
| First start: avatar, name, cooking machines | `app/ui/welcome_popup.py`; change them later on the Profile tab |
| Cooking machines | Profile tab → *My cooking machines*; the Recipes tab hides dishes your machines can't cook |
| Recipes tab | `app/ui/recipes_screen.py` → `app/recipe_engine.py`, with the daily catalogue update from `app/catalog.py` |
| Works without data | All matching runs on the phone; the catalogue is only checked once a day |
| Filters: veg/non-veg, nutrition, cuisine | *Filters* panel on the Recipes tab |
| **Sort** | *Sort by*: **Longest first** (default), Best match, Most protein, Least carbs, Most carbs, Fewest calories, Quickest (`recipe_engine.sort_matches`) |
| **1 person by default** | Matching, ingredient amounts and deductions use 1 serving; change it per recipe (− / +) or permanently in Profile → *Cooking for* |
| Recommended dishes for the nearest meal | `app/meal_time.py` + `recommend()`; a horizontal strip of thumbnails |
| Items expiring today: notification + highlighted dishes | `app/expiry.py`; **Use today** label, and those dishes are ranked first |
| **Every recipe has an image** | Built-in: `assets/recipe_images/`. New catalogue recipes: downloaded and cached. Your own without a photo: a generated soft picture (`images.make_default_image`) |
| Add your own recipe with an image | `app/ui/add_recipe_screen.py`; photos up to 10 MB, stored as a small JPEG (`ui/image_picker.py`) |
| Share as an image card | `app/recipe_card.py` + `app/share.py` |
| Subtract used ingredients after cooking | Detail → Start cooking → Finished → `plan_deduction()` |
| **Calendar of what you cooked** | `app/ui/calendar_screen.py` (reads the `cook_log` table) |
| **User info: favourite dish + streak** | `app/ui/profile_screen.py` + `app/stats.py` |
| **Rounder, softer UI** | `app/ui/widgets.py` (palette, rounded buttons, inputs, cards, chips, popups) + `assets/ui/` |

---

## 5. Every file, and why it exists

```
FridgeChef/
├── main.py                       Entry point: window, database, screens, rounded tab bar, Back button, expiry timer
├── requirements.txt              Python packages for running the app on a computer
├── buildozer.spec                Android packaging settings (permissions, what goes into the APK)
├── README.md                     This document
├── .gitignore                    Files NOT uploaded to GitHub (incl. local_data/ and site/)
├── .github/workflows/
│   ├── build-apk.yml             Builds the signed APK; a version tag also publishes a Release
│   └── publish-catalog.yml       Publishes the recipe catalogue to GitHub Pages
├── docs/
│   ├── How FridgeChef Works.docx The beginner's guide
│   └── KILL_SWITCH.md            The Google Cloud billing kill switch (protects other services in that project)
├── app/
│   ├── __init__.py               Makes "app" a package; holds APP_VERSION
│   ├── config.py                 Public addresses of the recipe catalogue (GitHub Pages)
│   ├── catalog.py                Daily catalogue download: version check, recipes, missing pictures
│   ├── validation.py             Input rules: names, quantities, prep time, servings
│   ├── dates.py                  dd-mm-yyyy dates; short cooking times ("2 h 30")
│   ├── models.py                 Data shapes (PantryItem, Ingredient, Recipe with nutrition + uid), option lists, slugify()
│   ├── units.py                  Unit conversion (kg↔g, tbsp→ml), name matching (curd = yogurt), tidy amounts
│   ├── seed_recipes.py           21 built-in recipes (the master list the catalogue is made from)
│   ├── ingredient_catalog.py     ~90 known ingredients with usual unit and category; suggest() for type-ahead
│   ├── database.py               All SQLite access; upgrades old database files in place (_migrate)
│   ├── recipe_engine.py          Matching, filtering, SORTING, recommending, deducting after cooking
│   ├── meal_time.py              Which meal is nearest to the current time
│   ├── expiry.py                 Expiring-today / soon checks; at most one notification per day
│   ├── stats.py                  Streaks (current, longest, this week), favourite dish
│   ├── images.py                 Finds a recipe's picture (bundled / downloaded / own photo); avatars; default pictures
│   ├── api_schema.py             Converts recipes ↔ JSON (used by the exporter AND the app, so the format always matches)
│   ├── recipe_card.py            Draws the 1080×1350 shareable recipe card
│   ├── share.py                  Android share sheet, or opens the image viewer on a PC
│   └── ui/
│       ├── widgets.py            Soft palette + rounded widgets, typing rules, RoundImage, Chip, recipe cards, popups
│       ├── autocomplete.py       Text box with an ingredient suggestion dropdown
│       ├── date_picker.py        Day / Month / Year dropdowns (dd-mm-yyyy)
│       ├── easter_egg.py         The "love" heart animation (+ the floating-icons effect reused as confetti)
│       ├── welcome_popup.py      First-start popup (avatar, name, machines) and the avatar picker
│       ├── cooked_popup.py       The "Yay!" message after cooking, with "Add a photo" for the Calendar
│       ├── image_picker.py       Pick a photo (Android photo picker or desktop file browser) and store a small copy
│       ├── pantry_screen.py      "Fridge" tab plus the Add/Edit item form
│       ├── recipes_screen.py     "Recipes" tab: matching, Up to date/Offline status, filters, sort, Recommended
│       ├── recipe_detail_screen.py  Recipe page: photo, nutrition boxes, servings, cooking mode, share, save
│       ├── add_recipe_screen.py  "New recipe" form
│       ├── cookbook_screen.py    "Cookbook" tab: your own recipes plus saved dishes
│       ├── calendar_screen.py    "Calendar" tab: month grid and the dishes cooked on each day
│       └── profile_screen.py     "Profile" tab: avatar, name, streak, stats, favourite dish, settings, machines
├── assets/                       Bundled with the app, so it works offline
│   ├── recipe_images/*.jpg       Picture for every built-in recipe (+ thumbs/ for lists)
│   ├── avatars/*.png             The avatars to choose from
│   ├── icons/*.png               Tab icons, flame, trophy, star, nutrition icons, fridge containers
│   └── ui/*                      Rounded shapes and textures used by the UI
├── killswitch/                   Google Cloud function that switches billing off above the budget
├── tools/
│   ├── make_assets.py            Developer tool that draws / downloads everything in assets/
│   └── export_catalog.py         Builds site/ (catalog.json + images) for GitHub Pages
└── tests/
    ├── test_engine.py            Units, matching, sorting, 1-person default, deductions, meal time, database, upgrade
    └── test_features.py          Streaks, favourite dish, suggestions, dates, easter egg, JSON format, input rules, photos, catalogue
```

### Design decisions
- **Logic and UI are separate.** Everything outside `app/ui/` is plain Python, so the logic can be tested in milliseconds and the catalogue exporter can reuse it without Kivy.
- **Two kinds of ID.** Every recipe has a numeric `id`, which is local to each database, and a text `uid` (e.g. `dal-tadka`) that is the same everywhere. The app uses the `uid` to update catalogue recipes without creating duplicates.
- **The network never freezes the screen.** The daily catalogue check runs on a background thread and hands its result back to the UI thread with `Clock.schedule_once` (SQLite may only be used by the thread that opened it).
- **Input is checked twice.** Text boxes refuse bad characters while you type, and the Save buttons check the same rules again (`app/validation.py`), so nothing invalid reaches the database.
- **Rounded corners use 9-slice images.** One small white rounded PNG is stretched without distorting its corners and tinted to any colour. This is Kivy's own technique, and it rounds buttons, inputs, dropdowns and popups consistently.
- **Database upgrades are automatic.** A database created by an older version gains the new columns, built-in recipes get their `uid`, picture and nutrition values, and your fridge, saved dishes and history are kept (tested in `test_upgrade_from_version_1_database`).

---

## 6. Key behaviours, in plain words

- **Matching:** names are normalised (`Curd` = `Dahi` = `yogurt`, `Tomatoes` = `tomato`). Amounts are converted between units, so `0.5 kg` covers `250 g`. Expired items are ignored. Water and salt are always assumed to be available.
- **Servings:** the default is **1 person**. A recipe written for 4 has all its amounts divided by 4 for the fridge check, the ingredient list and the deduction.
- **Ranking (Best match):** (1) uses something expiring today and is missing at most 1 ingredient → (2) ready to cook → (3) uses something expiring soon → (4) fewer missing ingredients → (5) quicker to make. Other sort options reorder by that value, and ties keep the best-match order.
- **Streak:** each day you tap *Finished – update fridge* counts as a cooking day. If you haven't cooked yet today but did yesterday, the streak is still alive. It resets after a full day without cooking.
- **Favourite dish:** your most-cooked dish. If two dishes are tied, the one you cooked most recently wins.
- **Dates:** you always see and pick dd-mm-yyyy. The database stores yyyy-mm-dd, because that text sorts in date order.
- **Easter egg:** try adding **love** (or *pyaar*, *ishq*, *amour*…) to the fridge or to a recipe 💖

### Changes in version 4.7.1
- **Recipe server retired:** a static catalogue on GitHub Pages instead of Cloud Run (see section 3).
- **Input rules:** names up to 126 characters (letters of any language, numbers, spaces and `' - , . & ( )`); quantities and nutrition 0–9999.99; prep time 1–14,400 minutes; servings 1–20. Fixes a crash when saving a recipe with a huge number.
- **Photos:** up to 10 MB, stored as a small JPEG; read at reduced size, so big phone photos don't run out of memory. Android uses the system photo picker, so the app needs no photo permissions.
- **Welcome popup** (avatar, name, at least one cooking machine); the Recipes tab only shows dishes your machines can cook; "Change photo" appears once you've cooked a dish.
- **Taps vs. scrolling:** cards open only on a real tap, so resting your thumb to scroll no longer opens a recipe.
- **Layout fixes for small phones:** titles shrink to fit, recipe badges stack, calendar rows stay on one line, Profile cards fit, jar labels shorten with "…".
- **Privacy:** no automatic Google backup of the app's data (`allow_backup = False`).

### Changes in version 4
- **"pcs" amounts keep their decimals** and are shown neatly: `9½ pcs`, `¼ bunch` (`units.pretty_quantity`).
- **Coloured fields in the Fridge form:** light red for non-veg, light yellow for eggs, light green for vegetarian items (`ingredient_catalog.food_type`).
- **"Yay!" after cooking:** confetti, your streak, what was taken from the fridge, and an **Add a photo** button for the Calendar (`ui/cooked_popup.py`).

## 7. Known limits

- **Notifications only fire while the app is running** (when it starts, and every hour while it's open). Background notifications would need an Android service.
- **Your own recipes stay on your phone.** They are never uploaded anywhere.
- **To add a built-in recipe,** add it to `seed_recipes.py` (plus a picture in `assets/recipe_images/`), push to `main`: the catalogue is republished automatically and every app picks the recipe up within a day.
