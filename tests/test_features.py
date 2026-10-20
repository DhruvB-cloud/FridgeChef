"""
test_features.py
----------------
WHY THIS FILE EXISTS:
    Automated checks for the second set of features:
      * streaks / favourite dish (app/stats.py)
      * ingredient suggestions (app/ingredient_catalog.py)
      * the recipe catalogue (app/catalog.py) - including a round trip through the JSON format
        (app/api_schema.py), versions, and unsafe picture names
      * the 4.7.1 input rules, photo limits and display fixes
    Run from the FridgeChef folder:   python -m unittest discover tests -v
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api_schema import recipe_from_dict, recipe_to_dict
from app.ingredient_catalog import info_for, suggest
from app.models import PantryItem
from app.seed_recipes import SEED_RECIPES
from app.stats import current_streak, favourite_dish, longest_streak, week_strip

TODAY = date(2026, 10, 4)          # a Sunday


def days_ago(*numbers):
    return {TODAY - timedelta(days=n) for n in numbers}


class StreakTest(unittest.TestCase):
    def test_streak_counts_consecutive_days(self):
        self.assertEqual(current_streak(days_ago(0, 1, 2), TODAY), (3, True))

    def test_streak_alive_if_cooked_yesterday(self):
        # Not cooked yet today, but yesterday and the day before: streak 2, "at risk".
        self.assertEqual(current_streak(days_ago(1, 2), TODAY), (2, False))

    def test_streak_broken_after_a_missed_day(self):
        self.assertEqual(current_streak(days_ago(2, 3, 4), TODAY), (0, False))

    def test_longest_streak(self):
        self.assertEqual(longest_streak(days_ago(0, 5, 6, 7, 8, 20)), 4)

    def test_week_strip_starts_monday(self):
        strip = week_strip(days_ago(0), TODAY)
        self.assertEqual(strip[0][0].weekday(), 0)       # Monday first
        self.assertEqual(strip[-1], (TODAY, True, True))  # Sunday = today, cooked

    def test_favourite_dish(self):
        log = [{"recipe_name": "Dal", "cooked_on": "2026-10-01"},
               {"recipe_name": "Poha", "cooked_on": "2026-10-02"},
               {"recipe_name": "Dal", "cooked_on": "2026-10-03"}]
        self.assertEqual(favourite_dish(log), ("Dal", 2))
        self.assertEqual(favourite_dish([]), (None, 0))


class SuggestTest(unittest.TestCase):
    def test_oni_suggests_onion_first(self):
        result = suggest("oni")
        self.assertEqual(result[0], "Onion")             # starts-with match first
        self.assertIn("Green onion", result)             # contains match later

    def test_user_names_and_info(self):
        self.assertIn("Grandma's masala", suggest("gran", extra_names=["Grandma's masala"]))
        info = info_for("onion")                         # 5.0: unit, tag, shelf life, usual amount
        self.assertEqual((info.unit, info.tag), ("pcs", "Fresh produce"))
        self.assertEqual(info_for("Tomatoes").unit, "pcs")   # plurals / other spellings found too
        self.assertEqual(suggest("o"), [])               # too short to be useful


class Version3Test(unittest.TestCase):
    """Bug-fix release: dd-mm-yyyy dates, 'Outside' category, the 'love' easter egg."""

    def test_dates_are_dd_mm_yyyy(self):
        from app.dates import format_date, parse_date
        self.assertEqual(format_date(date(2026, 10, 4)), "04-10-2026")
        self.assertEqual(parse_date("04-10-2026"), date(2026, 10, 4))
        self.assertEqual(parse_date("2026-10-04"), date(2026, 10, 4))   # old format still understood
        self.assertEqual(format_date(None), "")
        with self.assertRaises(ValueError):
            parse_date("31-02-2026")                                     # no 31st of February

    def test_love_easter_egg_words(self):
        from app.ui.easter_egg import is_love
        for word in ("love", " Love ", "LOVE!!", "loves", "pyaar"):
            self.assertTrue(is_love(word), word)
        for word in ("lovage", "olive", "clove", ""):
            self.assertFalse(is_love(word), word)

    def test_grocery_renamed_to_outside(self):
        import sqlite3
        from app.database import Database
        from app.models import CATEGORIES
        self.assertEqual(CATEGORIES, ["Fridge", "Outside"])
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "x.db")
            db = Database(path)
            db.conn.execute("INSERT INTO pantry_items(name, category, quantity, unit, added_on) "
                            "VALUES ('Rice', 'Grocery', 1, 'kg', '2026-01-01')")   # an old-style row
            db.conn.commit()
            db.close()
            db = Database(path)                                          # re-open -> migration runs
            self.assertEqual(db.list_pantry()[0].category, "Outside")
            db.close()

    def test_date_picker_dropdowns(self):
        from app.ui.date_picker import DatePicker
        picker = DatePicker(date(2028, 2, 10))
        self.assertEqual((picker.day.text, picker.month.text, picker.year.text), ("10", "02 - Feb", "2028"))
        self.assertEqual(len(picker.day.values), 29)                     # 2028 is a leap year
        picker.day.text = "29"
        picker.year.text = "2027"                                        # 2027: February has 28 days
        self.assertEqual(picker.get_date(), date(2027, 2, 28))           # day moved to the last valid one
        self.assertIn("28-02-2027", picker.preview.text)                 # preview in dd-mm-yyyy
        picker.set_date(None)                                            # "Never expires"
        self.assertIsNone(picker.get_date())


class Version4Test(unittest.TestCase):
    """pcs fractions, food-type colours, cooked-dish photos, share-card file names."""

    def test_pcs_fractions_display(self):
        from app.units import pretty_quantity
        self.assertEqual(pretty_quantity(9.5, "pcs"), "9½ pcs")
        self.assertEqual(pretty_quantity(0.5, "bunch"), "½ bunch")
        self.assertEqual(pretty_quantity(2.75, "pcs"), "2¾ pcs")
        self.assertEqual(pretty_quantity(9.33, "pcs"), "9.33 pcs")      # no symbol -> decimals kept
        self.assertEqual(pretty_quantity(1.5, "kg"), "1.5 kg")          # weights never use symbols

    def test_food_type(self):
        from app.ingredient_catalog import food_type
        self.assertEqual(food_type("Chicken breast"), "nonveg")
        self.assertEqual(food_type("Prawns"), "nonveg")
        self.assertEqual(food_type("Eggs"), "egg")
        self.assertEqual(food_type("Eggplant"), "veg")                  # not an egg!
        self.assertEqual(food_type("Hamper"), "veg")                    # not ham!
        self.assertIsNone(food_type("  "))

    def test_cooked_photo_saved_with_calendar_entry(self):
        from app.database import Database
        from app.models import Recipe
        with tempfile.TemporaryDirectory() as folder:
            db = Database(os.path.join(folder, "x.db"))
            rid = db.add_recipe(Recipe(name="Test Dish", cuisine="Indian", is_veg=True,
                                       prep_minutes=5, servings=1, steps=["Cook"]))
            log_id = db.log_cooked(rid, 1)
            self.assertIsNone(db.cook_log()[0]["photo_path"])
            db.set_cook_photo(log_id, "C:/photos/dish.jpg")
            entry = db.cook_log()[0]
            self.assertEqual((entry["id"], entry["photo_path"], entry["recipe_name"]),
                             (log_id, "C:/photos/dish.jpg", "Test Dish"))
            db.close()

    def test_times_cooked_unlocks_change_photo(self):
        # 4.7.1: "Change photo" only shows once the recipe was cooked, using db.times_cooked().
        from app.database import Database
        from app.models import Recipe
        with tempfile.TemporaryDirectory() as folder:
            db = Database(os.path.join(folder, "x.db"))                  # a fresh, empty database
            rid = db.add_recipe(Recipe(name="Test Dish", cuisine="Indian", is_veg=True,
                                       prep_minutes=5, servings=1, steps=["Cook"]))
            self.assertEqual(db.times_cooked(rid), 0)                     # never cooked -> no button
            db.log_cooked(rid, 1)                                         # cook it twice
            db.log_cooked(rid, 2)
            self.assertEqual(db.times_cooked(rid), 2)                     # counted -> button shows
            db.close()

    def test_old_share_cards_are_tidied(self):
        import time
        from app.ui.recipe_detail_screen import remove_old_cards
        with tempfile.TemporaryDirectory() as folder:
            for i in range(8):                                          # 8 old cards
                path = os.path.join(folder, f"recipe_card_1_{i}.png")
                open(path, "wb").close()
                os.utime(path, (time.time() + i, time.time() + i))      # different ages
            remove_old_cards(folder, keep=5)
            self.assertEqual(sorted(os.listdir(folder)),
                             [f"recipe_card_1_{i}.png" for i in range(3, 8)])   # newest 5 kept


class Version41Test(unittest.TestCase):
    """Version 4.1: items are drawn as a bottle, glass jar or dish in the fridge picture."""

    def test_container_guess(self):
        from app.models import guess_container
        self.assertEqual(guess_container("Soy sauce", "ml"), "bottle")      # liquids -> bottle
        self.assertEqual(guess_container("Milk", "l"), "carton")           # 5.0: milk comes in a carton
        self.assertEqual(guess_container("Soy sauce", "L"), "bottle")       # other liquids: bottle
        self.assertEqual(guess_container("Leftover dal", "cup"), "dish")    # cooked food -> dish
        self.assertEqual(guess_container("Rice (cooked)", "g"), "dish")
        self.assertEqual(guess_container("Rice (uncooked)", "g"), "jar")    # "uncooked" is not "cooked"
        self.assertEqual(guess_container("Rice", "kg", "Grain"), "jar")     # dry food -> jar
        self.assertEqual(guess_container("Yogurt", "kg", "Fresh produce"), "tub")    # 5.0: dairy
        self.assertEqual(guess_container("Egg", "pcs", "Fresh produce"), "basket")
        self.assertEqual(guess_container("Green onion", "pcs", "Fresh produce"), "greens")
        self.assertEqual(guess_container("Tomato", "pcs", "Fresh produce"), "basket")

    def test_container_saved_and_old_files_upgraded(self):
        import sqlite3
        from app.database import Database
        from app.models import PantryItem
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "old.db")
            old = sqlite3.connect(path)                                  # a 4.0 file: no container column
            old.execute("CREATE TABLE pantry_items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, "
                        "category TEXT NOT NULL DEFAULT 'Fridge', quantity REAL NOT NULL, unit TEXT NOT NULL, "
                        "expiry TEXT, added_on TEXT NOT NULL)")
            old.execute("INSERT INTO pantry_items(name, quantity, unit, added_on) "
                        "VALUES ('Ketchup', 500, 'ml', '2026-01-01')")
            old.commit()
            old.close()
            db = Database(path)                                          # opening adds the column
            ketchup = db.list_pantry()[0]
            self.assertIsNone(ketchup.container)                         # nothing chosen yet...
            self.assertEqual(ketchup.kept_in(), "bottle")                # ...so it is guessed
            ketchup.container = "jar"                                    # the user picks a jar
            db.update_pantry_item(ketchup)
            db.add_pantry_item(PantryItem("Dal", 1, "cup", container="dish"))
            kinds = {i.name: i.kept_in() for i in db.list_pantry()}
            self.assertEqual(kinds, {"Ketchup": "jar", "Dal": "dish", "Water": "bottle"})
            db.close()

    def test_water_is_always_there(self):
        from app.database import Database
        from app.models import UNLIMITED
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "x.db")
            db = Database(path)
            water = [i for i in db.list_pantry() if i.is_water]
            self.assertEqual(len(water), 1)                             # added automatically
            self.assertIsNone(water[0].expiry)                          # never expires
            self.assertEqual(water[0].quantity, UNLIMITED)              # never runs out
            db.conn.execute("INSERT INTO pantry_items(name, quantity, unit, expiry, added_on) "
                            "VALUES ('water', 2, 'l', '2026-01-01', '2026-01-01')")   # a second, dated one
            db.conn.commit()
            db.close()
            db = Database(path)                                          # re-open -> tidied up
            water = [i for i in db.list_pantry() if i.is_water]
            self.assertEqual(len(water), 1)
            self.assertIsNone(water[0].expiry)
            db.close()

    def test_same_name_items_stay_separate_and_soonest_is_used_first(self):
        from app.database import Database
        from app.models import Ingredient, PantryItem, Recipe
        from app.recipe_engine import plan_deduction
        with tempfile.TemporaryDirectory() as folder:
            db = Database(os.path.join(folder, "x.db"))
            db.add_pantry_item(PantryItem("Milk", 1, "l", expiry=TODAY + timedelta(days=7)))
            db.add_pantry_item(PantryItem("Milk", 1, "l", expiry=TODAY + timedelta(days=1)))
            milks = [i for i in db.list_pantry() if i.name == "Milk"]
            self.assertEqual(len(milks), 2)                             # two separate items
            tea = Recipe("Chai", "Indian", True, 5, 1, ingredients=[Ingredient("milk", 1, "l")])
            changes, _ = plan_deduction(tea, db.list_pantry(), 1, today=TODAY)
            soonest = min(milks, key=lambda i: i.expiry)
            self.assertEqual(changes, [(soonest.id, 0)])                # tomorrow's milk is used up
            db.close()


class Version47Test(unittest.TestCase):
    """Version 4.7: real food photos (with credits) and the user's own photo for any recipe."""

    def test_every_builtin_recipe_has_a_free_photo_with_credit(self):
        from app.images import CATALOG_PHOTOS_DIR, RECIPE_IMAGES_DIR, photo_credit
        from app.seed_recipes import SEED_RECIPES
        for i, recipe in enumerate(SEED_RECIPES):
            # 5.0: the first 21 photos are bundled in the APK, the 80 newer ones are catalogue photos.
            folder = RECIPE_IMAGES_DIR if i < 21 else CATALOG_PHOTOS_DIR
            self.assertTrue(os.path.exists(os.path.join(folder, f"{recipe.uid}.jpg")), recipe.uid)
            self.assertTrue(os.path.exists(os.path.join(folder, "thumbs", f"{recipe.uid}.jpg")), recipe.uid)
            credit = photo_credit(recipe.image_path)
            self.assertIsNotNone(credit, recipe.uid)                     # who took it...
            self.assertTrue(credit["author"] and len(credit["author"].splitlines()) == 1, recipe.uid)
            self.assertTrue(credit["licence"].lower().startswith(("cc0", "cc by", "public domain")),
                            (recipe.uid, credit["licence"]))             # ...and a free licence

    def test_own_photo_replaces_and_restores_the_picture(self):
        from app.database import Database
        with tempfile.TemporaryDirectory() as folder:
            db = Database(os.path.join(folder, "x.db"))
            recipe = db.list_recipes()[0]
            original = recipe.image_path
            photo = os.path.join(folder, "mine.jpg")
            open(photo, "wb").close()                                    # a (fake) photo file
            db.set_custom_image(recipe.id, photo)
            again = db.get_recipe(recipe.id)
            self.assertEqual(again.picture, photo)                       # the user's photo is shown...
            self.assertEqual(again.image_path, original)                 # ...the original is kept
            self.assertEqual(db.custom_images(), {recipe.uid: photo})
            db.log_cooked(recipe.id, 1)                                  # the Calendar shows it too
            self.assertEqual(db.cook_log()[0]["image_path"], photo)
            os.remove(photo)                                             # photo deleted from the phone:
            self.assertEqual(db.get_recipe(recipe.id).picture, original)  # fall back to the original
            db.set_custom_image(recipe.id, None)                         # "Use original"
            self.assertIsNone(db.get_recipe(recipe.id).custom_image)
            db.close()


