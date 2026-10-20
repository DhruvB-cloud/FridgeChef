"""
main.py
-------
WHY THIS FILE EXISTS:
    This is the entry point - run `python main.py` on a PC, and on Android the packaging tool
    (buildozer) also starts the app from a file called main.py. It:
      * configures the window (phone-sized on desktop),
      * creates the database in the app's private data folder,
      * builds the screens and the rounded bottom tab bar (Fridge, Recipes, Cookbook, Calendar, Profile),
      * handles "Back" (including the Android back button),
      * checks for items expiring today on start-up and every hour, sending a notification.
"""

# --- Window configuration MUST happen before any other Kivy import creates the window.
from kivy.utils import platform                     # 'android', 'win', 'linux', 'macosx'...
from kivy.config import Config

if platform not in ("android", "ios"):             # on a PC, imitate a phone screen for testing
    Config.set("graphics", "width", "420")
    Config.set("graphics", "height", "840")
    Config.set("input", "mouse", "mouse,multitouch_on_demand")   # no red dots on right-click (desktop)
else:
    # 4.7.1 fix: on a phone every finger touch ALSO arrives as a fake "mouse" event, so Kivy saw
    # each touch TWICE. The second copy went straight to the recipe card under your finger, which
    # grabbed it - swipes starting on a card froze, cards opened on touch, keyboards flickered.
    # A phone has no mouse, so Kivy's mouse input is switched off here.
    for option in ("mouse", "androidtouch"):           # "androidtouch" = an old, unused provider
        if Config.has_option("input", option):
            Config.remove_option("input", option)

import os                                          # paths for data folders

from kivy.animation import Animation               # the fade-in when the app opens (5.0)
from kivy.app import App                           # base class of every Kivy application
from kivy.clock import Clock                       # timers (run something later / repeatedly)
from kivy.core.window import Window                # the app window (colour, keyboard events)
from kivy.graphics import Rectangle                # the background picture
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import NoTransition, ScreenManager

from app import images
from app.database import Database
from app.expiry import notify_if_needed
from app.ui.add_recipe_screen import AddRecipeScreen
from app.ui.pantry_screen import PantryScreen
from app.ui.profile_screen import ProfileScreen
from app.ui.recipe_detail_screen import RecipeDetailScreen
from app.ui.recipes_screen import RecipesScreen
from app.ui.widgets import (BG, GRAD_PRIMARY, WHITE, bg_rect, icon_image, set_bg,
                            ui_texture)

NAV_BAR = (0.09, 0.15, 0.13, 0.97)                # deep green-black floating tab bar (version 4.3)

# The tabs of the bottom bar: (screen name, label, icon file in assets/icons).
# 5.0: three tabs - Cookbook merged into Recipes (All / Saved / Mine), Calendar moved into Profile.
TABS = [("pantry", "Fridge", "tab_fridge"), ("recipes", "Recipes", "tab_recipes"),
        ("profile", "Profile", "tab_profile")]
TAB_NAMES = {name for name, _, _ in TABS}          # used to tell tabs apart from sub-screens


class NavTab(ButtonBehavior, BoxLayout):
    """One tab of the bottom bar: an emoji icon above a small label, in a rounded pill."""

    def __init__(self, label, icon_name, on_tap, **kwargs):
        super().__init__(orientation="vertical", padding=(0, dp(6), 0, dp(4)), spacing=dp(2), **kwargs)
        # The active tab is a glossy green gradient "bubble"; it is invisible (alpha 0) until active.
        bg_rect(self, (1, 1, 1, 0), radius=dp(18), gradient=GRAD_PRIMARY)
        row = BoxLayout(size_hint_y=None, height=dp(26))
        self.icon = icon_image(icon_name, dp(26))
        row.add_widget(BoxLayout())                      # empty boxes on both sides = centred icon
        row.add_widget(self.icon)
        row.add_widget(BoxLayout())
        self.add_widget(row)
        self.label = Label(text=label, font_size=sp(10.5), color=(1, 1, 1, 0.6), size_hint_y=None,
                           height=dp(16))
        self.add_widget(self.label)
        # on_press (finger DOWN), not on_release: the tab reacts the moment you touch it (4.0.1)
        self.bind(on_press=lambda *_: on_tap())

    def set_active(self, active):
        # Active tab = glossy green bubble with white bold text; the others are softly faded.
        set_bg(self, WHITE if active else (1, 1, 1, 0))
        self.label.color = WHITE if active else (1, 1, 1, 0.6)
        self.label.bold = active
        self.icon.opacity = 1 if active else 0.75


