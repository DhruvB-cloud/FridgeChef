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
| **The recipe API server** (`server/app.py`) | Python + **Flask** | Your computer (or any server) |

Every time the **Recipes tab** opens, the app sends an API request to the server and shows what comes back. If the server can't be reached (no mobile data, PC switched off), the app automatically uses the copy of the recipes saved on the phone. Everything you enter is always stored on the device.

---

## 1. Running it on your PC

```powershell
cd F:\Projects\FridgeChef
py -3.13 -m venv .venv                 # Kivy does not support Python 3.14 yet - use 3.13
.\.venv\Scripts\activate
pip install -r requirements.txt
```

**Start the app**: it starts the local API server for you:
```powershell
.\.venv\Scripts\python main.py         # opens a phone-sized window; starts server\app.py in the background if it isn't running
```

The status chip on the Recipes tab shows **Live** when the server answered and **Offline** when the app is using the copy saved on the device. The server's messages go to `server.log` in the app's data folder (shown on the Profile tab). When you close the app, it stops the server too.

To run the server yourself instead (e.g. to watch its output), start it in a separate terminal *before* the app. The app will then use that one:
```powershell
.\.venv\Scripts\python server\app.py   # http://127.0.0.1:5000/api/health should answer {"status": "ok"}
```

**Run the automated tests** (logic, database upgrade, streaks, suggestions and the API):
```powershell
.\.venv\Scripts\python -m unittest discover tests -v
```

> **VS Code tip:** if the editor underlines `kivy` imports, press `Ctrl+Shift+P` → *Python: Select Interpreter* → choose `.venv\Scripts\python.exe`.

## 2. Using it on your phone

> **Sharing the app (GitHub, app store, APK for friends)?** Put the server in the cloud first. Follow **[docs/CLOUD_DEPLOYMENT.md](docs/CLOUD_DEPLOYMENT.md)** (Google Cloud Run, free for an app this size), then paste the URL into `CLOUD_SERVER` in `app/config.py` and rebuild the APK. The steps below are only for testing on your own phone with your PC as the server.

1. Build the APK (Linux or WSL only):
   ```bash
   pip install buildozer cython
   sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev
   cd /mnt/f/Projects/FridgeChef
   buildozer android debug          # the APK appears in ./bin/
   ```
2. Run `server\app.py` on your PC. It listens on all network interfaces (`0.0.0.0`), so other devices can reach it.
3. Find your PC's Wi-Fi IP address (`ipconfig` → IPv4 Address, e.g. `192.168.1.20`).
4. On the phone, open **Profile → Recipe server**, enter `http://192.168.1.20:5000` and tap **Test connection**.

> Android 9+ blocks plain `http://` traffic by default. If **Test connection** fails while the PC browser can open the URL, this is why. The cloud server uses `https://`, so it doesn't have this problem. Meanwhile, the app keeps working in Offline mode.

---

## 3. The API

