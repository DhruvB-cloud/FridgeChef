"""
recipe_detail_screen.py
-----------------------
WHY THIS FILE EXISTS:
    Shows one recipe and runs the "cook it" flow:
      1. Big rounded photo, chips (veg, cuisine, time), and protein / carbs / calories boxes.
      2. Servings start at the user's default (1 person unless changed in Profile); the
         ingredient amounts and the have/missing check follow the chosen servings.
      3. "Start cooking" -> each step gets a tick box.
      4. "Finished - update fridge" shows exactly what will be subtracted; after confirming, the
         fridge is updated AND the dish is written to the cooking history - which feeds the
         Calendar, the streak and the favourite dish on the Profile tab.
    It also has "Save" (Cookbook), "Share card" (image) and "Delete" for the user's own recipes.
"""

import os
from datetime import datetime                      # time stamp in share card file names

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from app.images import resolve_image
from app.recipe_card import create_recipe_card
from app.recipe_engine import build_pantry_index, match_recipe, plan_deduction
from app.share import share_image
from app.ui.cooked_popup import show_cooked_popup   # the "Yay!" message after cooking
from app.stats import current_streak
from app.units import pretty_quantity
from app.ui.widgets import (BLUE, BLUE_SOFT, DANGER, DANGER_SOFT, HEX_AMBER, HEX_GREY, INK, MUTED,
                            NEUTRAL, PEACH_SOFT, PRIMARY, PRIMARY_DARK, PRIMARY_SOFT, WHITE, Card,
                            Chip, ChipRow, Header, RoundImage, SoftButton, WrapLabel, colored,
                            confirm, diet_chip, escape, icon_image, recipe_status_lines,
                            scroll_list, section_title, show_message)


def remove_old_cards(folder, keep=5):
    """Delete all but the newest `keep` share cards, so the folder doesn't grow forever.

    A card that is still open in another program (e.g. Windows Photos) can't be deleted -
    that's fine, it is simply skipped and removed on a later share.
    """
    try:
        cards = sorted((os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".png")),
                       key=os.path.getmtime, reverse=True)   # newest first
    except OSError:                                    # folder missing/unreadable: nothing to tidy
        return
    for old in cards[keep:]:                           # everything after the newest few
        try:
            os.remove(old)
        except OSError:                                # still open somewhere -> try again next time
            pass


def stat_box(icon_name, value, label, bg):
    """One small rounded box: icon, big number, caption (e.g. muscle / 20 g / protein)."""
    box = Card(color=bg, shadow=False, padding=dp(8), spacing=dp(2), radius=dp(18))
    box.add_widget(BoxLayout(size_hint_y=None, height=dp(30)))       # spacer row for the icon
    box.children[0].add_widget(BoxLayout())
    box.children[0].add_widget(icon_image(icon_name, dp(28)))
    box.children[0].add_widget(BoxLayout())
    box.add_widget(Label(text=f"[b]{value}[/b]", markup=True, color=INK, font_size=sp(17),
                         size_hint_y=None, height=dp(24)))
    box.add_widget(Label(text=label, color=MUTED, font_size=sp(12), size_hint_y=None, height=dp(18)))
    return box


