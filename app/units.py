"""
units.py
--------
WHY THIS FILE EXISTS:
    A user may store "1 kg rice" in the pantry while a recipe asks for "200 g rice".
    To compare or subtract them we must convert both into the same *base unit*.
    This module is the single place that knows how units relate to each other,
    and how ingredient names are normalised ("Tomatoes" == "tomato", "curd" == "yogurt").
"""

# ----------------------------------------------------------------------------------------------
# UNIT CONVERSION
# ----------------------------------------------------------------------------------------------

# Every unit the app understands, mapped to (dimension, factor-to-base-unit).
#   dimension -> "mass" (base = grams), "volume" (base = millilitres) or "count" (base = pieces)
#   factor    -> how many base units one of this unit equals
UNITS = {
    "g": ("mass", 1.0),            # 1 gram = 1 gram (the base unit for mass)
    "kg": ("mass", 1000.0),        # 1 kilogram = 1000 grams
    "ml": ("volume", 1.0),         # 1 millilitre = 1 ml (the base unit for volume)
    "l": ("volume", 1000.0),       # 1 litre = 1000 ml
    "tsp": ("volume", 5.0),        # 1 teaspoon is about 5 ml
    "tbsp": ("volume", 15.0),      # 1 tablespoon is about 15 ml
    "cup": ("volume", 240.0),      # 1 cup is about 240 ml
    "pcs": ("count", 1.0),         # "pieces" - eggs, onions, lemons... (base unit for counting)
    "bunch": ("count", 1.0),       # a bunch of herbs is counted as one piece
}

# The list shown in the unit drop-downs of the UI (keeps the same order as above).
UNIT_CHOICES = list(UNITS.keys())


def to_base(quantity, unit):
    """Convert (quantity, unit) into (base_quantity, dimension).

    Example: to_base(1.5, "kg") -> (1500.0, "mass")
    Unknown units are treated as plain "count" so the app never crashes on bad data.
    """
    dimension, factor = UNITS.get(unit, ("count", 1.0))   # look the unit up, default to count
    return float(quantity) * factor, dimension            # multiply to reach the base unit


def from_base(base_quantity, unit):
    """The reverse of to_base: turn base units back into the given unit.

    Example: from_base(1500, "kg") -> 1.5
    """
    _dimension, factor = UNITS.get(unit, ("count", 1.0))  # we only need the factor here
    return base_quantity / factor                         # divide to go back to the original unit


def compatible(unit_a, unit_b):
    """True when two units measure the same thing (e.g. g and kg), so they can be compared."""
    return to_base(1, unit_a)[1] == to_base(1, unit_b)[1]  # compare the two dimensions


# Common fractions shown as one symbol for counted things ("9½ pcs" reads better than "9.5 pcs").
FRACTION_SYMBOLS = {0.25: "¼", 0.5: "½", 0.75: "¾"}


def pretty_quantity(quantity, unit):
    """Format a number nicely for display.

    2.0 -> '2', 0.25 g -> '0.25 g'. For counted units (pcs, bunch) halves and quarters become
    fraction symbols: 9.5 pcs -> '9½ pcs', 0.5 bunch -> '½ bunch'. The stored value stays a
    decimal (a recipe may really use half an onion) - only the display changes.
    """
    quantity = float(quantity)                            # works for ints, floats and numeric text
    if quantity.is_integer():                             # whole numbers look nicer without ".0"
        return f"{int(quantity)} {unit}"
    if UNITS.get(unit, ("count", 1.0))[0] == "count":    # pieces / bunches: try a fraction symbol
        whole = int(quantity)                             # 9.5 -> 9
        part = round(quantity - whole, 2)                 # 9.5 -> 0.5
        if part in FRACTION_SYMBOLS:
            return f"{whole if whole else ''}{FRACTION_SYMBOLS[part]} {unit}"   # '9½' or just '½'
    return f"{round(quantity, 2):g} {unit}"               # otherwise at most two decimals


# ----------------------------------------------------------------------------------------------
# INGREDIENT NAME NORMALISATION
# ----------------------------------------------------------------------------------------------

# Different words people use for the same ingredient. Left side = what a user might type,
# right side = the single "canonical" name the app uses internally for matching.
ALIASES = {
    "curd": "yogurt",
    "dahi": "yogurt",
    "yoghurt": "yogurt",
    "coriander leaves": "coriander",
    "cilantro": "coriander",
    "dhania": "coriander",
    "aubergine": "eggplant",
    "brinjal": "eggplant",
    "capsicum": "bell pepper",
    "chilli": "green chili",
    "green chilli": "green chili",
    "chili": "green chili",
    "chickpea": "chickpeas",
    "chana": "chickpeas",
    "garbanzo": "chickpeas",
    "paneer cheese": "paneer",
    "cottage cheese": "paneer",
    "spring onion": "green onion",
    "scallion": "green onion",
    "bread slice": "bread",
    "atta": "wheat flour",
    "maida": "flour",
    "all purpose flour": "flour",
    "ghee": "butter",
    "mince": "minced meat",
    "keema": "minced meat",
    "chicken breast": "chicken",
}

# Ingredients we assume every kitchen has, so recipes are never blocked by them.
ALWAYS_AVAILABLE = {"water", "salt"}


def normalize_name(name):
    """Turn any user-typed ingredient name into the canonical form used for matching.

    Steps: lower-case -> trim spaces -> apply alias table -> drop a simple English plural 's'.
    Example: "  Tomatoes " -> "tomato", "Curd" -> "yogurt".
    """
    text = " ".join(str(name).lower().split())            # lower-case and collapse extra spaces
    if text in ALIASES:                                   # direct alias hit (e.g. "curd")
        return ALIASES[text]
    # Plural handling: "tomatoes" -> "tomato", "onions" -> "onion" (but keep words like "chickpeas"
    # which are listed as canonical names themselves, and short words like "gas").
    canonical_names = set(ALIASES.values())               # names that must stay exactly as written
    if text not in canonical_names and len(text) > 3:
        if text.endswith("oes"):                          # tomatoes / potatoes
            text = text[:-2]
        elif text.endswith("ies"):                        # berries -> berry
            text = text[:-3] + "y"
        elif text.endswith("s") and not text.endswith("ss"):  # onions -> onion (but not "glass")
            text = text[:-1]
    return ALIASES.get(text, text)                        # the singular form may itself be an alias
