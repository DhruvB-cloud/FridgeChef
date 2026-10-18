"""
recipes_screen.py
-----------------
WHY THIS FILE EXISTS:
    The "Recipes" tab. Every time it opens (and whenever a filter changes) it sends an API request
    to the FridgeChef server (see app/api_client.py and server/app.py) with:
        what's in the fridge + which machines you own + your filters + "cooking for 1 person".
    The server answers with the matching recipes and the "Recommended for <meal>" list.

    * ONLINE  -> results come from the server. Every recipe received is also saved in the local
                 database (so it can be opened, cooked, saved - and used offline later).
    * OFFLINE -> (no data / server off) the same matching runs on the phone using its local copy.
    Your own recipes live only on the phone, so they are matched locally and merged into the list.

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

from app.api_client import RecipeApiClient
from app.expiry import expiring_today
from app.meal_time import current_meal
from app.models import CUISINES, NUTRITION_TAGS, SORT_OPTIONS
from app.recipe_engine import filter_matches, match_all, recommend, sort_matches
from app.ui.widgets import (SideScroller, AMBER, AMBER_SOFT, DANGER_SOFT, HEX_RED, MUTED, NEUTRAL, PRIMARY_DARK,
                            PRIMARY_SOFT, THUMB_RATIO, Card, Chip, Header, RecipeThumb, Scene, SoftInput,
                            SoftSpinner, SoftToggle, WrapLabel, colored, labeled, scroll_list)

# Drop-down label -> value understood by recipe_engine.filter_matches().
DIET_OPTIONS = {"All diets": "All", "Veg only": "Veg", "Non-veg only": "Non-Veg"}
TIME_OPTIONS = {"Any time": None, "Up to 15 min": 15, "Up to 30 min": 30, "Up to 60 min": 60}
ANY_NUTRITION, ANY_CUISINE = "Any nutrition", "All cuisines"
THUMB_WIDTH = dp(160)         # about this wide per thumbnail -> number of grid columns
STRIP_THUMB = dp(148)         # width of a thumbnail in the Recommended strip


class RecipesScreen(Screen):
    """The Recipes tab."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.request_id = 0              # increases with every request; stale answers are ignored
        self.state = None                # last results: dict(meal, recommended, results, online)
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
        self.search = SoftInput(hint_text="Search recipes...")
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
        self.time = SoftSpinner(text="Any time", values=list(TIME_OPTIONS))
        self.nutrition = SoftSpinner(text=ANY_NUTRITION, values=[ANY_NUTRITION] + NUTRITION_TAGS)
        self.cuisine = SoftSpinner(text=ANY_CUISINE, values=[ANY_CUISINE] + CUISINES)
        self.sort = SoftSpinner(text=SORT_OPTIONS[0], values=SORT_OPTIONS)   # protein / carbs sorting
        self.cook_now = SoftToggle("Cook-now only")       # pressed = hide recipes with gaps
        for caption, widget in (("Diet", self.diet), ("Preparation time", self.time),
                                ("Nutrition", self.nutrition), ("Cuisine", self.cuisine),
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
            max_minutes=TIME_OPTIONS[self.time.text],
            nutrition="Any" if self.nutrition.text == ANY_NUTRITION else self.nutrition.text,
            cuisine="Any" if self.cuisine.text == ANY_CUISINE else self.cuisine.text,
            search=self.search.text.strip(),
            sort=self.sort.text,
        )

    def _active_filter_count(self):
        """How many filters differ from their default - shown on the Filters button."""
        defaults = ("All diets", "Any time", ANY_NUTRITION, ANY_CUISINE, SORT_OPTIONS[0])
        values = (self.diet.text, self.time.text, self.nutrition.text, self.cuisine.text, self.sort.text)
        return sum(v != d for v, d in zip(values, defaults)) + (self.cook_now.state == "down")

    # ------------------------------------------------------------------ loading data
    def on_pre_enter(self, *_):
        self.refresh()                                   # opening the tab = a new API request

    def refresh(self):
        """Send the API request (in the background). Falls back to offline matching on failure."""
        db = self.app.db
        count = self._active_filter_count()
        self.filters_btn.text = f"Filters ({count})" if count else "Filters"
        pantry = db.list_pantry()
        snapshot = dict(pantry=pantry, appliances=db.owned_appliances(),
                        servings=db.default_servings(), filters=self.current_filters(),
                        only_cookable=self.cook_now.state == "down",
                        today=date.today(), now=datetime.now())
        self._show_banner(pantry)
        self.request_id += 1
        request_id = self.request_id
        url = self.app.server_url()
        if not url:                                      # user switched the server off in Profile
            self._apply_offline(snapshot)
            return
        self._set_status("Loading", NEUTRAL, MUTED)
        filters = dict(snapshot["filters"], only_cookable=snapshot["only_cookable"])

        def done(result, error):                         # runs on the BACKGROUND thread...
            # ...so hop back to the UI thread before touching any widget or the database.
            Clock.schedule_once(lambda dt: self._on_answer(request_id, snapshot, result, error))
        RecipeApiClient(url).fetch_async(done, pantry=pantry, appliances=snapshot["appliances"],
                                         filters=filters, servings=snapshot["servings"],
                                         today=snapshot["today"], now=snapshot["now"])

    def _on_answer(self, request_id, snapshot, result, error):
        if request_id != self.request_id:               # a newer request was sent meanwhile
            return
        if error is not None:
            print(f"[FridgeChef] {error} - using offline recipes")
            self._apply_offline(snapshot)
            return
        meal, recommended, results = result
        db = self.app.db
        saved = db.saved_flags()
        own_photos = db.custom_images()                  # photos the user chose on this phone
        # Save every server recipe locally (keeps the offline copy fresh) and use the LOCAL id.
        for match in {id(m): m for m in recommended + results}.values():   # each object once
            match.recipe.id = db.upsert_catalog_recipe(match.recipe, commit=False)
            match.recipe.is_saved = saved.get(match.recipe.uid, False)
            match.recipe.custom_image = own_photos.get(match.recipe.uid)
        db.commit()
        # The user's own recipes only exist on the phone: match them here and merge them in.
        mine = match_all(db.list_user_recipes(), snapshot["pantry"], snapshot["appliances"],
                         servings=snapshot["servings"])
        f = snapshot["filters"]
        mine_filtered = filter_matches(mine, only_cookable=snapshot["only_cookable"], **f)
        results = sort_matches(results + mine_filtered, f["sort"])
        recommended = recommend(recommended + filter_matches(mine, **f), meal)
        self.state = dict(meal=meal, recommended=recommended, results=results, online=True,
                          servings=snapshot["servings"])
        self._set_status("Live", PRIMARY_SOFT, PRIMARY_DARK)
        self._render()

    def _apply_offline(self, snapshot):
        """Do the same work as the server, but with the recipes stored on this phone."""
        db = self.app.db
        matches = match_all(db.list_recipes(), snapshot["pantry"], snapshot["appliances"],
                            servings=snapshot["servings"])
        f = snapshot["filters"]
        meal = current_meal(snapshot["now"])
        self.state = dict(meal=meal, online=False, servings=snapshot["servings"],
                          recommended=recommend(filter_matches(matches, **f), meal),
                          results=filter_matches(matches, only_cookable=snapshot["only_cookable"], **f))
        self._set_status("Offline", AMBER_SOFT, AMBER)
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
        source = "live recipes" if s["online"] else "offline recipes"
        self.header.set_subtitle(f"For {people} • {source}")
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
