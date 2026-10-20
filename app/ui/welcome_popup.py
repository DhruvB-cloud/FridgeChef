"""
welcome_popup.py
----------------
WHY THIS FILE EXISTS (version 4.7.1):
    The first time someone opens FridgeChef, a "Welcome" popup asks for:
      * an avatar (a cartoon picture: chef, cat, panda, ...),
      * their name,
      * which cooking machines they own (Stove, Oven, ...) - the Recipes tab then only shows
        dishes those machines can cook.
    Everything can be changed later on the Profile tab. The avatar grid is also reused there
    (tap your avatar on Profile to pick another one).
"""

from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ToggleButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.stacklayout import StackLayout

from app.images import AVATARS, avatar_path
from app.ui.widgets import (INK, MUTED, NEUTRAL, PRIMARY, PRIMARY_SOFT, SoftButton, SoftInput, SoftToggle,
                            WrapLabel, light_popup, scroll_list, section_title)

WELCOME_DONE = "welcome_done"           # settings key: "1" once the welcome popup was completed


class AvatarChoice(ToggleButtonBehavior, BoxLayout):
    """One avatar in the grid: a rounded tile that turns green with a ring when selected."""

    def __init__(self, name, **kwargs):
        super().__init__(padding=dp(8), **kwargs)
        self.avatar_name = name                         # e.g. "panda" - what gets saved
        self.allow_no_selection = False                 # tapping the selected one keeps it selected
        with self.canvas.before:                        # the tile behind the picture
            self._fill = Color(*NEUTRAL)                # grey when not chosen
            self._tile = RoundedRectangle(radius=[dp(18)])
            self._ring_color = Color(*PRIMARY)          # green outline when chosen
            self._ring = Line(width=dp(2))
        self.add_widget(Image(source=avatar_path(name), fit_mode="contain"))   # the cartoon itself
        self.bind(pos=self._redraw, size=self._redraw, state=self._redraw)     # keep drawing in sync
        self._redraw()

    def _redraw(self, *_):
        chosen = self.state == "down"                   # "down" = selected (ToggleButtonBehavior)
        self._fill.rgba = PRIMARY_SOFT if chosen else NEUTRAL
        self._ring_color.a = 1 if chosen else 0         # invisible ring when not chosen
        self._tile.pos, self._tile.size = self.pos, self.size
        self._ring.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(18))


def avatar_grid(selected, on_pick, group="avatars"):
    """A 4-column grid of every avatar. `selected` starts highlighted; on_pick(name) runs on a tap."""
    grid = GridLayout(cols=4, spacing=dp(10), size_hint_y=None)
    grid.bind(minimum_height=grid.setter("height"))     # grow to fit all rows
    for name in AVATARS:
        if avatar_path(name) is None:                   # picture missing -> skip it
            continue
        tile = AvatarChoice(name, group=group, size_hint_y=None, height=dp(72),
                            state="down" if name == selected else "normal")
        # 'n=name' freezes this tile's name; only react when it becomes selected.
        tile.bind(state=lambda t, state, n=name: on_pick(n) if state == "down" else None)
        grid.add_widget(tile)
    return grid


def needs_welcome(db):
    """True until the welcome popup has been completed once."""
    return db.get_setting(WELCOME_DONE, "0") != "1"


def show_welcome(app, on_done=None):
    """Open the first-start popup. on_done() runs after the user taps "Let's cook!"."""
    db = app.db
    picked = {"avatar": db.get_setting("user_avatar") or AVATARS[0]}   # chef is pre-selected

    box = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(10))
    scroll, inner = scroll_list(spacing=dp(12), padding=(dp(2), dp(4)))
    inner.add_widget(WrapLabel(text="Let's set up your kitchen. You can change all of this later on "
                                    "the Profile tab.", color=MUTED, font_size=sp(14)))

    inner.add_widget(section_title("Pick your avatar", size=16))
    inner.add_widget(avatar_grid(picked["avatar"], lambda n: picked.update(avatar=n), group="welcome"))

    inner.add_widget(section_title("Your name", size=16))
    name_in = SoftInput(text=db.get_setting("user_name", "") or "", hint_text="Your name",
                        size_hint_y=None, height=dp(46))
    inner.add_widget(name_in)

    inner.add_widget(section_title("Your cooking machines", size=16))
    inner.add_widget(WrapLabel(text="Recipes will only show dishes you can cook with these.",
                               color=MUTED, font_size=sp(13)))
    chips = StackLayout(size_hint_y=None, spacing=dp(8))   # chips flow onto new lines when needed
    chips.bind(minimum_height=chips.setter("height"))
    toggles = {}                                         # appliance name -> its toggle
    for appliance, owned in db.get_appliances().items():
        t = SoftToggle(appliance, state="down" if owned else "normal", size_hint=(None, None),
                       height=dp(40), width=dp(30 + 8 * len(appliance)))   # width fits the word
        toggles[appliance] = t
        chips.add_widget(t)
    inner.add_widget(chips)
    box.add_widget(scroll)

    # auto_dismiss=False: tapping outside does not close it - the user finishes with the button.
    popup = light_popup("Welcome to FridgeChef!", box, size_hint=(0.94, 0.9), auto_dismiss=False)

    def finish(*_):
        db.set_setting("user_avatar", picked["avatar"])               # save the avatar...
        db.set_setting("user_name", name_in.text.strip())             # ...the name...
        for appliance, t in toggles.items():                          # ...and every machine
            db.set_appliance(appliance, t.state == "down")
        db.set_setting(WELCOME_DONE, "1")                             # never show this again
        popup.dismiss()
        if on_done:
            on_done()                                                 # e.g. reload the Recipes tab
    box.add_widget(SoftButton("Let's cook!", size_hint_y=None, height=dp(50), on_release=finish))
    popup.open()
    return popup


def show_avatar_picker(app, on_done=None):
    """Profile tab: tap your avatar -> choose another one."""
    box = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(12))
    current = app.db.get_setting("user_avatar") or AVATARS[0]
    popup = light_popup("Choose your avatar", box, height=dp(330))

    def pick(name):
        app.db.set_setting("user_avatar", name)                       # save at once
        popup.dismiss()
        if on_done:
            on_done()                                                 # e.g. redraw the Profile
    box.add_widget(avatar_grid(current, pick, group="profile_avatar"))
    box.add_widget(SoftButton("Close", bg=NEUTRAL, fg=INK, size_hint_y=None,
                              height=dp(46), on_release=lambda *_: popup.dismiss()))
    popup.open()
    return popup
