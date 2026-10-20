"""
recipes_screen.py
-----------------
WHY THIS FILE EXISTS:
    The "Recipes" tab. Version 5.0 (testers wanted a simpler app) merged the old Recipes and
    Cookbook tabs into ONE list:
      * three chips at the top, plus a search box:
          Available   - dishes you can cook right now, sorted by meal time: "Recommended for
                        <meal>" first, then dishes for the next meals of the day
          Unavailable - dishes that still miss an ingredient (fewest missing first)
          Saved       - dishes you saved AND your own recipes (+ New recipe)
      * every recipe is one row: its photo on the left, name, cooking time and cuisine on the
        right, and one coloured badge (Ready to cook / Missing 2 / Use today / Needs Oven);
      * no filter panel. Available / Unavailable only show dishes your cooking machines can make.

    All matching happens on the phone (app/recipe_engine.py). Once a day app/catalog.py downloads
    the published recipe catalogue and saves new / changed recipes; the status chip shows
    "Up to date" after a successful check, else "Offline" (the saved recipes keep working).
"""

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ToggleButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from app.catalog import apply_catalog, sync_if_due
from app.dates import short_minutes
from app.expiry import expiring_today
from app.meal_time import current_meal
from app.models import MEAL_TYPES, SORT_OPTIONS
from app.recipe_engine import filter_matches, match_all
from app.ui.widgets import (AMBER, AMBER_SOFT, DANGER_SOFT, HEX_RED, INK, MUTED, NEUTRAL,
                            PRIMARY_DARK, PRIMARY_SOFT, STATUS_BADGE, WHITE, Card, Chip, Header, Pill,
                            SoftButton, SoftInput, TapCard, WrapLabel, bg_rect, colored, recipe_picture,
                            scroll_list, thumb_status)

# The three views of the list: (key, label, colour of the chip when selected).
VIEWS = [("available", "Available", (0.20, 0.64, 0.46, 1)),    # emerald
         ("unavailable", "Unavailable", (0.98, 0.55, 0.24, 1)),   # warm orange
         ("saved", "Saved", (0.91, 0.36, 0.48, 1))]               # raspberry (saved + your own)
ROW_HEIGHT = dp(104)
# A colour per cuisine (hex text for Kivy markup) - small touches of colour that blend with the badges.
CUISINE_COLORS = {"Indian": "b9561a", "Arabic": "86650f", "English": "3b62b4", "Italian": "2d7b45",
                  "Asian": "bb3448", "Mexican": "7a46b8"}      # 5.0 QA: dark enough to read as small text
SAVED_PILL = ((1, 0.90, 0.93, 1), (0.85, 0.27, 0.42, 1))   # soft pink badge, raspberry text


def meal_rank(recipe, meal):
    """0 if the recipe is for `meal`, 1 if for the next meal of the day, ... (wrapping round).

    E.g. at Lunch: a lunch dish -> 0, a snack -> 1, a dinner dish -> 2, breakfast -> 3.
    """
    start = MEAL_TYPES.index(meal) if meal in MEAL_TYPES else 0
    ranks = [(MEAL_TYPES.index(m) - start) % len(MEAL_TYPES) for m in recipe.meal_types if m in MEAL_TYPES]
    return min(ranks) if ranks else len(MEAL_TYPES)        # no meal type at all -> last


def unavailable_rank(match):
    """Sort key for Unavailable: fewer missing ingredients first, then 'uses food expiring today/soon'."""
    return (len(match.missing), not match.uses_expiring_today, not match.uses_expiring_soon)


