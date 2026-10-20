"""
widgets.py
----------
WHY THIS FILE EXISTS:
    Kivy's default widgets are square and grey. This file defines the app's soft, rounded look ONCE
    (colours, rounded buttons, inputs, drop-downs, cards, chips, popups, recipe tiles) and every
    screen reuses these pieces. To restyle the whole app, edit only this file.

HOW THE ROUNDED CORNERS WORK:
    * Buttons, inputs, drop-downs and popups use small white rounded PNGs from assets/ui/
      (made by tools/make_assets.py). Kivy stretches them like a "9-slice" image - the corners
      keep their shape while the middle stretches - and multiplies them by `background_color`,
      so one white image becomes a rounded button of any colour.
    * Cards and chips draw a RoundedRectangle directly on the canvas.
"""

import os

from kivy.clock import Clock                            # run something on the next frame
from kivy.loader import Loader                          # loads pictures on background threads
from kivy.utils import platform                         # 'android', 'win', ... (keyboard fix below)
from kivy.core.text import LabelBase                    # register the app's own fonts
from kivy.graphics import (ClearBuffers, ClearColor, Color, Fbo, Line, Rectangle,   # low-level drawing instructions
                           RoundedRectangle)                                    # (Fbo = off-screen canvas, for cropping)
from kivy.graphics.texture import Texture               # home-made gradient pictures
from kivy.uix.floatlayout import FloatLayout            # layers: photo, shade, name, badges
from kivy.metrics import dp, sp           # dp = density-independent pixels, sp = scaled font size
from kivy.uix.behaviors import ButtonBehavior           # makes any widget clickable
from kivy.uix.boxlayout import BoxLayout                # lays children out in a row or column
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.stacklayout import StackLayout
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget

from app.images import ASSETS_DIR, resolve_image

# ----------------------------------------------------------------------------------------------
# FONTS (version 4.3) - Poppins, a modern rounded font (free, SIL Open Font License, see
# assets/fonts/OFL.txt). Registering it under Kivy's default name "Roboto" switches EVERY label,
# button and text box of the app to Poppins at once. "Display" is the heavy weight for big titles.
# ----------------------------------------------------------------------------------------------
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
_font = lambda name: os.path.join(FONTS_DIR, f"Poppins-{name}.ttf")
LabelBase.register("Roboto", fn_regular=_font("Regular"), fn_italic=_font("Italic"),
                   fn_bold=_font("SemiBold"), fn_bolditalic=_font("BoldItalic"))
LabelBase.register("Display", fn_regular=_font("Bold"), fn_bold=_font("Bold"))
DISPLAY = "Display"                                      # font_name for big headings

# ----------------------------------------------------------------------------------------------
# SOFT COLOUR PALETTE - Kivy uses (red, green, blue, alpha) with values from 0 to 1.
# ----------------------------------------------------------------------------------------------
BG = (0.973, 0.961, 0.937, 1)        # warm cream app background
SURFACE = (1, 1, 1, 1)               # cards
INK = (0.13, 0.16, 0.17, 1)          # main text (deep charcoal, not pure black)
MUTED = (0.54, 0.56, 0.58, 1)        # secondary text
PRIMARY = (0.20, 0.64, 0.46, 1)      # fresh emerald green - main buttons, active tab
PRIMARY_DARK = (0.12, 0.47, 0.34, 1)  # deep green for text on light backgrounds
PRIMARY_SOFT = (0.89, 0.95, 0.89, 1)  # very light sage - highlights
PEACH = (0.96, 0.66, 0.53, 1)        # warm accent (streak, share)
PEACH_SOFT = (0.99, 0.93, 0.89, 1)
DANGER = (0.88, 0.45, 0.45, 1)       # soft red - delete, expires today
DANGER_SOFT = (0.99, 0.91, 0.91, 1)
AMBER = (0.91, 0.65, 0.30, 1)
AMBER_SOFT = (1, 0.95, 0.86, 1)
BLUE = (0.47, 0.63, 0.85, 1)
BLUE_SOFT = (0.90, 0.94, 0.99, 1)
NEUTRAL = (0.93, 0.92, 0.89, 1)      # secondary buttons
INPUT_BG = (0.965, 0.957, 0.94, 1)   # text boxes
SELECTED_FILL = (0.88, 0.96, 0.88, 1)  # light green: the text box / drop-down you are using right now
# Food-type fills for the Name box in the Fridge form:
NONVEG_FILL = (1.0, 0.88, 0.88, 1)   # light red    - meat, chicken, fish...
EGG_FILL = (1.0, 0.96, 0.78, 1)      # light yellow - eggs
VEG_FILL = (0.86, 0.95, 0.86, 1)     # light green  - everything vegetarian
WHITE = (1, 1, 1, 1)

# Gradients: (top colour, bottom colour). Buttons, the active tab and header badges use these.
GRAD_PRIMARY = ((0.33, 0.78, 0.52, 1), (0.10, 0.55, 0.42, 1))   # emerald
GRAD_DANGER = ((1.00, 0.55, 0.45, 1), (0.89, 0.32, 0.36, 1))    # coral
TAB_ACCENTS = {                                          # header badge colour of each tab
    "tab_fridge": ((0.84, 0.92, 1.00, 1), (0.60, 0.78, 0.98, 1)),
    "tab_recipes": ((1.00, 0.90, 0.70, 1), (0.98, 0.72, 0.42, 1)),
    "tab_cookbook": ((1.00, 0.84, 0.76, 1), (0.88, 0.56, 0.44, 1)),
    "tab_calendar": ((0.84, 0.95, 0.86, 1), (0.56, 0.82, 0.62, 1)),
    "tab_profile": ((1.00, 0.86, 0.84, 1), (0.98, 0.62, 0.60, 1)),
}

# The same colours as hex text, for Kivy "markup" like "[color=d0605f]text[/color]".
HEX_RED, HEX_AMBER, HEX_GREEN, HEX_GREY, HEX_INK = "d0605f", "c98a2e", "4f8a5b", "8a8f93", "33383b"