class SchemaTest(unittest.TestCase):
    def test_recipe_round_trip(self):
        original = SEED_RECIPES[0]
        copy = recipe_from_dict(recipe_to_dict(original))
        self.assertEqual((copy.uid, copy.name, copy.protein_g, copy.image_path),
                         (original.uid, original.name, original.protein_g, original.image_path))
        self.assertEqual(len(copy.ingredients), len(original.ingredients))


class Version471Test(unittest.TestCase):
    """The input rules and display fixes from the 4.7.1 QA report."""

    def test_name_rules(self):
        from app.validation import NAME_MAX, clean_name_chars, name_error
        self.assertIsNone(name_error("Mum's Rajma (spicy) - v2.0, & more"))   # everyday marks are fine
        self.assertIsNone(name_error("पनीर भुर्जी"))                           # letters in any language
        self.assertIsNotNone(name_error("   "))                                 # empty
        self.assertIsNotNone(name_error("A" * (NAME_MAX + 1)))                  # 127 characters
        self.assertIsNone(name_error("A" * NAME_MAX))                           # exactly 126 is allowed
        self.assertIsNotNone(name_error("Curry 🍛"))                            # emoji
        self.assertIsNotNone(name_error("<script>"))                            # symbols
        self.assertEqual(clean_name_chars("Dal; <b>tadka</b> 🍛!"), "Dal btadkab ")

    def test_number_rules(self):
        from app.validation import parse_quantity, parse_whole
        self.assertEqual(parse_quantity("9999.99"), 9999.99)                   # the biggest quantity
        self.assertEqual(parse_quantity("", allow_zero=True), 0.0)              # optional box left empty
        for bad in ("", ".", "-5", "0", "10000", "1.234", "1e3", "abc", "nan", "inf"):
            with self.assertRaises(ValueError, msg=bad):
                parse_quantity(bad)
        self.assertEqual(parse_whole("14400", "minutes", 1, 14400), 14400)
        for bad in ("0", "14401", "-1", "9" * 25, "", "1.5"):
            with self.assertRaises(ValueError, msg=bad):
                parse_whole(bad, "minutes", 1, 14400)

    def test_short_minutes(self):
        from app.dates import short_minutes
        self.assertEqual([short_minutes(m) for m in (45, 60, 90, 1440, 1500, 14400)],
                         ["45 min", "1 h", "1 h 30", "1 d", "1 d 1 h", "10 d"])

    def test_tiny_quantities_are_zero(self):
        from app.units import pretty_quantity
        self.assertEqual(pretty_quantity(0.0004, "kg"), "0 kg")                 # below 0.001 -> 0
        self.assertEqual(pretty_quantity(0.004, "kg"), "0.004 kg")              # not hidden as "0"

    def test_longest_first_is_the_default_sort(self):
        from app.models import SORT_OPTIONS
        from app.recipe_engine import match_all, sort_matches
        self.assertEqual(SORT_OPTIONS[0], "Longest first")
        ordered = sort_matches(match_all(SEED_RECIPES, [], {"Stove"}), SORT_OPTIONS[0])
        minutes = [m.recipe.prep_minutes for m in ordered]
        self.assertEqual(minutes, sorted(minutes, reverse=True))               # most minutes first

    def test_photo_limits(self):
        from PIL import Image
        from app.ui.image_picker import MAX_BYTES, PhotoError, import_image
        with tempfile.TemporaryDirectory() as folder:
            small = os.path.join(folder, "ok.png")
            Image.new("RGB", (3000, 2000), "red").save(small)
            out = import_image(small, os.path.join(folder, "out"))
            with Image.open(out) as result:
                self.assertEqual(result.size, (1280, 853))                     # shrunk, shape kept
            self.assertLess(os.path.getsize(out), 5 * 1024 * 1024)            # stored copy under 5 MB
            big = os.path.join(folder, "big.jpg")
            with open(big, "wb") as f:
                f.write(b"\xff" * (MAX_BYTES + 10))                              # just over 10 MB
            with self.assertRaises(PhotoError):
                import_image(big, folder)
            junk = os.path.join(folder, "junk.jpg")
            with open(junk, "wb") as f:
                f.write(b"not a picture")
            with self.assertRaises(PhotoError):
                import_image(junk, folder)


