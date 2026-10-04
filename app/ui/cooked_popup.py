"""
cooked_popup.py
---------------
WHY THIS FILE EXISTS:
    "When a user has cooked a dish, a small yay message should be displayed and give the user an
    option to upload a photo, so that it can be stored in the calendar along with the dish name."

    After "Finished - update fridge", show_cooked_popup() opens a cheerful popup:
        party icon (pops in)  +  "Yay! Dal Tadka is ready!"  +  streak line
        [ Add a photo ]  [ Done ]
    while a little confetti floats up. A chosen photo is copied into the app's own folder
    (images/cooked/) and attached to that day's calendar entry (cook_log.photo_path), so the
    Calendar shows YOUR photo next to the dish name. It can also be added later from the Calendar.
"""

import os                                           # building the photos folder path

from kivy.animation import Animation                # the "pop" of the party icon
from kivy.metrics import dp, sp                     # density-independent sizes
from kivy.uix.anchorlayout import AnchorLayout      # centres its child
from kivy.uix.boxlayout import BoxLayout            # vertical / horizontal stacking

from app.ui.easter_egg import confetti              # floating party icons
from app.ui.image_picker import import_image, pick_image   # choose + copy a photo
from app.ui.widgets import (INK, MUTED, NEUTRAL, PEACH_SOFT, RoundImage, SoftButton, WrapLabel,
                            escape, icon_image, light_popup, scroll_list, show_message)


def cooked_photos_dir(app):
    """Folder where photos of cooked dishes are kept: <data>/images/cooked"""
    return os.path.join(app.images_dir, "cooked")


def attach_photo(app, log_id, on_done=None):
    """Let the user pick a photo and store it with calendar entry `log_id`.

    on_done(path) is called afterwards (used to show the photo right away).
    Shared by this popup and the Calendar's "Add photo" button.
    """
    def picked(path):
        try:
            stored = import_image(path, cooked_photos_dir(app))   # resized copy in our own folder
        except Exception as error:                                # not an image / unreadable
            show_message("Photo problem", f"Could not use this file:\n{escape(error)}")
            return
        app.db.set_cook_photo(log_id, stored)                    # remember it in the calendar
        if on_done:
            on_done(stored)
    pick_image(picked)                                            # gallery (phone) / file browser (PC)


def show_cooked_popup(app, recipe_name, log_id, streak, summary):
    """The celebration popup shown right after cooking."""
    box = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(10))

    # --- party icon that "pops" in
    icon_row = BoxLayout(size_hint_y=None, height=dp(84))
    party = icon_image("party", dp(10))                      # starts tiny...
    party.opacity = 0
    icon_row.add_widget(BoxLayout())                          # spacer left
    holder = AnchorLayout(size_hint=(None, None), size=(dp(84), dp(84)))   # keeps the icon centred while it grows
    holder.add_widget(party)
    icon_row.add_widget(holder)
    icon_row.add_widget(BoxLayout())                          # spacer right
    box.add_widget(icon_row)
    Animation(size=(dp(80), dp(80)), opacity=1, duration=0.5, t="out_back").start(party)   # ...and pops

    # --- the yay message + streak
    box.add_widget(WrapLabel(text=f"[b]Yay! {escape(recipe_name)} is ready![/b]", font_size=sp(20),
                             halign="center"))
    days = f"{streak} day{'s' if streak != 1 else ''}"
    box.add_widget(WrapLabel(text=f"Cooking streak: [b]{days}[/b]  •  Enjoy your meal!",
                             font_size=sp(14), color=MUTED, halign="center"))

    # --- photo preview (hidden until a photo is chosen)
    preview = RoundImage(None, radius=dp(18), size_hint_y=None, height=0, opacity=0)
    box.add_widget(preview)
    saved_note = WrapLabel(text="Add a photo of your dish - it will be saved in your Calendar.",
                           font_size=sp(13), color=MUTED, halign="center")
    box.add_widget(saved_note)

    # --- what was taken from the fridge (small, scrollable)
    scroll, inner = scroll_list()
    inner.add_widget(WrapLabel(text=f"[b]Fridge updated[/b]\n{summary}", font_size=sp(12), color=MUTED))
    box.add_widget(scroll)

    # --- buttons
    buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
    photo_btn = SoftButton("Add a photo", bg=PEACH_SOFT, fg=(0.70, 0.40, 0.28, 1))
    done_btn = SoftButton("Done")
    buttons.add_widget(photo_btn)
    buttons.add_widget(done_btn)
    box.add_widget(buttons)

    popup = light_popup("", box, height=dp(520))              # no title - the message is the title
    popup.separator_height = 0                                # (and no line under the empty title)
    done_btn.bind(on_release=lambda *_: popup.dismiss())

    def show_photo(path):
        """A photo was stored: show it in the popup and confirm."""
        preview.set_source(path)
        preview.height, preview.opacity = dp(170), 1          # reveal the preview
        saved_note.text = "[color=4f8a5b][b]Saved to your Calendar![/b][/color]"
        photo_btn.text = "Change photo"
        popup.height = dp(680)                                # make room for the picture

    photo_btn.bind(on_release=lambda *_: attach_photo(app, log_id, on_done=show_photo))
    popup.open()
    confetti("party")                                         # a few party icons float up
    return popup