# Rounded 9-slice images. border = how many pixels at each edge must NOT stretch (the corners).
UI_DIR = os.path.join(ASSETS_DIR, "ui")
ROUND = os.path.join(UI_DIR, "round.png")
ROUND_PRESSED = os.path.join(UI_DIR, "round_pressed.png")
ROUND_FOCUS = os.path.join(UI_DIR, "round_focus.png")
ROUND_BIG = os.path.join(UI_DIR, "round_big.png")
BORDER = (24, 24, 24, 24)
BORDER_BIG = (36, 36, 36, 36)

CARD_RADIUS = dp(20)                 # roundness of cards


def escape(text):
    """Escape user text so characters like '[' don't break Kivy markup."""
    return str(text).replace("&", "&amp;").replace("[", "&bl;").replace("]", "&br;")


def colored(text, hex_color, bold=False):
    """Wrap text in Kivy markup tags so it shows in a colour (and optionally bold)."""
    text = escape(text)
    if bold:
        text = f"[b]{text}[/b]"
    return f"[color={hex_color}]{text}[/color]"


_TEXTURES = {}                                          # file name -> loaded texture (load each once)


def ui_texture(name):
    """A picture from assets/ui (e.g. 'oak.jpg') as a texture that shapes can be painted with."""
    if name not in _TEXTURES:
        from kivy.core.image import Image as CoreImage   # local import: only needed here
        texture = CoreImage(os.path.join(UI_DIR, name)).texture
        texture.wrap = "clamp_to_edge"                   # never repeat the far edge (avoids a thin seam line)
        _TEXTURES[name] = texture
    return _TEXTURES[name]


_GRADIENTS = {}                                         # (top, bottom) -> texture (make each once)


def gradient_texture(top, bottom, steps=64):
    """A tiny 1 x 64 picture fading from `top` to `bottom` (RGBA, 0-1). Stretched over a rounded
    shape it paints a smooth vertical gradient. (A RoundedRectangle shows the FIRST row at the top.)"""
    key = (tuple(top), tuple(bottom))
    if key not in _GRADIENTS:
        rows = []
        for i in range(steps):                          # mix the two colours a bit more each row
            t = i / (steps - 1)
            rows.append(bytes(int(255 * (a * (1 - t) + b * t)) for a, b in zip(top, bottom)))
        texture = Texture.create(size=(1, steps), colorfmt="rgba")
        texture.blit_buffer(b"".join(rows), colorfmt="rgba", bufferfmt="ubyte")
        texture.wrap = "clamp_to_edge"
        _GRADIENTS[key] = texture
    return _GRADIENTS[key]


# Layered shadow: three soft shapes, each a little bigger and fainter = a blurred-looking shadow.
SHADOW_LAYERS = ((dp(1), dp(2), 0.05), (dp(4), dp(5), 0.035), (dp(9), dp(9), 0.02))   # (spread, drop, alpha)


def bg_rect(widget, color, radius=0, shadow=False, texture=None, gradient=None,
            shadow_color=(0.30, 0.22, 0.15)):
    """Paint a (rounded) background behind any widget and keep it in sync when it moves/resizes.

    shadow=True        a soft, layered shadow below the shape, which makes cards "float".
    texture='oak.jpg'  paints the shape with that picture (tinted by `color`; WHITE = true colours).
    gradient=(top, bottom) paints a vertical colour gradient (then `color` works as a tint).
    shadow_color       the shadow's colour (a coloured shadow looks like a glow).
    """
    with widget.canvas.before:                          # drawn BEFORE (= behind) the children
        shadows = []
        if shadow:
            for spread, drop, alpha in SHADOW_LAYERS:
                Color(*shadow_color, alpha)
                shadows.append((RoundedRectangle(radius=[radius + spread]), spread, drop))
        widget._bg_color = Color(*color)
        if gradient:
            tex = gradient_texture(*gradient) if radius else gradient_texture(gradient[1], gradient[0])
        else:
            tex = ui_texture(texture) if texture else None
        widget._bg_rect = (RoundedRectangle(radius=[radius], texture=tex) if radius
                           else Rectangle(texture=tex))

    def _sync(*_):                                       # follow the widget when it moves/resizes
        widget._bg_rect.pos = widget.pos
        widget._bg_rect.size = widget.size
        for shape, spread, drop in shadows:
            shape.pos = (widget.x - spread, widget.y - spread - drop)
            shape.size = (widget.width + 2 * spread, widget.height + 2 * spread)
    widget.bind(pos=_sync, size=_sync)
    _sync()


def set_bg(widget, color):
    """Change the colour of a background painted by bg_rect()."""
    widget._bg_color.rgba = color


