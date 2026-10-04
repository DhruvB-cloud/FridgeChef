"""
test_engine.py
--------------
WHY THIS FILE EXISTS:
    Automated checks for the app's logic (no UI needed, so they run in a second).
    Run from the FridgeChef folder with:   python -m unittest discover tests
    If you change recipe_engine.py / units.py / meal_time.py, run these to make sure nothing broke.
"""

import os
import sys
import tempfile                                   # temporary folders that clean themselves up
import unittest                                   # Python's built-in test framework
from datetime import date, datetime, timedelta

# Make "import app..." work when running this file from the tests folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Database
from app.images import resolve_image
from app.expiry import build_message, expiring_today
from app.meal_time import current_meal
from app.models import Ingredient, PantryItem, Recipe
from app.recipe_engine import (build_pantry_index, filter_matches, match_all, match_recipe,
                               plan_deduction, recommend)
from app.units import normalize_name, to_base

TODAY = date(2026, 10, 4)                          # fixed "today" so tests never depend on the clock


def raita():
    """A tiny test recipe: needs 250 g yogurt + 1 cucumber, optional coriander, no appliance."""
    return Recipe(name="Raita", cuisine="Indian", is_veg=True, prep_minutes=5, servings=2,
                  meal_types=["Lunch"], appliances=[],
                  ingredients=[Ingredient("yogurt", 250, "g"), Ingredient("cucumber", 1, "pcs"),
                               Ingredient("coriander", 0.1, "bunch", optional=True),
                               Ingredient("salt", 1, "tsp")])


class UnitsTest(unittest.TestCase):
    def test_aliases_and_plurals(self):
        self.assertEqual(normalize_name("Curd"), "yogurt")          # alias
        self.assertEqual(normalize_name(" Tomatoes "), "tomato")    # plural + spaces
        self.assertEqual(normalize_name("Onions"), "onion")
        self.assertEqual(normalize_name("chickpeas"), "chickpeas")  # canonical name kept

    def test_conversion(self):
        self.assertEqual(to_base(1.5, "kg"), (1500.0, "mass"))
        self.assertEqual(to_base(2, "tbsp"), (30.0, "volume"))


