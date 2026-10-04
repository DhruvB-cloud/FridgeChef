"""
database.py
-----------
WHY THIS FILE EXISTS:
    Everything the user enters (fridge items, appliances, their own recipes, saved dishes,
    cooking history) must survive app restarts AND work with no internet. SQLite is a database
    that lives in a single file on the phone/PC and ships with Python - perfect for offline use.

    This class is the ONLY place in the app that writes SQL. The UI calls simple methods like
    db.add_pantry_item(item) and gets back the dataclasses from models.py.
    The web server (server/app.py) reuses this same class for its own recipe catalogue.

TABLES:
    pantry_items        - what is in the fridge / kitchen cupboard
    appliances          - which cooking machines the user owns
    recipes             - built-in + server + user recipes (list fields stored as JSON text)
    recipe_ingredients  - the ingredient lines belonging to each recipe
    cook_log            - history of what was cooked and when (Calendar + streak + favourite dish)
    settings            - tiny key/value store (user name, default servings, server address...)

UPGRADES:
    Version 1 of the app created tables without some columns. _migrate() adds missing columns
    to an existing database file, so updating the app never loses the user's data.
"""

import json                                   # converts Python lists <-> text for storing in SQLite
import os                                     # used to create the folder that holds the database
import sqlite3                                # the built-in SQLite driver
import uuid                                   # random ids for user-created recipes
from datetime import date, datetime           # for expiry dates and timestamps

from app.models import APPLIANCES, Ingredient, PantryItem, Recipe   # our data shapes
from app.seed_recipes import SEED_RECIPES                            # the starter recipe library

# SQL that creates every table if it does not exist yet. Running it on every start is safe.
SCHEMA = """
CREATE TABLE IF NOT EXISTS pantry_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,   -- unique id, generated automatically
    name        TEXT    NOT NULL,                    -- e.g. 'Curd'
    category    TEXT    NOT NULL DEFAULT 'Fridge',   -- 'Fridge' or 'Outside'
    quantity    REAL    NOT NULL,                    -- how much is left
    unit        TEXT    NOT NULL,                    -- g / kg / ml / l / pcs ...
    expiry      TEXT,                                -- ISO date 'YYYY-MM-DD' or NULL
    added_on    TEXT    NOT NULL                     -- when the user added it
);
CREATE TABLE IF NOT EXISTS appliances (
    name        TEXT PRIMARY KEY,                    -- 'Stove', 'Oven' ...
    owned       INTEGER NOT NULL DEFAULT 0           -- 1 = user owns it, 0 = does not
);
CREATE TABLE IF NOT EXISTS recipes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    cuisine         TEXT    NOT NULL,
    is_veg          INTEGER NOT NULL,                -- SQLite has no boolean: 1 = True, 0 = False
    prep_minutes    INTEGER NOT NULL,
    servings        INTEGER NOT NULL,
    steps           TEXT    NOT NULL,                -- JSON list of strings
    meal_types      TEXT    NOT NULL,                -- JSON list of strings
    nutrition_tags  TEXT    NOT NULL,                -- JSON list of strings
    appliances      TEXT    NOT NULL,                -- JSON list of strings
    image_path      TEXT,                            -- 'asset:<file>' or a full photo path
    is_user         INTEGER NOT NULL DEFAULT 0,      -- 1 = created by the user
    is_saved        INTEGER NOT NULL DEFAULT 0,      -- 1 = in "Saved dishes"
    created_on      TEXT    NOT NULL,
    uid             TEXT,                            -- stable id shared with the server
    protein_g       REAL    NOT NULL DEFAULT 0,      -- per serving
    carbs_g         REAL    NOT NULL DEFAULT 0,      -- per serving
    calories        REAL    NOT NULL DEFAULT 0       -- per serving
);
CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id   INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,  -- deleted with recipe
    name        TEXT    NOT NULL,
    quantity    REAL    NOT NULL,
    unit        TEXT    NOT NULL,
    optional    INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS cook_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id   INTEGER NOT NULL,
    servings    INTEGER NOT NULL,
    cooked_on   TEXT    NOT NULL,                    -- ISO date-time, e.g. 2026-10-04T19:30:00
    recipe_name TEXT,                                -- kept even if the recipe is deleted later
    photo_path  TEXT                                 -- the user's own photo of the cooked dish
);
CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT
);
"""