# ----------------------------------------------------------------------------------------------
# TEXT
# ----------------------------------------------------------------------------------------------
class WrapLabel(Label):
    """A Label that wraps long text and grows in height to fit it (Kivy labels don't by default)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)          # height is controlled by us, not the layout
        kwargs.setdefault("halign", "left")             # left-aligned text
        kwargs.setdefault("valign", "middle")
        kwargs.setdefault("color", INK)                 # dark text on our light background
        kwargs.setdefault("markup", True)               # allow [b], [color] tags
        kwargs.setdefault("font_size", sp(15))
        super().__init__(**kwargs)
        # Whenever the width changes, wrap text at that width; whenever the rendered text
        # changes size, update our height to match.
        self.bind(width=self._wrap, texture_size=self._fit_height)
        # Start small: an EMPTY label never changes texture_size, so without this line it would
        # keep Kivy's default height of 100 pixels and leave a big gap.
        self._fit_height()

    def _wrap(self, *_):
        self.text_size = (self.width, None)             # None height = unlimited lines

    def _fit_height(self, *_):
        self.height = self.texture_size[1] + dp(4)      # rendered text height + a little padding


def section_title(text, size=17):
    """Bold heading used above lists ('Fridge', 'Recommended for Lunch'...)."""
    return WrapLabel(text=f"[b]{escape(text)}[/b]", font_size=sp(size))


class Chip(Label):
    """A small rounded 'pill' label, e.g. [VEG] [15 min] [20 g protein]."""

    def __init__(self, text, bg=PRIMARY_SOFT, fg=PRIMARY_DARK, **kwargs):
        super().__init__(text=text, color=fg, font_size=sp(12), bold=True, markup=True,
                         size_hint=(None, None), height=dp(24), **kwargs)
        bg_rect(self, bg, radius=dp(12))
        # Width follows the text: text width + 20dp padding.
        self.bind(texture_size=lambda *_: setattr(self, "width", self.texture_size[0] + dp(20)))


class ChipRow(StackLayout):
    """A row of chips that wraps onto a second line when needed."""

    def __init__(self, chips=(), **kwargs):
        super().__init__(size_hint_y=None, spacing=dp(6), **kwargs)
        self.bind(minimum_height=self.setter("height"))
        for chip in chips:
            self.add_widget(chip)


# ----------------------------------------------------------------------------------------------
# BUTTONS & INPUTS
# ----------------------------------------------------------------------------------------------
def _default_height(kwargs, height):
    """Give a widget a default height - unless the caller already chose a size.

    Bug fixed in version 4: setting a default height even when the caller passed size=(w, h)
    overrode that h. The 34 dp Edit/Delete buttons became 46 dp and overlapped the quantity chip.
    """
    if "size" not in kwargs:                         # size=(w, h) already contains a height
        kwargs.setdefault("height", height)          # otherwise use the default (if none given)


def _round_background(widget, color):
    """Apply the rounded 9-slice images to any Button-like widget."""
    widget.background_normal = ROUND
    widget.background_down = ROUND_PRESSED                # slightly darker while pressed
    widget.background_disabled_normal = ROUND
    widget.border = BORDER
    widget.background_color = color                      # tints the white image


class SoftButton(Button):
    """A rounded button. Green (PRIMARY) and red (DANGER) buttons are glossy gradients with a soft
    coloured glow underneath (version 4.3); all other colours are flat and soft."""

    def __init__(self, text="", bg=PRIMARY, fg=WHITE, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        _default_height(kwargs, dp(46))                 # comfortable touch target on phones
        kwargs.setdefault("font_size", sp(15))
        kwargs.setdefault("bold", True)
        super().__init__(text=text, color=fg, markup=True, **kwargs)
        with self.canvas.before:                        # the gradient look (hidden for flat colours)
            self._glow = []
            for spread, drop, alpha in ((dp(0), dp(3), 0.22), (dp(3), dp(6), 0.12)):
                self._glow.append((Color(0, 0, 0, 0), RoundedRectangle(radius=[dp(16) + spread]),
                                   spread, drop, alpha))
            self._shine = Color(1, 1, 1, 0)             # 0 = hidden, 1 = shown (dimmed while pressed)
            self._grad = RoundedRectangle(radius=[dp(16)])
        self.bind(pos=self._sync, size=self._sync, state=self._sync)
        self.set_colors(bg, fg)

    def set_colors(self, bg, fg):
        """Change colours later (e.g. Save -> Saved)."""
        self.color = fg
        gradient = {PRIMARY: GRAD_PRIMARY, DANGER: GRAD_DANGER}.get(tuple(bg))
        self._gradient = gradient
        if gradient:                                    # glossy gradient: hide Kivy's own background
            self.background_normal = self.background_down = ""
            self.background_color = (0, 0, 0, 0)
            self._grad.texture = gradient_texture(*gradient)
            for color, _shape, _spread, _drop, alpha in self._glow:
                color.rgba = (*gradient[1][:3], alpha)  # glow in the button's own colour
        else:                                           # flat soft colour (rounded 9-slice image)
            _round_background(self, bg)
            for color, *_ in self._glow:
                color.a = 0
        self._sync()

    def _sync(self, *_):
        self._grad.pos, self._grad.size = self.pos, self.size
        for _color, shape, spread, drop, _alpha in self._glow:
            shape.pos = (self.x + dp(6) - spread, self.y - drop - spread)
            shape.size = (self.width - dp(12) + 2 * spread, self.height + 2 * spread - dp(4))
        if self._gradient:
            self._shine.rgba = (0.86, 0.86, 0.86, 1) if self.state == "down" else (1, 1, 1, 1)
        else:
            self._shine.a = 0


class SoftToggle(ToggleButton):
    """A rounded toggle: grey when off, sage green when on. Used for chips and filters."""

    def __init__(self, text="", **kwargs):
        kwargs.setdefault("size_hint_y", None)
        _default_height(kwargs, dp(40))
        kwargs.setdefault("font_size", sp(14))
        super().__init__(text=text, **kwargs)
        _round_background(self, NEUTRAL)
        self.background_down = ROUND                    # we show "on" with colour, not darkness
        self.bind(state=self._restyle)
        self._restyle()

    def _restyle(self, *_):
        on = self.state == "down"
        self.background_color = PRIMARY if on else WHITE   # white "glass" when off, green when on
        self.color = WHITE if on else INK


class SoftOption(Button):
    """One entry in a drop-down list (used by SoftSpinner)."""

    def __init__(self, **kwargs):
        super().__init__(size_hint_y=None, height=dp(42), color=INK, font_size=sp(14), **kwargs)
        _round_background(self, WHITE)


class SoftDropDown(DropDown):
    """The list that opens under a SoftSpinner: a white rounded panel with a soft shadow."""

    def __init__(self, **kwargs):
        kwargs.setdefault("max_height", dp(300))        # long lists (e.g. 31 days) scroll instead of overflowing
        super().__init__(**kwargs)
        self.container.padding = dp(6)
        self.container.spacing = dp(2)
        bg_rect(self, WHITE, radius=dp(16), shadow=True)


class SoftSpinner(Spinner):
    """A rounded drop-down selector."""

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        _default_height(kwargs, dp(42))
        kwargs.setdefault("font_size", sp(14))
        super().__init__(option_cls=SoftOption, dropdown_cls=SoftDropDown, color=INK, **kwargs)
        _round_background(self, NEUTRAL)
        # While its list is open the drop-down turns soft green, like a selected text box.
        self.bind(is_open=lambda _s, opened: setattr(self, "background_color",
                                                     SELECTED_FILL if opened else NEUTRAL))


class SoftInput(TextInput):
    """A rounded text box: soft grey normally, soft GREEN while selected (focused).

    set_tint(color) gives it a fixed fill instead - the Fridge form uses that to colour the Name
    box light red / yellow / green for non-veg / egg / veg items.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("multiline", False)
        kwargs.setdefault("size_hint_y", None)
        _default_height(kwargs, dp(46))
        kwargs.setdefault("font_size", sp(15))
        super().__init__(**kwargs)
        self.background_normal = ROUND
        self.background_active = ROUND_FOCUS
        self.border = BORDER
        self.background_color = INPUT_BG
        self.foreground_color = INK
        self.hint_text_color = MUTED
        self.cursor_color = PRIMARY_DARK
        self.write_tab = False                          # Tab key moves to the next field
        self.tint = None                                # fixed fill colour (None = use focus colours)
        # NOTE: not named "_on_focus" - that name belongs to Kivy (see autocomplete.py).
        self.bind(focus=self._apply_fill)               # selected -> green, unselected -> grey
        if not self.multiline:                          # centre single-line text vertically
            # line_height is only known once Kivy has measured the font, so re-centre whenever
            # it (or the box height) changes.
            self.bind(height=self._center_text, line_height=self._center_text)
            self._center_text()
        else:
            self.padding = (dp(14), dp(12), dp(14), dp(12))

    def on_touch_up(self, touch):
        """A TAP on the box always opens the keyboard (bug fix for phones, version 4.0.1).

        On Android a quick tap sometimes did not show the keyboard - you had to press and hold.
        In Kivy the keyboard is only requested at the moment a box GAINS focus, so if the keyboard
        got closed while the box kept its focus, tapping again did nothing. Here every short tap
        (finger lifted close to where it went down) makes sure the box is focused AFTER all other
        touch handling has finished; on Android an already-focused box quickly drops and regains
        focus, which asks Android for the keyboard again.
        """
        handled = super().on_touch_up(touch)               # normal text-box behaviour first
        moved = abs(touch.x - touch.ox) + abs(touch.y - touch.oy)   # how far the finger travelled
        if self.collide_point(*touch.pos) and not self.disabled and moved < dp(12):   # a tap on us
            Clock.schedule_once(self._open_keyboard, 0)   # 0 = on the next frame, after everything else
        return handled

    def _open_keyboard(self, *_):
        if not self.focus:                                 # not focused (e.g. focus was taken away) -> take it
            self.focus = True
        elif platform == "android":                        # focused, but the keyboard may be hidden:
            self.focus = False                             # dropping and regaining focus makes Android
            self.focus = True                              # show the keyboard again

    def set_tint(self, color):
        """Use a fixed fill colour (or None to go back to grey / green-when-selected)."""
        self.tint = color
        self._apply_fill()

    def _apply_fill(self, *_):
        if self.tint is not None:                       # e.g. light red for "Chicken"
            self.background_color = self.tint
        else:
            self.background_color = SELECTED_FILL if self.focus else INPUT_BG

    def _center_text(self, *_):
        line = self.line_height if self.line_height > 1 else self.font_size * 1.2   # estimate until measured
        pad = max(dp(4), (self.height - line) / 2)
        self.padding = (dp(14), pad, dp(14), pad)


