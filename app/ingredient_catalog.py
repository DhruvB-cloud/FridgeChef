"""
ingredient_catalog.py
---------------------
WHY THIS FILE EXISTS:
    Powers the type-ahead drop-down: when the user types "oni", the app suggests "Onion".

    Version 5.0 (testers asked for less typing): every known ingredient also carries
      * its UNIT    - only kg, pcs or L (the three units the Fridge form offers),
      * its TAG     - Fresh produce, Meat, Bakery, Frozen, Grain, Pantry or Dry goods,
      * its SHELF LIFE in days - so the expiry date is filled in automatically,
      * a DEFAULT QUANTITY - what people usually buy (e.g. 1 L milk, 6 eggs).
    So adding "Milk" to the fridge is: type the name, check the amount, Save.

    The suggest() function also mixes in names the user has typed before (from their pantry and
    recipes), so the list gets more personal over time.
"""

from collections import namedtuple

# The three units the Fridge form offers, and the tags an item can carry.
FRIDGE_UNITS = ["kg", "pcs", "L"]
TAGS = ["Fresh produce", "Meat", "Bakery", "Frozen", "Grain", "Pantry", "Dry goods"]
# Dairy and eggs have no tag of their own in the list Dhruv chose, so they count as fresh produce.

# What we know about one ingredient (a namedtuple = a tiny read-only class with named fields).
IngredientInfo = namedtuple("IngredientInfo", "unit tag shelf_days default_qty")

# For names we don't know: counted in pieces, kept a week, tagged as pantry food.
UNKNOWN = IngredientInfo("pcs", "Pantry", 7, 1)


def _group(tag, unit, days, qty, names):
    """Many ingredients with the same tag / unit / shelf life / usual amount, in one line each."""
    return [(name, IngredientInfo(unit, tag, days, qty)) for name in names.split(", ")]


# (name, IngredientInfo) - grouped by tag; shelf lives are typical for a home fridge or cupboard.
CATALOG = (
    # ---------------------------------------------------------------- FRESH PRODUCE: vegetables
    _group("Fresh produce", "pcs", 7, 4, "Onion, Potato, Sweet potato, Garlic, Lemon, Lime")
    + _group("Fresh produce", "pcs", 6, 3, "Tomato, Carrot, Bell pepper, Cucumber, Zucchini, "
             "Eggplant, Avocado, Green chili, Jalapeno, Leek, Corn")
    + _group("Fresh produce", "pcs", 5, 1, "Cabbage, Cauliflower, Broccoli, Lettuce, Pumpkin")
    + _group("Fresh produce", "kg", 5, 0.25, "Mushroom, Okra, Green beans, Peas, Bean sprouts, "
             "Ginger, Spinach")
    # herbs (one bunch each, they wilt fast)
    + _group("Fresh produce", "pcs", 4, 1, "Coriander, Mint, Parsley, Basil, Dill, Curry leaves, "
             "Fenugreek leaves, Green onion")
    # fruit
    + _group("Fresh produce", "pcs", 6, 6, "Apple, Banana, Orange, Mango, Pomegranate")
    + _group("Fresh produce", "kg", 5, 0.5, "Grapes, Strawberry, Pineapple")
    # dairy & eggs
    + _group("Fresh produce", "L", 5, 1, "Milk")
    + _group("Fresh produce", "L", 7, 0.2, "Cream, Sour cream")
    + _group("Fresh produce", "kg", 7, 0.5, "Yogurt, Curd, Labneh")
    + _group("Fresh produce", "kg", 4, 0.2, "Paneer")
    + _group("Fresh produce", "kg", 21, 0.2, "Cheese, Mozzarella, Parmesan")
    + _group("Fresh produce", "kg", 30, 0.1, "Butter")
    + _group("Fresh produce", "pcs", 21, 6, "Egg")
    # ---------------------------------------------------------------- MEAT
    + _group("Meat", "kg", 2, 0.5, "Chicken, Lamb, Minced meat, Fish, Prawns")
    + _group("Meat", "pcs", 4, 6, "Chicken sausage")
    # ---------------------------------------------------------------- BAKERY
    + _group("Bakery", "pcs", 4, 1, "Bread")
    + _group("Bakery", "pcs", 4, 6, "Pita bread, Bread roll, Tortilla")
    # ---------------------------------------------------------------- FROZEN
    + _group("Frozen", "kg", 90, 0.5, "Frozen peas, Frozen mixed vegetables, Frozen berries")
    + _group("Frozen", "pcs", 90, 1, "Puff pastry, Pizza base, Spring roll wrappers")
    # ---------------------------------------------------------------- GRAIN
    + _group("Grain", "kg", 365, 1, "Rice, Basmati rice, Arborio rice, Oats, Poha, Semolina, Bulgur, "
             "Couscous, Pasta, Spaghetti, Noodles, Rice noodles, Lasagne sheets")
    + _group("Grain", "kg", 180, 1, "Flour, Wheat flour, Gram flour, Cornflour, Breadcrumbs")
    + _group("Grain", "kg", 3, 0.5, "Dosa batter")
    # ---------------------------------------------------------------- PANTRY (oils, sauces, spices, tins)
    + _group("Pantry", "L", 365, 1, "Oil, Olive oil, Vinegar")
    + _group("Pantry", "L", 365, 0.25, "Soy sauce, Chili sauce, Ketchup, Teriyaki sauce, Coconut milk, "
             "Honey, Tahini, Vegetable stock")
    + _group("Pantry", "kg", 180, 0.2, "Tomato puree, Pesto, Green curry paste, Salsa, Pickle, "
             "Ginger garlic paste")
    + _group("Pantry", "kg", 365, 0.1, "Cumin, Turmeric, Garam masala, Red chili powder, Paprika, "
             "Cinnamon, Cardamom, Mustard seeds, Za'atar, Sumac, Chili flakes, Oregano, Black pepper, "
             "Yeast, Baking powder")
    + _group("Pantry", "pcs", 365, 2, "Baked beans, Chopped tomatoes")
    + _group("Pantry", "kg", 365, 1, "Salt, Sugar")
    # ---------------------------------------------------------------- DRY GOODS (pulses, nuts, dried fruit)
    + _group("Dry goods", "kg", 365, 0.5, "Lentils, Moong dal, Kidney beans, Chickpeas, Black beans, "
             "Fava beans, Peanuts, Cashews, Raisins, Dates, Tortilla chips")
)

