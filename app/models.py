"""
models.py
---------
WHY THIS FILE EXISTS:
    These small "dataclasses" describe the *shape* of the data the app works with
    (a pantry item, a recipe, an ingredient line). The database layer turns rows into these
    objects and the UI / recipe engine work only with these objects - never with raw SQL rows.
    That separation means you could swap SQLite for something else without touching the UI.
"""

import re                                   # regular expressions, used by slugify()
from dataclasses import dataclass, field   # dataclass auto-writes __init__, __repr__ etc. for us
from datetime import date                   # used to compare expiry dates with "today"
from typing import List, Optional           # type hints, purely for readability / editor help

# The meal slots the app knows about, in the order they happen during a day.
MEAL_TYPES = ["Breakfast", "Brunch", "Lunch", "Snacks", "Dinner"]

# Cuisines a recipe can belong to (used by the cuisine filter).
CUISINES = ["Indian", "Arabic", "English"]

# Nutritional tags a recipe can carry (used by the nutrition filter).
NUTRITION_TAGS = ["High Protein", "Low Carb", "Low Calorie", "High Fiber", "Balanced"]

# Cooking machines the user can own. Recipes list which of these they can be made with.
APPLIANCES = ["Stove", "Rice Cooker", "Oven", "Microwave"]

# Where a pantry item lives - only used for grouping in the Fridge screen.
CATEGORIES = ["Fridge", "Outside"]   # "Outside" = cupboard / shelf, i.e. not refrigerated

# What an item is kept in - decides its picture and its place in the fridge drawing (version 4.1):
#   jar    -> on the shelves      bottle -> in the door rack      dish -> on the leftovers shelf
CONTAINERS = ["bottle", "jar", "dish"]
CONTAINER_LABELS = {"bottle": "Bottle", "jar": "Glass jar", "dish": "Dish"}   # names shown in the form

# Words that mean "cooked food", so the item is probably kept in a dish.
DISH_WORDS = ("leftover", "cooked", "curry", "dal", "sabzi", "biryani", "pulao", "soup", "stew")

# Ways the recipe list can be sorted (the "Sort" drop-down on the Recipes tab).
SORT_OPTIONS = ["Best match", "Most protein", "Least carbs", "Most carbs", "Fewest calories", "Quickest"]


def slugify(text):
    """Turn a name into a safe, stable id: "Fruit & Yogurt Bowl" -> "fruit-yogurt-bowl".

    Used as the recipe `uid` (shared by the phone and the server) and as the image file name.
    """
    text = re.sub(r"[^a-z0-9]+", "-", str(text).lower())   # every run of non-letters -> one dash
    return text.strip("-") or "recipe"                      # no leading/trailing dashes


def guess_container(name, unit):
    """A sensible first choice for the container picker (the user can always change it).

    "Leftover dal" -> dish, "Soy sauce" in ml -> bottle, everything else -> jar.
    Also used for items saved before version 4.1, which have no container yet.
    """
    words = re.findall(r"[a-z]+", str(name).lower())        # "Rice (uncooked)" -> ["rice", "uncooked"]
    if any(word in DISH_WORDS for word in words):           # whole words only: "uncooked" is not "cooked"
        return "dish"
    if unit in ("ml", "l"):                                 # liquids
        return "bottle"
    return "jar"


@dataclass
class PantryItem:
    """One thing the user owns, e.g. '500 g Curd, in the Fridge, expires 2026-10-06'."""
    name: str                          # display name exactly as the user typed it
    quantity: float                    # how much is left
    unit: str                          # one of units.UNIT_CHOICES
    category: str = "Fridge"           # "Fridge" or "Outside"
    expiry: Optional[date] = None      # None means "does not expire" (e.g. salt)
    id: Optional[int] = None           # database primary key (None until saved)
    container: Optional[str] = None    # "bottle" / "jar" / "dish" (None = guess from name and unit)

    def kept_in(self):
        """The container to draw: the user's choice, or a guess for older items."""
        return self.container if self.container in CONTAINERS else guess_container(self.name, self.unit)

    def days_left(self, today=None):
        """Days until expiry: 0 = expires today, negative = already expired, None = never."""
        if self.expiry is None:                         # non-perishable item
            return None
        today = today or date.today()                   # allow tests to inject a fake "today"
        return (self.expiry - today).days               # subtracting dates gives a timedelta

    def expires_today(self, today=None):
        """True when the item must be used today."""
        return self.days_left(today) == 0

    def is_expired(self, today=None):
        """True when the expiry date is already in the past."""
        left = self.days_left(today)
        return left is not None and left < 0


@dataclass
class Ingredient:
    """One line of a recipe's ingredient list, e.g. '200 ml yogurt'."""
    name: str                          # ingredient name (matched against pantry via normalize_name)
    quantity: float                    # amount needed for the recipe's default servings
    unit: str                          # unit of the amount above
    optional: bool = False             # optional items never block a recipe from being "cookable"


@dataclass
class Recipe:
    """A full recipe - either built-in (seed) or created by the user."""
    name: str
    cuisine: str                                           # one of CUISINES
    is_veg: bool                                           # True = vegetarian
    prep_minutes: int                                      # total preparation + cooking time
    servings: int                                          # how many people the quantities feed
    ingredients: List[Ingredient] = field(default_factory=list)   # what you need
    steps: List[str] = field(default_factory=list)                 # how to cook it, in order
    meal_types: List[str] = field(default_factory=list)            # when it is usually eaten
    nutrition_tags: List[str] = field(default_factory=list)        # e.g. ["High Protein"]
    appliances: List[str] = field(default_factory=list)            # ANY one of these is enough
    image_path: Optional[str] = None       # "asset:<file>" for built-in images, else a full file path
    is_user: bool = False                                          # True = created by the user
    is_saved: bool = False                                         # True = in "Saved dishes"
    id: Optional[int] = None               # LOCAL database primary key (differs per device)
    # Nutrition PER SERVING - used for the "Most protein" / "Least carbs" sorting and the
    # nutrition boxes on the recipe page. 0 means "unknown".
    protein_g: float = 0.0
    carbs_g: float = 0.0
    calories: float = 0.0
    # A stable text id that is the same on every device and on the server (e.g. "dal-tadka").
    # The numeric `id` above can differ between the phone and the server; `uid` never does.
    uid: Optional[str] = None
