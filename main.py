"""
main.py
-------
WHY THIS FILE EXISTS:
    This is the entry point - run `python main.py` on a PC, and on Android the packaging tool
    (buildozer) also starts the app from a file called main.py. It:
      * configures the window (phone-sized on desktop),
      * creates the database in the app's private data folder,
      * builds the screens and the rounded bottom tab bar (Fridge, Recipes, Cookbook, Calendar, Profile),
      * knows the recipe server address (used by the Recipes tab),
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

import os                                          # paths for data folders
import subprocess                                  # start the local server as a separate process
import sys                                         # sys.executable = the Python running this app
import threading                                   # check / start the server without freezing the window
import time                                        # short waits while the server starts
from urllib.parse import urlparse                  # read the port number out of the server address

from kivy.app import App                           # base class of every Kivy application
from kivy.clock import Clock                       # timers (run something later / repeatedly)
from kivy.core.window import Window                # the app window (colour, keyboard events)
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import NoTransition, ScreenManager

from app import images
from app.api_client import ApiError, RecipeApiClient
from app.config import DEFAULT_SERVER, is_local    # server address (local now, cloud later)
from app.database import Database
from app.expiry import notify_if_needed
from app.ui.add_recipe_screen import AddRecipeScreen
from app.ui.calendar_screen import CalendarScreen
from app.ui.cookbook_screen import CookbookScreen
from app.ui.pantry_screen import PantryScreen
from app.ui.profile_screen import ProfileScreen
from app.ui.recipe_detail_screen import RecipeDetailScreen
from app.ui.recipes_screen import RecipesScreen
from app.ui.widgets import BG, MUTED, PRIMARY_DARK, PRIMARY_SOFT, WHITE, bg_rect, icon_image, set_bg

# The tabs of the bottom bar: (screen name, label, icon file in assets/icons).
TABS = [("pantry", "Fridge", "tab_fridge"), ("recipes", "Recipes", "tab_recipes"),
        ("cookbook", "Cookbook", "tab_cookbook"), ("calendar", "Calendar", "tab_calendar"),
        ("profile", "Profile", "tab_profile")]
TAB_NAMES = {name for name, _, _ in TABS}          # used to tell tabs apart from sub-screens


class NavTab(ButtonBehavior, BoxLayout):
    """One tab of the bottom bar: an emoji icon above a small label, in a rounded pill."""

    def __init__(self, label, icon_name, on_tap, **kwargs):
        super().__init__(orientation="vertical", padding=(0, dp(6), 0, dp(4)), spacing=dp(2), **kwargs)
        bg_rect(self, (0, 0, 0, 0), radius=dp(18))      # transparent until the tab is active
        row = BoxLayout(size_hint_y=None, height=dp(26))
        self.icon = icon_image(icon_name, dp(26))
        row.add_widget(BoxLayout())                      # empty boxes on both sides = centred icon
        row.add_widget(self.icon)
        row.add_widget(BoxLayout())
        self.add_widget(row)
        self.label = Label(text=label, font_size=sp(11), color=MUTED, size_hint_y=None, height=dp(16))
        self.add_widget(self.label)
        self.bind(on_release=lambda *_: on_tap())

    def set_active(self, active):
        set_bg(self, PRIMARY_SOFT if active else (0, 0, 0, 0))
        self.label.color = PRIMARY_DARK if active else MUTED
        self.label.bold = active
        self.icon.opacity = 1 if active else 0.6        # inactive icons look slightly faded


class FridgeChefApp(App):
    """The application object. Kivy calls build() once at start-up."""

    title = "FridgeChef"                           # window title on desktop

    def build(self):
        Window.clearcolor = BG                     # background colour behind everything
        Window.softinput_mode = "below_target"     # Android: keyboard pushes the focused field up

        # user_data_dir is a private, writable folder that Kivy picks per platform:
        #   Windows: C:\Users\<you>\AppData\Roaming\fridgechef   Android: the app's internal storage
        self.data_dir = self.user_data_dir
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
        self.sm.add_widget(CookbookScreen(self, name="cookbook"))
        self.sm.add_widget(CalendarScreen(self, name="calendar"))
        self.sm.add_widget(ProfileScreen(self, name="profile"))
        self.sm.add_widget(RecipeDetailScreen(self, name="detail"))
        self.sm.add_widget(AddRecipeScreen(self, name="add_recipe"))

        root = BoxLayout(orientation="vertical")
        root.add_widget(self.sm)                   # the current page fills the space...
        root.add_widget(self._build_nav_bar())     # ...above the bottom tab bar

        Window.bind(on_keyboard=self._on_key)      # catch the Android back button / Esc key
        # First-time users (empty fridge) start on the Fridge tab, everyone else on Recipes.
        self.navigate("recipes" if self.db.list_pantry() else "pantry", from_tab=True)
        return root                                # Kivy shows whatever build() returns

    def on_start(self):
        """Runs once the window is visible."""
        if platform == "android":
            self._request_android_permissions()
        else:
            self._ensure_local_server()            # PC: start server/app.py if nobody else did
        Clock.schedule_once(lambda dt: self.check_expiry(), 2)      # check 2 s after start-up
        Clock.schedule_interval(lambda dt: self.check_expiry(), 3600)   # and every hour after

    def on_stop(self):
        """Runs when the app closes - close the database cleanly (and our local server, if we started it)."""
        self.db.close()
        if self.server_process is not None:        # only a server WE started, never someone else's
            self.server_process.terminate()        # ask the server process to stop

    # ------------------------------------------------------------------ local server (PC only)
    server_process = None                          # the server/app.py process we started, if any

    def _ensure_local_server(self):
        """While developing on a PC, make sure the local recipe server is running.

        If the address in Profile points to this computer (127.0.0.1) and nothing answers there,
        start "python server/app.py" in the background. Runs on a background thread so the window
        appears immediately; when the server is ready, the Recipes tab is refreshed.
        """
        url = self.server_url()                    # "" = online recipes switched off
        if not url or not is_local(url):           # cloud server or offline mode -> nothing to start
            return

        def work():                                # runs on a background thread
            client = RecipeApiClient(url, timeout=1)   # short timeout: it's on this computer
            try:
                client.health()                    # someone (e.g. you, in a terminal) already runs it
                return
            except ApiError:                       # nothing answered -> start it ourselves
                pass
            port = urlparse(url).port or 5000      # "http://127.0.0.1:5000" -> 5000
            log = open(os.path.join(self.data_dir, "server.log"), "a")   # server messages go here
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)   # Windows: no extra black console window
            self.server_process = subprocess.Popen(
                [sys.executable, os.path.join(images.PROJECT_DIR, "server", "app.py")],   # same Python as the app
                env=dict(os.environ, PORT=str(port)), stdout=log, stderr=log, creationflags=flags)
            for _ in range(60):                    # wait up to ~15 s for it to answer
                time.sleep(0.25)
                try:
                    client.health()                # ready!
                    Clock.schedule_once(lambda dt: self._server_ready())   # back to the UI thread
                    return
                except ApiError:
                    continue                       # not yet - keep waiting
            print("[FridgeChef] Local server did not start - see server.log")
        threading.Thread(target=work, daemon=True).start()

    def _server_ready(self):
        """The local server just came up: reload the Recipes tab if it is showing 'Offline'."""
        if self.sm.current == "recipes":
            self.sm.current_screen.refresh()

    def server_url(self):
        """Address of the recipe API, or "" when the user turned online recipes off (Profile tab)."""
        if self.db.get_setting("use_server", "1") != "1":
            return ""
        return (self.db.get_setting("server_url", DEFAULT_SERVER) or "").strip()

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
        bg_rect(bar, WHITE, radius=dp(24), shadow=True)  # a floating white rounded bar
        self.nav_tabs = {}
        for name, label, icon_name in TABS:
            tab = NavTab(label, icon_name, on_tap=lambda n=name: self.navigate(n, from_tab=True))
            self.nav_tabs[name] = tab
            bar.add_widget(tab)
        outer.add_widget(bar)
        return outer

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
        """Ask for notification + photo permissions (Android 13+ requires asking at runtime)."""
        try:
            from android.permissions import Permission, request_permissions   # only exists on Android
            wanted = []
            for perm in ("POST_NOTIFICATIONS", "READ_MEDIA_IMAGES", "READ_EXTERNAL_STORAGE"):
                if hasattr(Permission, perm):      # older python-for-android versions lack some
                    wanted.append(getattr(Permission, perm))
            request_permissions(wanted)
        except Exception as error:
            print(f"[FridgeChef] Permission request failed: {error}")


# Standard Python idiom: only start the app when this file is run directly
# (not when it is imported, e.g. by a test).
if __name__ == "__main__":
    FridgeChefApp().run()
