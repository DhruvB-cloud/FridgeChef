"""
seed_recipes.py
---------------
WHY THIS FILE EXISTS:
    On the very first launch the database is empty, so the user would see no recipes at all.
    This file holds a starter library of Indian, Arabic and English recipes that the database
    copies into itself once (see Database._seed_if_empty). Because they are stored in the local
    SQLite file afterwards, they work fully offline.

HOW TO ADD MORE BUILT-IN RECIPES:
    Copy one Recipe(...) block below, change the values, add its numbers to NUTRITION at the
    bottom (and its picture to tools/make_assets.py). On the next start, Database._seed() inserts
    any built-in recipe it doesn't have yet - no need to delete anything.
    User-created recipes are added from the app instead.

NOTES:
    * Eggs are marked as NON-veg, following the common Indian convention.
    * `appliances` means "ANY ONE of these is enough". An empty list means "no cooking machine needed".
    * Quantities are for the `servings` number given; the app scales them if the user cooks more/less.
"""

from app.models import Ingredient, Recipe, slugify   # the data shapes defined in models.py


def I(name, quantity, unit, optional=False):
    """Tiny helper so each ingredient fits on one readable line below."""
    return Ingredient(name=name, quantity=quantity, unit=unit, optional=optional)


# The full starter list. Each Recipe(...) call creates one recipe object.
SEED_RECIPES = [
    # ------------------------------------------------------------------ INDIAN
    Recipe(
        name="Masala Omelette", cuisine="Indian", is_veg=False, prep_minutes=15, servings=1,
        meal_types=["Breakfast", "Brunch"], nutrition_tags=["High Protein", "Low Carb"],
        appliances=["Stove"],
        ingredients=[I("egg", 3, "pcs"), I("onion", 1, "pcs"), I("tomato", 1, "pcs"),
                     I("green chili", 1, "pcs", True), I("coriander", 0.25, "bunch", True),
                     I("oil", 1, "tbsp"), I("salt", 0.5, "tsp")],
        steps=["Finely chop the onion, tomato, chili and coriander.",
               "Whisk the eggs with salt, then stir in the chopped vegetables.",
               "Heat oil in a pan on medium heat and pour in the egg mixture.",
               "Cook 2-3 minutes, flip, cook 1 more minute and serve hot."]),
    Recipe(
        name="Vegetable Poha", cuisine="Indian", is_veg=True, prep_minutes=20, servings=2,
        meal_types=["Breakfast", "Brunch", "Snacks"], nutrition_tags=["Low Calorie", "Balanced"],
        appliances=["Stove"],
        ingredients=[I("poha", 200, "g"), I("onion", 1, "pcs"), I("potato", 1, "pcs"),
                     I("peas", 50, "g", True), I("green chili", 1, "pcs", True),
                     I("lemon", 1, "pcs"), I("peanuts", 30, "g", True), I("oil", 2, "tbsp"),
                     I("turmeric", 0.5, "tsp"), I("coriander", 0.25, "bunch", True)],
        steps=["Rinse the poha in a sieve and let it drain for 5 minutes.",
               "Fry peanuts in oil, then add chopped onion, chili and diced potato.",
               "Cover and cook until the potato is soft; add peas and turmeric.",
               "Fold in the poha with salt, cook 2 minutes, finish with lemon and coriander."]),
    Recipe(
        name="Jeera Rice", cuisine="Indian", is_veg=True, prep_minutes=25, servings=2,
        meal_types=["Lunch", "Dinner"], nutrition_tags=["Balanced"],
        appliances=["Rice Cooker", "Stove"],
        ingredients=[I("rice", 200, "g"), I("cumin", 1, "tsp"), I("butter", 1, "tbsp"),
                     I("water", 400, "ml"), I("salt", 0.5, "tsp")],
        steps=["Wash the rice until the water runs clear and soak for 10 minutes.",
               "Melt butter, let the cumin seeds splutter.",
               "Add rice, water and salt (rice cooker: put everything in and press Cook).",
               "On a stove: cover and simmer 12 minutes, rest 5 minutes, fluff with a fork."]),
    Recipe(
        name="Dal Tadka", cuisine="Indian", is_veg=True, prep_minutes=35, servings=3,
        meal_types=["Lunch", "Dinner"], nutrition_tags=["High Protein", "High Fiber"],
        appliances=["Stove"],
        ingredients=[I("lentils", 150, "g"), I("onion", 1, "pcs"), I("tomato", 1, "pcs"),
                     I("garlic", 3, "pcs"), I("cumin", 1, "tsp"), I("turmeric", 0.5, "tsp"),
                     I("butter", 1, "tbsp"), I("coriander", 0.25, "bunch", True),
                     I("water", 600, "ml"), I("salt", 1, "tsp")],
        steps=["Boil the washed lentils with turmeric and water until soft (about 20 minutes).",
               "In another pan heat butter, add cumin and chopped garlic.",
               "Add onion, cook until golden, then tomato until mushy.",
               "Pour the tadka over the dal, add salt, garnish with coriander."]),
    Recipe(
        name="Cucumber Raita", cuisine="Indian", is_veg=True, prep_minutes=5, servings=2,
        meal_types=["Lunch", "Dinner", "Snacks"], nutrition_tags=["Low Calorie", "Low Carb"],
        appliances=[],
        ingredients=[I("yogurt", 250, "g"), I("cucumber", 1, "pcs"),
                     I("onion", 0.5, "pcs", True), I("cumin", 0.5, "tsp", True),
                     I("coriander", 0.1, "bunch", True), I("salt", 0.25, "tsp")],
        steps=["Whisk the yogurt (curd) until smooth.",
               "Grate the cucumber and squeeze out the extra water.",
               "Mix everything together with salt and roasted cumin. Serve chilled."]),
    Recipe(
        name="Paneer Bhurji", cuisine="Indian", is_veg=True, prep_minutes=20, servings=2,
        meal_types=["Breakfast", "Lunch", "Dinner"], nutrition_tags=["High Protein", "Low Carb"],
        appliances=["Stove"],
        ingredients=[I("paneer", 200, "g"), I("onion", 1, "pcs"), I("tomato", 1, "pcs"),
                     I("bell pepper", 1, "pcs", True), I("green chili", 1, "pcs", True),
                     I("turmeric", 0.25, "tsp"), I("oil", 1, "tbsp"), I("salt", 0.5, "tsp")],
        steps=["Crumble the paneer with your hands.",
               "Sauté onion and chili in oil, then add tomato and bell pepper.",
               "Add turmeric and salt, then the paneer. Cook 3-4 minutes, stirring."]),
    Recipe(
        name="Chicken Curry", cuisine="Indian", is_veg=False, prep_minutes=50, servings=4,
        meal_types=["Lunch", "Dinner"], nutrition_tags=["High Protein"],
        appliances=["Stove"],
        ingredients=[I("chicken", 500, "g"), I("onion", 2, "pcs"), I("tomato", 2, "pcs"),
                     I("yogurt", 100, "g"), I("ginger garlic paste", 1, "tbsp"),
                     I("garam masala", 1, "tsp"), I("oil", 3, "tbsp"),
                     I("coriander", 0.25, "bunch", True), I("salt", 1, "tsp")],
        steps=["Marinate chicken in yogurt, salt and half the garam masala for 15 minutes.",
               "Fry sliced onions in oil until deep golden, add ginger garlic paste.",
               "Add chopped tomatoes and cook until oil separates.",
               "Add the chicken, cover and cook 20-25 minutes. Finish with garam masala and coriander."]),
    Recipe(
        name="Aloo Tikki", cuisine="Indian", is_veg=True, prep_minutes=30, servings=2,
        meal_types=["Snacks"], nutrition_tags=["Balanced"],
        appliances=["Stove"],
        ingredients=[I("potato", 3, "pcs"), I("bread", 1, "pcs"), I("peas", 50, "g", True),
                     I("green chili", 1, "pcs", True), I("coriander", 0.25, "bunch", True),
                     I("oil", 3, "tbsp"), I("salt", 0.5, "tsp")],
        steps=["Boil and mash the potatoes.",
               "Mix in crumbled bread, peas, chili, coriander and salt.",
               "Shape into flat patties and shallow-fry until crisp on both sides."]),
    Recipe(
        name="Vegetable Pulao", cuisine="Indian", is_veg=True, prep_minutes=30, servings=3,
        meal_types=["Lunch", "Dinner"], nutrition_tags=["Balanced", "High Fiber"],
        appliances=["Rice Cooker", "Stove"],
        ingredients=[I("rice", 200, "g"), I("carrot", 1, "pcs"), I("peas", 50, "g"),
                     I("onion", 1, "pcs"), I("garam masala", 0.5, "tsp"), I("butter", 1, "tbsp"),
                     I("water", 400, "ml"), I("salt", 0.5, "tsp")],
        steps=["Soak the rice for 15 minutes.",
               "Sauté onion in butter, add diced carrot and peas with garam masala.",
               "Add rice, water and salt. Rice cooker: press Cook. Stove: simmer covered 12 minutes."]),

    # ------------------------------------------------------------------ ARABIC
    Recipe(
        name="Hummus", cuisine="Arabic", is_veg=True, prep_minutes=10, servings=4,
        meal_types=["Snacks", "Lunch"], nutrition_tags=["High Protein", "High Fiber"],
        appliances=[],
        ingredients=[I("chickpeas", 400, "g"), I("tahini", 2, "tbsp"), I("lemon", 1, "pcs"),
                     I("garlic", 1, "pcs"), I("olive oil", 2, "tbsp"), I("salt", 0.5, "tsp")],
        steps=["Drain the (cooked/canned) chickpeas, keep a little liquid.",
               "Blend chickpeas, tahini, lemon juice, garlic and salt until smooth.",
               "Loosen with a spoon of liquid if needed. Drizzle with olive oil to serve."]),
    Recipe(
        name="Shakshuka", cuisine="Arabic", is_veg=False, prep_minutes=25, servings=2,
        meal_types=["Breakfast", "Brunch"], nutrition_tags=["High Protein", "Low Carb"],
        appliances=["Stove", "Oven"],
        ingredients=[I("egg", 4, "pcs"), I("tomato", 4, "pcs"), I("onion", 1, "pcs"),
                     I("bell pepper", 1, "pcs"), I("garlic", 2, "pcs"), I("cumin", 1, "tsp"),
                     I("paprika", 1, "tsp"), I("olive oil", 2, "tbsp"), I("salt", 0.5, "tsp")],
        steps=["Sauté onion, pepper and garlic in olive oil until soft.",
               "Add chopped tomatoes, cumin, paprika and salt; simmer 10 minutes.",
               "Make 4 wells and crack an egg into each.",
               "Cover and cook 5-7 minutes (or bake at 190°C) until the whites set."]),
    Recipe(
        name="Fattoush Salad", cuisine="Arabic", is_veg=True, prep_minutes=15, servings=2,
        meal_types=["Lunch", "Snacks"], nutrition_tags=["Low Calorie", "High Fiber"],
        appliances=[],
        ingredients=[I("tomato", 2, "pcs"), I("cucumber", 1, "pcs"), I("lettuce", 1, "pcs"),
                     I("green onion", 2, "pcs", True), I("mint", 0.5, "bunch", True),
                     I("lemon", 1, "pcs"), I("olive oil", 2, "tbsp"),
                     I("pita bread", 1, "pcs", True), I("salt", 0.25, "tsp")],
        steps=["Chop the vegetables and herbs into bite-sized pieces.",
               "Toast or fry the pita and break it into chips.",
               "Whisk lemon juice, olive oil and salt; toss everything just before serving."]),
    Recipe(
        name="Chicken Shawarma Bowl", cuisine="Arabic", is_veg=False, prep_minutes=40, servings=2,
        meal_types=["Lunch", "Dinner"], nutrition_tags=["High Protein"],
        appliances=["Oven", "Stove"],
        ingredients=[I("chicken", 400, "g"), I("yogurt", 100, "g"), I("garlic", 2, "pcs"),
                     I("lemon", 1, "pcs"), I("cumin", 1, "tsp"), I("paprika", 1, "tsp"),
                     I("cucumber", 1, "pcs"), I("tomato", 1, "pcs"),
                     I("rice", 150, "g", True), I("salt", 0.5, "tsp")],
        steps=["Marinate sliced chicken with yogurt, garlic, lemon, spices and salt (20 minutes).",
               "Roast at 220°C for 20 minutes or pan-fry until charred and cooked through.",
               "Serve over rice with chopped cucumber and tomato."]),
    Recipe(
        name="Mujaddara", cuisine="Arabic", is_veg=True, prep_minutes=45, servings=3,
        meal_types=["Lunch", "Dinner"], nutrition_tags=["High Fiber", "High Protein"],
        appliances=["Stove", "Rice Cooker"],
        ingredients=[I("lentils", 150, "g"), I("rice", 150, "g"), I("onion", 3, "pcs"),
                     I("cumin", 1, "tsp"), I("olive oil", 3, "tbsp"),
                     I("water", 700, "ml"), I("salt", 1, "tsp")],
        steps=["Boil the lentils for 15 minutes.",
               "Meanwhile fry sliced onions in olive oil until dark golden; keep half aside.",
               "Add rice, cumin, salt, the half-cooked lentils and water. Simmer covered 15 minutes.",
               "Top with the reserved crispy onions."]),

    # ------------------------------------------------------------------ ENGLISH
    Recipe(
        name="Scrambled Eggs on Toast", cuisine="English", is_veg=False, prep_minutes=10, servings=1,
        meal_types=["Breakfast", "Brunch"], nutrition_tags=["High Protein"],
        appliances=["Stove", "Microwave"],
        ingredients=[I("egg", 3, "pcs"), I("bread", 2, "pcs"), I("butter", 1, "tbsp"),
                     I("milk", 50, "ml", True), I("salt", 0.25, "tsp")],
        steps=["Whisk eggs with milk and salt.",
               "Melt butter on low heat, add eggs and stir gently until just set.",
               "(Microwave: cook in a bowl in 30-second bursts, stirring in between.)",
               "Serve on buttered toast."]),
    Recipe(
        name="Porridge with Fruit", cuisine="English", is_veg=True, prep_minutes=7, servings=1,
        meal_types=["Breakfast"], nutrition_tags=["High Fiber", "Balanced"],
        appliances=["Microwave", "Stove"],
        ingredients=[I("oats", 50, "g"), I("milk", 250, "ml"), I("banana", 1, "pcs", True),
                     I("honey", 1, "tbsp", True)],
        steps=["Mix oats and milk in a bowl or pan.",
               "Microwave 2-3 minutes (stir halfway) or simmer 5 minutes on the stove.",
               "Top with sliced banana and honey."]),
    Recipe(
        name="Jacket Potato with Beans", cuisine="English", is_veg=True, prep_minutes=45, servings=2,
        meal_types=["Lunch", "Dinner"], nutrition_tags=["Balanced", "High Fiber"],
        appliances=["Oven", "Microwave"],
        ingredients=[I("potato", 2, "pcs"), I("baked beans", 200, "g"), I("cheese", 50, "g"),
                     I("butter", 1, "tbsp", True)],
        steps=["Prick the potatoes with a fork.",
               "Bake at 200°C for 45 minutes, or microwave 8-10 minutes turning once.",
               "Heat the beans, split the potatoes, add butter, beans and grated cheese."]),
    Recipe(
        name="Tomato Soup", cuisine="English", is_veg=True, prep_minutes=30, servings=3,
        meal_types=["Lunch", "Dinner", "Snacks"], nutrition_tags=["Low Calorie"],
        appliances=["Stove"],
        ingredients=[I("tomato", 6, "pcs"), I("onion", 1, "pcs"), I("garlic", 2, "pcs"),
                     I("butter", 1, "tbsp"), I("milk", 100, "ml", True),
                     I("water", 300, "ml"), I("salt", 0.5, "tsp")],
        steps=["Sauté onion and garlic in butter until soft.",
               "Add chopped tomatoes, water and salt; simmer 20 minutes.",
               "Blend until smooth, stir in milk for creaminess."]),
    Recipe(
        name="Fruit & Yogurt Bowl", cuisine="English", is_veg=True, prep_minutes=5, servings=1,
        meal_types=["Breakfast", "Snacks"], nutrition_tags=["Low Calorie", "Balanced"],
        appliances=[],
        ingredients=[I("yogurt", 200, "g"), I("banana", 1, "pcs"), I("apple", 1, "pcs", True),
                     I("honey", 1, "tbsp", True), I("oats", 20, "g", True)],
        steps=["Spoon the yogurt into a bowl.",
               "Top with sliced fruit, oats and a drizzle of honey."]),
    Recipe(
        name="Cottage Pie", cuisine="English", is_veg=False, prep_minutes=60, servings=4,
        meal_types=["Dinner"], nutrition_tags=["High Protein"],
        appliances=["Oven"],
        ingredients=[I("minced meat", 500, "g"), I("potato", 4, "pcs"), I("onion", 1, "pcs"),
                     I("carrot", 1, "pcs"), I("peas", 50, "g", True), I("butter", 2, "tbsp"),
                     I("milk", 50, "ml"), I("salt", 1, "tsp")],
        steps=["Boil the potatoes and mash with butter, milk and salt.",
               "Brown the mince with onion and carrot, add peas and a splash of water.",
               "Put the mince in a dish, cover with mash, bake at 200°C for 25 minutes."]),
    Recipe(
        name="Cheese Toastie", cuisine="English", is_veg=True, prep_minutes=8, servings=1,
        meal_types=["Snacks", "Brunch"], nutrition_tags=["Balanced"],
        appliances=["Stove", "Oven"],
        ingredients=[I("bread", 2, "pcs"), I("cheese", 50, "g"), I("butter", 1, "tbsp"),
                     I("tomato", 1, "pcs", True)],
        steps=["Butter the outside of both bread slices.",
               "Fill with cheese (and tomato slices).",
               "Toast in a pan 2-3 minutes per side, or 8 minutes in a hot oven."]),
]