| Method & URL | What it does |
|---|---|
| `GET /api/health` | `{"status": "ok", "api_version": 1, "recipes": 21}` |
| `GET /api/recipes?cuisine=Indian&diet=Veg` | The catalogue (both filters optional) |
| `GET /api/recipes/<uid>` | One recipe, e.g. `/api/recipes/dal-tadka` |
| `POST /api/recipes/search` | **Called by the Recipes tab.** Matches the catalogue against your fridge |
| `GET /images/<file>` | A recipe picture (the app downloads any it doesn't already have) |

Example `POST /api/recipes/search` body:
```json
{
  "pantry": [{"name": "Curd", "quantity": 500, "unit": "g", "expiry": "2026-10-04"}],
  "appliances": ["Stove", "Rice Cooker"],
  "servings": 1,
  "filters": {"diet": "Veg", "max_minutes": 30, "nutrition": "Any", "cuisine": "Any",
              "only_cookable": false, "search": "", "sort": "Most protein"},
  "today": "2026-10-04",
  "now": "2026-10-04T13:05"
}
```
The response contains `meal` (e.g. "Lunch"), `recommended` and `results`. Each match includes the full recipe and its `have` / `missing` / `uses_expiring_today` lists. The phone sends its own date and time, so expiry checks and the meal slot are always correct for the user, even if the server is in a different time zone.

---

## 4. How each requirement is implemented

| Requirement | Where |
|---|---|
| Fridge items / groceries with quantity, unit and expiry | `app/ui/pantry_screen.py` → `app/database.py`; "Where is it?" = **Fridge** or **Outside** |
| **Dates as dd-mm-yyyy, picked from dropdowns** | `app/ui/date_picker.py` (Day / Month / Year + "Never expires") and `app/dates.py` |
| **Easter egg: adding "love"** | `app/ui/easter_egg.py`: a heart animation plays, and nothing is added |
| **Server in the cloud** | Google Cloud Run: `Dockerfile`, `server/wsgi.py`, guide in `docs/CLOUD_DEPLOYMENT.md`; the address goes in `app/config.py` |
| Type-ahead dropdown for ingredient names ("oni" → Onion) | `app/ui/autocomplete.py` + `app/ingredient_catalog.py`; picking a suggestion also fills in the usual unit and category |
| Cooking machines | Profile tab → *My cooking machines* |
| Recipes tab fetches from an API / web server | `app/ui/recipes_screen.py` → `app/api_client.py` → `server/app.py` |
| Works without data | Recipes received from the server are saved locally (`Database.upsert_catalog_recipe`); offline, the same engine runs on the phone |
| Filters: veg/non-veg, time, nutrition, cuisine | *Filters* panel on the Recipes tab |
| **Sort by protein / carbs** | *Sort by*: Most protein, Least carbs, Most carbs, Fewest calories, Quickest (`recipe_engine.sort_matches`) |
| **1 person by default** | Matching, ingredient amounts and deductions use 1 serving; change it per recipe (− / +) or permanently in Profile → *Cooking for* |
| Recommended dishes for the nearest meal | `app/meal_time.py` + `recommend()`; a horizontal strip on phones, a second column on wide screens |
| Items expiring today: notification + highlighted dishes | `app/expiry.py`; **USE TODAY** label, and those dishes are ranked first |
| **Every recipe has an image** | Built-in: `assets/recipe_images/`. Server-only: downloaded and cached. Your own without a photo: a generated soft picture (`images.make_default_image`) |
| Add your own recipe with an image | `app/ui/add_recipe_screen.py` |
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
├── requirements.txt              Python packages (Flask is only needed for the server)
├── buildozer.spec                Android packaging settings (permissions, what goes into the APK)
├── README.md                     This document
├── Dockerfile                    How Google Cloud Run builds the server container (see docs/CLOUD_DEPLOYMENT.md)
├── .gcloudignore / .dockerignore Files NOT uploaded to the cloud (your .venv, tests, build output)
├── .gitignore                    Files NOT uploaded to GitHub
├── docs/
│   └── CLOUD_DEPLOYMENT.md       Step-by-step: Google Cloud account → deploy the server → point the app at it
├── app/                          ── code shared by the app (and partly by the server) ──
│   ├── __init__.py               Makes "app" a package; holds APP_VERSION
│   ├── config.py                 Server addresses: LOCAL_SERVER now, CLOUD_SERVER after deploying
│   ├── dates.py                  Shows dates as dd-mm-yyyy (the database keeps yyyy-mm-dd, which sorts correctly)
│   ├── models.py                 Data shapes (PantryItem, Ingredient, Recipe with nutrition + uid), option lists, slugify()
│   ├── units.py                  Unit conversion (kg↔g, tbsp→ml) and name matching (curd = yogurt)
│   ├── seed_recipes.py           21 built-in recipes, plus a table of protein / carbs / calories per serving
│   ├── ingredient_catalog.py     ~90 known ingredients with usual unit and category; suggest() for type-ahead
│   ├── database.py               All SQLite access; upgrades old database files in place (_migrate)
│   ├── recipe_engine.py          Matching, filtering, SORTING, recommending, deducting after cooking
│   ├── meal_time.py              Which meal is nearest to the current time
│   ├── expiry.py                 Expiring-today / soon checks; at most one notification per day
│   ├── stats.py                  Streaks (current, longest, this week), favourite dish
│   ├── images.py                 Finds a recipe's picture (bundled / downloaded / own photo); draws default pictures
│   ├── api_schema.py             Converts objects ↔ JSON. Used by BOTH the app and the server, so the format always matches
│   ├── api_client.py             Calls the server from the app (in a background thread, with offline fallback)
│   ├── recipe_card.py            Draws the 1080×1350 shareable recipe card
│   ├── share.py                  Android share sheet, or opens the image viewer on a PC
│   └── ui/
│       ├── widgets.py            Soft palette + rounded widgets, RoundImage, Chip, RecipeTile, RecipeCard, popups
│       ├── autocomplete.py       Text box with an ingredient suggestion dropdown
│       ├── date_picker.py        Day / Month / Year dropdowns (dd-mm-yyyy) + "Never expires"
│       ├── easter_egg.py         The "love" heart animation (+ the floating-icons effect reused as confetti)
│       ├── cooked_popup.py       The "Yay!" message after cooking, with "Add a photo" for the Calendar
│       ├── image_picker.py       Pick a photo (Android picker or desktop file browser) and store a resized copy
│       ├── pantry_screen.py      "Fridge" tab plus the Add/Edit item form
│       ├── recipes_screen.py     "Recipes" tab: API request, Live/Offline status, filters, sort, Recommended
│       ├── recipe_detail_screen.py  Recipe page: photo, nutrition boxes, servings, cooking mode, share, save
│       ├── add_recipe_screen.py  "New recipe" form
│       ├── cookbook_screen.py    "Cookbook" tab: your own recipes plus saved dishes (picture grid)
│       ├── calendar_screen.py    "Calendar" tab: month grid and the dishes cooked on each day
│       └── profile_screen.py     "Profile" tab: name, streak, stats, favourite dish, settings, machines, server
├── server/
│   ├── __init__.py               Makes "server" a package (needed by gunicorn in the cloud)
│   ├── app.py                    The Flask web server / REST API (every line commented)
│   ├── wsgi.py                   Entry point for gunicorn in the cloud
│   ├── requirements.txt          Packages for the cloud server (Flask, gunicorn, Pillow)
│   └── data/catalog.db           The server's own recipe database (created on first run)
├── assets/                       Bundled with the app, so it works offline
│   ├── recipe_images/*.jpg       Default picture for every built-in recipe
│   ├── icons/*.png               Tab icons, flame, trophy, star, nutrition icons
│   └── ui/*.png                  White rounded shapes used to round buttons, inputs and popups
├── tools/
│   └── make_assets.py            Developer tool (Windows) that draws everything in assets/
└── tests/
    ├── test_engine.py            Units, matching, sorting, 1-person default, deductions, meal time, database, upgrade
    └── test_features.py          Streaks, favourite dish, suggestions, dates, date picker, easter egg, JSON format, API, cloud entry point
```

### Design decisions
- **Logic and UI are separate.** Everything outside `app/ui/` is plain Python. That's why the server can reuse the same `recipe_engine.py`, so results are identical online and offline, and the logic can be tested in milliseconds.
- **Two kinds of ID.** Every recipe has a numeric `id`, which is local to each database, and a text `uid` (e.g. `dal-tadka`) that is the same on the phone and the server. The app uses the `uid` to store server recipes locally without creating duplicates.
- **The network call never freezes the screen.** `RecipeApiClient.fetch_async` runs on a background thread and hands its result back to the UI thread with `Clock.schedule_once`. If you change filters while a request is still running, the older answer is ignored.
- **Pictures are files, not fonts.** The food illustrations are drawn once with Windows' colour emoji font (`tools/make_assets.py`) and shipped as JPG/PNG files, because phones don't have that font.
- **Rounded corners use 9-slice images.** One small white rounded PNG is stretched without distorting its corners and tinted to any colour. This is Kivy's own technique, and it rounds buttons, inputs, dropdowns and popups consistently.
- **Database upgrades are automatic.** A database created by version 1 of the app gains the new columns, built-in recipes get their `uid`, picture and nutrition values, and your fridge, saved dishes and history are kept (tested in `test_upgrade_from_version_1_database`).

---

## 6. Key behaviours, in plain words

- **Matching:** names are normalised (`Curd` = `Dahi` = `yogurt`, `Tomatoes` = `tomato`). Amounts are converted between units, so `0.5 kg` covers `250 g`. Expired items are ignored. Water and salt are always assumed to be available.
- **Servings:** the default is **1 person**. A recipe written for 4 has all its amounts divided by 4 for the fridge check, the ingredient list and the deduction.
- **Ranking (Best match):** (1) uses something expiring today and is missing at most 1 ingredient → (2) ready to cook → (3) uses something expiring soon → (4) fewer missing ingredients → (5) quicker to make. Other sort options reorder by that value, and ties keep the best-match order.
- **Streak:** each day you tap *Finished – update fridge* counts as a cooking day. If you haven't cooked yet today but did yesterday, the streak is still alive ("Cook today to keep your streak alive!"). It resets after a full day without cooking.
- **Favourite dish:** your most-cooked dish. If two dishes are tied, the one you cooked most recently wins.
- **Dates:** you always see and pick dd-mm-yyyy. The database stores yyyy-mm-dd, because that text sorts in date order, which keeps "soonest expiry first" working. The day dropdown always matches the month, so 31-02 is impossible.
- **Easter egg:** try adding **love** (or *pyaar*, *ishq*, *amour*…) to the fridge or to a recipe 💖

### Changes in version 4
- **"pcs" amounts keep their decimals** (a recipe may really use half a cucumber) and are shown neatly: `9½ pcs`, `¼ bunch` (`units.pretty_quantity`).
- **Coloured fields in the Fridge form:** the box you're typing in turns light green. The Name box turns **light red** for non-veg (chicken, fish, prawns…), **light yellow** for eggs and **light green** for vegetarian items (`ingredient_catalog.food_type`). "Eggplant" is correctly treated as veg.
- **"Yay!" after cooking:** confetti, your streak, what was taken from the fridge, and an **Add a photo** button. The photo is stored with that day's entry and shown in the Calendar (on the day's tile and under the dish), and it can also be added later there (`ui/cooked_popup.py`).
- **Share error fixed:** `[Errno 22] Invalid argument` happened because the previous card was still open in Windows Photos, and Windows doesn't allow overwriting an open file. Each share now writes a new file, and old cards are tidied up automatically.
- **Overlapping Edit/Delete buttons fixed:** the rounded widgets ignored an explicit `size=(w, h)` and used their default height (`widgets._default_height`).

### Bugs fixed in version 3
- **Couldn't type ingredient names.** The type-ahead box defined a method called `_on_focus`, which accidentally replaced Kivy's own method with the same name, the one that connects the keyboard. The box looked focused, but key presses were ignored. It's renamed now; see the note in `autocomplete.py`.
- **Suggestions disappeared while typing fast.** Kivy closes a dropdown a moment *later*, so a close requested for "o" could arrive after "on" had opened the list. The suggestion list now closes immediately.
- **The first tap after typing did nothing.** An open Kivy dropdown swallows every tap on screen. The suggestion list now closes *and* passes the tap on to whatever you tapped.

## 7. Known limits

- **Notifications only fire while the app is running** (when it starts, and every hour while it's open). Background notifications would need an Android service.
- **The server has no login.** It only serves the public recipe catalogue (read-only), so it's safe on the internet. The phone sends its fridge list for matching, but the server never stores it. If you ever add features that save user data on the server, add authentication first.
- **Your own recipes stay on your phone**, and they aren't uploaded to the server. They are matched on the phone and merged into the server's results.
- **To add a built-in recipe,** add it to `seed_recipes.py` (plus a `NUTRITION` entry and an `ART` entry in `tools/make_assets.py`), run `tools/make_assets.py`, then restart the server and the app. Both databases pick it up automatically on start.
