"""
recipe_engine.py
----------------
WHY THIS FILE EXISTS:
    This is the "brain" of the app. It contains NO user-interface code, which means it can be
    tested on its own (see tests/test_engine.py). It answers four questions:

      1. match_recipe()      - Can I cook this recipe with what is in my fridge and my appliances?
                               What is missing? Does it use something that expires today?
      2. filter_matches()    - Apply the user's filters (veg / time / nutrition / cuisine).
      3. recommend()         - Which dishes suit the nearest meal time, best ones first?
      4. plan_deduction()    - After cooking, how much of each pantry item should be subtracted?
"""

from dataclasses import dataclass, field     # for the RecipeMatch result object
from datetime import date                    # "today", for expiry checks

from app.units import ALWAYS_AVAILABLE, compatible, from_base, normalize_name, to_base


@dataclass
class RecipeMatch:
    """The result of checking ONE recipe against the pantry."""
    recipe: object                                      # the Recipe that was checked
    servings: int                                       # servings the check was done for
    have: list = field(default_factory=list)            # Ingredient objects we have enough of
    missing: list = field(default_factory=list)         # REQUIRED ingredients we lack
    missing_optional: list = field(default_factory=list)  # optional ones we lack (not blocking)
    appliance_ok: bool = True                           # do we own a machine that can cook it?
    uses_expiring_today: list = field(default_factory=list)  # pantry names expiring today it uses
    uses_expiring_soon: list = field(default_factory=list)   # pantry names expiring in <= 2 days

    @property
    def can_cook(self):
        """True when nothing required is missing AND we have a suitable appliance."""
        return not self.missing and self.appliance_ok

    def sort_key(self):
        """A tuple Python can sort by. Smaller tuple = shown higher in the list.

        Order of importance:
          1. dishes that use an item expiring TODAY (so food isn't wasted) - but only if they are
             realistic, i.e. at most 1 required ingredient missing
          2. dishes you can cook right now
          3. dishes that use items expiring soon
          4. fewer missing ingredients
          5. quicker dishes
        """
        realistic = len(self.missing) <= 1              # a dish missing 4 things can't rescue the curd
        return (
            0 if self.uses_expiring_today and realistic else 1,   # 0 sorts before 1
            0 if self.can_cook else 1,
            0 if self.uses_expiring_soon else 1,
            len(self.missing),
            self.recipe.prep_minutes,
        )


def build_pantry_index(items, today=None):
    """Group usable pantry items by their normalised name.

    Returns {"tomato": [PantryItem, PantryItem], "yogurt": [PantryItem], ...}
    Expired items and empty items are left out, because you should not cook with them.
    """
    today = today or date.today()
    index = {}
    for item in items:
        if item.is_expired(today) or item.quantity <= 0:   # skip unusable food
            continue
        key = normalize_name(item.name)                    # "Curd" and "yogurt" share one key
        index.setdefault(key, []).append(item)             # create the list on first use
    return index


def _available_base(pantry_list, unit):
    """How much (in base units) of an ingredient we have, counting only compatible units.

    Returns (amount, has_incompatible). has_incompatible is True when the user stored the item in
    a unit we cannot convert (e.g. recipe wants 'g' but fridge says '2 pcs' of cheese).
    """
    total, incompatible = 0.0, False
    for item in pantry_list:
        if compatible(item.unit, unit):                    # e.g. both are mass units
            total += to_base(item.quantity, item.unit)[0]  # add up in grams / ml / pieces
        else:
            incompatible = True                            # can't compare, but we DO have some
    return total, incompatible


def match_recipe(recipe, pantry_index, owned_appliances, servings=None, today=None):
    """Check one recipe against the pantry. Returns a RecipeMatch."""
    today = today or date.today()
    servings = servings or recipe.servings                 # default: the recipe's own servings
    scale = servings / recipe.servings                     # e.g. cook 4 of a 2-serving recipe -> x2
    result = RecipeMatch(recipe=recipe, servings=servings)

    # Appliance check: an empty list means "no machine needed"; otherwise ANY one is enough.
    result.appliance_ok = (not recipe.appliances) or any(a in owned_appliances
                                                         for a in recipe.appliances)

    for ing in recipe.ingredients:
        key = normalize_name(ing.name)                     # canonical name for lookups
        if key in ALWAYS_AVAILABLE:                        # water / salt never block a recipe
            result.have.append(ing)
            continue
        pantry_list = pantry_index.get(key, [])            # matching pantry items (maybe none)
        needed, _dim = to_base(ing.quantity * scale, ing.unit)   # required amount in base units
        available, incompatible = _available_base(pantry_list, ing.unit)
        # Enough if the compatible stock covers it, OR we have it in a unit we can't convert
        # (we trust the user here rather than wrongly saying "missing").
        enough = available + 1e-9 >= needed or (incompatible and available == 0)
        if pantry_list and enough:
            result.have.append(ing)
            # Note which expiring items this recipe would use up.
            for item in pantry_list:
                left = item.days_left(today)
                if left == 0 and item.name not in result.uses_expiring_today:
                    result.uses_expiring_today.append(item.name)
                elif left is not None and 0 < left <= 2 and item.name not in result.uses_expiring_soon:
                    result.uses_expiring_soon.append(item.name)
        elif ing.optional:
            result.missing_optional.append(ing)            # nice-to-have, does not block cooking
        else:
            result.missing.append(ing)                     # required and not enough -> missing
    return result


def match_all(recipes, pantry_items, owned_appliances, today=None, servings=1):
    """Run match_recipe for every recipe (builds the pantry index only once - faster).

    servings defaults to 1: by default the app checks whether you can cook for ONE person.
    """
    index = build_pantry_index(pantry_items, today)
    return [match_recipe(r, index, owned_appliances, servings=servings, today=today) for r in recipes]


