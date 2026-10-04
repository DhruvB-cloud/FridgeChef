"""
ingredient_catalog.py
---------------------
WHY THIS FILE EXISTS:
    Powers the type-ahead drop-down: when the user types "oni", the app suggests "Onion".
    Each known ingredient also carries a sensible default unit and where it is usually kept,
    so picking a suggestion fills in the unit and Fridge/Outside fields automatically.
    The suggest() function also mixes in names the user has typed before (from their pantry and
    recipes), so the list gets more personal over time.
"""

# (name, default unit, usual category) - alphabetical inside each group for easy maintenance.
CATALOG = [
    # Vegetables
    ("Bell pepper", "pcs", "Fridge"), ("Broccoli", "g", "Fridge"), ("Cabbage", "g", "Fridge"),
    ("Carrot", "pcs", "Fridge"), ("Cauliflower", "g", "Fridge"), ("Cucumber", "pcs", "Fridge"),
    ("Eggplant", "pcs", "Fridge"), ("Garlic", "pcs", "Outside"), ("Ginger", "g", "Fridge"),
    ("Green beans", "g", "Fridge"), ("Green chili", "pcs", "Fridge"), ("Green onion", "pcs", "Fridge"),
    ("Lettuce", "pcs", "Fridge"), ("Mushroom", "g", "Fridge"), ("Okra", "g", "Fridge"),
    ("Onion", "pcs", "Outside"), ("Peas", "g", "Fridge"), ("Potato", "pcs", "Outside"),
    ("Pumpkin", "g", "Fridge"), ("Spinach", "g", "Fridge"), ("Sweet potato", "pcs", "Outside"),
    ("Tomato", "pcs", "Fridge"), ("Zucchini", "pcs", "Fridge"),
    # Herbs
    ("Basil", "bunch", "Fridge"), ("Coriander", "bunch", "Fridge"), ("Curry leaves", "bunch", "Fridge"),
    ("Dill", "bunch", "Fridge"), ("Fenugreek leaves", "bunch", "Fridge"), ("Mint", "bunch", "Fridge"),
    ("Parsley", "bunch", "Fridge"),
    # Dairy & eggs
    ("Butter", "g", "Fridge"), ("Cheese", "g", "Fridge"), ("Cream", "ml", "Fridge"),
    ("Egg", "pcs", "Fridge"), ("Labneh", "g", "Fridge"), ("Milk", "ml", "Fridge"),
    ("Paneer", "g", "Fridge"), ("Yogurt", "g", "Fridge"), ("Curd", "g", "Fridge"),
    # Fruits
    ("Apple", "pcs", "Fridge"), ("Avocado", "pcs", "Fridge"), ("Banana", "pcs", "Outside"),
    ("Dates", "g", "Outside"), ("Grapes", "g", "Fridge"), ("Lemon", "pcs", "Fridge"),
    ("Lime", "pcs", "Fridge"), ("Mango", "pcs", "Fridge"), ("Orange", "pcs", "Fridge"),
    ("Pomegranate", "pcs", "Fridge"), ("Strawberry", "g", "Fridge"),
    # Meat & fish
    ("Chicken", "g", "Fridge"), ("Fish", "g", "Fridge"), ("Lamb", "g", "Fridge"),
    ("Minced meat", "g", "Fridge"), ("Prawns", "g", "Fridge"),
    # Grains, flours, pulses
    ("Basmati rice", "g", "Outside"), ("Bread", "pcs", "Outside"), ("Bulgur", "g", "Outside"),
    ("Chickpeas", "g", "Outside"), ("Couscous", "g", "Outside"), ("Flour", "g", "Outside"),
    ("Kidney beans", "g", "Outside"), ("Lentils", "g", "Outside"), ("Oats", "g", "Outside"),
    ("Pasta", "g", "Outside"), ("Pita bread", "pcs", "Outside"), ("Poha", "g", "Outside"),
    ("Rice", "g", "Outside"), ("Semolina", "g", "Outside"), ("Wheat flour", "g", "Outside"),
    # Spices, oils & pantry
    ("Baked beans", "g", "Outside"), ("Cinnamon", "tsp", "Outside"), ("Cumin", "tsp", "Outside"),
    ("Garam masala", "tsp", "Outside"), ("Ginger garlic paste", "tbsp", "Fridge"),
    ("Honey", "tbsp", "Outside"), ("Oil", "ml", "Outside"), ("Olive oil", "ml", "Outside"),
    ("Paprika", "tsp", "Outside"), ("Peanuts", "g", "Outside"), ("Red chili powder", "tsp", "Outside"),
    ("Salt", "g", "Outside"), ("Sugar", "g", "Outside"), ("Tahini", "tbsp", "Outside"),
    ("Turmeric", "tsp", "Outside"), ("Za'atar", "tsp", "Outside"),
]

# Fast lookup: lower-case name -> (name, unit, category).
_BY_NAME = {name.lower(): (name, unit, cat) for name, unit, cat in CATALOG}


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
    """Return (unit, category) for a known ingredient, or None if we don't know it."""
    hit = _BY_NAME.get(str(name).strip().lower())
    return (hit[1], hit[2]) if hit else None


def suggest(text, extra_names=(), limit=6):
    """Suggestions for what the user has typed so far.

    Names that START with the text come first ("oni" -> "Onion"), then names that merely
    CONTAIN it ("oni" -> "Green onion"). Matching ignores upper/lower case.
    """
    text = str(text).strip().lower()
    if len(text) < 2:                                    # 1 letter matches too much to be useful
        return []
    names, seen = [], set()
    for name in [n for n, _, _ in CATALOG] + [str(e).strip() for e in extra_names]:
        key = name.lower()
        if key and key not in seen:                     # skip duplicates (catalog + user names)
            seen.add(key)
            names.append(name)
    starts = [n for n in names if n.lower().startswith(text)]
    contains = [n for n in names if text in n.lower() and n not in starts]
    result = sorted(starts, key=len) + sorted(contains, key=len)   # shorter names first
    # Hide the suggestion if it is exactly what's already typed - nothing left to complete.
    return [n for n in result if n.lower() != text][:limit]