# Fast lookup: lower-case name -> (name, info).
_BY_NAME = {name.lower(): (name, info) for name, info in CATALOG}


# ----------------------------------------------------------------------------------------------
# FOOD TYPE (used to colour the Name box in the Fridge form)
# ----------------------------------------------------------------------------------------------
# Words that mean meat / fish / seafood. Matched as WHOLE words, so "hamper" isn't "ham".
NON_VEG_WORDS = {
    "chicken", "mutton", "lamb", "goat", "beef", "veal", "pork", "bacon", "ham", "sausage", "salami",
    "pepperoni", "turkey", "duck", "meat", "mince", "minced", "keema", "kheema", "liver", "kebab",
    "fish", "tuna", "salmon", "sardine", "mackerel", "pomfret", "rohu", "hilsa", "surmai", "anchovy",
    "prawn", "shrimp", "crab", "lobster", "squid", "octopus", "mussel", "oyster", "clam", "seafood",
    "gelatin", "gelatine", "lard",
}
EGG_WORDS = {"egg", "anda", "omelette", "omelet"}   # "eggplant" is ONE word, so it stays veg


def food_type(name):
    """Classify an ingredient name: "nonveg", "egg", "veg", or None for an empty name.

    "Chicken breast" -> nonveg, "Eggs" -> egg, "Eggplant" -> veg, "Paneer" -> veg.
    Anything that isn't recognised as meat/fish or egg counts as veg.
    """
    import re                                             # local import: only this function needs it
    words = re.findall(r"[a-z]+", str(name).lower())      # "Chicken-Breast 2" -> ["chicken", "breast"]
    if not words:                                         # nothing typed yet
        return None
    singular = {w[:-1] if w.endswith("s") and len(w) > 3 else w for w in words}   # "prawns" -> "prawn"
    words = set(words) | singular                         # check both forms
    if words & NON_VEG_WORDS:                             # '&' = words that appear in both sets
        return "nonveg"
    if words & EGG_WORDS:
        return "egg"
    return "veg"


def info_for(name):
    """IngredientInfo(unit, tag, shelf_days, default_qty) for a known ingredient, or None.

    Also finds plurals and other spellings ("Tomatoes", "curd", "capsicum") through the same name
    matching the recipes use (units.normalize_name).
    """
    key = str(name).strip().lower()
    if key in _BY_NAME:
        return _BY_NAME[key][1]
    from app.units import normalize_name                  # local import avoids a circular import
    wanted = normalize_name(key)
    for known, (_, info) in _BY_NAME.items():
        if normalize_name(known) == wanted:
            return info
    return None


def guess_info(name):
    """Like info_for, but never None: unknown meat names get the Meat tag, everything else UNKNOWN."""
    info = info_for(name)
    if info is not None:
        return info
    if food_type(name) == "nonveg":                       # e.g. "Turkey breast"
        return IngredientInfo("kg", "Meat", 2, 0.5)
    return UNKNOWN


def suggest(text, extra_names=(), limit=6):
    """Suggestions for what the user has typed so far.

    Names that START with the text come first ("oni" -> "Onion"), then names that merely
    CONTAIN it ("oni" -> "Green onion"). Matching ignores upper/lower case.
    """
    text = str(text).strip().lower()
    if len(text) < 2:                                    # 1 letter matches too much to be useful
        return []
    names, seen = [], set()
    for name in [n for n, _ in CATALOG] + [str(e).strip() for e in extra_names]:
        key = name.lower()
        if key and key not in seen:                     # skip duplicates (catalog + user names)
            seen.add(key)
            names.append(name)
    starts = [n for n in names if n.lower().startswith(text)]
    contains = [n for n in names if text in n.lower() and n not in starts]
    result = sorted(starts, key=len) + sorted(contains, key=len)   # shorter names first
    # Hide the suggestion if it is exactly what's already typed - nothing left to complete.
    return [n for n in result if n.lower() != text][:limit]