class RecipeDetailScreen(Screen):
    """One recipe, full details."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.recipe_id = None          # which recipe is displayed (local id)
        self.servings = None           # chosen servings (None = user's default)
        self.cooking = False           # True while in cooking mode
        self.done_steps = set()        # step numbers ticked in cooking mode
        root = BoxLayout(orientation="vertical")
        self.header = Header("", on_back=self.app.go_back)
        root.add_widget(self.header)
        scroll, self.content = scroll_list(spacing=dp(14), padding=(dp(16), dp(4), dp(16), dp(16)))
        root.add_widget(scroll)
        # Bottom action bar - its buttons change between normal mode and cooking mode.
        self.actions = BoxLayout(size_hint_y=None, height=dp(62), padding=(dp(16), dp(8)), spacing=dp(8))
        root.add_widget(self.actions)
        self.add_widget(root)

    def show(self, recipe_id):
        """Called by the app before switching to this screen."""
        self.recipe_id = recipe_id
        self.servings = None
        self.cooking = False
        self.done_steps = set()

    def on_pre_enter(self, *_):
        self.refresh()

    # ------------------------------------------------------------------ drawing
    def refresh(self):
        db = self.app.db
        recipe = db.get_recipe(self.recipe_id)
        if recipe is None:                                 # deleted meanwhile -> leave
            self.app.go_back()
            return
        self.recipe = recipe
        servings = self.servings or db.default_servings()  # default: 1 person
        self.current_servings = servings
        match = match_recipe(recipe, build_pantry_index(db.list_pantry()), db.owned_appliances(), servings)
        scale = servings / recipe.servings                 # to show scaled ingredient amounts
        self.header.set_title(recipe.name)
        self.header.set_subtitle(f"{recipe.cuisine} • {recipe.prep_minutes} min")
        c = self.content
        c.clear_widgets()

        # --- photo (every recipe has one: bundled, downloaded, own photo or generated)
        c.add_widget(RoundImage(resolve_image(recipe.image_path), radius=dp(26),
                                size_hint_y=None, height=dp(210)))

        # --- chips
        chips = [diet_chip(recipe.is_veg), Chip(recipe.cuisine, BLUE_SOFT, BLUE),
                 Chip(f"{recipe.prep_minutes} min", NEUTRAL, INK)]
        chips += [Chip(t, PEACH_SOFT, (0.70, 0.40, 0.28, 1)) for t in recipe.nutrition_tags]
        c.add_widget(ChipRow(chips))

        # --- nutrition boxes (per person)
        if recipe.protein_g or recipe.carbs_g or recipe.calories:
            row = BoxLayout(size_hint_y=None, height=dp(98), spacing=dp(10))
            row.add_widget(stat_box("muscle", f"{recipe.protein_g:g} g", "protein", PEACH_SOFT))
            row.add_widget(stat_box("grain", f"{recipe.carbs_g:g} g", "carbs", (1, 0.96, 0.86, 1)))
            row.add_widget(stat_box("bolt", f"{recipe.calories:g}", "kcal", BLUE_SOFT))
            c.add_widget(row)
            c.add_widget(WrapLabel(text="Nutrition per person (approximate)", color=MUTED,
                                   font_size=sp(12), halign="center"))

        # --- status (ready / missing / use today)
        status = Card(spacing=dp(4))
        machines = " or ".join(recipe.appliances) if recipe.appliances else "no cooking machine needed"
        status.add_widget(WrapLabel(text=f"Cook with: {escape(machines)}", color=MUTED, font_size=sp(13)))
        for line in recipe_status_lines(match):
            status.add_widget(WrapLabel(text=line))
        c.add_widget(status)

        # --- servings stepper:  ( - )  Cooking for 1 person  ( + )
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        row.add_widget(SoftButton("-", size_hint=(None, None), size=(dp(48), dp(48)), bg=NEUTRAL,
                                  fg=INK, font_size=sp(20), on_release=lambda *_: self._change_servings(-1)))
        people = "1 person" if servings == 1 else f"{servings} people"
        row.add_widget(Label(text=f"Cooking for [b]{people}[/b]", markup=True, color=INK, font_size=sp(16)))
        row.add_widget(SoftButton("+", size_hint=(None, None), size=(dp(48), dp(48)), bg=NEUTRAL,
                                  fg=INK, font_size=sp(20), on_release=lambda *_: self._change_servings(+1)))
        c.add_widget(row)

        # --- ingredients with have / missing chips
        ing_card = Card(spacing=dp(8))
        ing_card.add_widget(section_title("Ingredients"))
        have = {id(i) for i in match.have}                 # id() = identity of each Ingredient object
        for ing in recipe.ingredients:
            line = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
            amount = pretty_quantity(ing.quantity * scale, ing.unit)
            line.add_widget(WrapLabel(text=f"{escape(ing.name)}  [color=8a8f93]{amount}[/color]",
                                      shorten=True, max_lines=1))
            if id(ing) in have:
                chip = Chip("have", PRIMARY_SOFT, PRIMARY_DARK)
            elif ing.optional:
                chip = Chip("optional", NEUTRAL, MUTED)
            else:
                chip = Chip("missing", DANGER_SOFT, DANGER)
            chip.pos_hint = {"center_y": 0.5}
            line.add_widget(chip)
            ing_card.add_widget(line)
        c.add_widget(ing_card)

        # --- steps (with tick boxes in cooking mode)
        steps_card = Card(spacing=dp(8))
        steps_card.add_widget(section_title("Cooking mode - tick each step" if self.cooking else "Method"))
        for num, step in enumerate(recipe.steps, start=1):
            if self.cooking:
                steps_card.add_widget(self._step_row(num, step))
            else:
                steps_card.add_widget(WrapLabel(text=f"[b]{num}.[/b]  {escape(step)}"))
        c.add_widget(steps_card)

        # --- delete button only for the user's own recipes
        if recipe.is_user and not self.cooking:
            c.add_widget(SoftButton("Delete this recipe", bg=DANGER_SOFT, fg=DANGER,
                                    on_release=lambda *_: self._delete()))

        self._build_actions(recipe, match)

    def _step_row(self, num, step):
        """A step with a checkbox; ticked steps turn grey."""
        row = BoxLayout(size_hint_y=None, spacing=dp(6))
        box = CheckBox(active=num in self.done_steps, size_hint=(None, None), size=(dp(36), dp(36)),
                       color=PRIMARY)
        hex_color = HEX_GREY if num in self.done_steps else "33383b"
        label = WrapLabel(text=colored(f"{num}. {step}", hex_color))
        label.bind(height=lambda l, h: setattr(row, "height", max(h, dp(36))))   # row follows label

        def _toggle(_cb, active):
            if active:
                self.done_steps.add(num)
            else:
                self.done_steps.discard(num)
            label.text = colored(f"{num}. {step}", HEX_GREY if active else "33383b")
        box.bind(active=_toggle)
        row.add_widget(box)
        row.add_widget(label)
        return row

    def _build_actions(self, recipe, match):
        """Fill the bottom bar with the right buttons for the current mode."""
        a = self.actions
        a.clear_widgets()
        if self.cooking:
            a.add_widget(SoftButton("Cancel", bg=NEUTRAL, fg=INK, size_hint_x=0.4,
                                    on_release=lambda *_: self._set_cooking(False)))
            a.add_widget(SoftButton("Finished - update fridge",
                                    on_release=lambda *_: self._finish_cooking()))
            return
        a.add_widget(SoftButton("Saved" if recipe.is_saved else "Save",
                                bg=PRIMARY_SOFT if recipe.is_saved else NEUTRAL,
                                fg=PRIMARY_DARK if recipe.is_saved else INK,
                                on_release=lambda *_: self._toggle_saved()))
        a.add_widget(SoftButton("Share", bg=BLUE_SOFT, fg=BLUE, on_release=lambda *_: self._share()))
        a.add_widget(SoftButton("Start cooking", bg=PRIMARY, fg=WHITE, size_hint_x=1.4,
                                on_release=lambda *_: self._start_cooking(match)))

    # ------------------------------------------------------------------ actions
    def _change_servings(self, delta):
        self.servings = max(1, min(20, self.current_servings + delta))   # keep between 1 and 20
        self.refresh()

    def _toggle_saved(self):
        self.app.db.set_saved(self.recipe.id, not self.recipe.is_saved)
        self.refresh()

    def _share(self):
        """Create the PNG card and hand it to the share sheet / image viewer."""
        # A NEW file name every time (date + time). Reusing one name failed with "[Errno 22] Invalid
        # argument" on Windows: the previous card was still open in the Photos app, and Windows
        # does not allow overwriting a file that another program has open.
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")  # e.g. 20261004-191530-123456 (unique even for quick taps)
        path = os.path.join(self.app.cards_dir, f"recipe_card_{self.recipe.id}_{stamp}.png")
        remove_old_cards(self.app.cards_dir)                # tidy up earlier cards (skips open ones)
        try:
            create_recipe_card(self.recipe, path, image_file=resolve_image(self.recipe.image_path))
        except Exception as error:
            show_message("Could not create card", escape(str(error)))
            return
        message = share_image(path, text=f"{self.recipe.name} - shared from FridgeChef")
        if "saved to" in message:                          # desktop: tell the user where it is
            show_message("Recipe card", escape(message))

    def _start_cooking(self, match):
        if match.missing:                                  # warn but let the user decide
            names = ", ".join(i.name for i in match.missing)
            confirm("Missing ingredients", f"You are missing: {escape(names)}.\nCook anyway?",
                    lambda: self._set_cooking(True), yes_text="Cook anyway")
        else:
            self._set_cooking(True)

    def _set_cooking(self, value):
        self.cooking = value
        self.done_steps = set()
        self.refresh()

    def _finish_cooking(self):
        """Show what will be subtracted, then update the fridge after confirmation."""
        db = self.app.db
        servings = self.current_servings
        pantry = db.list_pantry()
        by_id = {item.id: item for item in pantry}         # quick lookup for the summary text
        changes, warnings = plan_deduction(self.recipe, pantry, servings)
        lines = []
        for item_id, new_qty in changes:
            item = by_id[item_id]
            after = "used up" if new_qty <= 1e-9 else pretty_quantity(new_qty, item.unit)
            lines.append(f"• {escape(item.name)}: {pretty_quantity(item.quantity, item.unit)} -> {after}")
        for w in warnings:
            lines.append(colored(w, HEX_AMBER))
        summary = "\n".join(lines) or "Nothing to subtract (no tracked ingredients used)."

        def _apply():
            db.apply_deductions(changes)                   # update / delete pantry rows
            log_id = db.log_cooked(self.recipe.id, servings, self.recipe.name)   # Calendar + streak
            streak, _ = current_streak(db.cooked_days())
            self.cooking = False
            self.refresh()
            # "Yay!" popup with confetti and an option to add a photo for the Calendar.
            show_cooked_popup(self.app, self.recipe.name, log_id, streak, summary)
        confirm("Update fridge?", f"These amounts will be removed:\n\n{summary}", _apply,
                yes_text="Update fridge", height=dp(420))

    def _delete(self):
        def _do():
            path = self.recipe.image_path
            if path and not path.startswith("asset:") and os.path.exists(path):
                try:
                    os.remove(path)                        # free the space used by the photo
                except OSError:
                    pass
            self.app.db.delete_recipe(self.recipe.id)
            self.app.go_back()
        confirm("Delete recipe", f"Delete '{escape(self.recipe.name)}' permanently?", _do,
                yes_text="Delete", yes_color=DANGER, height=dp(230))
