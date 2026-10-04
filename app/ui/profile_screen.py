"""
profile_screen.py
-----------------
WHY THIS FILE EXISTS:
    The "Profile" (user info) tab. It shows:
      * your name and avatar,
      * a Duolingo-style cooking STREAK (days in a row you cooked) with this week's 7 circles,
      * your longest streak, total meals cooked and your FAVOURITE DISH (most cooked),
      * settings: how many people you usually cook for (default 1), which cooking machines you own
        (this replaced the old Kitchen tab), and the address of the recipe server.
    The numbers are calculated by app/stats.py from the cook_log table.
"""

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.stacklayout import StackLayout
from kivy.uix.widget import Widget

from app import APP_VERSION
from app.api_client import DEFAULT_SERVER, RecipeApiClient
from app.images import resolve_image
from app.meal_time import current_meal
from app.stats import current_streak, favourite_dish, longest_streak, streak_message, week_strip
from app.ui.widgets import (BLUE_SOFT, INK, MUTED, NEUTRAL, PEACH, PEACH_SOFT, PRIMARY,
                            PRIMARY_DARK, PRIMARY_SOFT, WHITE, Card, Header, RoundImage, SoftButton,
                            SoftInput, SoftToggle, TapCard, WrapLabel, escape, icon_image, labeled,
                            scroll_list, section_title)


class Circle(Widget):
    """A filled circle (optionally with a ring) - used for the avatar and the week strip."""

    def __init__(self, color, ring=None, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*color)
            self._disc = Ellipse()
            if ring:
                Color(*ring)
                self._ring = Line(width=dp(1.6))
        self._has_ring = bool(ring)
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self._disc.pos, self._disc.size = self.pos, self.size
        if self._has_ring:
            self._ring.ellipse = (self.x - dp(3), self.y - dp(3), self.width + dp(6), self.height + dp(6))


def centered(widget):
    """Wrap a fixed-size widget so it sits in the middle of its column."""
    box = BoxLayout(size_hint_y=None, height=widget.height)
    box.add_widget(Widget())
    box.add_widget(widget)
    box.add_widget(Widget())
    return box


class ProfileScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        root = BoxLayout(orientation="vertical")
        root.add_widget(Header("Profile", "Your cooking journey"))
        scroll, self.content = scroll_list(spacing=dp(14), padding=(dp(16), dp(4), dp(16), dp(24)))
        root.add_widget(scroll)
        self.add_widget(root)
        # Save the name 0.6 s after the user stops typing (instead of on every key).
        self._save_name = Clock.create_trigger(lambda dt: self.app.db.set_setting("user_name", self.name_in.text.strip()), 0.6)

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        db = self.app.db
        c = self.content
        c.clear_widgets()
        days = db.cooked_days()
        log = db.cook_log()
        streak, cooked_today = current_streak(days)

        # ---------------------------------------------------------- avatar + name
        who = Card(orientation="horizontal", spacing=dp(14), padding=dp(14))
        name = db.get_setting("user_name", "") or ""
        avatar = Circle(PRIMARY_SOFT, size_hint=(None, None), size=(dp(64), dp(64)))
        initial = Label(text=f"[b]{escape((name or 'Chef')[:1].upper())}[/b]", markup=True,
                        color=PRIMARY_DARK, font_size=sp(28))
        avatar.bind(pos=lambda w, p: setattr(initial, "center", w.center),
                    size=lambda w, s: setattr(initial, "center", w.center))
        avatar.add_widget(initial)
        who.add_widget(avatar)
        self.name_in = SoftInput(text=name, hint_text="Your name")
        self.name_in.bind(text=lambda *_: self._save_name())
        who.add_widget(labeled("Hello, chef!", self.name_in))
        c.add_widget(who)

        # ---------------------------------------------------------- streak card
        sc = Card(color=PEACH_SOFT, spacing=dp(10), padding=dp(16))
        top = BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(12))
        top.add_widget(icon_image("fire", dp(58)))
        texts = BoxLayout(orientation="vertical")
        texts.add_widget(Label(text=f"[b]{streak} day streak[/b]", markup=True, color=(0.72, 0.38, 0.22, 1),
                               font_size=sp(26), halign="left", valign="bottom", text_size=(dp(240), None),
                               size_hint_x=None, width=dp(240)))
        texts.add_widget(Label(text=streak_message(streak, cooked_today), color=INK, font_size=sp(13),
                               halign="left", valign="top", text_size=(dp(240), None),
                               size_hint_x=None, width=dp(240)))
        top.add_widget(texts)
        sc.add_widget(top)
        week = BoxLayout(size_hint_y=None, height=dp(62), spacing=dp(4))
        for day, cooked, is_today in week_strip(days):
            col = BoxLayout(orientation="vertical", spacing=dp(4))
            col.add_widget(Label(text=day.strftime("%a")[:2], color=MUTED, font_size=sp(12),
                                 size_hint_y=None, height=dp(16)))
            dot = Circle(PEACH if cooked else WHITE, ring=PEACH if is_today else None,
                         size_hint=(None, None), size=(dp(34), dp(34)))
            if cooked:                                    # a little flame inside cooked days
                flame = icon_image("fire", dp(20))
                dot.add_widget(flame)
                dot.bind(pos=lambda w, p, f=flame: setattr(f, "center", w.center))
            col.add_widget(centered(dot))
            week.add_widget(col)
        sc.add_widget(week)
        c.add_widget(sc)

        # ---------------------------------------------------------- stats row
        stats = BoxLayout(size_hint_y=None, height=dp(104), spacing=dp(10))
        for icon_name, value, caption, bg in (("trophy", longest_streak(days), "best streak", (1, 0.96, 0.86, 1)),
                                              ("plate", len(log), "meals cooked", BLUE_SOFT),
                                              ("tab_calendar", len(days), "cooking days", PRIMARY_SOFT)):
            box = Card(color=bg, shadow=False, padding=dp(8), spacing=dp(2), radius=dp(18))
            box.add_widget(centered(icon_image(icon_name, dp(30))))
            box.add_widget(Label(text=f"[b]{value}[/b]", markup=True, color=INK, font_size=sp(20),
                                 size_hint_y=None, height=dp(28)))
            box.add_widget(Label(text=caption, color=MUTED, font_size=sp(12), size_hint_y=None, height=dp(18)))
            stats.add_widget(box)
        c.add_widget(stats)

        # ---------------------------------------------------------- favourite dish
        fav_name, fav_count = favourite_dish(log)
        c.add_widget(section_title("Favourite dish"))
        if fav_name:
            entry = next(e for e in log if e["recipe_name"] == fav_name)   # newest entry of that dish
            fav = TapCard(orientation="horizontal", spacing=dp(12), padding=dp(10))
            holder = BoxLayout(size_hint=(None, None), size=(dp(76), dp(76)), pos_hint={"center_y": 0.5})
            holder.add_widget(RoundImage(resolve_image(entry["image_path"]), radius=dp(16)))
            fav.add_widget(holder)
            text = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
            text.bind(minimum_height=text.setter("height"))
            text.add_widget(WrapLabel(text=f"[b]{escape(fav_name)}[/b]", font_size=sp(17)))
            times = "once" if fav_count == 1 else f"{fav_count} times"
            text.add_widget(WrapLabel(text=f"Cooked {times}", color=MUTED, font_size=sp(14)))
            fav.add_widget(text)
            fav.add_widget(centered(icon_image("star", dp(30))))
            if entry["recipe_exists"]:
                fav.bind(on_release=lambda *_: self.app.open_recipe(entry["recipe_id"]))
            c.add_widget(fav)
        else:
            empty = Card(shadow=False)
            empty.add_widget(WrapLabel(text="Cook a dish and tap 'Finished' - your favourite will show up here.",
                                       color=MUTED, font_size=sp(14)))
            c.add_widget(empty)

        # ---------------------------------------------------------- settings
        c.add_widget(section_title("Settings"))
        servings = db.default_servings()
        sv = Card(spacing=dp(8))
        sv.add_widget(WrapLabel(text="[b]Cooking for[/b]  (recipes and the fridge check use this)",
                                font_size=sp(14)))
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        row.add_widget(SoftButton("-", size_hint=(None, None), size=(dp(46), dp(46)), bg=NEUTRAL, fg=INK,
                                  on_release=lambda *_: self._set_servings(servings - 1)))
        row.add_widget(Label(text=f"[b]{servings} {'person' if servings == 1 else 'people'}[/b]",
                             markup=True, color=INK, font_size=sp(17)))
        row.add_widget(SoftButton("+", size_hint=(None, None), size=(dp(46), dp(46)), bg=NEUTRAL, fg=INK,
                                  on_release=lambda *_: self._set_servings(servings + 1)))
        sv.add_widget(row)
        c.add_widget(sv)

        kitchen = Card(spacing=dp(10))
        kitchen.add_widget(WrapLabel(text="[b]My cooking machines[/b]", font_size=sp(14)))
        chips = StackLayout(size_hint_y=None, spacing=dp(8))
        chips.bind(minimum_height=chips.setter("height"))
        for appliance, owned in db.get_appliances().items():
            t = SoftToggle(appliance, state="down" if owned else "normal", size_hint=(None, None),
                           height=dp(40), width=dp(30 + 8 * len(appliance)))
            # Save immediately when tapped. 'n=appliance' freezes the name for this button.
            t.bind(state=lambda btn, state, n=appliance: db.set_appliance(n, state == "down"))
            chips.add_widget(t)
        kitchen.add_widget(chips)
        c.add_widget(kitchen)

        server = Card(spacing=dp(10))
        server.add_widget(WrapLabel(text="[b]Recipe server[/b]", font_size=sp(14)))
        server.add_widget(WrapLabel(
            text="The Recipes tab asks this server for recipes. On a phone, use your computer's "
                 "Wi-Fi address, e.g. http://192.168.1.20:5000. Without a connection the app uses "
                 "the recipes saved on this device.", color=MUTED, font_size=sp(13)))
        use = SoftToggle("Use online recipes", state="down" if db.get_setting("use_server", "1") == "1" else "normal")
        use.bind(state=lambda btn, state: db.set_setting("use_server", "1" if state == "down" else "0"))
        server.add_widget(use)
        url_in = SoftInput(text=db.get_setting("server_url", DEFAULT_SERVER), hint_text=DEFAULT_SERVER)
        url_in.bind(text=lambda inp, text: db.set_setting("server_url", text.strip()))
        server.add_widget(url_in)
        self.server_status = WrapLabel(text="", font_size=sp(13), color=MUTED)
        server.add_widget(SoftButton("Test connection", bg=NEUTRAL, fg=INK,
                                     on_release=lambda *_: self._test_server(url_in.text.strip())))
        server.add_widget(self.server_status)
        c.add_widget(server)

        about = Card(shadow=False, color=(0, 0, 0, 0.03))
        about.add_widget(WrapLabel(
            text=f"It's {current_meal()} time. Everything you enter is stored on this device, so the "
                 f"app works without mobile data.\nData folder: {escape(self.app.data_dir)}\n"
                 f"FridgeChef v{APP_VERSION}", color=MUTED, font_size=sp(12)))
        c.add_widget(about)

    # ------------------------------------------------------------------ actions
    def _set_servings(self, value):
        self.app.db.set_setting("default_servings", max(1, min(20, value)))
        self.refresh()

    def _test_server(self, url):
        """Call GET /api/health in the background and show the result."""
        self.server_status.text = "Checking..."
        import threading

        def work():
            try:
                info = RecipeApiClient(url).health()
                text = f"[color=4f8a5b][b]Connected[/b][/color] - {info.get('recipes', '?')} recipes available"
            except Exception as error:
                text = f"[color=d0605f][b]Not reachable[/b][/color] - {escape(error)}"
            Clock.schedule_once(lambda dt: setattr(self.server_status, "text", text))
        threading.Thread(target=work, daemon=True).start()
