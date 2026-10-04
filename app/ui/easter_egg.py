"""
easter_egg.py
-------------
WHY THIS FILE EXISTS:
    A little surprise: if someone tries to add "love" as an ingredient (in the Fridge or in a
    recipe), it is NOT added - instead a burst of hearts floats up across the screen with a
    sweet message. is_love() decides when it triggers; play_hearts() runs the animation.

HOW THE ANIMATION WORKS:
    A transparent full-screen layer is placed on top of the window. One big heart "pops" in the
    middle (grows, then fades), while ~16 small hearts float upwards, drift sideways and fade out.
    Kivy's Animation class smoothly changes widget properties (size, position, opacity) over time.
    After 2.8 seconds the layer is removed again. The layer never blocks taps.
"""

import random                                       # random positions / speeds for the small hearts

from kivy.animation import Animation                # smoothly changes properties over time
from kivy.clock import Clock                        # run code later (remove the layer)
from kivy.core.window import Window                 # the app window we draw on top of
from kivy.metrics import dp, sp                     # density-independent sizes
from kivy.uix.floatlayout import FloatLayout        # a layer where children are placed freely
from kivy.uix.image import Image                    # shows the heart picture
from kivy.uix.label import Label                    # the message text

from app.images import icon                         # path to assets/icons/heart.png
from app.ui.widgets import bg_rect                  # rounded background behind the message

LOVE_WORDS = {"love", "luv", "pyaar", "pyar", "ishq", "hubb", "amour"}   # English, Hindi, Arabic, French
MESSAGE = "Love isn't an ingredient - it's already in every dish you cook!"


def is_love(name):
    """True when the typed ingredient is 'love' (any capitals, spaces or trailing '!'/'s')."""
    word = str(name).strip().lower().rstrip("!.s ")  # "  Love!! " -> "love", "loves" -> "love"
    return word in LOVE_WORDS                        # set lookup: fast and simple


def float_icons(layer, icon_name, count, spread=dp(140)):
    """Let `count` small icons float up from the bottom of `layer`, drifting sideways and fading.

    Shared by the heart easter egg and the "Yay, you cooked!" confetti.
    """
    cx = Window.width / 2                            # horizontal centre of the screen
    for _ in range(count):
        size = dp(random.randint(22, 46))            # each icon a different size
        piece = Image(source=icon(icon_name), size_hint=(None, None), size=(size, size),
                      fit_mode="contain", opacity=0.95)
        piece.x = cx + random.uniform(-spread, spread) - size / 2      # spread around the centre
        piece.y = -size - random.uniform(0, dp(80))                    # start just below the screen
        layer.add_widget(piece)
        travel = random.uniform(0.55, 0.95) * Window.height            # how far up it floats
        drift = random.uniform(-dp(90), dp(90))                        # sideways movement
        float_up = Animation(y=piece.y + travel, x=piece.x + drift, opacity=0,
                             duration=random.uniform(1.6, 2.6), t="out_quad")   # slows down at the end
        Clock.schedule_once(lambda dt, a=float_up, p=piece: a.start(p),
                            random.uniform(0, 0.5))   # start at slightly different moments


def confetti(icon_name="party", count=14, seconds=3.0):
    """A short burst of floating icons over everything (no message) - used after cooking."""
    layer = FloatLayout(size=Window.size)            # transparent layer; taps pass through it
    Window.add_widget(layer)                         # on top of the window (and any popup)
    float_icons(layer, icon_name, count, spread=Window.width / 2.5)
    Clock.schedule_once(lambda dt: Window.remove_widget(layer), seconds)   # clean up afterwards


def play_hearts(message=MESSAGE):
    """Show the heart burst animation over the whole window."""
    layer = FloatLayout(size=Window.size)            # covers the window; touches pass through it
    Window.add_widget(layer)                         # added last = drawn on top of everything
    cx, cy = Window.width / 2, Window.height / 2     # centre of the screen

    # --- 1. the big heart: grows from tiny to big with a bouncy curve, then fades away
    big = Image(source=icon("heart"), size_hint=(None, None), size=(dp(20), dp(20)),
                fit_mode="contain", opacity=0)       # start small and invisible
    big.center = (cx, cy + dp(40))                   # a little above the middle
    layer.add_widget(big)
    final = dp(150)                                  # final size of the big heart
    pop = Animation(size=(final, final), x=cx - final / 2, y=cy + dp(40) - final / 2,
                    opacity=1, duration=0.45, t="out_back")   # "out_back" overshoots = bouncy
    beat = (Animation(size=(final * 0.88, final * 0.88), x=cx - final * 0.44,
                      y=cy + dp(40) - final * 0.44, duration=0.18)   # shrink a bit...
            + Animation(size=(final, final), x=cx - final / 2,
                        y=cy + dp(40) - final / 2, duration=0.18))   # ...and back = a heartbeat
    fade = Animation(opacity=0, duration=0.6)        # disappear
    (pop + beat + beat + Animation(duration=0.5) + fade).start(big)   # '+' = one after another

    # --- 2. many small hearts float up from the bottom, drifting and fading
    float_icons(layer, "heart", 16)

    # --- 3. the message in a soft pink pill
    label = Label(text=message, color=(0.75, 0.25, 0.42, 1), font_size=sp(15), bold=True,
                  size_hint=(None, None), halign="center", valign="middle", opacity=0)
    label.text_size = (min(Window.width - dp(60), dp(340)), None)     # wrap long text
    label.texture_update()                           # measure the text now
    label.size = (label.texture_size[0] + dp(32), label.texture_size[1] + dp(22))   # text + padding
    label.center = (cx, cy - dp(70))                 # below the big heart
    bg_rect(label, (1, 0.92, 0.95, 1), radius=dp(20))   # pale pink rounded background
    layer.add_widget(label)
    (Animation(opacity=1, duration=0.3) + Animation(duration=1.8)
     + Animation(opacity=0, duration=0.5)).start(label)   # fade in, stay, fade out

    # --- 4. clean up: remove the whole layer when everything has finished
    Clock.schedule_once(lambda dt: Window.remove_widget(layer), 3.0)