# Older screens used these names - keep them pointing to the new rounded versions.
FlatButton = SoftButton


# ----------------------------------------------------------------------------------------------
# CARDS, IMAGES, LAYOUT HELPERS
# ----------------------------------------------------------------------------------------------
class Card(BoxLayout):
    """A white rounded box (with a soft shadow) whose height grows with its content."""

    def __init__(self, color=SURFACE, shadow=True, radius=CARD_RADIUS, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", dp(14))
        kwargs.setdefault("spacing", dp(6))
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.bind(minimum_height=self.setter("height"))  # auto height = sum of children heights
        bg_rect(self, color, radius=radius, shadow=shadow)


TAP_SLOP = dp(12)                                  # a finger may wobble this far and still count as a tap


class TapBehavior(ButtonBehavior):
    """Adds an 'on_tap' event: fired only for a real TAP (finger lifted without sliding away).

    Why not on_press (version 4.7.1 fix): inside a scrolling list, Kivy's ScrollView waits a
    quarter of a second to see whether the finger moves. If it doesn't (you rested your thumb
    before swiping, or the phone was busy drawing), Kivy treats the touch as a press - and
    on_press opened a recipe the moment you tried to scroll.
    Why not plain on_release: for quick taps ScrollView delays the release by 0.2 seconds, which
    made every card feel slow (the reason 4.0.1 switched to on_press).
    So on_tap fires:
      * at once, when ScrollView hands over a touch whose finger is ALREADY lifted (a quick tap);
      * otherwise on release - but only if the finger stayed within TAP_SLOP of where it started.
    """
    __events__ = ("on_tap",)                           # tells Kivy this widget has an 'on_tap' event

    def on_press(self):
        touch = self.last_touch                        # the touch that pressed us (set by ButtonBehavior)
        if touch.time_end != -1:                       # time_end is set when the finger lifts -> quick tap
            self._fire_tap(touch)                      # react immediately, no 0.2 s wait

    def on_release(self):
        touch = self.last_touch                        # the same touch, now ending
        moved = max(abs(touch.x - touch.ox), abs(touch.y - touch.oy))   # distance from where it started
        if moved <= TAP_SLOP:                          # it stayed put: a tap, not a swipe
            self._fire_tap(touch)

    def _fire_tap(self, touch):
        key = f"tapped_{id(self)}"                     # remember per touch, so one tap fires only once
        if not touch.ud.get(key):                      # touch.ud = a dict that travels with the touch
            touch.ud[key] = True
            self.dispatch("on_tap")                    # run whatever was bound with bind(on_tap=...)

    def on_tap(self):
        pass                                           # default handler; Kivy requires one per event


class TapCard(TapBehavior, Card):
    """A Card you can tap. Use bind(on_tap=...) - see TapBehavior for why not on_press."""


class SideScroller(ScrollView):
    """A sideways-scrolling strip that lets up/down swipes scroll the page around it.

    Kivy's ScrollView keeps holding a vertical swipe that starts on a horizontal strip ("until the
    timeout is done", says a comment in Kivy's own code), so the page looked stuck when your finger
    happened to land on the Recommended strip. Here, as soon as a swipe is clearly more vertical
    than horizontal, the strip lets go of it and the page scrolls instead (fixed in version 4.0.1).
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("do_scroll_y", False)         # this strip only moves sideways
        kwargs.setdefault("bar_width", 0)               # no scroll bar
        super().__init__(**kwargs)

    def on_scroll_move(self, touch):
        uid, avoid = self._get_uid(), self._get_uid("svavoid")
        if avoid not in touch.ud and uid in touch.ud and touch.ud[uid]["mode"] == "unknown":
            dx = abs(touch.x - touch.ox)                # how far the finger moved sideways...
            dy = abs(touch.y - touch.oy)                # ...and up/down, since it went down
            if dy > dp(8) and dy > dx:                  # clearly a vertical swipe:
                touch.ud[avoid] = True                  #   tell Kivy this strip ignores the touch,
                touch.ungrab(self)                      #   stop following it,
                self._touch = None                      #   and cancel the pending "tap" timer
                return False                            #   -> the page's ScrollView takes over
        return super().on_scroll_move(touch)


class RoundImage(Widget):
    """A picture with rounded corners, cropped to fill its box (like CSS 'object-fit: cover').

    Kivy's Image widget can't round corners, so we draw the picture as the texture of a
    RoundedRectangle, using only the centre part of the picture that matches our shape.
    """

    def __init__(self, source=None, radius=dp(16), placeholder=NEUTRAL, **kwargs):
        super().__init__(**kwargs)
        self._texture = None
        self._placeholder = placeholder
        with self.canvas:
            self._color = Color(*placeholder)
            self._rect = RoundedRectangle(radius=[radius])
        self.bind(pos=self._update, size=self._update)
        self.set_source(source)

    def set_source(self, source):
        """Load (or replace) the picture IN THE BACKGROUND. Missing/broken file -> placeholder colour.

        (Version 4.0.1: loading every picture directly froze the screen for a moment on phones,
        e.g. when opening the Recipes tab with ~30 pictures. Kivy's Loader reads files on helper
        threads and hands the finished picture over a few per frame, so scrolling stays smooth.)
        """
        self._texture = None
        self._crop_key = None                              # new picture -> crop it afresh in _update
        self._source = source                              # remember which picture we want now
        if source and os.path.exists(source):
            proxy = Loader.image(source)                   # starts loading (or returns it from the cache)
            if proxy.loaded:                               # already in memory -> show immediately
                self._texture = proxy.texture
            else:                                          # still loading -> show it when ready
                proxy.bind(on_load=lambda p, s=source: self._loaded(p, s))
        self._update()

    def _loaded(self, proxy, source):
        """Called by the Loader when the picture is ready (only if it is still the one we want)."""
        if source == self._source and proxy.texture is not None:
            self._texture = proxy.texture
            self._update()

    def _update(self, *_):
        self._rect.pos, self._rect.size = self.pos, self.size
        tex = self._texture
        if tex is None or self.width <= 0 or self.height <= 0:
            self._rect.texture = None
            self._color.rgba = self._placeholder
            return
        self._color.rgba = WHITE                        # white = show the picture's true colours
        tw, th = tex.size
        box_ratio = self.width / self.height
        if tw / th > box_ratio:                         # picture is wider than the box: crop sides
            crop_w = int(th * box_ratio)
            crop = ((tw - crop_w) // 2, 0, crop_w, th)
        else:                                           # picture is taller: crop top and bottom
            crop_h = int(tw / box_ratio)
            crop = (0, (th - crop_h) // 2, tw, crop_h)
        key = (id(tex), crop)                           # which picture + which part of it
        if key != getattr(self, "_crop_key", None):     # only re-crop when picture or shape changed
            self._crop_key = key                        #   (not when scrolling just moves the widget)
            self._rect.texture = cropped_texture(tex, *crop)

    # Version 4.7.1 fix: Kivy's RoundedRectangle ignores the "region" part of a texture and always
    # stretches the WHOLE picture into its shape - so a square photo in the wide box on the recipe
    # page looked squashed. Copying just the cropped part into its own texture avoids that.


def cropped_texture(tex, x, y, w, h):
    """Return a NEW texture holding only the part (x, y, w, h) of `tex`, the right way up."""
    fbo = Fbo(size=(w, h))                              # an off-screen canvas exactly the crop's size
    with fbo:
        ClearColor(0, 0, 0, 0)                          # start fully transparent...
        ClearBuffers()                                  # ...by wiping the canvas
        Color(1, 1, 1, 1)                               # white tint = true colours
        # Drawn with a negative height (pos at the top): an Fbo stores its picture upside down,
        # so this flip makes the final texture come out upright.
        Rectangle(pos=(0, h), size=(w, -h), texture=tex.get_region(x, y, w, h))
    fbo.draw()                                          # render once, right now
    return fbo.texture                                  # the finished, cropped picture


class Header(BoxLayout):
    """Big friendly title at the top of a screen, with an optional subtitle, Back button and
    a slot on the right (e.g. the 'Live' status chip on the Recipes tab)."""

    def __init__(self, title, subtitle="", on_back=None, icon=None, **kwargs):
        super().__init__(size_hint_y=None, height=dp(78), padding=(dp(16), dp(12), dp(16), dp(6)),
                         spacing=dp(12), **kwargs)
        if on_back:
            self.add_widget(SoftButton("<", size_hint=(None, None), size=(dp(44), dp(44)),
                                       pos_hint={"center_y": 0.5}, bg=SURFACE, fg=INK,
                                       font_size=sp(20), on_release=lambda *_: on_back()))
        if icon:                                         # the tab's icon on a glowing gradient badge
            accent = TAB_ACCENTS.get(icon, ((1, 1, 1, 1), (0.92, 0.92, 0.92, 1)))
            badge = BoxLayout(size_hint=(None, None), size=(dp(50), dp(50)), padding=dp(10),
                              pos_hint={"center_y": 0.5})
            bg_rect(badge, WHITE, radius=dp(17), shadow=True, gradient=accent,
                    shadow_color=accent[1][:3])
            badge.add_widget(icon_image(icon, dp(30)))
            self.add_widget(badge)
        texts = BoxLayout(orientation="vertical")
        self.title_label = Label(text=title, font_name=DISPLAY, font_size=sp(24), color=INK,
                                 halign="left", valign="bottom", shorten=True, markup=True)
        self.subtitle_label = Label(text=subtitle, font_size=sp(13), color=MUTED, halign="left",
                                    valign="top", size_hint_y=0.6, markup=True, shorten=True)
        for label in (self.title_label, self.subtitle_label):
            label.bind(size=lambda l, s: setattr(l, "text_size", s))   # left-align inside
            texts.add_widget(label)
        self.add_widget(texts)
        # Optional right-hand slot. (Not called "right": Kivy already uses that name for x + width.)
        self.right_slot = BoxLayout(size_hint_x=None, width=0, padding=(0, dp(10)))
        self.add_widget(self.right_slot)

    def set_title(self, text):
        self.title_label.text = escape(text)

    def set_subtitle(self, text):
        self.subtitle_label.text = text

    def set_right(self, widget, width):
        """Put a widget (e.g. a status chip) on the right side of the header."""
        self.right_slot.clear_widgets()
        self.right_slot.width = width
        widget.pos_hint = {"center_y": 0.5}
        self.right_slot.add_widget(widget)


def scroll_list(spacing=dp(12), padding=0):
    """Return (ScrollView, inner_layout). Add rows to inner_layout; it scrolls when too long."""
    inner = GridLayout(cols=1, spacing=spacing, padding=padding, size_hint_y=None)
    inner.bind(minimum_height=inner.setter("height"))    # inner grows with its rows -> scrollable
    scroll = ScrollView(do_scroll_x=False, bar_width=dp(3), bar_color=(0, 0, 0, 0.15),
                        bar_inactive_color=(0, 0, 0, 0.05))
    scroll.add_widget(inner)
    return scroll, inner


def labeled(label_text, widget, height=dp(46)):
    """A small caption above an input widget - used by every form."""
    box = BoxLayout(orientation="vertical", size_hint_y=None, height=height + dp(24), spacing=dp(2))
    caption = Label(text=label_text, color=MUTED, font_size=sp(13), size_hint_y=None,
                    height=dp(20), halign="left")
    caption.bind(size=lambda l, s: setattr(l, "text_size", s))   # left-align the caption
    box.add_widget(caption)
    widget.size_hint_y = None
    widget.height = height
    box.add_widget(widget)
    return box


def icon_image(name, size=dp(28)):
    """A bundled emoji icon (assets/icons/<name>.png) at a fixed size."""
    from kivy.uix.image import Image                     # local import: only needed here
    from app.images import icon
    return Image(source=icon(name), size_hint=(None, None), size=(size, size), fit_mode="contain")


# ----------------------------------------------------------------------------------------------
# POPUPS
# ----------------------------------------------------------------------------------------------
def light_popup(title, content, size_hint=(0.92, None), height=None, auto_dismiss=True):
    """A white popup with big rounded corners and a soft dark overlay behind it."""
    popup = Popup(title=title, content=content, size_hint=size_hint, auto_dismiss=auto_dismiss,
                  background=ROUND_BIG, border=BORDER_BIG, background_color=WHITE,
                  title_color=INK, title_size=sp(19), title_font=DISPLAY, separator_color=PRIMARY_SOFT,
                  separator_height=dp(2), overlay_color=(0.15, 0.15, 0.12, 0.35))
    if size_hint[1] is None:                             # caller chose a fixed height
        popup.height = height or dp(260)
    return popup


def show_message(title, text, height=dp(300)):
    """Simple information popup with an OK button."""
    box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(12))
    scroll, inner = scroll_list()
    inner.add_widget(WrapLabel(text=text))
    box.add_widget(scroll)
    popup = light_popup(title, box, height=height)
    box.add_widget(SoftButton("OK", on_release=lambda *_: popup.dismiss()))
    popup.open()
    return popup


def confirm(title, text, on_yes, yes_text="Yes", yes_color=PRIMARY, height=dp(320)):
    """Yes / Cancel popup. `on_yes` is called only if the user taps the yes button."""
    box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(12))
    scroll, inner = scroll_list()
    inner.add_widget(WrapLabel(text=text))
    box.add_widget(scroll)
    buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
    popup = light_popup(title, box, height=height)

    def _yes(*_):
        popup.dismiss()                                  # close first...
        on_yes()                                         # ...then run the action
    buttons.add_widget(SoftButton("Cancel", bg=NEUTRAL, fg=INK, on_release=lambda *_: popup.dismiss()))
    buttons.add_widget(SoftButton(yes_text, bg=yes_color, on_release=_yes))
    box.add_widget(buttons)
    popup.open()


# ----------------------------------------------------------------------------------------------
# RECIPE TILES - how one recipe looks in a list (Recipes tab, Cookbook, Calendar)
# ----------------------------------------------------------------------------------------------
def recipe_status_lines(match):
    """The coloured status lines for a RecipeMatch (shared by tiles and the detail screen)."""
    lines = []
    if match.uses_expiring_today:                        # the most important information first
        lines.append(colored("USE TODAY: " + ", ".join(match.uses_expiring_today), HEX_RED, bold=True))
    if match.uses_expiring_soon:
        lines.append(colored("Use soon: " + ", ".join(match.uses_expiring_soon), HEX_AMBER))
    if not match.appliance_ok:
        lines.append(colored("Needs: " + " or ".join(match.recipe.appliances), HEX_GREY))
    if match.missing:
        names = ", ".join(i.name for i in match.missing[:4])
        more = f" +{len(match.missing) - 4}" if len(match.missing) > 4 else ""
        lines.append(colored(f"Missing: {names}{more}", HEX_RED))
    elif match.appliance_ok:
        lines.append(colored("Ready to cook", HEX_GREEN, bold=True))
    return lines


def diet_chip(is_veg):
    return Chip("VEG", PRIMARY_SOFT, PRIMARY_DARK) if is_veg else Chip("NON-VEG", DANGER_SOFT, DANGER)


def nutrition_text(recipe):
    """'20 g protein • 8 g carbs' (empty when unknown)."""
    parts = []
    if recipe.protein_g:
        parts.append(f"{recipe.protein_g:g} g protein")
    if recipe.carbs_g:
        parts.append(f"{recipe.carbs_g:g} g carbs")
    return " • ".join(parts)


class RecipeTile(TapCard):
    """Wide list row: rounded picture on the left, name + chips + status on the right."""

    def __init__(self, match, on_open, **kwargs):
        super().__init__(orientation="horizontal", spacing=dp(12), padding=dp(10), **kwargs)
        recipe = match.recipe
        picture = RoundImage(resolve_image(recipe.picture, small=True), radius=dp(16),
                             size_hint=(None, None), size=(dp(88), dp(88)))
        holder = BoxLayout(size_hint=(None, None), size=(dp(88), dp(88)),
                           pos_hint={"center_y": 0.5})               # vertically centred in the row
        holder.add_widget(picture)
        self.add_widget(holder)
        text_col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        text_col.bind(minimum_height=text_col.setter("height"))
        text_col.add_widget(WrapLabel(text=f"[b]{escape(recipe.name)}[/b]", font_size=sp(16)))
        chips = [diet_chip(recipe.is_veg), Chip(f"{recipe.prep_minutes} min", NEUTRAL, INK),
                 Chip(recipe.cuisine, BLUE_SOFT, (0.30, 0.42, 0.62, 1))]
        if recipe.protein_g:
            chips.append(Chip(f"{recipe.protein_g:g}g protein", PEACH_SOFT, (0.70, 0.40, 0.28, 1)))
        text_col.add_widget(ChipRow(chips))
        for line in recipe_status_lines(match):
            text_col.add_widget(WrapLabel(text=line, font_size=sp(13)))
        self.add_widget(text_col)
        self.bind(on_tap=lambda *_: on_open(recipe.id))       # tap -> open the recipe (real taps only, not swipes)


class RecipeCard(TapCard):
    """Compact vertical card (picture on top) - used in the Recommended strip and Cookbook grid."""

    def __init__(self, match, on_open, width=None, **kwargs):
        super().__init__(padding=dp(8), spacing=dp(4), **kwargs)
        if width:                                        # fixed width inside horizontal strips
            self.size_hint_x = None
            self.width = width
        recipe = match.recipe
        self.add_widget(RoundImage(resolve_image(recipe.picture, small=True), radius=dp(14),
                                   size_hint_y=None, height=dp(112)))
        self.add_widget(WrapLabel(text=f"[b]{escape(recipe.name)}[/b]", font_size=sp(14),
                                  max_lines=2, shorten=True, shorten_from="right"))
        info = f"{recipe.prep_minutes} min"
        if recipe.protein_g:
            info += f" • {recipe.protein_g:g}g protein"
        self.add_widget(WrapLabel(text=info, font_size=sp(12), color=MUTED))
        lines = recipe_status_lines(match)
        if lines:                                        # only the most important status line
            self.add_widget(WrapLabel(text=lines[0], font_size=sp(12), max_lines=2))
        self.bind(on_tap=lambda *_: on_open(recipe.id))       # on_tap = real taps only, not swipes



# ----------------------------------------------------------------------------------------------
# KITCHEN SCENES (version 4.2) - one look for every tab
# ----------------------------------------------------------------------------------------------
# Every tab shows its content inside a "scene": a thick rounded frame around an inner surface,
# drawn like a part of a kitchen. The SAME frame size, corner roundness, shadow, caption style and
# spacing are used everywhere - only the colours / textures change - so the tabs look like one app:
#     Fridge   -> a blue fridge           Recipes  -> an oak-wood kitchen counter
#     Cookbook -> an open book            Calendar -> a paper wall calendar
#     Profile  -> a warm "chef's corner"
# Version 4.3 adds depth: gradient frames, a coloured glow underneath, a glossy rim, and a light
# shining down from the top inside (the fridge light / the lamp over the counter).
SCENES = {
    #              frame colour (or texture)       inner surface (or texture)      caption colour
    "fridge": dict(frame=(0.70, 0.84, 0.97, 1), surface=(0.29, 0.60, 0.92, 1), caption=(1, 1, 1, 0.9),
                   frame_gradient=((0.93, 0.97, 1.00, 1), (0.64, 0.80, 0.97, 1)),
                   surface_gradient=((0.42, 0.73, 0.99, 1), (0.18, 0.47, 0.86, 1)),
                   light=(1, 1, 1, 0.42), glow=(0.20, 0.45, 0.85)),
    "kitchen": dict(frame=(0.55, 0.37, 0.23, 1), surface=WHITE, surface_texture="oak.jpg",
                    caption=(0.33, 0.20, 0.10, 1),
                    frame_gradient=((0.66, 0.45, 0.28, 1), (0.42, 0.26, 0.15, 1)),
                    light=(1, 0.94, 0.76, 0.55), glow=(0.45, 0.28, 0.12)),
    # (The book's frame is plain leather colour: Kivy leaves a 1-pixel sliver beside rounded shapes
    #  painted with a picture, which showed next to the book. The cover itself uses the texture.)
    "book": dict(frame=(0.45, 0.24, 0.18, 1), surface=(0.99, 0.97, 0.92, 1),
                 caption=(0.47, 0.27, 0.19, 1),
                 frame_gradient=((0.56, 0.31, 0.23, 1), (0.34, 0.17, 0.12, 1)), glow=(0.35, 0.16, 0.10)),
    "calendar": dict(frame=(0.80, 0.88, 0.81, 1), surface=WHITE, caption=PRIMARY_DARK,
                     frame_gradient=((0.86, 0.95, 0.88, 1), (0.62, 0.82, 0.68, 1)), glow=(0.20, 0.50, 0.30)),
    "profile": dict(frame=(0.97, 0.88, 0.82, 1), surface=(1, 0.984, 0.968, 1), caption=(0.70, 0.40, 0.28, 1),
                    frame_gradient=((1.00, 0.91, 0.85, 1), (0.97, 0.76, 0.68, 1)),
                    surface_gradient=((1, 0.99, 0.98, 1), (1, 0.965, 0.94, 1)), glow=(0.80, 0.40, 0.30)),
}
SCENE_FRAME = dp(9)                  # thickness of the frame
SCENE_RADIUS = dp(20)                # roundness of the inner surface (the frame adds its thickness)


class Scene(BoxLayout):
    """A kitchen 'room' (see SCENES). Put the tab's content into `scene.inner`."""

    def __init__(self, theme, **kwargs):
        kwargs.setdefault("padding", SCENE_FRAME)
        super().__init__(orientation="vertical", **kwargs)
        self.theme = t = SCENES[theme]
        bg_rect(self, WHITE if t.get("frame_gradient") else t["frame"], radius=SCENE_RADIUS + SCENE_FRAME,
                shadow=True, gradient=t.get("frame_gradient"), texture=t.get("frame_texture"),
                shadow_color=t.get("glow", (0.30, 0.22, 0.15)))
        with self.canvas.before:                        # a thin glossy rim along the frame's edge
            Color(1, 1, 1, 0.55)
            self._rim = Line(width=dp(1))
        self.inner = BoxLayout(orientation="vertical", padding=(dp(12), dp(10)), spacing=dp(8))
        bg_rect(self.inner, WHITE if t.get("surface_gradient") else t["surface"], radius=SCENE_RADIUS,
                gradient=t.get("surface_gradient"), texture=t.get("surface_texture"))
        if t.get("light"):                              # light shining down from the top inside
            with self.inner.canvas.before:
                Color(1, 1, 1, 1)
                # (Corners of 1 px, not 0: with a 0 corner Kivy stretches the gradient wrongly.)
                self._light = RoundedRectangle(radius=[SCENE_RADIUS, SCENE_RADIUS, 1, 1],
                                               texture=gradient_texture(t["light"], (*t["light"][:3], 0)))
            self.inner.bind(pos=self._draw_light, size=self._draw_light)
        self.bind(pos=self._draw_rim, size=self._draw_rim)
        self.add_widget(self.inner)

    def _draw_rim(self, *_):
        r = SCENE_RADIUS + SCENE_FRAME
        self._rim.rounded_rectangle = (self.x + dp(1), self.y + dp(1), self.width - dp(2),
                                       self.height - dp(2), r - dp(1))

    def _draw_light(self, *_):
        height = min(self.inner.height * 0.4, dp(260))  # the top 40 % glows, fading downwards
        self._light.pos = (self.inner.x, self.inner.top - height)
        self._light.size = (self.inner.width, height)

    def caption(self, text):
        """A small label in this scene's colour, e.g. 'SHELVES' or 'RECOMMENDED FOR LUNCH'."""
        return scene_caption(text, self.theme["caption"])


def scene_caption(text, color=MUTED):
    """The one caption style of the app: small, bold, capital letters."""
    label = Label(text=str(text).upper(), color=color, font_size=sp(11.5), bold=True,
                  size_hint_y=None, height=dp(20), halign="left", valign="middle")
    label.bind(size=lambda l, s: setattr(l, "text_size", s))   # left-align
    return label


def primary_action(text, on_release):
    """The big main button under a scene ('+ Add Item', '+ New recipe') - the same on every tab."""
    return SoftButton(text, height=dp(54), font_size=sp(18), on_release=lambda *_: on_release())


def thumb_status(match):
    """The ONE most important fact about a recipe for a thumbnail: (text, hex colour)."""
    if match.uses_expiring_today:
        return "Use today", HEX_RED
    if not match.appliance_ok:
        return "Needs " + " or ".join(match.recipe.appliances), HEX_GREY
    if match.missing:
        return f"Missing {len(match.missing)}", HEX_AMBER
    return "Ready to cook", HEX_GREEN


class Pill(Label):
    """A small rounded badge with its own background (e.g. 'Use today' on a recipe photo)."""

    def __init__(self, text, bg, fg, font_size=sp(10.5), **kwargs):
        super().__init__(text=text, color=fg, font_size=font_size, bold=True, markup=True,
                         size_hint=(None, None), height=dp(22), **kwargs)
        bg_rect(self, bg, radius=dp(11))
        self.bind(texture_size=lambda *_: setattr(self, "width", self.texture_size[0] + dp(14)))


THUMB_RATIO = 1.22                   # thumbnails are a little taller than wide (portrait cards)
STATUS_BADGE = {HEX_RED: (DANGER_SOFT, DANGER), HEX_AMBER: (AMBER_SOFT, (0.75, 0.48, 0.12, 1)),
                HEX_GREEN: (PRIMARY_SOFT, PRIMARY_DARK), HEX_GREY: (NEUTRAL, INK)}


class RecipeThumb(TapBehavior, FloatLayout):
    """A recipe as a modern photo card: the picture fills the card, the name sits on a dark fade
    at the bottom, and two floating badges show the status and the cooking time."""

    def __init__(self, match, on_open, width=None, **kwargs):
        super().__init__(size_hint_y=None, **kwargs)
        if width:                                        # fixed width inside a sideways strip
            self.size_hint_x = None
            self.width = width
        self.height = (width or dp(150)) * THUMB_RATIO
        self.bind(width=lambda *_: setattr(self, "height", self.width * THUMB_RATIO))
        bg_rect(self, (0, 0, 0, 0), radius=dp(20), shadow=True)   # only the soft shadow
        recipe = match.recipe
        self.add_widget(RoundImage(resolve_image(recipe.picture, small=True), radius=dp(20),
                                   pos_hint={"x": 0, "y": 0}))
        shade = Widget(size_hint=(1, 0.55), pos_hint={"x": 0, "y": 0})   # dark fade behind the name
        with shade.canvas:
            Color(1, 1, 1, 1)
            fade = RoundedRectangle(radius=[1, 1, dp(20), dp(20)],      # 1, not 0 (see Scene)
                                    texture=gradient_texture((0.05, 0.05, 0.05, 0), (0.05, 0.05, 0.05, 0.72)))
        shade.bind(pos=lambda w, p: setattr(fade, "pos", p), size=lambda w, sz: setattr(fade, "size", sz))
        self.add_widget(shade)
        name = Label(text=recipe.name, bold=True, color=WHITE, font_size=sp(14),   # plain text, no markup
                     size_hint=(1, 0.36), pos_hint={"x": 0, "y": 0.02}, halign="left", valign="bottom",
                     max_lines=2, shorten=True, shorten_from="right", padding=(dp(11), dp(8)))
        name.bind(size=lambda l, sz: setattr(l, "text_size", sz))   # wrap inside the card
        self.add_widget(name)
        text, hex_color = thumb_status(match)
        bg, fg = STATUS_BADGE[hex_color]
        self.add_widget(Pill(escape(text), bg, fg, pos_hint={"x": 0.06, "top": 0.95}))
        self.add_widget(Pill(f"{recipe.prep_minutes} min", (0.08, 0.08, 0.08, 0.5), WHITE,
                             pos_hint={"right": 0.94, "top": 0.95}))
        self.bind(on_tap=lambda *_: on_open(recipe.id))       # on_tap = real taps only, not swipes