class ViewChip(ToggleButtonBehavior, Label):
    """One of the Available / Unavailable / Saved chips: white when off, filled with its colour when on."""

    def __init__(self, key, text, color, **kwargs):
        super().__init__(text=text, bold=True, font_size=sp(14), size_hint=(None, None),
                         height=dp(38), group="recipe_views", allow_no_selection=False, **kwargs)
        self.key, self.label_text, self.on_color = key, text, color
        bg_rect(self, WHITE, radius=dp(19))                # sets self._bg_color (see widgets.bg_rect)
        self.bind(state=self._restyle,
                  texture_size=lambda *_: setattr(self, "width", self.texture_size[0] + dp(30)))
        self._restyle()

    def set_count(self, count):
        self.text = f"{self.label_text}  {count}"           # e.g. "Saved  4"

    def _restyle(self, *_):
        on = self.state == "down"
        self._bg_color.rgba = self.on_color if on else WHITE   # filled when selected
        self.color = WHITE if on else INK


class RecipeRow(TapCard):
    """One recipe in the list: photo on the left; name, time + cuisine and badges on the right."""

    def __init__(self, match, on_open, **kwargs):
        super().__init__(orientation="horizontal", padding=dp(10), spacing=dp(12), radius=dp(22), **kwargs)
        recipe = match.recipe
        holder = BoxLayout(size_hint=(None, None), size=(dp(84), dp(84)), pos_hint={"center_y": 0.5})
        holder.add_widget(recipe_picture(recipe, small=True, radius=dp(18)))   # photo, or a coloured letter
        self.add_widget(holder)

        text = BoxLayout(orientation="vertical", spacing=dp(2), size_hint_y=None, height=dp(84),
                         pos_hint={"center_y": 0.5})
        name = Label(text=recipe.name, bold=True, color=INK, font_size=sp(16), halign="left",
                     valign="top", max_lines=2, shorten=True, shorten_from="right")
        name.bind(size=lambda l, sz: setattr(l, "text_size", sz))
        text.add_widget(name)
        cuisine_hex = CUISINE_COLORS.get(recipe.cuisine, "656b70")   # every cuisine has its own colour
        meta = Label(text=f"{short_minutes(recipe.prep_minutes)}  •  [color={cuisine_hex}][b]{recipe.cuisine}[/b][/color]",
                     markup=True, color=MUTED, font_size=sp(13), halign="left", valign="middle",
                     size_hint_y=None, height=dp(20))
        meta.bind(size=lambda l, sz: setattr(l, "text_size", sz))
        text.add_widget(meta)
        badges = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(6))
        status, hex_color = thumb_status(match)
        badges.add_widget(Pill(status, *STATUS_BADGE[hex_color], font_size=sp(11.5)))
        if recipe.is_saved:                                # a pink badge for saved dishes
            badges.add_widget(Pill("Saved", *SAVED_PILL, font_size=sp(11.5)))
        badges.add_widget(Widget())                        # keeps the badges on the left
        text.add_widget(badges)
        self.add_widget(text)
        self.bind(on_tap=lambda *_: on_open(recipe.id))     # real taps only, never swipes (4.7.1)