class MatchTest(unittest.TestCase):
    def test_cookable_with_curd_alias_and_kg(self):
        pantry = [PantryItem("Curd", 0.5, "kg", expiry=TODAY + timedelta(days=5), id=1),
                  PantryItem("Cucumbers", 2, "pcs", id=2)]
        m = match_recipe(raita(), build_pantry_index(pantry, TODAY), set(), today=TODAY)
        self.assertTrue(m.can_cook)                 # 500 g curd >= 250 g yogurt
        self.assertEqual(len(m.missing_optional), 1)  # coriander is optional

    def test_missing_and_scaling(self):
        pantry = [PantryItem("Curd", 300, "g", id=1), PantryItem("cucumber", 1, "pcs", id=2)]
        m = match_recipe(raita(), build_pantry_index(pantry, TODAY), set(), servings=4, today=TODAY)
        self.assertFalse(m.can_cook)               # 4 servings needs 500 g yogurt + 2 cucumbers
        self.assertEqual({i.name for i in m.missing}, {"yogurt", "cucumber"})

    def test_expired_items_are_ignored(self):
        pantry = [PantryItem("Curd", 1, "kg", expiry=TODAY - timedelta(days=1), id=1),
                  PantryItem("cucumber", 1, "pcs", id=2)]
        m = match_recipe(raita(), build_pantry_index(pantry, TODAY), set(), today=TODAY)
        self.assertEqual([i.name for i in m.missing], ["yogurt"])

    def test_appliance_required(self):
        r = raita()
        r.appliances = ["Oven"]
        pantry = [PantryItem("Curd", 1, "kg", id=1), PantryItem("cucumber", 1, "pcs", id=2)]
        index = build_pantry_index(pantry, TODAY)
        self.assertFalse(match_recipe(r, index, {"Stove"}, today=TODAY).can_cook)
        self.assertTrue(match_recipe(r, index, {"Oven"}, today=TODAY).can_cook)

    def test_expiring_today_goes_first_in_recommendations(self):
        other = raita()
        other.name, other.ingredients = "Cucumber Snack", [Ingredient("cucumber", 1, "pcs")]
        pantry = [PantryItem("Curd", 1, "kg", expiry=TODAY, id=1), PantryItem("cucumber", 3, "pcs", id=2)]
        matches = match_all([other, raita()], pantry, set(), today=TODAY)
        recs = recommend(matches, "Lunch")
        self.assertEqual(recs[0].recipe.name, "Raita")          # uses curd that expires today
        self.assertEqual(recs[0].uses_expiring_today, ["Curd"])

    def test_unrealistic_dish_not_boosted_by_expiring_item(self):
        big = raita()
        big.name = "Big Feast"
        big.ingredients = big.ingredients + [Ingredient("chicken", 1, "kg"), Ingredient("lemon", 2, "pcs")]
        pantry = [PantryItem("Curd", 1, "kg", expiry=TODAY, id=1), PantryItem("cucumber", 3, "pcs", id=2)]
        ranked = filter_matches(match_all([big, raita()], pantry, set(), today=TODAY))
        self.assertEqual(ranked[0].recipe.name, "Raita")          # missing 2 things -> no boost

    def test_sort_by_protein_and_carbs(self):
        lean, heavy = raita(), raita()
        lean.name, lean.protein_g, lean.carbs_g = "Lean", 30, 5
        heavy.name, heavy.protein_g, heavy.carbs_g = "Heavy", 8, 60
        matches = match_all([heavy, lean], [], set(), today=TODAY)
        self.assertEqual(filter_matches(matches, sort="Most protein")[0].recipe.name, "Lean")
        self.assertEqual(filter_matches(matches, sort="Least carbs")[0].recipe.name, "Lean")
        self.assertEqual(filter_matches(matches, sort="Most carbs")[0].recipe.name, "Heavy")

    def test_default_is_one_person(self):
        # Raita serves 2 with 250 g yogurt; for ONE person 125 g is enough.
        pantry = [PantryItem("Curd", 130, "g", id=1), PantryItem("cucumber", 1, "pcs", id=2)]
        self.assertTrue(match_all([raita()], pantry, set(), today=TODAY)[0].can_cook)
        self.assertFalse(match_all([raita()], pantry, set(), today=TODAY, servings=2)[0].can_cook)

    def test_filters(self):
        matches = match_all([raita()], [], set(), today=TODAY)
        self.assertEqual(len(filter_matches(matches, diet="Non-Veg")), 0)
        self.assertEqual(len(filter_matches(matches, diet="Veg", max_minutes=10)), 1)
        self.assertEqual(len(filter_matches(matches, cuisine="Arabic")), 0)
        self.assertEqual(len(filter_matches(matches, only_cookable=True)), 0)


class DeductionTest(unittest.TestCase):
    def test_first_expiring_used_first_and_units_converted(self):
        pantry = [PantryItem("Curd", 200, "g", expiry=TODAY + timedelta(days=1), id=1),
                  PantryItem("Curd", 1, "kg", expiry=TODAY + timedelta(days=9), id=2),
                  PantryItem("cucumber", 1, "pcs", id=3)]
        changes, warnings = plan_deduction(raita(), pantry, servings=2, today=TODAY)
        result = dict(changes)
        self.assertEqual(result[1], 0)                          # the 200 g tub is used up first
        self.assertAlmostEqual(result[2], 0.95)                 # then 50 g from the 1 kg tub
        self.assertEqual(result[3], 0)                          # cucumber used up
        self.assertEqual(warnings, [])


