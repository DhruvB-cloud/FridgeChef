"""
add_recipe_screen.py
--------------------
WHY THIS FILE EXISTS:
    "The user can also add their own recipe with an image and have it saved."
    This screen is a form: name, cuisine, veg/non-veg, time, servings, nutrition numbers, meal types,
    nutrition tags, cooking machines, ingredient rows (with type-ahead suggestions) and steps, plus
    a photo. If no photo is chosen, a soft default picture is generated - so every recipe has one.
    On Save it stores the recipe in SQLite with is_user=True and is_saved=True (-> Cookbook tab).
"""

import os
import uuid

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.stacklayout import StackLayout       # wraps chips onto new lines when out of space

from app.images import make_default_image
from app.models import APPLIANCES, CUISINES, MEAL_TYPES, NUTRITION_TAGS, Ingredient, Recipe
from app.units import UNIT_CHOICES
from app.ui.autocomplete import AutoCompleteInput
from app.ui.easter_egg import is_love, play_hearts   # the "love" surprise
from app.ui.image_picker import import_image, pick_image
from app.ui.widgets import (DANGER, DANGER_SOFT, INK, MUTED, NEUTRAL, Card, Header, RoundImage,
                            SoftButton, SoftInput, SoftSpinner, SoftToggle, WrapLabel, escape,
                            labeled, scroll_list, section_title, show_message)


class ChipGroup(StackLayout):
    """A wrap-around row of rounded toggle 'chips' for multi-select (e.g. meal types)."""

    def __init__(self, options, **kwargs):
        super().__init__(size_hint_y=None, spacing=dp(8), **kwargs)
        self.bind(minimum_height=self.setter("height"))   # grow when chips wrap to a new line
        self.buttons = []
        for option in options:
            btn = SoftToggle(option, size_hint=(None, None), height=dp(38),
                             width=dp(28 + 8 * len(option)))   # rough width from the text length
            self.buttons.append(btn)
            self.add_widget(btn)

    def selected(self):
        """Names of all pressed chips."""
        return [b.text for b in self.buttons if b.state == "down"]

    def clear(self):
        for b in self.buttons:
            b.state = "normal"


class IngredientRow(BoxLayout):
    """One editable ingredient line: name (with suggestions) | qty | unit | optional | remove."""

    def __init__(self, on_remove, known_names, **kwargs):
        super().__init__(size_hint_y=None, height=dp(44), spacing=dp(6), **kwargs)
        self.name_in = AutoCompleteInput(hint_text="Ingredient", size_hint_x=0.4, height=dp(44),
                                         extra_names=known_names, on_pick=self._picked)
        self.qty_in = SoftInput(hint_text="Qty", input_filter="float", size_hint_x=0.17, height=dp(44))
        self.unit_in = SoftSpinner(text="g", values=UNIT_CHOICES, size_hint_x=0.18, height=dp(44))
        self.optional = SoftToggle("opt", size_hint_x=0.13, height=dp(44), font_size=sp(13))
        for widget in (self.name_in, self.qty_in, self.unit_in, self.optional):
            self.add_widget(widget)
        self.add_widget(SoftButton("x", bg=DANGER_SOFT, fg=DANGER, size_hint_x=0.12, height=dp(44),
                                   on_release=lambda *_: on_remove(self)))

    def _picked(self, _name, info):
        """Suggestion chosen -> use its usual unit and jump to the quantity box."""
        if info:
            self.unit_in.text = info[0]
        self.qty_in.focus = True

    def to_ingredient(self):
        """Return an Ingredient, None for a blank row, or raise ValueError for bad input."""
        name = self.name_in.text.strip()
        if not name:
            return None                                   # blank rows are simply ignored
        try:
            qty = float(self.qty_in.text)
        except ValueError:
            raise ValueError(f"Enter a quantity for '{name}'.")
        if qty <= 0:
            raise ValueError(f"Quantity for '{name}' must be greater than 0.")
        return Ingredient(name=name, quantity=qty, unit=self.unit_in.text,
                          optional=self.optional.state == "down")