class RecipesScreen(Screen):
    """The Recipes tab."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.view = "available"          # which chip is selected
        self.state = None                # last results, see _apply_local
        # A "trigger" runs refresh() once, 0.35 s after the LAST call - so typing "paneer" refreshes
        # once instead of six times.
        self.refresh_soon = Clock.create_trigger(lambda dt: self.refresh(), 0.35)

        root = BoxLayout(orientation="vertical")
        self.header = Header("Recipes", "Finding recipes for your fridge...", icon="tab_recipes")
        self.status_chip = Chip("...", NEUTRAL, MUTED)
        self.header.set_right(self.status_chip, dp(92))
        root.add_widget(self.header)
        body = BoxLayout(orientation="vertical", padding=(dp(16), 0, dp(16), dp(6)), spacing=dp(10))

        self.search = SoftInput(hint_text="Search 100+ recipes...", rule="name", height=dp(48))
        self.search.bind(text=lambda *_: self.refresh_soon())
        body.add_widget(self.search)

        # The chips may not all fit a small phone: they sit in a sideways-scrolling row.
        chip_scroll = ScrollView(do_scroll_y=False, size_hint_y=None, height=dp(40), bar_width=0)
        chips = BoxLayout(size_hint_x=None, spacing=dp(8))
        chips.bind(minimum_width=chips.setter("width"))
        chip_scroll.add_widget(chips)
        self.chips = {}
        for key, text, color in VIEWS:
            chip = ViewChip(key, text, color, state="down" if key == self.view else "normal")
            chip.bind(state=lambda c, state: self._pick_view(c.key) if state == "down" else None)
            self.chips[key] = chip
            chips.add_widget(chip)
        body.add_widget(chip_scroll)

        self.banner = BoxLayout(orientation="vertical", size_hint_y=None, height=0)   # "Use today" note
        self.banner.bind(minimum_height=self.banner.setter("height"))
        body.add_widget(self.banner)

        self.scroll, self.list = scroll_list(spacing=dp(10), padding=(dp(2), dp(4), dp(2), dp(12)))
        body.add_widget(self.scroll)
        root.add_widget(body)
        self.add_widget(root)

    # ------------------------------------------------------------------ loading data
    def on_pre_enter(self, *_):
        self.refresh()

    def _pick_view(self, key):
        self.view = key
        self.refresh()

    def refresh(self):
        """Match all saved recipes on the phone (instant) and, once a day, check for new recipes."""
        db = self.app.db
        pantry = db.list_pantry()
        self._show_banner(pantry)
        # Once a day: look for new recipes in the background (see app/catalog.py).
        checking = sync_if_due(db, lambda update, ok: Clock.schedule_once(   # back to the UI thread
            lambda dt: self._catalog_checked(update, ok)))
        if checking:
            self._set_status("Checking", NEUTRAL, MUTED)
        elif self.status_chip.text == "...":             # today's check already succeeded earlier
            self._set_status("Up to date", PRIMARY_SOFT, PRIMARY_DARK)
        self._apply_local(pantry)

    def _catalog_checked(self, update, ok):
        """The daily catalogue check finished (runs on the UI thread)."""
        if not ok:
            self._set_status("Offline", AMBER_SOFT, AMBER)   # the saved recipes still work
            return
        apply_catalog(self.app.db, update)               # save new / changed recipes (if any)
        self._set_status("Up to date", PRIMARY_SOFT, PRIMARY_DARK)
        if update and self.app.sm.current == "recipes":  # new recipes arrived -> show them
            self.refresh()

    def _apply_local(self, pantry):
        """Match every saved recipe (catalogue + your own) on this phone, then draw the list."""
        db = self.app.db
        servings = db.default_servings()
        matches = match_all(db.list_recipes(), pantry, db.owned_appliances(), servings=servings)
        search = self.search.text.strip()
        usable = [m for m in matches if m.appliance_ok]    # your machines can cook these
        views = {
            "available": [m for m in usable if not m.missing],   # every required ingredient is in the fridge
            "unavailable": [m for m in usable if m.missing],
            "saved": [m for m in matches if m.recipe.is_saved or m.recipe.is_user],   # + your own recipes
        }
        for key, chip in self.chips.items():
            chip.set_count(len(views[key]))
        results = filter_matches(views[self.view], search=search, sort=SORT_OPTIONS[0])   # longest first
        if self.view == "unavailable":
            # Fewest missing ingredients first; among equals, dishes that use food expiring soon.
            # (QA 5.0: "Best match" put expiring-food dishes first even when they missed 5 things.)
            results.sort(key=unavailable_rank)
        meal = current_meal()
        if self.view == "available":
            # Sorted by meal time: this meal's dishes first, then the next meals of the day. Python's
            # sort is "stable", so dishes with the same rank keep their longest-first order.
            results.sort(key=lambda m: meal_rank(m.recipe, meal))
            recommended = [m for m in results if meal in m.recipe.meal_types]
        else:
            recommended = []
        rest = [m for m in results if m not in recommended]
        self.header.set_subtitle(f"{len(views['available'])} ready to cook")   # short: fits small phones
        self.state = dict(view=self.view, recommended=recommended, results=rest, search=search, meal=meal)
        self._render()

    def _set_status(self, text, bg, fg):
        self.status_chip.text = text
        self.status_chip._bg_color.rgba = bg
        self.status_chip.color = fg

    def _show_banner(self, pantry):
        self.banner.clear_widgets()
        today_items = expiring_today(pantry)
        if today_items:
            card = Card(color=DANGER_SOFT, shadow=False, padding=dp(10), radius=dp(16))
            card.add_widget(WrapLabel(
                text=colored("Use today: " + ", ".join(i.name for i in today_items), HEX_RED, True)
                + "  - dishes that use them are marked [b]Use today[/b].", font_size=sp(13)))
            self.banner.add_widget(card)

    # ------------------------------------------------------------------ drawing
    @staticmethod
    def _fingerprint(matches):
        """A short summary of the list: changes only when something VISIBLE changes."""
        return tuple((m.recipe.uid, m.recipe.picture, m.recipe.is_saved, thumb_status(m)) for m in matches)

    def _render(self):
        s = self.state
        # Rebuilding 100 rows while you scroll would interrupt the swipe and jump to the top, so the
        # list is only rebuilt when what it shows has really changed (idea from version 4.0.1).
        shown = (s["view"], s["meal"], self._fingerprint(s["recommended"]), self._fingerprint(s["results"]))
        if shown == getattr(self, "_shown", None):
            return
        self._shown = shown
        self.list.clear_widgets()
        if s["view"] == "saved":                           # your own recipes live here: "+ New recipe" on top
            self.list.add_widget(SoftButton("+  New recipe", height=dp(52),
                                            on_release=lambda *_: self.app.open_add_recipe()))
        if s["view"] == "available" and (s["recommended"] or s["results"]):
            # The Recommended section is always shown under Available (Dhruv), even when empty.
            self.list.add_widget(self._caption(f"Recommended for {s['meal']}"))
            for m in s["recommended"]:
                self.list.add_widget(RecipeRow(m, on_open=self.app.open_recipe))
            if not s["recommended"]:
                self.list.add_widget(self._note(f"No {s['meal'].lower()} dish can be cooked with your fridge "
                                                f"yet - here is what you can make for other meals."))
            if s["results"]:
                self.list.add_widget(self._caption("More you can cook"))
        if not s["recommended"] and not s["results"]:
            self.list.add_widget(self._empty_note(s))
        for m in s["results"]:
            self.list.add_widget(RecipeRow(m, on_open=self.app.open_recipe))
        self.scroll.scroll_y = 1                           # a new list starts at the top

    @staticmethod
    def _caption(text):
        """A small coloured section title inside the list."""
        label = Label(text=f"[b]{text.upper()}[/b]", markup=True, color=PRIMARY_DARK, font_size=sp(12.5),
                      size_hint_y=None, height=dp(26), halign="left", valign="bottom")
        label.bind(size=lambda l, sz: setattr(l, "text_size", sz))
        return label

    @staticmethod
    def _empty_note(s):
        if s["search"]:
            text = f"No recipe matches \"{s['search']}\"."
        elif s["view"] == "saved":
            text = ("Nothing saved yet. Open a recipe and tap [b]Save[/b] to keep it here, "
                    "or add your own with [b]+ New recipe[/b].")
        elif s["view"] == "available":
            text = ("Nothing can be cooked with what's in your fridge yet. Add a few items on the "
                    "[b]Fridge[/b] tab, or look at [b]Unavailable[/b] for dishes that miss just one thing.")
        else:
            text = "No recipes for your cooking machines. Tick more machines on the Profile tab."
        return RecipesScreen._note(text)

    @staticmethod
    def _note(text):
        """A soft card with a short message."""
        card = Card(shadow=False, padding=dp(14), radius=dp(18))
        card.add_widget(WrapLabel(text=text, color=MUTED, font_size=sp(14)))
        return card