# ----------------------------------------------------------------------------------------------
# NUTRITION PER SERVING (approximate values: protein grams, carb grams, kilocalories).
# Kept in one table instead of inside every Recipe(...) above so the numbers are easy to review.
# ----------------------------------------------------------------------------------------------
NUTRITION = {
    "Masala Omelette": (20, 8, 290),
    "Vegetable Poha": (6, 48, 300),
    "Jeera Rice": (4, 45, 230),
    "Dal Tadka": (12, 30, 220),
    "Cucumber Raita": (5, 7, 90),
    "Paneer Bhurji": (19, 7, 290),
    "Chicken Curry": (30, 9, 340),
    "Aloo Tikki": (5, 42, 280),
    "Vegetable Pulao": (5, 50, 270),
    "Hummus": (8, 20, 210),
    "Shakshuka": (15, 12, 260),
    "Fattoush Salad": (4, 18, 170),
    "Chicken Shawarma Bowl": (42, 45, 520),
    "Mujaddara": (13, 50, 360),
    "Scrambled Eggs on Toast": (24, 28, 430),
    "Porridge with Fruit": (12, 60, 360),
    "Jacket Potato with Beans": (15, 70, 450),
    "Tomato Soup": (3, 15, 120),
    "Fruit & Yogurt Bowl": (11, 45, 280),
    "Cottage Pie": (28, 35, 480),
    "Cheese Toastie": (16, 30, 380),
}

# Give every built-in recipe its stable uid, its default picture and its nutrition numbers.
for _recipe in SEED_RECIPES:
    _recipe.uid = slugify(_recipe.name)                    # e.g. "dal-tadka"
    _recipe.image_path = f"asset:{_recipe.uid}.jpg"        # assets/recipe_images/dal-tadka.jpg
    _recipe.protein_g, _recipe.carbs_g, _recipe.calories = NUTRITION.get(_recipe.name, (0, 0, 0))