class Version50Test(unittest.TestCase):
    """5.0: 101 recipes, the ingredient catalogue (unit / tag / shelf life) and the kg-pcs-L fridge."""

    def test_101_recipes_and_every_ingredient_is_in_the_catalogue(self):
        from app.ingredient_catalog import FRIDGE_UNITS, TAGS, info_for
        from app.units import ALWAYS_AVAILABLE, normalize_name
        self.assertGreaterEqual(len(SEED_RECIPES), 100)
        self.assertEqual(len({r.uid for r in SEED_RECIPES}), len(SEED_RECIPES))   # no duplicate ids
        for recipe in SEED_RECIPES:
            for ing in recipe.ingredients:
                if normalize_name(ing.name) in ALWAYS_AVAILABLE:
                    continue
                info = info_for(ing.name)
                self.assertIsNotNone(info, f"{recipe.name}: {ing.name}")
                self.assertIn(info.unit, FRIDGE_UNITS)
                self.assertIn(info.tag, TAGS)

    def test_unknown_names_get_sensible_defaults(self):
        from app.ingredient_catalog import guess_info
        self.assertEqual(guess_info("Turkey breast").tag, "Meat")           # meat words -> Meat
        self.assertEqual(guess_info("Mystery sauce").unit, "pcs")            # anything else
        self.assertEqual(guess_info("Milk").unit, "L")

    def test_old_fridge_items_move_to_kg_pcs_l_and_get_a_tag(self):
        import sqlite3
        from app.database import Database
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "old.db")
            db = Database(path)
            db.close()
            raw = sqlite3.connect(path)                                     # pretend an old version wrote these
            raw.execute("INSERT INTO pantry_items(name, category, quantity, unit, added_on) "
                        "VALUES ('Paneer', 'Fridge', 500, 'g', '2026-10-01'), "
                        "('Milk', 'Fridge', 1, 'l', '2026-10-01'), ('Mint', 'Fridge', 2, 'bunch', '2026-10-01')")
            raw.execute("UPDATE pantry_items SET tag=NULL")
            raw.commit()
            raw.close()
            db = Database(path)                                             # opening upgrades the file
            items = {i.name: i for i in db.list_pantry()}
            self.assertEqual((items["Paneer"].quantity, items["Paneer"].unit), (0.5, "kg"))
            self.assertEqual((items["Milk"].quantity, items["Milk"].unit), (1, "L"))
            self.assertEqual(items["Mint"].unit, "pcs")
            self.assertEqual(items["Paneer"].tag, "Fresh produce")
            self.assertEqual(items["Water"].unit, "L")
            db.close()
            db = Database(path)                                             # a second start changes nothing
            self.assertEqual({i.name: i.quantity for i in db.list_pantry()}["Paneer"], 0.5)
            db.close()


