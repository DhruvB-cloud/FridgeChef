"""
profile_screen.py
-----------------
WHY THIS FILE EXISTS:
    The "Profile" (user info) tab. It shows:
      * your name and avatar (tap the avatar to choose another one - version 4.7.1),
      * a Duolingo-style cooking STREAK (days in a row you cooked) with this week's 7 circles,
      * the COOKING CALENDAR (version 5.0 - it used to be a tab of its own),
      * settings: how many people you usually cook for (default 1), which cooking machines you own.
    Version 5.0 removed the stats row, the favourite dish and the title above the box to keep the
    tab simple. The streak is calculated by app/stats.py from the cook_log table.
"""

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image                    # the avatar picture (4.7.1)
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.stacklayout import StackLayout
from kivy.uix.widget import Widget

from app import APP_VERSION
from app.images import avatar_path
from app.meal_time import current_meal
from app.stats import current_streak, streak_message, week_strip
from app.ui.calendar_screen import CalendarPanel     # 5.0: the calendar is part of the Profile tab
from app.ui.welcome_popup import show_avatar_picker
from app.validation import name_error                 # 4.7.1: the shared name rules
from app.ui.widgets import (INK, MUTED, NEUTRAL, PEACH, PEACH_SOFT,
                            PRIMARY_DARK, PRIMARY_SOFT, WHITE, Card, Scene, SoftButton,
                            SoftInput, SoftToggle, TapBehavior, WrapLabel, escape, icon_image, labeled,
                            scroll_list, section_title, show_message, shrink_to_fit)


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


class TapCircle(TapBehavior, Circle):
    """The Profile avatar: a Circle you can tap (opens the avatar picker, version 4.7.1)."""

    def __init__(self, color, ring=None, **kwargs):
        # Kivy's ButtonBehavior (inside TapBehavior) runs first and only accepts NAMED values, so the
        # colour must be passed as color=... - passing it plainly crashed the Profile tab (4.7.1 bug).
        super().__init__(color=color, ring=ring, **kwargs)


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
        # 5.0: no title above the box any more (Dhruv: "remove the section on top, outside the box") -
        # the coloured frame starts right at the top of the screen.
        # The "chef's corner" scene (same frame as every other tab); the cards scroll inside it.
        body = BoxLayout(padding=(dp(16), dp(16), dp(16), dp(8)))
        scene = Scene("profile")
        scroll, self.content = scroll_list(spacing=dp(14), padding=(dp(2), dp(4), dp(2), dp(12)))
        scene.inner.add_widget(scroll)
        body.add_widget(scene)
        root.add_widget(body)
        self.add_widget(root)
        # Save the name 0.6 s after the user stops typing (instead of on every key).
        self._save_name = Clock.create_trigger(lambda dt: self._store_name(), 0.6)
        # 5.0: the cooking calendar lives on this tab now (it keeps the month you are looking at).
        self.calendar = CalendarPanel(app)

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        db = self.app.db
        c = self.content
        c.clear_widgets()
        days = db.cooked_days()
        streak, cooked_today = current_streak(days)

        # ---------------------------------------------------------- avatar + name
        who = Card(orientation="horizontal", spacing=dp(14), padding=dp(14))
        name = db.get_setting("user_name", "") or ""
        avatar = TapCircle(PRIMARY_SOFT, size_hint=(None, None), size=(dp(64), dp(64)))
        picture = avatar_path(db.get_setting("user_avatar"))   # 4.7.1: the avatar chosen at welcome
        if picture:                                            # a cartoon avatar inside the circle
            face = Image(source=picture, fit_mode="contain", size_hint=(None, None), size=(dp(48), dp(48)))
        else:                                                  # none chosen: the name's first letter
            face = Label(text=f"[b]{escape((name or 'Chef')[:1].upper())}[/b]", markup=True,
                         color=PRIMARY_DARK, font_size=sp(28))
        avatar.bind(pos=lambda w, p: setattr(face, "center", w.center),
                    size=lambda w, s: setattr(face, "center", w.center))
        avatar.add_widget(face)
        avatar.bind(on_tap=lambda *_: show_avatar_picker(self.app, on_done=self.refresh))   # tap -> change it
        who.add_widget(avatar)
        self.name_in = SoftInput(text=name, hint_text="Your name", rule="name")   # 4.7.1: max 126, no symbols
        self.name_in.bind(text=lambda *_: self._save_name())
        who.add_widget(labeled("Hello, chef!", self.name_in))
        c.add_widget(who)

        # ---------------------------------------------------------- streak card
        sc = Card(color=PEACH_SOFT, spacing=dp(10), padding=dp(16))
        top = BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(12))
        flame_icon = icon_image("fire", dp(58))
        flame_icon.pos_hint = {"center_y": 0.5}
        top.add_widget(flame_icon)
        # 4.7.1: the texts use the card's real width (they had a fixed 240 dp and were cut off on the
        # right). The message wraps onto more lines when needed and the row grows to fit.
        texts = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2), pos_hint={"center_y": 0.5})
        texts.bind(minimum_height=texts.setter("height"),
                   height=lambda w, h: setattr(top, "height", max(dp(64), h)))   # row follows the texts
        title = Label(text=f"[b]{streak} day streak[/b]", markup=True, color=(0.72, 0.38, 0.22, 1),
                      font_size=sp(26), halign="left", valign="middle", shorten=True,
                      size_hint_y=None, height=dp(34))
        title.bind(size=lambda l, sz: setattr(l, "text_size", sz))   # fit inside, "..." if ever too long
        shrink_to_fit(title, largest=26, smallest=16)        # narrow phones: smaller font, not "1 da...reak"
        texts.add_widget(title)
        texts.add_widget(WrapLabel(text=streak_message(streak, cooked_today), font_size=sp(13)))
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

        # ---------------------------------------------------------- cooking calendar (5.0)
        c.add_widget(section_title("Cooking calendar"))
        self.calendar.refresh()
        c.add_widget(self.calendar)

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
            t.bind(state=lambda btn, state, n=appliance: self._set_machine(btn, n, state == "down"))
            chips.add_widget(t)
        kitchen.add_widget(chips)
        c.add_widget(kitchen)

        about = Card(shadow=False, color=(0, 0, 0, 0.03))
        about.add_widget(WrapLabel(
            text=f"It's {current_meal()} time. Everything you enter is stored on this device, so the "
                 f"app works without mobile data.\nData folder: {escape(self.app.data_dir)}\n"
                 f"FridgeChef v{APP_VERSION}", color=MUTED, font_size=sp(12)))
        c.add_widget(about)

    # ------------------------------------------------------------------ actions
    def _store_name(self):
        """Save the typed name - but only a valid one (4.7.1: a name is required, so an empty box
        keeps the previous name instead of erasing it)."""
        if name_error(self.name_in.text) is None:
            self.app.db.set_setting("user_name", self.name_in.text.strip())

    def _set_machine(self, button, name, owned):
        """Tick / untick a cooking machine - at least one must stay ticked (4.7.1)."""
        db = self.app.db
        if not owned and db.owned_appliances() <= {name}:   # this is the last ticked machine
            button.state = "down"                         # undo the tap...
            show_message("Cooking machines", "Please keep at least one cooking machine - "
                                             "recipes are chosen by the machines you have.", height=dp(250))
            return
        db.set_appliance(name, owned)

    def _set_servings(self, value):
        self.app.db.set_setting("default_servings", max(1, min(20, value)))
        self.refresh()
