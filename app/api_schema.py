"""
api_schema.py
-------------
WHY THIS FILE EXISTS:
    The recipe catalogue is published as JSON (plain text that every language understands - see
    tools/export_catalog.py and app/catalog.py). This module converts recipes to JSON-friendly
    dicts and back. The exporter and the app both import it, so the format can never drift apart.

    (Version 4.7.1: the Cloud Run server is retired, so the functions for fridge items and match
    results - only the server used them - were removed.)

    Example of a recipe as JSON:
        {"uid": "dal-tadka", "name": "Dal Tadka", "cuisine": "Indian", "is_veg": true,
         "protein_g": 12, ..., "image": "dal-tadka.jpg",
         "ingredients": [{"name": "lentils", "quantity": 150, "unit": "g", "optional": false}, ...]}
"""

from app.images import asset_name
from app.models import Ingredient, Recipe


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