# How each "Sort" option orders recipes. Each value is a function that turns a RecipeMatch into a
# sort key; Python sorts small keys first, so "most protein" uses the NEGATIVE protein amount.
# Recipes with unknown nutrition (0) are pushed to the end for the nutrition sorts.
SORT_KEYS = {
    "Most protein": lambda m: (m.recipe.protein_g <= 0, -m.recipe.protein_g),
    "Least carbs": lambda m: (m.recipe.carbs_g <= 0, m.recipe.carbs_g),
    "Most carbs": lambda m: (m.recipe.carbs_g <= 0, -m.recipe.carbs_g),
    "Fewest calories": lambda m: (m.recipe.calories <= 0, m.recipe.calories),
    "Quickest": lambda m: m.recipe.prep_minutes,
}


def sort_matches(matches, sort="Best match"):
    """Return the matches ordered by the chosen sort option (default: best match first)."""
    ordered = sorted(matches, key=RecipeMatch.sort_key)       # best match first...
    if sort in SORT_KEYS:
        # ...then re-sort by the chosen value. Python's sort is "stable": recipes with equal values
        # keep their best-match order, so ties are still broken sensibly.
        ordered.sort(key=SORT_KEYS[sort])
    return ordered


def filter_matches(matches, diet="All", max_minutes=None, nutrition="Any",
                   cuisine="Any", only_cookable=False, max_missing=None, search="",
                   sort="Best match"):
    """Apply the user's filters and return the remaining matches, best first.

    diet          - "All", "Veg" or "Non-Veg"
    max_minutes   - None for no limit, else e.g. 15 / 30 / 60
    nutrition     - "Any" or one of models.NUTRITION_TAGS
    cuisine       - "Any" or one of models.CUISINES
    only_cookable - True -> hide recipes with missing ingredients / no appliance
    max_missing   - hide recipes missing more than this many ingredients (None = no limit)
    search        - free-text search on the recipe name
    sort          - one of models.SORT_OPTIONS (e.g. "Most protein", "Least carbs")
    """
    result = []
    search = search.strip().lower()
    for m in matches:
        r = m.recipe
        if diet == "Veg" and not r.is_veg:
            continue                                        # 'continue' skips to the next recipe
        if diet == "Non-Veg" and r.is_veg:
            continue
        if max_minutes is not None and r.prep_minutes > max_minutes:
            continue
        if nutrition != "Any" and nutrition not in r.nutrition_tags:
            continue
        if cuisine != "Any" and r.cuisine != cuisine:
            continue
        if only_cookable and not m.can_cook:
            continue
        if max_missing is not None and len(m.missing) > max_missing:
            continue
        if search and search not in r.name.lower():
            continue
        result.append(m)                                    # survived every filter
    return sort_matches(result, sort)                       # order as the user chose


def recommend(matches, meal, limit=8):
    """Dishes for the given meal slot that are cookable or nearly cookable, best first.

    A dish is recommended when it belongs to the meal slot, we own a suitable appliance,
    and at most 1 required ingredient is missing. Dishes using items that expire today rise to
    the top (see RecipeMatch.sort_key).
    """
    picks = [m for m in matches
             if meal in m.recipe.meal_types and m.appliance_ok and len(m.missing) <= 1]
    picks.sort(key=RecipeMatch.sort_key)
    return picks[:limit]                                    # keep the column short


def plan_deduction(recipe, pantry_items, servings, today=None):
    """Work out what to subtract from the pantry after cooking `recipe` for `servings` people.

    Strategy "first expiring, first used": if you have two packs of curd, the one expiring
    sooner is used first - the same thing a sensible cook does.

    Returns (changes, warnings):
        changes  - list of (pantry_item_id, new_quantity) ready for Database.apply_deductions
        warnings - list of strings for things we could not subtract automatically
    """
    today = today or date.today()
    scale = servings / recipe.servings
    index = build_pantry_index(pantry_items, today)
    remaining_qty = {}                                      # item.id -> quantity after deductions
    changes_order = []                                      # keep ids in the order we touched them
    warnings = []

    for ing in recipe.ingredients:
        key = normalize_name(ing.name)
        if key in ALWAYS_AVAILABLE:                         # we don't track water / salt
            continue
        candidates = [i for i in index.get(key, []) if compatible(i.unit, ing.unit)]
        if not candidates:                                  # nothing usable to subtract from
            if index.get(key):                              # we have it, but in another unit
                warnings.append(f"{ing.name}: stored in a different unit - please update it manually.")
            continue
        # Soonest expiry first; items without an expiry date last (date.max is the far future).
        candidates.sort(key=lambda i: i.expiry or date.max)
        need_base, _dim = to_base(ing.quantity * scale, ing.unit)   # what the recipe uses
        for item in candidates:
            if need_base <= 1e-9:                           # already covered
                break
            current = remaining_qty.get(item.id, item.quantity)    # account for earlier deductions
            have_base, _ = to_base(current, item.unit)
            take = min(have_base, need_base)                # can't take more than the pack holds
            remaining_qty[item.id] = from_base(have_base - take, item.unit)  # back to item's unit
            if item.id not in changes_order:
                changes_order.append(item.id)
            need_base -= take
        if need_base > 1e-9 and not ing.optional:           # pantry ran out before the recipe did
            warnings.append(f"{ing.name}: not enough in stock - used everything you had.")

    changes = [(item_id, remaining_qty[item_id]) for item_id in changes_order]
    return changes, warnings
