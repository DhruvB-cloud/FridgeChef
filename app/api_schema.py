"""
api_schema.py
-------------
WHY THIS FILE EXISTS:
    The app and the web server exchange data as JSON (plain text that every language
    understands). This module converts our Python objects to JSON-friendly dicts and back.
    BOTH sides import it, so the format can never drift apart between client and server.

    Example of a recipe as JSON:
        {"uid": "dal-tadka", "name": "Dal Tadka", "cuisine": "Indian", "is_veg": true,
         "protein_g": 12, ..., "image": "dal-tadka.jpg",
         "ingredients": [{"name": "lentils", "quantity": 150, "unit": "g", "optional": false}, ...]}
"""

from datetime import date

from app.images import asset_name
from app.models import Ingredient, PantryItem, Recipe
from app.recipe_engine import RecipeMatch

API_VERSION = 1          # bump when the JSON format changes in an incompatible way


# ------------------------------------------------------------------ ingredients
def ingredient_to_dict(ing):
    return {"name": ing.name, "quantity": ing.quantity, "unit": ing.unit, "optional": ing.optional}


def ingredient_from_dict(d):
    return Ingredient(name=d["name"], quantity=float(d["quantity"]), unit=d["unit"],
                      optional=bool(d.get("optional", False)))


# ------------------------------------------------------------------ recipes
def recipe_to_dict(r):
    """Recipe -> dict. Only built-in pictures are sent (as a file name), never local file paths."""
    return {
        "uid": r.uid, "name": r.name, "cuisine": r.cuisine, "is_veg": r.is_veg,
        "prep_minutes": r.prep_minutes, "servings": r.servings,
        "protein_g": r.protein_g, "carbs_g": r.carbs_g, "calories": r.calories,
        "meal_types": r.meal_types, "nutrition_tags": r.nutrition_tags, "appliances": r.appliances,
        "steps": r.steps, "image": asset_name(r.image_path),
        "ingredients": [ingredient_to_dict(i) for i in r.ingredients],
    }


def recipe_from_dict(d):
    """dict -> Recipe. The local numeric id is filled in later by the database."""
    return Recipe(
        uid=d["uid"], name=d["name"], cuisine=d["cuisine"], is_veg=bool(d["is_veg"]),
        prep_minutes=int(d["prep_minutes"]), servings=int(d["servings"]),
        protein_g=float(d.get("protein_g", 0)), carbs_g=float(d.get("carbs_g", 0)),
        calories=float(d.get("calories", 0)),
        meal_types=list(d.get("meal_types", [])), nutrition_tags=list(d.get("nutrition_tags", [])),
        appliances=list(d.get("appliances", [])), steps=list(d.get("steps", [])),
        image_path=f"asset:{d['image']}" if d.get("image") else None,
        ingredients=[ingredient_from_dict(i) for i in d.get("ingredients", [])],
    )


# ------------------------------------------------------------------ pantry (sent by the phone)
def pantry_to_dict(item):
    return {"name": item.name, "quantity": item.quantity, "unit": item.unit,
            "expiry": item.expiry.isoformat() if item.expiry else None}


def pantry_from_dict(d, index=0):
    return PantryItem(name=d["name"], quantity=float(d["quantity"]), unit=d["unit"],
                      expiry=date.fromisoformat(d["expiry"]) if d.get("expiry") else None,
                      id=index)          # a temporary id - the server never stores pantry items


# ------------------------------------------------------------------ matches (sent by the server)
def match_to_dict(m):
    return {
        "recipe": recipe_to_dict(m.recipe), "servings": m.servings,
        "have": [i.name for i in m.have],
        "missing": [ingredient_to_dict(i) for i in m.missing],
        "missing_optional": [ingredient_to_dict(i) for i in m.missing_optional],
        "appliance_ok": m.appliance_ok, "can_cook": m.can_cook,
        "uses_expiring_today": m.uses_expiring_today, "uses_expiring_soon": m.uses_expiring_soon,
    }


def match_from_dict(d):
    recipe = recipe_from_dict(d["recipe"])
    have_names = set(d.get("have", []))
    return RecipeMatch(
        recipe=recipe, servings=int(d.get("servings", 1)),
        have=[i for i in recipe.ingredients if i.name in have_names],
        missing=[ingredient_from_dict(i) for i in d.get("missing", [])],
        missing_optional=[ingredient_from_dict(i) for i in d.get("missing_optional", [])],
        appliance_ok=bool(d.get("appliance_ok", True)),
        uses_expiring_today=list(d.get("uses_expiring_today", [])),
        uses_expiring_soon=list(d.get("uses_expiring_soon", [])),
    )
