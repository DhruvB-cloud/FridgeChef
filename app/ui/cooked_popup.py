"""
cooked_popup.py
---------------
WHY THIS FILE EXISTS:
    "When a user has cooked a dish, a small yay message should be displayed."

    After "Finished - update fridge", show_cooked_popup() opens a cheerful popup:
        party icon (pops in)  +  "Yay! Dal Tadka is ready!"  +  streak line  +  [ Done ]
    while a little confetti floats up, and lists what was taken from the fridge.

    Version 5.0: the cooking calendar was removed (Dhruv), so the "Add a photo for your Calendar"
    button went with it - there was nowhere left to show that photo. A recipe's own picture can
    still be changed with "Change photo" on the recipe page.
"""

from kivy.animation import Animation                # the "pop" of the party icon
from kivy.metrics import dp, sp                     # density-independent sizes
from kivy.uix.anchorlayout import AnchorLayout      # centres its child
from kivy.uix.boxlayout import BoxLayout            # vertical / horizontal stacking

from app.ui.easter_egg import confetti              # floating party icons
from app.ui.widgets import MUTED, SoftButton, WrapLabel, escape, icon_image, light_popup, scroll_list


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

    # --- what was taken from the fridge (small, scrollable)
    scroll, inner = scroll_list()
    inner.add_widget(WrapLabel(text=f"[b]Fridge updated[/b]\n{summary}", font_size=sp(12), color=MUTED))
    box.add_widget(scroll)

    # --- the button
    done_btn = SoftButton("Done", size_hint_y=None, height=dp(46))
    box.add_widget(done_btn)

    popup = light_popup("", box, height=dp(440))              # no title - the message is the title
    popup.separator_height = 0                                # (and no line under the empty title)
    done_btn.bind(on_release=lambda *_: popup.dismiss())
    popup.open()
    confetti("party")                                         # a few party icons float up
    return popup