class CatalogTest(unittest.TestCase):
    """4.7.1: the published recipe catalogue (replaces the retired Cloud Run server)."""

    def test_export_round_trip_and_version(self):
        from app.catalog import fingerprint
        dicts = [recipe_to_dict(r) for r in SEED_RECIPES]
        self.assertEqual(fingerprint(dicts), fingerprint(list(dicts)))     # same recipes -> same version
        changed = [dict(dicts[0], name="Something else")] + dicts[1:]
        self.assertNotEqual(fingerprint(dicts), fingerprint(changed))      # any change -> new version
        back = [recipe_from_dict(d) for d in dicts]
        self.assertEqual([r.uid for r in back], [r.uid for r in SEED_RECIPES])

    def test_apply_saves_recipes_once_a_day(self):
        from app import catalog
        from app.database import Database
        from app.models import Ingredient, Recipe
        new = Recipe(name="Brand New Dish", cuisine="Indian", is_veg=True, prep_minutes=5, servings=1,
                     ingredients=[Ingredient("Rice", 100, "g")], steps=["Cook"])
        with tempfile.TemporaryDirectory() as folder:
            db = Database(os.path.join(folder, "x.db"))
            before = len(db.list_catalog_recipes())
            catalog.apply_catalog(db, ("v2", [new]))                     # a download with one new recipe
            self.assertEqual(len(db.list_catalog_recipes()), before + 1)
            self.assertEqual(db.get_setting(catalog.VERSION), "v2")
            self.assertFalse(catalog.sync_if_due(db, lambda *a: None))   # checked today -> no new check
            db.close()

    def test_unsafe_picture_names_are_ignored(self):
        from unittest import mock
        from app import catalog
        bad = dict(recipe_to_dict(SEED_RECIPES[0]), image="../../secret.jpg")
        good = recipe_to_dict(SEED_RECIPES[1])
        body = json.dumps({"version": "x", "recipes": [bad, good, {"broken": True}]}).encode()
        with mock.patch.object(catalog, "_download", return_value=body):   # no real network
            version, recipes = catalog.fetch_catalog()
        self.assertEqual(version, "x")
        self.assertEqual(len(recipes), 2)                                # the broken entry is skipped
        self.assertIsNone(recipes[0].image_path)                         # "../../secret.jpg" dropped
        self.assertEqual(recipes[1].image_path, SEED_RECIPES[1].image_path)


if __name__ == "__main__":
    unittest.main()