# Columns added after version 1: table -> [(column, SQL type + default)].
MIGRATIONS = {
    "recipes": [("uid", "TEXT"), ("protein_g", "REAL NOT NULL DEFAULT 0"),
                ("carbs_g", "REAL NOT NULL DEFAULT 0"), ("calories", "REAL NOT NULL DEFAULT 0")],
    "cook_log": [("recipe_name", "TEXT"), ("photo_path", "TEXT")],   # photo_path: version 4
}


class Database:
    """Thin wrapper around one SQLite connection with app-specific helper methods."""

    def __init__(self, path, check_same_thread=True):
        # Make sure the folder for the database file exists (first launch on a new device).
        folder = os.path.dirname(path)                     # e.g. '.../fridgechef' from '.../x.db'
        if folder:                                         # "" means current folder - nothing to create
            os.makedirs(folder, exist_ok=True)             # exist_ok: no error if it already exists
        self.path = path                                   # remember where the file is (for debugging)
        # check_same_thread=False is only used by the web server, which guards access with a lock.
        self.conn = sqlite3.connect(path, check_same_thread=check_same_thread)
        self.conn.row_factory = sqlite3.Row                # rows behave like dicts: row["name"]
        self.conn.execute("PRAGMA foreign_keys = ON")      # enforce ON DELETE CASCADE above
        self.conn.executescript(SCHEMA)                    # create any missing tables
        self._migrate()                                    # add columns missing in old files
        self._seed()                                       # insert / update built-in data

    # ------------------------------------------------------------------ setup helpers
    def _migrate(self):
        """Add columns that older versions of the database file don't have yet."""
        for table, columns in MIGRATIONS.items():
            # PRAGMA table_info lists the existing columns of a table.
            existing = {row["name"] for row in self.conn.execute(f"PRAGMA table_info({table})")}
            for column, sql_type in columns:
                if column not in existing:
                    self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
        # Version 3 renamed the "Grocery" category to "Outside" (= not in the fridge).
        self.conn.execute("UPDATE pantry_items SET category='Outside' WHERE category='Grocery'")
        # Old cook_log rows have no recipe_name: copy it from the recipes table.
        self.conn.execute("UPDATE cook_log SET recipe_name = (SELECT name FROM recipes "
                          "WHERE recipes.id = cook_log.recipe_id) WHERE recipe_name IS NULL")
        # Old user recipes have no uid: give each a random one.
        for row in self.conn.execute("SELECT id FROM recipes WHERE uid IS NULL AND is_user=1").fetchall():
            self.conn.execute("UPDATE recipes SET uid=? WHERE id=?", (f"user-{uuid.uuid4().hex[:12]}", row["id"]))
        self.conn.commit()

    def _seed(self):
        """Make sure the appliance list and every built-in recipe exist and are up to date."""
        for name in APPLIANCES:                            # make sure every appliance row exists
            # INSERT OR IGNORE does nothing if the row is already there, so user choices survive.
            self.conn.execute("INSERT OR IGNORE INTO appliances(name, owned) VALUES (?, ?)",
                              (name, 1 if name == "Stove" else 0))  # assume most kitchens have a stove
        for recipe in SEED_RECIPES:
            row = self.conn.execute("SELECT id FROM recipes WHERE uid=?", (recipe.uid,)).fetchone()
            if row is None:
                # A database from version 1 has the recipe but without a uid - adopt it by name.
                row = self.conn.execute("SELECT id FROM recipes WHERE name=? AND is_user=0 AND uid IS NULL",
                                        (recipe.name,)).fetchone()
            if row is None:
                self.add_recipe(recipe, commit=False)      # brand-new database: insert
            else:                                          # existing row: fill in the new fields
                self.conn.execute(
                    "UPDATE recipes SET uid=?, protein_g=?, carbs_g=?, calories=?, "
                    "image_path=COALESCE(image_path, ?) WHERE id=?",   # keep an image if one exists
                    (recipe.uid, recipe.protein_g, recipe.carbs_g, recipe.calories,
                     recipe.image_path, row["id"]))
        self.conn.commit()                                 # save everything in one go (faster)

    def close(self):
        """Close the connection when the app exits."""
        self.conn.close()

    # ------------------------------------------------------------------ pantry
    @staticmethod
    def _row_to_item(row):
        """Convert one pantry_items row into a PantryItem object."""
        return PantryItem(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            quantity=row["quantity"],
            unit=row["unit"],
            # Stored as text 'YYYY-MM-DD'; turn it back into a date object (or keep None).
            expiry=date.fromisoformat(row["expiry"]) if row["expiry"] else None,
        )

    def list_pantry(self):
        """All pantry items, soonest-expiring first (items without expiry go last)."""
        rows = self.conn.execute(
            # "expiry IS NULL" is 0 for dated items and 1 for undated ones, so dated items sort first.
            "SELECT * FROM pantry_items ORDER BY expiry IS NULL, expiry, name COLLATE NOCASE"
        ).fetchall()
        return [self._row_to_item(r) for r in rows]        # list comprehension: convert every row

    def add_pantry_item(self, item):
        """Insert a new pantry item and return its new id."""
        cur = self.conn.execute(
            "INSERT INTO pantry_items(name, category, quantity, unit, expiry, added_on) "
            "VALUES (?, ?, ?, ?, ?, ?)",                   # '?' placeholders prevent SQL injection
            (item.name.strip(), item.category, float(item.quantity), item.unit,
             item.expiry.isoformat() if item.expiry else None, datetime.now().isoformat()),
        )
        self.conn.commit()                                 # write to disk immediately
        item.id = cur.lastrowid                            # the id SQLite just generated
        return item.id

    def update_pantry_item(self, item):
        """Overwrite an existing pantry item (used by the Edit popup)."""
        self.conn.execute(
            "UPDATE pantry_items SET name=?, category=?, quantity=?, unit=?, expiry=? WHERE id=?",
            (item.name.strip(), item.category, float(item.quantity), item.unit,
             item.expiry.isoformat() if item.expiry else None, item.id),
        )
        self.conn.commit()

    def delete_pantry_item(self, item_id):
        """Remove a pantry item completely."""
        self.conn.execute("DELETE FROM pantry_items WHERE id=?", (item_id,))  # note the tuple comma
        self.conn.commit()

    def apply_deductions(self, changes):
        """Save the result of cooking.

        `changes` is a list of (item_id, new_quantity). Items that hit zero are deleted,
        because an empty pack should disappear from "Items in Fridge".
        """
        for item_id, new_quantity in changes:
            if new_quantity <= 1e-9:                       # tiny tolerance for floating-point maths
                self.conn.execute("DELETE FROM pantry_items WHERE id=?", (item_id,))
            else:
                self.conn.execute("UPDATE pantry_items SET quantity=? WHERE id=?",
                                  (round(new_quantity, 3), item_id))
        self.conn.commit()                                 # all changes saved together

    def ingredient_names(self):
        """Every ingredient name the user has used (pantry + recipes) - for the type-ahead list."""
        rows = self.conn.execute("SELECT name FROM pantry_items UNION SELECT name FROM recipe_ingredients")
        return [r["name"] for r in rows]

    # ------------------------------------------------------------------ appliances
    def get_appliances(self):
        """Dict like {'Stove': True, 'Oven': False, ...} in the order of models.APPLIANCES."""
        rows = self.conn.execute("SELECT name, owned FROM appliances").fetchall()
        owned = {r["name"]: bool(r["owned"]) for r in rows}           # dict comprehension
        return {name: owned.get(name, False) for name in APPLIANCES}  # keep a stable order

    def owned_appliances(self):
        """Just the names of appliances the user owns, as a set (fast 'in' checks)."""
        return {name for name, owned in self.get_appliances().items() if owned}

    def set_appliance(self, name, owned):
        """Tick / untick an appliance."""
        self.conn.execute("INSERT OR REPLACE INTO appliances(name, owned) VALUES (?, ?)",
                          (name, 1 if owned else 0))
        self.conn.commit()

    # ------------------------------------------------------------------ recipes
    def _row_to_recipe(self, row):
        """Build a Recipe object from a recipes row + its ingredient rows."""
        ingredient_rows = self.conn.execute(
            "SELECT * FROM recipe_ingredients WHERE recipe_id=? ORDER BY id", (row["id"],)
        ).fetchall()
        return Recipe(
            id=row["id"],
            uid=row["uid"],
            name=row["name"],
            cuisine=row["cuisine"],
            is_veg=bool(row["is_veg"]),
            prep_minutes=row["prep_minutes"],
            servings=row["servings"],
            protein_g=row["protein_g"],
            carbs_g=row["carbs_g"],
            calories=row["calories"],
            steps=json.loads(row["steps"]),                # JSON text -> Python list
            meal_types=json.loads(row["meal_types"]),
            nutrition_tags=json.loads(row["nutrition_tags"]),
            appliances=json.loads(row["appliances"]),
            image_path=row["image_path"],
            is_user=bool(row["is_user"]),
            is_saved=bool(row["is_saved"]),
            ingredients=[Ingredient(name=r["name"], quantity=r["quantity"], unit=r["unit"],
                                    optional=bool(r["optional"])) for r in ingredient_rows],
        )

    def _select_recipes(self, where="1=1", params=()):
        """Shared helper: recipes matching a WHERE clause, sorted by name."""
        rows = self.conn.execute(f"SELECT * FROM recipes WHERE {where} ORDER BY name COLLATE NOCASE",
                                 params).fetchall()
        return [self._row_to_recipe(r) for r in rows]

    def list_recipes(self):
        """Every recipe in the database."""
        return self._select_recipes()

    def list_catalog_recipes(self):
        """Built-in / server recipes (not created by the user)."""
        return self._select_recipes("is_user=0")

    def list_user_recipes(self):
        """Recipes the user created on this device."""
        return self._select_recipes("is_user=1")

    def list_my_recipes(self):
        """Recipes the user created OR saved - shown on the 'Cookbook' tab."""
        return self._select_recipes("is_user=1 OR is_saved=1")

    def get_recipe(self, recipe_id):
        """One recipe by local id, or None if it was deleted."""
        row = self.conn.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()
        return self._row_to_recipe(row) if row else None

    def get_recipe_by_uid(self, uid):
        """One recipe by its stable uid, or None."""
        row = self.conn.execute("SELECT * FROM recipes WHERE uid=?", (uid,)).fetchone()
        return self._row_to_recipe(row) if row else None

    def _insert_ingredients(self, recipe):
        for ing in recipe.ingredients:                     # one row per ingredient line
            self.conn.execute(
                "INSERT INTO recipe_ingredients(recipe_id, name, quantity, unit, optional) "
                "VALUES (?, ?, ?, ?, ?)",
                (recipe.id, ing.name.strip(), float(ing.quantity), ing.unit, int(ing.optional)),
            )

    def add_recipe(self, recipe, commit=True):
        """Insert a recipe and its ingredients. Returns the new local recipe id."""
        if not recipe.uid:                                 # user recipes get a random stable id
            recipe.uid = f"user-{uuid.uuid4().hex[:12]}"
        cur = self.conn.execute(
            "INSERT INTO recipes(name, cuisine, is_veg, prep_minutes, servings, steps, meal_types, "
            "nutrition_tags, appliances, image_path, is_user, is_saved, created_on, uid, "
            "protein_g, carbs_g, calories) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (recipe.name.strip(), recipe.cuisine, int(recipe.is_veg), int(recipe.prep_minutes),
             int(recipe.servings), json.dumps(recipe.steps), json.dumps(recipe.meal_types),
             json.dumps(recipe.nutrition_tags), json.dumps(recipe.appliances), recipe.image_path,
             int(recipe.is_user), int(recipe.is_saved), datetime.now().isoformat(), recipe.uid,
             float(recipe.protein_g), float(recipe.carbs_g), float(recipe.calories)),
        )
        recipe.id = cur.lastrowid                          # remember the generated id on the object
        self._insert_ingredients(recipe)
        if commit:                                         # seeding passes commit=False for speed
            self.conn.commit()
        return recipe.id

    def upsert_catalog_recipe(self, recipe, commit=True):
        """Store a recipe received from the server: update it if we know its uid, else insert.

        Keeps the user's "Saved" flag. Returns the LOCAL id (which the UI uses to open the recipe).
        This is how the phone keeps an up-to-date offline copy of the server's catalogue.
        """
        row = self.conn.execute("SELECT id, image_path FROM recipes WHERE uid=?", (recipe.uid,)).fetchone()
        if row is None:
            recipe.is_user = False
            return self.add_recipe(recipe, commit=commit)
        recipe.id = row["id"]
        self.conn.execute(
            "UPDATE recipes SET name=?, cuisine=?, is_veg=?, prep_minutes=?, servings=?, steps=?, "
            "meal_types=?, nutrition_tags=?, appliances=?, image_path=?, protein_g=?, carbs_g=?, "
            "calories=? WHERE id=?",
            (recipe.name, recipe.cuisine, int(recipe.is_veg), int(recipe.prep_minutes),
             int(recipe.servings), json.dumps(recipe.steps), json.dumps(recipe.meal_types),
             json.dumps(recipe.nutrition_tags), json.dumps(recipe.appliances),
             recipe.image_path or row["image_path"], float(recipe.protein_g),
             float(recipe.carbs_g), float(recipe.calories), recipe.id))
        self.conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id=?", (recipe.id,))
        self._insert_ingredients(recipe)                   # replace the ingredient list
        if commit:
            self.conn.commit()
        return recipe.id

    def commit(self):
        """Save pending changes (used after many upserts with commit=False)."""
        self.conn.commit()

    def saved_flags(self):
        """{uid: is_saved} for every recipe - lets server results show the local Saved state."""
        return {r["uid"]: bool(r["is_saved"]) for r in self.conn.execute("SELECT uid, is_saved FROM recipes")}

    def set_saved(self, recipe_id, saved):
        """Add to / remove from 'Saved dishes'."""
        self.conn.execute("UPDATE recipes SET is_saved=? WHERE id=?", (int(saved), recipe_id))
        self.conn.commit()

    def delete_recipe(self, recipe_id):
        """Delete a (user) recipe; its ingredient rows go too thanks to ON DELETE CASCADE."""
        self.conn.execute("DELETE FROM recipes WHERE id=?", (recipe_id,))
        self.conn.commit()

    # ------------------------------------------------------------------ cooking history
    def log_cooked(self, recipe_id, servings, recipe_name=None, when=None):
        """Remember that a dish was cooked. Feeds the Calendar, the streak and the favourite dish."""
        if recipe_name is None:                            # look the name up if not given
            row = self.conn.execute("SELECT name FROM recipes WHERE id=?", (recipe_id,)).fetchone()
            recipe_name = row["name"] if row else "Unknown dish"
        when = when or datetime.now()
        cur = self.conn.execute(
            "INSERT INTO cook_log(recipe_id, servings, cooked_on, recipe_name) VALUES (?, ?, ?, ?)",
            (recipe_id, int(servings), when.isoformat(timespec="seconds"), recipe_name))
        self.conn.commit()
        return cur.lastrowid                               # the entry's id - used to attach a photo

    def set_cook_photo(self, log_id, photo_path):
        """Attach the user's photo of the cooked dish to one calendar entry."""
        self.conn.execute("UPDATE cook_log SET photo_path=? WHERE id=?", (photo_path, log_id))
        self.conn.commit()

    def cook_log(self, start=None, end=None):
        """Cooking history as dicts, newest first. start/end (dates) limit the range, inclusive.

        Each dict: id, recipe_id, recipe_name, servings, cooked_on (text), photo_path (the user's
        own photo or None), image_path (the recipe's picture) and recipe_exists (0 if the recipe
        was deleted since - then image_path is None too).
        """
        sql = ("SELECT c.id, c.recipe_id, c.recipe_name, c.servings, c.cooked_on, c.photo_path, r.image_path, "
               "r.id IS NOT NULL AS recipe_exists "
               "FROM cook_log c LEFT JOIN recipes r ON r.id = c.recipe_id WHERE 1=1")
        params = []
        if start:
            sql += " AND c.cooked_on >= ?"                  # ISO text sorts like dates do
            params.append(start.isoformat())
        if end:
            sql += " AND c.cooked_on < ?"
            params.append(date.fromordinal(end.toordinal() + 1).isoformat())   # the day after `end`
        sql += " ORDER BY c.cooked_on DESC"
        return [dict(r) for r in self.conn.execute(sql, params)]

    def cooked_days(self):
        """Set of dates on which something was cooked (for streaks)."""
        rows = self.conn.execute("SELECT DISTINCT substr(cooked_on, 1, 10) AS d FROM cook_log")
        return {date.fromisoformat(r["d"]) for r in rows}

    # ------------------------------------------------------------------ settings
    def get_setting(self, key, default=None):
        """Read a small saved value, e.g. the date of the last notification."""
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        """Store a small value (overwrites the previous one)."""
        self.conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)",
                          (key, str(value)))
        self.conn.commit()

    def default_servings(self):
        """How many people the user usually cooks for (Profile tab). Default: 1 person."""
        try:
            return max(1, int(self.get_setting("default_servings", "1")))
        except ValueError:
            return 1
