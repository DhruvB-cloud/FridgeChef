"""
recipes_screen.py
-----------------
WHY THIS FILE EXISTS:
    The "Recipes" tab. Every time it opens (and whenever a filter changes) it matches every recipe
    on the phone against: what's in the fridge + which machines you own + your filters +
    "cooking for 1 person", and shows the matches plus a "Recommended for <meal>" list.

    Version 4.7.1: there is no recipe server any more. Once a day app/catalog.py downloads the
    published recipe catalogue (a plain file on GitHub Pages) and saves new / changed recipes in
    the local database; the status chip shows "Up to date" after a successful check, else
    "Offline" (the saved recipes keep working either way).

    Layout (version 4.2): the tab is the KITCHEN. Recipes are thumbnails lying on an oak-wood
    counter - "Recommended for <meal>" as a sideways strip, then all recipes as a grid
    (2 columns on a phone, more on wider screens). The counter stays put; the thumbnails scroll.
"""

from datetime import date, datetime

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from app.catalog import apply_catalog, sync_if_due
from app.expiry import expiring_today
from app.meal_time import current_meal
from app.models import CUISINES, NUTRITION_TAGS, SORT_OPTIONS
from app.recipe_engine import filter_matches, match_all, recommend
from app.ui.widgets import (SideScroller, AMBER, AMBER_SOFT, DANGER_SOFT, HEX_RED, MUTED, NEUTRAL, PRIMARY_DARK,
                            PRIMARY_SOFT, THUMB_RATIO, Card, Chip, Header, RecipeThumb, Scene, SoftInput,
                            SoftSpinner, SoftToggle, WrapLabel, colored, labeled, scroll_list)

# Drop-down label -> value understood by recipe_engine.filter_matches().
DIET_OPTIONS = {"All diets": "All", "Veg only": "Veg", "Non-veg only": "Non-Veg"}
ANY_NUTRITION, ANY_CUISINE = "Any nutrition", "All cuisines"
THUMB_WIDTH = dp(160)         # about this wide per thumbnail -> number of grid columns
STRIP_THUMB = dp(148)         # width of a thumbnail in the Recommended strip