class MealTimeTest(unittest.TestCase):
    def test_slots(self):
        at = lambda h, m=0: current_meal(datetime(2026, 10, 4, h, m))
        self.assertEqual(at(7), "Breakfast")
        self.assertEqual(at(10, 30), "Brunch")
        self.assertEqual(at(12, 40), "Lunch")
        self.assertEqual(at(13, 50), "Snacks")      # lunch was > 45 minutes ago -> next meal
        self.assertEqual(at(19), "Dinner")
        self.assertEqual(at(23, 30), "Breakfast")   # wraps around midnight


class DatabaseTest(unittest.TestCase):
    def test_roundtrip_and_cooking(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(os.path.join(folder, "test.db"))
            self.assertGreater(len(db.list_recipes()), 15)      # seed recipes inserted
            item_id = db.add_pantry_item(PantryItem("Curd", 500, "g", expiry=TODAY))
            self.assertEqual(expiring_today(db.list_pantry(), TODAY)[0].name, "Curd")
            self.assertIn("Curd expires today", build_message(expiring_today(db.list_pantry(), TODAY)))
            db.apply_deductions([(item_id, 0)])                 # cooking used it all
            self.assertEqual(db.list_pantry(), [])              # -> removed from the fridge
            r = raita()
            r.is_user = True
            rid = db.add_recipe(r)
            self.assertEqual(db.get_recipe(rid).ingredients[0].name, "yogurt")
            self.assertIn(rid, [x.id for x in db.list_my_recipes()])
            self.assertTrue(db.get_recipe(rid).uid.startswith("user-"))
            # Every built-in recipe has a uid, a bundled picture and nutrition numbers.
            for recipe in db.list_catalog_recipes():
                self.assertTrue(recipe.uid and recipe.image_path.startswith("asset:"))
                self.assertIsNotNone(resolve_image(recipe.image_path), recipe.uid)
                self.assertGreater(recipe.protein_g, 0)
            # Cooking history feeds the calendar.
            db.log_cooked(rid, 1, when=datetime(2026, 10, 3, 19, 0))
            self.assertEqual(db.cook_log(date(2026, 10, 3), date(2026, 10, 3))[0]["recipe_name"], "Raita")
            self.assertEqual(db.cooked_days(), {date(2026, 10, 3)})
            db.close()

    def test_upgrade_from_version_1_database(self):
        """A database created by the first app version must upgrade without losing data."""
        import sqlite3
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "old.db")
            conn = sqlite3.connect(path)
            conn.executescript("""
                CREATE TABLE recipes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                  cuisine TEXT NOT NULL, is_veg INTEGER NOT NULL, prep_minutes INTEGER NOT NULL,
                  servings INTEGER NOT NULL, steps TEXT NOT NULL, meal_types TEXT NOT NULL,
                  nutrition_tags TEXT NOT NULL, appliances TEXT NOT NULL, image_path TEXT,
                  is_user INTEGER NOT NULL DEFAULT 0, is_saved INTEGER NOT NULL DEFAULT 0,
                  created_on TEXT NOT NULL);
                CREATE TABLE cook_log (id INTEGER PRIMARY KEY AUTOINCREMENT, recipe_id INTEGER NOT NULL,
                  servings INTEGER NOT NULL, cooked_on TEXT NOT NULL);
                INSERT INTO recipes VALUES (1, 'Dal Tadka', 'Indian', 1, 35, 3, '[]', '[]', '[]', '[]',
                  NULL, 0, 1, '2026-01-01');
                INSERT INTO cook_log VALUES (1, 1, 2, '2026-10-01T20:00:00');
            """)
            conn.commit()
            conn.close()
            db = Database(path)
            dal = db.get_recipe(1)
            self.assertEqual(dal.uid, "dal-tadka")              # adopted, not duplicated
            self.assertTrue(dal.is_saved)                       # user's Saved flag kept
            self.assertEqual(dal.image_path, "asset:dal-tadka.jpg")
            self.assertEqual(len([r for r in db.list_recipes() if r.name == "Dal Tadka"]), 1)
            self.assertEqual(db.cook_log()[0]["recipe_name"], "Dal Tadka")
            db.close()


if __name__ == "__main__":
    unittest.main()
