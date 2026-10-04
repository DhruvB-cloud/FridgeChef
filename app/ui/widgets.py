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

from kivy.core.image import Image as CoreImage          # loads a picture into a GPU texture
from kivy.graphics import Color, Rectangle, RoundedRectangle   # low-level drawing instructions
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
# SOFT COLOUR PALETTE - Kivy uses (red, green, blue, alpha) with values from 0 to 1.
# ----------------------------------------------------------------------------------------------
BG = (0.973, 0.961, 0.937, 1)        # warm cream app background
SURFACE = (1, 1, 1, 1)               # cards
INK = (0.20, 0.22, 0.23, 1)          # main text (soft charcoal, not pure black)
MUTED = (0.54, 0.56, 0.58, 1)        # secondary text
PRIMARY = (0.43, 0.67, 0.47, 1)      # soft sage green - main buttons, active tab
PRIMARY_DARK = (0.30, 0.52, 0.35, 1)  # sage for text on light backgrounds
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


def bg_rect(widget, color, radius=0, shadow=False):
    """Paint a (rounded) background behind any widget and keep it in sync when it moves/resizes.

    shadow=True adds a very soft shadow slightly below the shape, which makes cards "float".
    """
    with widget.canvas.before:                          # drawn BEFORE (= behind) the children
        if shadow:
            Color(0, 0, 0, 0.045)
            widget._shadow = RoundedRectangle(radius=[radius + dp(2)])
        widget._bg_color = Color(*color)
        widget._bg_rect = (RoundedRectangle(radius=[radius]) if radius else Rectangle())

    def _sync(*_):                                       # follow the widget when it moves/resizes
        widget._bg_rect.pos = widget.pos
        widget._bg_rect.size = widget.size
        if shadow:
            widget._shadow.pos = (widget.x - dp(1), widget.y - dp(3))
            widget._shadow.size = (widget.width + dp(2), widget.height + dp(2))
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
    """A rounded, softly coloured button."""

    def __init__(self, text="", bg=PRIMARY, fg=WHITE, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        _default_height(kwargs, dp(46))                 # comfortable touch target on phones
        kwargs.setdefault("font_size", sp(15))
        kwargs.setdefault("bold", True)
        super().__init__(text=text, color=fg, markup=True, **kwargs)
        _round_background(self, bg)

    def set_colors(self, bg, fg):
        """Change colours later (e.g. Save -> Saved)."""
        self.background_color = bg
        self.color = fg


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
        self.background_color = PRIMARY if on else NEUTRAL
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


class TapCard(ButtonBehavior, Card):
    """A Card you can tap (ButtonBehavior adds on_press / on_release events)."""


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
        """Load (or replace) the picture. A missing/broken file shows the placeholder colour."""
        self._texture = None
        if source and os.path.exists(source):
            try:
                self._texture = CoreImage(source).texture   # Kivy caches textures by file name
            except Exception:                              # unreadable image -> placeholder
                self._texture = None
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
            region = tex.get_region((tw - crop_w) // 2, 0, crop_w, th)
        else:                                           # picture is taller: crop top and bottom
            crop_h = int(tw / box_ratio)
            region = tex.get_region(0, (th - crop_h) // 2, tw, crop_h)
        self._rect.texture = region


class Header(BoxLayout):
    """Big friendly title at the top of a screen, with an optional subtitle, Back button and
    a slot on the right (e.g. the 'Live' status chip on the Recipes tab)."""

    def __init__(self, title, subtitle="", on_back=None, **kwargs):
        super().__init__(size_hint_y=None, height=dp(72), padding=(dp(16), dp(10), dp(16), dp(6)),
                         spacing=dp(10), **kwargs)
        if on_back:
            self.add_widget(SoftButton("<", size_hint=(None, None), size=(dp(44), dp(44)),
                                       pos_hint={"center_y": 0.5}, bg=SURFACE, fg=INK,
                                       font_size=sp(20), on_release=lambda *_: on_back()))
        texts = BoxLayout(orientation="vertical")
        self.title_label = Label(text=title, bold=True, font_size=sp(24), color=INK,
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
                  title_color=INK, title_size=sp(19), separator_color=PRIMARY_SOFT,
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
        picture = RoundImage(resolve_image(recipe.image_path), radius=dp(16),
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
        self.bind(on_release=lambda *_: on_open(recipe.id))   # tap -> open the recipe


class RecipeCard(TapCard):
    """Compact vertical card (picture on top) - used in the Recommended strip and Cookbook grid."""

    def __init__(self, match, on_open, width=None, **kwargs):
        super().__init__(padding=dp(8), spacing=dp(4), **kwargs)
        if width:                                        # fixed width inside horizontal strips
            self.size_hint_x = None
            self.width = width
        recipe = match.recipe
        self.add_widget(RoundImage(resolve_image(recipe.image_path), radius=dp(14),
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
        self.bind(on_release=lambda *_: on_open(recipe.id))