class RecipesScreen(Screen):
    """The Recipes tab."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.state = None                # last results: dict(meal, recommended, results, servings)
        self.cols = None                 # thumbnails per grid row (None = not decided yet)
        # A "trigger" runs refresh() once, 0.35 s after the LAST call - so typing "paneer" sends
        # one request instead of six.
        self.refresh_soon = Clock.create_trigger(lambda dt: self.refresh(), 0.35)

        root = BoxLayout(orientation="vertical")
        self.header = Header("What's cooking?", "Finding recipes for your fridge...", icon="tab_recipes")
        self.status_chip = Chip("...", NEUTRAL, MUTED)
        self.header.set_right(self.status_chip, dp(78))
        root.add_widget(self.header)
        self.body = BoxLayout(orientation="vertical", padding=(dp(16), 0, dp(16), dp(6)), spacing=dp(10))

        # ---------- search + "Filters" button
        top = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.search = SoftInput(hint_text="Search recipes...", rule="name")   # 4.7.1: max 126, no symbols
        self.search.bind(text=lambda *_: self.refresh_soon())
        self.filters_btn = SoftToggle("Filters", size_hint=(None, None), size=(dp(100), dp(46)))
        self.filters_btn.bind(state=lambda *_: self._toggle_filter_panel())
        top.add_widget(self.search)
        top.add_widget(self.filters_btn)
        self.body.add_widget(top)

        # ---------- the (hidden by default) filter panel
        self.filter_panel = Card(shadow=False, padding=dp(12))
        grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        self.diet = SoftSpinner(text="All diets", values=list(DIET_OPTIONS))
        self.nutrition = SoftSpinner(text=ANY_NUTRITION, values=[ANY_NUTRITION] + NUTRITION_TAGS)
        self.cuisine = SoftSpinner(text=ANY_CUISINE, values=[ANY_CUISINE] + CUISINES)
        self.sort = SoftSpinner(text=SORT_OPTIONS[0], values=SORT_OPTIONS)   # protein / carbs sorting
        self.cook_now = SoftToggle("Cook-now only")       # pressed = hide recipes with gaps
        # 4.7.1: no "Preparation time" limit any more - recipes are listed longest first by default.
        for caption, widget in (("Diet", self.diet), ("Nutrition", self.nutrition), ("Cuisine", self.cuisine),
                                ("Sort by", self.sort), ("Show", self.cook_now)):
            grid.add_widget(labeled(caption, widget, height=dp(42)))
            # Any change -> ask the server again. Spinners fire 'text', the toggle fires 'state'.
            widget.bind(**{"state" if widget is self.cook_now else "text": lambda *_: self.refresh_soon()})
        self.filter_panel.add_widget(grid)

        # ---------- banner for items expiring today
        self.banner = BoxLayout(orientation="vertical", size_hint_y=None, height=0)   # height=0: empty = no gap
        self.banner.bind(minimum_height=self.banner.setter("height"))
        self.body.add_widget(self.banner)

        # ---------- results area: the oak kitchen counter (filled by _render)
        self.scene = Scene("kitchen")
        self.content = self.scene.inner
        self.content.bind(size=self._maybe_relayout)
        self.body.add_widget(self.scene)
        root.add_widget(self.body)
        self.add_widget(root)

    # ------------------------------------------------------------------ filters
    def _toggle_filter_panel(self):
        """Show or hide the filter panel just below the search row."""
        if self.filters_btn.state == "down" and self.filter_panel.parent is None:
            self.body.add_widget(self.filter_panel, index=len(self.body.children) - 1)
        elif self.filters_btn.state == "normal" and self.filter_panel.parent is not None:
            self.body.remove_widget(self.filter_panel)

    def current_filters(self):
        """The filter values in the form the engine / server expects."""
        return dict(
            diet=DIET_OPTIONS[self.diet.text],
            max_minutes=None,                            # 4.7.1: the time limit filter was removed
            nutrition="Any" if self.nutrition.text == ANY_NUTRITION else self.nutrition.text,
            cuisine="Any" if self.cuisine.text == ANY_CUISINE else self.cuisine.text,
            search=self.search.text.strip(),
            sort=self.sort.text,
        )

    def _active_filter_count(self):
        """How many filters differ from their default - shown on the Filters button."""
        defaults = ("All diets", ANY_NUTRITION, ANY_CUISINE, SORT_OPTIONS[0])
        values = (self.diet.text, self.nutrition.text, self.cuisine.text, self.sort.text)
        return sum(v != d for v, d in zip(values, defaults)) + (self.cook_now.state == "down")

    # ------------------------------------------------------------------ loading data
    def on_pre_enter(self, *_):
        self.refresh()                                   # opening the tab = a new API request

    def refresh(self):
        """Match all saved recipes on the phone (instant) and, once a day, check for new recipes."""
        db = self.app.db
        count = self._active_filter_count()
        self.filters_btn.text = f"Filters ({count})" if count else "Filters"
        pantry = db.list_pantry()
        snapshot = dict(pantry=pantry, appliances=db.owned_appliances(),
                        servings=db.default_servings(), filters=self.current_filters(),
                        only_cookable=self.cook_now.state == "down",
                        today=date.today(), now=datetime.now())
        self._show_banner(pantry)
        # Once a day: look for new recipes in the background (see app/catalog.py).
        checking = sync_if_due(db, lambda update, ok: Clock.schedule_once(   # back to the UI thread
            lambda dt: self._catalog_checked(update, ok)))
        if checking:
            self._set_status("Checking", NEUTRAL, MUTED)
        elif self.status_chip.text == "...":             # today's check already succeeded earlier
            self._set_status("Up to date", PRIMARY_SOFT, PRIMARY_DARK)
        self._apply_local(snapshot)                      # results appear immediately

    def _catalog_checked(self, update, ok):
        """The daily catalogue check finished (runs on the UI thread)."""
        if not ok:
            self._set_status("Offline", AMBER_SOFT, AMBER)   # the saved recipes still work
            return
        apply_catalog(self.app.db, update)               # save new / changed recipes (if any)
        self._set_status("Up to date", PRIMARY_SOFT, PRIMARY_DARK)
        if update and self.app.sm.current == "recipes":  # new recipes arrived -> show them
            self.refresh()

    def _apply_local(self, snapshot):
        """Match every saved recipe (catalogue + your own) on this phone."""
        db = self.app.db
        matches = match_all(db.list_recipes(), snapshot["pantry"], snapshot["appliances"],
                            servings=snapshot["servings"])
        f = snapshot["filters"]
        meal = current_meal(snapshot["now"])
        self.state = dict(meal=meal, servings=snapshot["servings"],
                          recommended=recommend(filter_matches(matches, **f), meal),
                          results=[m for m in filter_matches(matches, only_cookable=snapshot["only_cookable"], **f)
                                   if m.appliance_ok])   # 4.7.1: only dishes your machines can cook
        self._render()

    def _set_status(self, text, bg, fg):
        self.status_chip.text = text
        self.status_chip._bg_color.rgba = bg
        self.status_chip.color = fg

    def _show_banner(self, pantry):
        self.banner.clear_widgets()
        today_items = expiring_today(pantry)
        if today_items:
            card = Card(color=DANGER_SOFT, shadow=False, padding=dp(10))
            card.add_widget(WrapLabel(
                text=colored("Expiring today: " + ", ".join(i.name for i in today_items), HEX_RED, True),
                font_size=sp(14)))
            self.banner.add_widget(card)

    # ------------------------------------------------------------------ drawing results
    def _maybe_relayout(self, *_):
        """Re-draw when the window gets wide/narrow enough for a different number of columns."""
        cols = max(2, int(self.content.width // THUMB_WIDTH))
        if cols != self.cols:
            self.cols = cols
            self._render()

    @staticmethod
    def _fingerprint(matches):
        """A short summary of a result list: changes only when something VISIBLE changes."""
        return tuple((m.recipe.uid, m.recipe.picture, m.appliance_ok,
                      tuple(i.name for i in m.missing), tuple(m.uses_expiring_today),
                      tuple(m.uses_expiring_soon)) for m in matches)

    def _render(self):
        if self.state is None or self.cols is None:
            return
        s = self.state
        people = "1 person" if s["servings"] == 1 else f"{s['servings']} people"
        self.header.set_subtitle(f"For {people} • {len(s['results'])} recipes")
        # Version 4.0.1: rebuilding ~30 cards while you scroll interrupted the swipe and jumped back
        # to the top. If the new answer looks exactly like what is on screen, keep the screen as it is.
        shown = (self.cols, s["meal"], self._fingerprint(s["recommended"]), self._fingerprint(s["results"]))
        if shown == getattr(self, "_shown", None):
            return
        self._shown = shown
        old_scroll = [w.scroll_y for w in self.content.walk() if isinstance(w, ScrollView) and w.do_scroll_y]
        self.content.clear_widgets()
        open_recipe = self.app.open_recipe
        caption = self.scene.caption                     # the shared caption style, in dark oak

        scroll, inner = scroll_list(spacing=dp(8), padding=(0, 0, 0, dp(8)))
        # ---- "Recommended for Lunch": a sideways strip of thumbnails
        inner.add_widget(caption(f"Recommended for {s['meal']}"))
        if s["recommended"]:
            strip = SideScroller(size_hint_y=None, height=STRIP_THUMB * THUMB_RATIO + dp(16))   # up/down swipes scroll the page
            row = BoxLayout(size_hint_x=None, spacing=dp(10), padding=(0, dp(2), 0, dp(6)))
            row.bind(minimum_width=row.setter("width"))  # row grows sideways with its thumbnails
            for m in s["recommended"]:
                row.add_widget(RecipeThumb(m, on_open=open_recipe, width=STRIP_THUMB, pos_hint={"top": 1}))
            strip.add_widget(row)
            inner.add_widget(strip)
        else:
            inner.add_widget(self._note(f"No {s['meal'].lower()} dishes match your fridge yet."))
        # ---- every recipe, as a grid of thumbnails
        inner.add_widget(caption(f"All recipes ({len(s['results'])})"))
        if not s["results"]:
            inner.add_widget(self._note("No recipes match these filters."))
        grid = GridLayout(cols=self.cols, spacing=dp(12), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for m in s["results"]:
            grid.add_widget(RecipeThumb(m, on_open=open_recipe))
        inner.add_widget(grid)
        self.content.add_widget(scroll)
        if old_scroll:                                   # stay where you were (don't jump to the top)
            Clock.schedule_once(lambda dt: setattr(scroll, "scroll_y", old_scroll[0]), 0)

    def _note(self, text):
        """A short message written on the counter (e.g. 'No recipes match these filters.')."""
        return WrapLabel(text=text, color=self.scene.theme["caption"], font_size=sp(14))
