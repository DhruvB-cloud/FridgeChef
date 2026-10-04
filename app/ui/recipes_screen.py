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

    Layout: on a phone, "Recommended" is a horizontal strip of picture cards above the full list;
    on a wide screen (tablet/PC) Recommended and All recipes are two side-by-side columns.
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
from app.ui.widgets import (AMBER, AMBER_SOFT, DANGER_SOFT, HEX_RED, MUTED, NEUTRAL, PRIMARY_DARK,
                            PRIMARY_SOFT, Card, Chip, Header, RecipeCard, RecipeTile, SoftInput,
                            SoftSpinner, SoftToggle, WrapLabel, bg_rect, colored, labeled,
                            scroll_list, section_title)

# Drop-down label -> value understood by recipe_engine.filter_matches().
DIET_OPTIONS = {"All diets": "All", "Veg only": "Veg", "Non-veg only": "Non-Veg"}
TIME_OPTIONS = {"Any time": None, "Up to 15 min": 15, "Up to 30 min": 30, "Up to 60 min": 60}
ANY_NUTRITION, ANY_CUISINE = "Any nutrition", "All cuisines"
WIDE_WIDTH = dp(700)          # from this width on, show two columns instead of a strip


class RecipesScreen(Screen):
    """The Recipes tab."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.request_id = 0              # increases with every request; stale answers are ignored
        self.state = None                # last results: dict(meal, recommended, results, online)
        self.wide = None                 # current layout mode (None = not decided yet)
        # A "trigger" runs refresh() once, 0.35 s after the LAST call - so typing "paneer" sends
        # one request instead of six.
        self.refresh_soon = Clock.create_trigger(lambda dt: self.refresh(), 0.35)

        root = BoxLayout(orientation="vertical")
        self.header = Header("What's cooking?", "Finding recipes for your fridge...")
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

        # ---------- results area (filled by _render)
        self.content = BoxLayout()
        self.content.bind(size=self._maybe_relayout)
        self.body.add_widget(self.content)
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
        # Save every server recipe locally (keeps the offline copy fresh) and use the LOCAL id.
        for match in {id(m): m for m in recommended + results}.values():   # each object once
            match.recipe.id = db.upsert_catalog_recipe(match.recipe, commit=False)
            match.recipe.is_saved = saved.get(match.recipe.uid, False)
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
        """Switch between phone layout and wide layout when the window size crosses the limit."""
        wide = self.content.width >= WIDE_WIDTH
        if wide != self.wide:
            self.wide = wide
            self._render()

    def _render(self):
        if self.state is None:
            return
        s = self.state
        people = "1 person" if s["servings"] == 1 else f"{s['servings']} people"
        source = "live from server" if s["online"] else "offline - saved on this phone"
        self.header.set_subtitle(f"For {people} • {source}")
        self.content.clear_widgets()
        open_recipe = self.app.open_recipe
        rec_title = f"Recommended for {s['meal']}"
        all_title = f"All recipes ({len(s['results'])})"
        empty_rec = WrapLabel(text=f"No {s['meal'].lower()} dishes match your fridge yet.",
                              color=MUTED, font_size=sp(14))

        if self.wide:                                    # ---- two columns side by side
            columns = BoxLayout(spacing=dp(14))
            left = BoxLayout(orientation="vertical", size_hint_x=0.42, padding=dp(10), spacing=dp(8))
            bg_rect(left, PRIMARY_SOFT, radius=dp(22))
            left.add_widget(section_title(rec_title))
            scroll, inner = scroll_list()
            for m in s["recommended"]:
                inner.add_widget(RecipeTile(m, on_open=open_recipe))
            if not s["recommended"]:
                inner.add_widget(empty_rec)
            left.add_widget(scroll)
            right = BoxLayout(orientation="vertical", size_hint_x=0.58, spacing=dp(8), padding=(0, dp(10), 0, 0))
            right.add_widget(section_title(all_title))
            scroll2, inner2 = scroll_list(padding=(0, 0, 0, dp(10)))
            self._fill_all(inner2, s["results"])
            right.add_widget(scroll2)
            columns.add_widget(left)
            columns.add_widget(right)
            self.content.add_widget(columns)
            return

        # ---- phone: one scrolling page with a horizontal Recommended strip on top
        scroll, inner = scroll_list(padding=(0, dp(2), 0, dp(14)))
        inner.add_widget(section_title(rec_title))
        if s["recommended"]:
            strip = ScrollView(do_scroll_y=False, size_hint_y=None, height=dp(232), bar_width=0)
            row = BoxLayout(size_hint_x=None, spacing=dp(12), padding=(dp(2), dp(4), dp(2), dp(6)))
            row.bind(minimum_width=row.setter("width"))  # row grows sideways with its cards
            for m in s["recommended"]:
                row.add_widget(RecipeCard(m, on_open=open_recipe, width=dp(168), pos_hint={"top": 1}))
            strip.add_widget(row)
            inner.add_widget(strip)
        else:
            inner.add_widget(empty_rec)
        inner.add_widget(section_title(all_title))
        self._fill_all(inner, s["results"])
        self.content.add_widget(scroll)

    def _fill_all(self, layout, results):
        if not results:
            layout.add_widget(WrapLabel(text="No recipes match these filters.", color=MUTED, font_size=sp(14)))
        for m in results:
            layout.add_widget(RecipeTile(m, on_open=self.app.open_recipe))
