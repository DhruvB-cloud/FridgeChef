"""
test_features.py
----------------
WHY THIS FILE EXISTS:
    Automated checks for the second set of features:
      * streaks / favourite dish (app/stats.py)
      * ingredient suggestions (app/ingredient_catalog.py)
      * the web API (server/app.py) - including a full round trip through the JSON format the
        phone uses (app/api_schema.py). Skipped automatically if Flask isn't installed.
    Run from the FridgeChef folder:   python -m unittest discover tests -v
"""

import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api_schema import match_from_dict, pantry_to_dict, recipe_from_dict, recipe_to_dict
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
        self.assertEqual(info_for("onion"), ("pcs", "Outside"))
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


class SchemaTest(unittest.TestCase):
    def test_recipe_round_trip(self):
        original = SEED_RECIPES[0]
        copy = recipe_from_dict(recipe_to_dict(original))
        self.assertEqual((copy.uid, copy.name, copy.protein_g, copy.image_path),
                         (original.uid, original.name, original.protein_g, original.image_path))
        self.assertEqual(len(copy.ingredients), len(original.ingredients))


try:
    import flask  # noqa: F401
    HAVE_FLASK = True
except ImportError:
    HAVE_FLASK = False


@unittest.skipUnless(HAVE_FLASK, "Flask not installed")
class ApiTest(unittest.TestCase):
    def setUp(self):
        from server.app import create_app
        self.folder = tempfile.TemporaryDirectory()
        self.app = create_app(os.path.join(self.folder.name, "catalog.db"))
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.extensions["fridgechef_db"].close()      # Windows can't delete an open file
        self.folder.cleanup()

    def test_health_and_catalogue(self):
        self.assertEqual(self.client.get("/api/health").get_json()["status"], "ok")
        veg = self.client.get("/api/recipes?diet=Veg").get_json()
        self.assertTrue(veg["count"] > 0 and all(r["is_veg"] for r in veg["recipes"]))
        self.assertEqual(self.client.get("/api/recipes/dal-tadka").get_json()["name"], "Dal Tadka")
        self.assertEqual(self.client.get("/api/recipes/nope").status_code, 404)

    def test_search_uses_fridge_expiry_and_sort(self):
        pantry = [PantryItem("Curd", 300, "g", expiry=TODAY), PantryItem("Cucumber", 1, "pcs")]
        body = {"pantry": [pantry_to_dict(p) for p in pantry], "appliances": ["Stove"], "servings": 1,
                "filters": {"sort": "Most protein"}, "today": TODAY.isoformat(),
                "now": "2026-10-04T13:00"}
        answer = self.client.post("/api/recipes/search", json=body).get_json()
        self.assertEqual(answer["meal"], "Lunch")        # from the phone's clock, not the server's
        top = match_from_dict(answer["recommended"][0])
        self.assertEqual(top.recipe.name, "Cucumber Raita")   # uses the curd expiring today
        self.assertEqual(top.uses_expiring_today, ["Curd"])
        proteins = [r["recipe"]["protein_g"] for r in answer["results"]]
        self.assertEqual(proteins, sorted(proteins, reverse=True))   # "Most protein" order

    def test_cloud_entry_point(self):
        """server/wsgi.py (used by gunicorn in the cloud) must build a working app."""
        import importlib
        wsgi = importlib.import_module("server.wsgi")
        response = wsgi.application.test_client().get("/api/health")
        self.assertEqual(response.get_json()["status"], "ok")
        wsgi.application.extensions["fridgechef_db"].close()

    def test_bad_request(self):
        self.assertEqual(self.client.post("/api/recipes/search", data="oops").status_code, 400)

    def test_images_served(self):
        response = self.client.get("/images/dal-tadka.jpg")
        self.assertEqual(response.status_code, 200)
        response.close()


if __name__ == "__main__":
    unittest.main()