class FridgeChefApp(App):
    """The application object. Kivy calls build() once at start-up."""

    title = "FridgeChef"                           # window title on desktop

    def build(self):
        Window.clearcolor = BG                     # background colour behind everything
        Window.softinput_mode = "below_target"     # Android: keyboard pushes the focused field up

        # Where the database, photos and share cards are kept:
        #   Android: user_data_dir = the app's private internal storage (chosen by Kivy).
        #   PC (4.7.1): the "local_data" folder inside this project. Kivy's own choice on Windows
        #   is C:\Users\<you>\AppData\Roaming\fridgechef, but nothing may be written to C:.
        if platform in ("android", "ios"):
            self.data_dir = self.user_data_dir
        else:
            self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_data")
            os.makedirs(self.data_dir, exist_ok=True)   # create it on the first run
        self.images_dir = os.path.join(self.data_dir, "images")   # photos of user recipes
        self.cards_dir = os.path.join(self.data_dir, "cards")     # generated share cards
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.cards_dir, exist_ok=True)
        images.set_cache_dir(os.path.join(self.data_dir, "image_cache"))   # downloaded server pictures
        self.db = Database(os.path.join(self.data_dir, "fridgechef.db"))
        self._give_old_recipes_pictures()

        self.history = []                          # stack of previous screen names for "Back"

        # NoTransition = instant switching (feels snappier than sliding on low-end phones).
        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(PantryScreen(self, name="pantry"))
        self.sm.add_widget(RecipesScreen(self, name="recipes"))
        self.sm.add_widget(ProfileScreen(self, name="profile"))
        self.sm.add_widget(RecipeDetailScreen(self, name="detail"))
        self.sm.add_widget(AddRecipeScreen(self, name="add_recipe"))

        root = BoxLayout(orientation="vertical")
        with root.canvas.before:                   # a soft, colourful blend of colours behind everything
            self._backdrop = Rectangle(texture=ui_texture("app_bg.jpg"))
        root.bind(pos=lambda w, p: setattr(self._backdrop, "pos", p),
                  size=lambda w, s: setattr(self._backdrop, "size", s))
        root.add_widget(self.sm)                   # the current page fills the space...
        root.add_widget(self._build_nav_bar())     # ...above the bottom tab bar

        Window.bind(on_keyboard=self._on_key)      # catch the Android back button / Esc key
        # First-time users (nothing but the built-in Water) start on the Fridge tab, everyone else on Recipes.
        has_food = any(not item.is_water for item in self.db.list_pantry())
        self.navigate("recipes" if has_food else "pantry", from_tab=True)
        root.opacity = 0                           # 5.0: start invisible, then fade in (see on_start)
        self.root_widget = root
        return root                                # Kivy shows whatever build() returns

    def on_start(self):
        """Runs once the window is visible."""
        # 5.0: after the loading animation, the app fades in instead of appearing all at once.
        Animation(opacity=1, duration=0.45, t="out_quad").start(self.root_widget)
        if platform == "android":
            self._request_android_permissions()
        Clock.schedule_once(lambda dt: self._maybe_welcome(), 0.5)  # 4.7.1: first start -> Welcome popup
        Clock.schedule_once(lambda dt: self.check_expiry(), 2)      # check 2 s after start-up
        Clock.schedule_interval(lambda dt: self.check_expiry(), 3600)   # and every hour after

    def _maybe_welcome(self):
        """Show the Welcome popup (avatar, name, cooking machines) until it was completed once."""
        from app.ui.welcome_popup import needs_welcome, show_welcome   # only needed here
        if needs_welcome(self.db):
            # Afterwards reload the visible tab, so Recipes uses the machines just chosen.
            screen = self.sm.current_screen
            show_welcome(self, on_done=lambda: screen.refresh() if hasattr(screen, "refresh") else None)

    def on_stop(self):
        """Runs when the app closes - close the database cleanly."""
        self.db.close()

    def _give_old_recipes_pictures(self):
        """Recipes created with version 1 may have no picture - generate a soft default one."""
        for recipe in self.db.list_user_recipes():
            if images.resolve_image(recipe.image_path) is None:
                path = images.make_default_image(
                    recipe.name, os.path.join(self.images_dir, f"default_{recipe.uid}.jpg"))
                self.db.conn.execute("UPDATE recipes SET image_path=? WHERE id=?", (path, recipe.id))
        self.db.commit()

    # ------------------------------------------------------------------ navigation
    def _build_nav_bar(self):
        outer = BoxLayout(size_hint_y=None, height=dp(78), padding=(dp(12), dp(4), dp(12), dp(10)))
        bar = BoxLayout(spacing=dp(4), padding=dp(5))
        bg_rect(bar, NAV_BAR, radius=dp(26), shadow=True, shadow_color=(0.05, 0.15, 0.10))   # floating dark bar
        self.nav_tabs = {}
        for name, label, icon_name in TABS:
            tab = NavTab(label, icon_name, on_tap=lambda n=name: self.tap_tab(n))
            self.nav_tabs[name] = tab
            bar.add_widget(tab)
        outer.add_widget(bar)
        return outer

    def tap_tab(self, name):
        """A tab was touched: highlight it IMMEDIATELY, then build the screen on the next frame.

        (Before 4.0.1 the highlight was only drawn after the new screen had been built, which can
        take a moment on a phone - so it looked like the tap had not registered.)
        """
        self._highlight_tab(name)                              # 1. instant visual feedback
        Clock.schedule_once(lambda dt: self.navigate(name, from_tab=True), 0)   # 2. then the work

    def _highlight_tab(self, name):
        """Highlight the active tab."""
        for tab, widget in self.nav_tabs.items():
            widget.set_active(tab == name)

    def navigate(self, name, from_tab=False, remember=True):
        """Switch to a screen. Tab presses reset the back-history."""
        if from_tab:
            self.history = []                      # tabs are top-level: nothing to go back to
        elif remember and self.sm.current and self.sm.current != name:
            self.history.append(self.sm.current)   # remember where we came from
        if self.sm.current == name and hasattr(self.sm.current_screen, "refresh"):
            self.sm.current_screen.refresh()       # tapping the active tab reloads it
        self.sm.current = name                     # triggers that screen's on_pre_enter -> refresh
        if name in TAB_NAMES:
            self._highlight_tab(name)

    def go_back(self):
        """Return to the previous screen (or the Recipes tab if there is no history)."""
        target = self.history.pop() if self.history else "recipes"
        self.navigate(target, remember=False)

    def open_recipe(self, recipe_id, replace=False):
        """Show the detail screen for one recipe. replace=True: don't come back to the current screen."""
        self.sm.get_screen("detail").show(recipe_id)
        if self.sm.current == "detail":            # already on a detail page: just redraw
            self.sm.current_screen.refresh()
        self.navigate("detail", remember=not replace)

    def open_add_recipe(self):
        self.navigate("add_recipe")

    def _on_key(self, _window, key, *_):
        """Android back button (and Esc on desktop) both send key code 27."""
        if key == 27:
            if self.history:
                self.go_back()
                return True                        # True = "handled", so the app doesn't close
            if self.sm.current != "recipes":
                self.navigate("recipes", from_tab=True)
                return True
        return False                               # on the Recipes tab: let Android close the app

    # ------------------------------------------------------------------ expiry & permissions
    def check_expiry(self):
        """Send the 'expires today' notification (max once per day) and refresh the visible page."""
        notify_if_needed(self.db, self.db.list_pantry())
        screen = self.sm.current_screen
        if screen.name == "pantry":                # e.g. midnight passed: new "Expires today" chips
            screen.refresh()

    def _request_android_permissions(self):
        """Ask for the notification permission (Android 13+ requires asking at runtime).

        4.7.1: no photo permissions any more - the system photo picker (app/ui/image_picker.py)
        gives access to the chosen picture without them.
        """
        try:
            from android.permissions import Permission, request_permissions   # only exists on Android
            wanted = []
            # WRITE_EXTERNAL_STORAGE: saving the share card to the gallery on Android 7-9 (4.0.1)
            for perm in ("POST_NOTIFICATIONS", "WRITE_EXTERNAL_STORAGE"):
                if hasattr(Permission, perm):      # older python-for-android versions lack some
                    wanted.append(getattr(Permission, perm))
            request_permissions(wanted)
        except Exception as error:
            print(f"[FridgeChef] Permission request failed: {error}")


# Standard Python idiom: only start the app when this file is run directly
# (not when it is imported, e.g. by a test).
if __name__ == "__main__":
    FridgeChefApp().run()