class AddRecipeScreen(Screen):
    """The 'create your own recipe' form."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.image_path = None                            # path of the imported photo, if any
        root = BoxLayout(orientation="vertical")
        root.add_widget(Header("New recipe", "Add your own dish", on_back=self.app.go_back))
        scroll, form = scroll_list(spacing=dp(14), padding=(dp(16), dp(4), dp(16), dp(20)))

        # --- photo first: it makes the form feel friendly
        photo_card = Card()
        self.preview = RoundImage(None, radius=dp(18), size_hint_y=None, height=dp(170))
        photo_card.add_widget(self.preview)
        self.photo_hint = WrapLabel(text="No photo yet - a soft picture is created automatically.",
                                    color=MUTED, font_size=sp(13), halign="center")
        photo_card.add_widget(self.photo_hint)
        photo_card.add_widget(SoftButton("Choose photo", bg=NEUTRAL, fg=INK,
                                         on_release=lambda *_: pick_image(self._photo_picked)))
        form.add_widget(photo_card)

        # --- basic info
        basics = Card(spacing=dp(10))
        self.name_in = SoftInput(hint_text="e.g. Mum's Rajma")
        basics.add_widget(labeled("Dish name", self.name_in))
        grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        self.cuisine = SoftSpinner(text=CUISINES[0], values=CUISINES)
        self.diet = SoftSpinner(text="Veg", values=["Veg", "Non-Veg"])
        self.minutes = SoftInput(text="20", input_filter="int")
        self.servings = SoftInput(text="1", input_filter="int")      # default: 1 person
        self.protein = SoftInput(hint_text="optional", input_filter="float")
        self.carbs = SoftInput(hint_text="optional", input_filter="float")
        self.calories = SoftInput(hint_text="optional", input_filter="float")
        for caption, widget in (("Cuisine", self.cuisine), ("Type", self.diet),
                                ("Prep time (minutes)", self.minutes), ("Servings", self.servings),
                                ("Protein per serving (g)", self.protein),
                                ("Carbs per serving (g)", self.carbs),
                                ("Calories per serving", self.calories)):
            grid.add_widget(labeled(caption, widget))
        basics.add_widget(grid)
        form.add_widget(basics)

        # --- multi-select chips
        chips = Card(spacing=dp(10))
        chips.add_widget(section_title("When is it eaten?", 16))
        self.meal_chips = ChipGroup(MEAL_TYPES)
        chips.add_widget(self.meal_chips)
        chips.add_widget(section_title("Nutrition", 16))
        self.nutrition_chips = ChipGroup(NUTRITION_TAGS)
        chips.add_widget(self.nutrition_chips)
        chips.add_widget(section_title("Can be cooked with (any of)", 16))
        chips.add_widget(WrapLabel(text="Leave empty if no cooking machine is needed.",
                                   color=MUTED, font_size=sp(13)))
        self.appliance_chips = ChipGroup(APPLIANCES)
        chips.add_widget(self.appliance_chips)
        form.add_widget(chips)

        # --- ingredients (rows can be added / removed)
        ing_card = Card(spacing=dp(10))
        ing_card.add_widget(section_title("Ingredients", 16))
        ing_card.add_widget(WrapLabel(text="Start typing for suggestions. Tap 'opt' for optional items.",
                                      color=MUTED, font_size=sp(13)))
        self.ing_rows = GridLayout(cols=1, spacing=dp(8), size_hint_y=None)
        self.ing_rows.bind(minimum_height=self.ing_rows.setter("height"))
        ing_card.add_widget(self.ing_rows)
        ing_card.add_widget(SoftButton("+  Add ingredient", bg=NEUTRAL, fg=INK,
                                       on_release=lambda *_: self._add_ing_row()))
        form.add_widget(ing_card)

        # --- steps
        steps_card = Card(spacing=dp(10))
        steps_card.add_widget(section_title("Steps (one per line)", 16))
        self.steps_in = SoftInput(multiline=True, height=dp(160),
                                  hint_text="Chop the onions\nFry in oil until golden\n...")
        steps_card.add_widget(self.steps_in)
        form.add_widget(steps_card)

        self.error = WrapLabel(text="", color=DANGER)
        form.add_widget(self.error)
        form.add_widget(SoftButton("Save recipe", height=dp(52), on_release=lambda *_: self._save()))

        root.add_widget(scroll)
        self.add_widget(root)
        self.reset()

    # ------------------------------------------------------------------ helpers
    def on_pre_enter(self, *_):
        # Refresh the suggestion lists with any new names the user typed elsewhere.
        names = self.app.db.ingredient_names()
        for row in self.ing_rows.children:
            row.name_in.extra_names = names

    def on_pre_leave(self, *_):
        """Leaving the screen: close any open suggestion list so it can't float over other screens."""
        for row in self.ing_rows.children:
            row.name_in.close_suggestions()

    def reset(self):
        """Clear the form (called after saving, and when opened fresh)."""
        self.name_in.text = ""
        self.minutes.text, self.servings.text = "20", "1"
        for box in (self.protein, self.carbs, self.calories, self.steps_in):
            box.text = ""
        self.error.text = ""
        for group in (self.meal_chips, self.nutrition_chips, self.appliance_chips):
            group.clear()
        self.ing_rows.clear_widgets()
        for _ in range(3):                                # start with 3 empty ingredient rows
            self._add_ing_row()
        self.image_path = None
        self.preview.set_source(None)
        self.photo_hint.text = "No photo yet - a soft picture is created automatically."

    def _add_ing_row(self):
        self.ing_rows.add_widget(IngredientRow(on_remove=self.ing_rows.remove_widget,
                                               known_names=self.app.db.ingredient_names()))

    def _photo_picked(self, path):
        """Copy the chosen photo into the app folder and show a preview."""
        try:
            self.image_path = import_image(path, self.app.images_dir)
        except Exception as error:                        # not an image, or unreadable
            show_message("Photo problem", f"Could not use this file:\n{escape(error)}")
            return
        self.preview.set_source(self.image_path)
        self.photo_hint.text = "Looks delicious!"

    @staticmethod
    def _number(box):
        """Optional number box -> float (empty = 0)."""
        return float(box.text) if box.text.strip() else 0.0

    def _save(self):
        """Validate everything and store the recipe."""
        name = self.name_in.text.strip()
        if not name:
            self.error.text = "Please give your dish a name."
            return
        # Easter egg - checked BEFORE the quantity checks, so "love" needs no quantity.
        love_rows = [row for row in self.ing_rows.children if is_love(row.name_in.text)]
        if love_rows:
            for row in love_rows:                         # "love" is never added as an ingredient...
                row.name_in.text, row.qty_in.text = "", ""   # ...its row is simply emptied
            play_hearts()                                 # ...and the hearts fly instead
            return                                        # the user can now finish and save normally
        try:
            minutes = int(self.minutes.text or 0)
            servings = int(self.servings.text or 0)
            if minutes <= 0 or servings <= 0:
                raise ValueError("Prep time and servings must be greater than 0.")
            protein, carbs, calories = (self._number(b) for b in (self.protein, self.carbs, self.calories))
            # Rows are added top-to-bottom but Kivy stores children newest-first, so reverse.
            ingredients = [ing for row in reversed(self.ing_rows.children)
                           if (ing := row.to_ingredient()) is not None]   # ':=' assigns and tests
        except ValueError as error:
            self.error.text = str(error)
            return
        if not ingredients:
            self.error.text = "Add at least one ingredient."
            return
        steps = [line.strip() for line in self.steps_in.text.splitlines() if line.strip()]
        if not steps:
            self.error.text = "Add at least one step."
            return
        image = self.image_path
        if image is None:                                 # every recipe gets a picture
            image = make_default_image(name, os.path.join(self.app.images_dir, f"{uuid.uuid4().hex}.jpg"))
        recipe = Recipe(
            name=name, cuisine=self.cuisine.text, is_veg=self.diet.text == "Veg",
            prep_minutes=minutes, servings=servings, ingredients=ingredients, steps=steps,
            meal_types=self.meal_chips.selected() or list(MEAL_TYPES),   # none picked = any time
            nutrition_tags=self.nutrition_chips.selected(),
            appliances=self.appliance_chips.selected(),
            protein_g=protein, carbs_g=carbs, calories=calories,
            image_path=image, is_user=True, is_saved=True,
        )
        recipe_id = self.app.db.add_recipe(recipe)
        self.reset()
        self.app.open_recipe(recipe_id, replace=True)     # show the new recipe straight away
