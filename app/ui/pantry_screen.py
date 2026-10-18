"""
pantry_screen.py
----------------
WHY THIS FILE EXISTS:
    The "Fridge" tab - where the user keeps track of what they have.

    Version 4.1 draws it as a real fridge (from Dhruv's own sketch):
        * jars stand on the white shelves at the top,
        * dishes (leftovers) stand on their own shelf,
        * bottles stand in the door rack at the bottom - Water is always there.
    Every item is drawn as the container picked in the Add form (bottle / glass jar / dish), with
    its name written on the container's label. Food that has gone past its expiry date turns
    mouldy green.

    Tapping an item opens a small popup:
        * fresh food   -> change the quantity, or "Remove from fridge"
        * expired food -> only "Throw Away"
        * Water        -> it never runs out and never expires
    Removing an item plays a short animation: it shrinks, floats up and fades out of the fridge.

    A banner lists items expiring today. The item name box suggests ingredients while you type
    ("oni" -> Onion). Expiry dates are picked from Day / Month / Year drop-downs (dd-mm-yyyy).
    Easter egg: try adding "love".
"""

from datetime import date, timedelta              # expiry dates

from kivy.animation import Animation              # the "disappearing from the fridge" effect
from kivy.core.text import Label as CoreLabel     # measures text without showing it (font fitting)
from kivy.graphics import (Color, Line, PopMatrix, PushMatrix, Rectangle, RoundedRectangle,
                           Scale, Translate, Triangle)   # low-level drawing: shelves, rail, handle
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty       # values Animation can change smoothly
from kivy.uix.behaviors import ButtonBehavior     # makes an item tappable
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout      # lets the name sit ON the container picture
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image                  # the bottle / jar / dish pictures
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen         # one "page" of the app
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from app.dates import format_date                 # shows dates as dd-mm-yyyy
from app.expiry import expiring_soon, expiring_today
from app.images import CONTAINER_ART, icon        # picture sizes + label positions, icon paths
from app.ingredient_catalog import food_type      # "nonveg" / "egg" / "veg"
from app.models import CONTAINER_LABELS, CONTAINERS, PantryItem
from app.units import UNIT_CHOICES
from app.ui.autocomplete import AutoCompleteInput
from app.ui.date_picker import DatePicker         # Day / Month / Year drop-downs
from app.ui.easter_egg import is_love, play_hearts   # the "love" surprise
from app.ui.widgets import (EGG_FILL, NONVEG_FILL, VEG_FILL,
                            DANGER, DANGER_SOFT, HEX_RED, INK, INPUT_BG, MUTED, NEUTRAL,
                            SELECTED_FILL, WHITE, Card, Header, Scene, SoftButton, SoftDropDown,
                            SoftInput, SoftSpinner, WrapLabel, bg_rect, colored, labeled,
                            light_popup, primary_action, scroll_list, set_bg, show_message)


# Food type -> (fill colour of the Name box, small coloured explanation under it).
FOOD_STYLES = {
    "nonveg": (NONVEG_FILL, "[color=d0605f][b]Non-veg item[/b][/color]"),
    "egg": (EGG_FILL, "[color=c98a2e][b]Egg[/b][/color]"),
    "veg": (VEG_FILL, "[color=4f8a5b][b]Vegetarian[/b][/color]"),
}

# The fridge's colours are the "fridge" scene in widgets.SCENES (shared look of all tabs).
SHELF = (1, 1, 1, 0.95)                           # white glass shelves and the door rail

MAX_ART_WIDTH = {"jar": dp(104), "dish": dp(104), "bottle": dp(84)}   # pictures never get bigger than this
EMPTY_SHELF_HEIGHT = dp(30)                       # an empty shelf is just a low gap with a line


def art_height(kind, width=None):
    """Height of a container picture drawn `width` wide (default: its biggest size)."""
    w, h = CONTAINER_ART[kind]["size"]
    return (width or MAX_ART_WIDTH[kind]) * h / w   # keep the picture's shape


def _text_size(text, font_size, wrap_width=None):
    """(width, height) the text would need in bold at this font size, wrapped at `wrap_width`."""
    label = CoreLabel(text=text, font_size=font_size, bold=True, halign="center",
                      text_size=(wrap_width, None))
    label.refresh()                                   # renders it off-screen
    return label.texture.size


def fit_font(text, width, height, largest=13, smallest=8):
    """The biggest font size at which `text` fits in the box without cutting a word in two."""
    for size in range(largest, smallest - 1, -1):     # try 13, 12, 11 ... 8
        font = sp(size)
        widest_word = max(_text_size(word, font)[0] for word in (text.split() or [text]))
        if widest_word <= width and _text_size(text, font, width)[1] <= height:
            return font
    return sp(smallest)                               # still too long: smallest size (end is cut off)


def expiry_text(item):
    """'Expires on 25-10-2026 (in 7 days)' for the item popup."""
    left = item.days_left()
    if left is None:
        return "[color=8a8f93]No expiry date[/color]"
    when = "today" if left == 0 else ("tomorrow" if left == 1 else f"in {left} days")
    text = f"Expires on [b]{format_date(item.expiry)}[/b] ({when})"
    return colored(text, HEX_RED) if left == 0 else text   # red on the last day


class ContainerArt(FloatLayout):
    """A bottle / jar / dish picture with the item's name written on its label."""

    def __init__(self, kind, name, expired=False, **kwargs):
        super().__init__(size_hint=(None, None), **kwargs)
        self.kind = kind
        w, h = CONTAINER_ART[kind]["size"]
        left, top, right, bottom = CONTAINER_ART[kind]["label"]   # design units, y = 0 at the top
        picture = f"container_{kind}_expired" if expired else f"container_{kind}"   # green = gone bad
        self.add_widget(Image(source=icon(picture), fit_mode="fill",       # our size keeps its shape
                              pos_hint={"x": 0, "y": 0}))   # FloatLayout only moves children with a pos_hint
        # The name covers exactly the cream label of the picture. Kivy measures y from the
        # BOTTOM, so the label's bottom edge is (h - bottom) / h of the way up.
        # (No "shorten": in Kivy it squeezes text onto ONE line. fit_font() picks a size instead.)
        self.name_label = Label(text=name, color=INK, bold=True, halign="center", valign="middle",
                                max_lines=3,
                                size_hint=((right - left) / w, (bottom - top) / h),
                                pos_hint={"x": left / w, "y": (h - bottom) / h})
        self.name_label.bind(size=self._fit_name)
        self.add_widget(self.name_label)

    def set_width(self, width):
        self.size = (width, art_height(self.kind, width))

    def _fit_name(self, label, size):
        """The label changed size: wrap the name inside it with the biggest font that fits."""
        width, height = max(size[0] - dp(6), 1), max(size[1] - dp(2), 1)   # a little inner margin
        label.text_size = (width, height)
        label.font_size = fit_font(label.text, width, height)


class ItemTile(ButtonBehavior, Widget):
    """One item standing on a shelf. `shrink` and `lift` drive the remove animation."""

    shrink = NumericProperty(1)                       # 1 = normal size, 0 = gone
    lift = NumericProperty(0)                         # how far it has floated up

    def __init__(self, item, on_open, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        # Move and scale everything this tile draws (the picture is a child, so it is included).
        with self.canvas.before:
            PushMatrix()                              # remember the normal drawing position...
            self._move = Translate()
            self._scale = Scale()
        with self.canvas.after:
            PopMatrix()                               # ...and go back to it after the tile
        self.art = ContainerArt(item.kept_in(), item.name, expired=item.is_expired())
        self.add_widget(self.art)
        self.bind(pos=self._place, size=self._place, shrink=self._place, lift=self._place)
        # on_press (finger down), not on_release: inside a scrolling page it reacts at once (4.0.1)
        self.bind(on_press=lambda *_: on_open(item))

    def _place(self, *_):
        """Stand the picture on the bottom of the tile, centred, as wide as fits."""
        self.art.set_width(min(self.width, MAX_ART_WIDTH[self.art.kind]))
        self.art.pos = (self.center_x - self.art.width / 2, self.y)
        self._move.y = self.lift
        self._scale.x = self._scale.y = self.shrink
        self._scale.origin = self.art.center          # shrink towards the picture's middle

    def vanish(self, on_done):
        """The 'disappearing from the fridge' animation, then call on_done()."""
        self.disabled = True                          # no second tap while it plays
        # "in_back" first grows the item a tiny bit, then pulls it away - like a little pop.
        anim = Animation(shrink=0.1, lift=dp(36), opacity=0, duration=0.55, t="in_back")
        anim.bind(on_complete=lambda *_: on_done())
        anim.start(self)


class ShelfRow(GridLayout):
    """A row of up to `cols` items standing on a shelf line."""

    def __init__(self, tiles, cols, height, **kwargs):
        super().__init__(cols=cols, spacing=dp(6), padding=(0, 0, 0, dp(8)), size_hint_y=None,
                         height=height + dp(8), **kwargs)   # dp(8) at the bottom = room for the shelf
        self.has_items = bool(tiles)                     # False = an empty shelf
        for tile in tiles:
            self.add_widget(tile)
        for _ in range(cols - len(tiles)):               # empty places keep the columns the same width
            self.add_widget(Widget())
        with self.canvas.before:                         # the shelf is drawn behind the items
            Color(*SHELF)
            self._shelf = Rectangle()
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        # A 4 dp thick line along the bottom, a bit wider than the row (like the sketch).
        self._shelf.pos = (self.x - dp(4), self.y + dp(2))
        self._shelf.size = (self.width + dp(8), dp(4))


class DoorRack(BoxLayout):
    """The door shelf: bottles standing behind a white rail, with posts at both ends."""

    def __init__(self, rows, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(8), size_hint_y=None,
                         padding=(dp(8), dp(4), dp(8), 0), **kwargs)
        self.bind(minimum_height=self.setter("height"))  # as tall as its rows
        for row in rows:
            self.add_widget(row)
        self._rows = rows
        with self.canvas.after:                          # drawn IN FRONT of the bottles, like a real rail
            Color(*SHELF)
            self._lines = [Line(width=dp(1.6)) for _ in range(2 + len(rows))]
        self.bind(pos=self._draw, size=self._draw)
        for row in rows:                                 # rows are placed AFTER the rack moves, so
            row.bind(pos=self._draw)                     # redraw the rails when they move too

    def _draw(self, *_):
        left, right = self.x + dp(1), self.right - dp(1)
        top = self.top - dp(2)
        self._lines[0].points = [left, top, left, self.y + dp(4)]       # left post
        self._lines[1].points = [right, top, right, self.y + dp(4)]     # right post
        for line, row in zip(self._lines[2:], self._rows):              # one front rail per row,
            y = row.y + dp(8) + dp(12)                                  # low, under the name labels
            line.points = [left, y, right, y] if row.has_items else []


def chunks(items, size):
    """[1,2,3,4,5], 2 -> [[1,2], [3,4], [5]]: splits the items into shelf rows."""
    return [items[i:i + size] for i in range(0, len(items), size)]


class PantryScreen(Screen):
    """The Fridge tab."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app                                    # gives access to app.db and helpers
        self.tiles = {}                                   # item id -> its tile (for the animation)
        root = BoxLayout(orientation="vertical")
        self.header = Header("My Fridge", icon="tab_fridge")
        root.add_widget(self.header)
        body = BoxLayout(orientation="vertical", padding=(dp(16), dp(4), dp(16), dp(8)), spacing=dp(10))
        # Banner area for "expires today" warnings (filled in refresh()).
        self.banner = BoxLayout(orientation="vertical", size_hint_y=None, height=0)   # height=0: empty = no gap
        self.banner.bind(minimum_height=self.banner.setter("height"))
        body.add_widget(self.banner)
        # The fridge itself stays put and its shelves scroll INSIDE it, like looking into a real one.
        self.scene = Scene("fridge")
        with self.scene.canvas.after:                     # the door handle on the right of the frame
            Color(1, 1, 1, 0.9)
            self._handle = RoundedRectangle(radius=[dp(3)])
        self.scene.bind(pos=self._draw_handle, size=self._draw_handle)
        scroll, self.list_box = scroll_list(spacing=dp(6), padding=(0, 0, 0, dp(4)))
        self.scene.inner.add_widget(scroll)
        body.add_widget(self.scene)
        # The big green button under the fridge (the same main button as on the other tabs).
        body.add_widget(primary_action("+  Add Item", lambda: AddItemPopup(self.app, self.refresh).open()))
        root.add_widget(body)
        self.add_widget(root)

    def _draw_handle(self, *_):
        """A short white bar in the right edge of the frame, near the top - the fridge door handle."""
        self._handle.pos = (self.scene.right - dp(7), self.scene.top - dp(118))
        self._handle.size = (dp(5), dp(76))

    def on_pre_enter(self, *_):
        """Kivy calls this just before the screen is shown - always show fresh data."""
        self.refresh()

    def refresh(self):
        items = self.app.db.list_pantry()                 # read everything from SQLite
        food = [i for i in items if not i.is_water]       # Water is always there - don't count it
        today_items = expiring_today(items)
        soon = expiring_soon(items)
        self.header.set_subtitle(f"{len(food)} items • {len(today_items) + len(soon)} expiring soon")
        self.banner.clear_widgets()
        if today_items:                                   # soft red card at the top
            card = Card(color=DANGER_SOFT, shadow=False)
            names = ", ".join(i.name for i in today_items)
            card.add_widget(WrapLabel(text=colored(f"Use today: {names}", HEX_RED, True)))
            card.add_widget(WrapLabel(text="Dishes using these are shown first on the Recipes tab.",
                                      font_size=sp(13), color=MUTED))
            self.banner.add_widget(card)

        self.list_box.clear_widgets()                     # rebuild the shelves from scratch
        self.tiles = {}
        self._fill_fridge(items, empty=not food)

    # ---------------------------------------------------------------- drawing helpers
    def _rows(self, items, cols, kind, minimum=1):
        """Shelf rows for `items`, `cols` per row; at least `minimum` rows (empty shelves too)."""
        tiles = [ItemTile(i, self.open_item) for i in items]
        self.tiles.update({t.item.id: t for t in tiles})  # remembered for the remove animation
        groups = chunks(tiles, cols)
        groups += [[] for _ in range(minimum - len(groups))]   # add empty shelves if needed
        return [ShelfRow(g, cols, art_height(kind) if g else EMPTY_SHELF_HEIGHT) for g in groups]

    def _fill_fridge(self, items, empty):
        """Jars on the shelves, dishes on the leftovers shelf, bottles in the door rack."""
        inner = self.list_box                             # the scrolling inside of the fridge
        caption = self.scene.caption                      # the shared caption style, in white
        by_kind = {kind: [i for i in items if i.kept_in() == kind] for kind in CONTAINERS}
        if empty:                                         # only Water: say how to start
            inner.add_widget(WrapLabel(text="Your fridge is empty. Tap [b]+ Add Item[/b] below.",
                                       color=WHITE, halign="center", font_size=sp(14)))
        inner.add_widget(caption("Shelves"))
        for row in self._rows(by_kind["jar"], 3, "jar", minimum=2):
            inner.add_widget(row)
        inner.add_widget(caption("Leftovers"))
        for row in self._rows(by_kind["dish"], 3, "dish"):
            inner.add_widget(row)
        inner.add_widget(caption("Door rack"))
        inner.add_widget(DoorRack(self._rows(by_kind["bottle"], 3, "bottle")))

    # ---------------------------------------------------------------- tapping an item
    def open_item(self, item):
        """Water -> a short note, expired food -> Throw Away, anything else -> quantity / remove."""
        if item.is_water:
            show_message("Water", "Water is always in your fridge.\nIt never runs out and never expires.",
                         height=dp(230))
        elif item.is_expired():
            self._throw_away_popup(item)
        else:
            EditItemPopup(self.app, item, on_saved=self.refresh, on_remove=self.remove_item).open()

    def _throw_away_popup(self, item):
        """Expired food: the only thing to do is throw it away."""
        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(12))
        box.add_widget(WrapLabel(text=f"This went bad on [b]{format_date(item.expiry)}[/b].",
                                 color=MUTED))
        popup = light_popup(item.name, box, height=dp(210))

        def _throw(*_):
            popup.dismiss()
            self.remove_item(item)
        box.add_widget(SoftButton("Throw Away", bg=DANGER, on_release=_throw))
        popup.open()

    def remove_item(self, item):
        """Play the 'disappearing' animation, then delete the item and redraw the fridge."""
        def _delete():
            self.app.db.delete_pantry_item(item.id)
            self.refresh()
        tile = self.tiles.get(item.id)
        if tile is None:                                  # not on screen (shouldn't happen): just delete
            _delete()
        else:
            tile.vanish(_delete)


class EditItemPopup:
    """Tapping fresh food: change the quantity, or remove it from the fridge. Nothing else."""

    def __init__(self, app, item, on_saved, on_remove):
        self.app, self.item, self.on_saved = app, item, on_saved
        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
        box.add_widget(WrapLabel(text=expiry_text(item), font_size=sp(14)))   # shown, not changeable
        row = BoxLayout(spacing=dp(8))
        self.qty_in = SoftInput(text=f"{item.quantity:g}", input_filter="float", hint_text="Quantity")
        row.add_widget(self.qty_in)
        row.add_widget(Label(text=item.unit, color=INK, font_size=sp(15), size_hint_x=0.35))   # e.g. "pcs"
        box.add_widget(labeled("Quantity", row))
        self.error = WrapLabel(text="", color=DANGER)     # validation messages appear here
        box.add_widget(self.error)
        box.add_widget(Widget())                          # pushes the buttons to the bottom
        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))

        def _remove(*_):
            self.popup.dismiss()
            on_remove(item)                               # the screen plays the animation
        buttons.add_widget(SoftButton("Remove from fridge", bg=DANGER_SOFT, fg=DANGER,
                                      font_size=sp(14), on_release=_remove))
        buttons.add_widget(SoftButton("Save", size_hint_x=0.6, on_release=lambda *_: self._save()))
        box.add_widget(buttons)
        self.popup = light_popup(item.name, box, height=dp(320))

    def open(self):
        self.popup.open()

    def _save(self):
        try:
            quantity = float(self.qty_in.text)
            if quantity <= 0:
                raise ValueError
        except ValueError:                                # empty or zero
            self.error.text = "Please enter a quantity greater than 0 (or tap Remove from fridge)."
            return
        self.item.quantity = quantity
        self.app.db.update_pantry_item(self.item)
        self.popup.dismiss()
        self.on_saved()


class ContainerChoice(ButtonBehavior, BoxLayout):
    """One line in the container drop-down: picture + name."""

    def __init__(self, kind, **kwargs):
        super().__init__(size_hint_y=None, height=dp(52), padding=(dp(8), dp(4)), spacing=dp(10), **kwargs)
        self.kind = kind
        bg_rect(self, WHITE, radius=dp(12))
        self.add_widget(Image(source=icon(f"container_{kind}"), fit_mode="contain",
                              size_hint_x=None, width=dp(40)))
        self.label = Label(text=CONTAINER_LABELS[kind], color=INK, font_size=sp(15), halign="left")
        self.label.bind(size=lambda l, s: setattr(l, "text_size", s))   # left-align
        self.add_widget(self.label)

    def set_selected(self, selected):
        set_bg(self, SELECTED_FILL if selected else WHITE)   # the current choice is light green
        self.label.bold = selected


class ContainerButton(ButtonBehavior, BoxLayout):
    """The small picture next to the Name box. Tap it: a drop-down with Bottle / Glass jar / Dish."""

    def __init__(self, value="jar", **kwargs):
        super().__init__(size_hint_x=None, width=dp(58), padding=dp(5), **kwargs)
        bg_rect(self, INPUT_BG, radius=dp(14))            # same grey box as the text inputs
        self.picture = Image(fit_mode="contain")
        self.add_widget(self.picture)
        with self.canvas.after:                           # a little "v" in the corner = "tap for more"
            Color(*MUTED)
            self._arrow = Triangle()
        self.bind(pos=self._draw_arrow, size=self._draw_arrow)
        self.dropdown = SoftDropDown(auto_width=False, width=dp(190))
        self.options = {}
        for kind in CONTAINERS:
            option = ContainerChoice(kind)
            option.bind(on_release=lambda o: self.dropdown.select(o.kind))
            self.options[kind] = option
            self.dropdown.add_widget(option)
        self.dropdown.bind(on_select=lambda _dd, kind: self.set_value(kind))
        self.bind(on_release=lambda *_: self.dropdown.open(self))
        self.set_value(value)

    def _draw_arrow(self, *_):
        x, y = self.right - dp(9), self.y + dp(7)        # bottom-right corner
        self._arrow.points = [x - dp(4), y + dp(4), x + dp(4), y + dp(4), x, y]

    def set_value(self, kind):
        self.value = kind
        self.picture.source = icon(f"container_{kind}")
        for option_kind, option in self.options.items():
            option.set_selected(option_kind == kind)


class AddItemPopup:
    """Form for adding a new item: container + name, quantity & unit, expiry date.

    (A plain class that *builds* a Popup, rather than subclassing Popup, keeps the code simple.)
    """

    def __init__(self, app, on_saved=None):
        self.app, self.on_saved = app, on_saved
        form = GridLayout(cols=1, spacing=dp(10), padding=dp(6), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        # Row 1: the container picture (a jar unless you pick another) + the type-ahead name box.
        name_row = BoxLayout(spacing=dp(8))
        self.container_btn = ContainerButton("jar")
        name_row.add_widget(self.container_btn)
        self.name_in = AutoCompleteInput(text="", hint_text="Start typing, e.g. oni...",
                                         extra_names=app.db.ingredient_names(),
                                         on_pick=self._picked)
        name_row.add_widget(self.name_in)
        form.add_widget(labeled("Name", name_row))
        # Food-type colouring: light red = non-veg, light yellow = egg, light green = veg.
        self.food_hint = WrapLabel(text="", font_size=sp(12))   # e.g. "Non-veg item" under the box
        form.add_widget(self.food_hint)
        self.name_in.bind(text=lambda *_: self._show_food_type())

        qty_row = BoxLayout(spacing=dp(8))
        self.qty_in = SoftInput(text="", input_filter="float", hint_text="Quantity")   # numbers only
        self.unit_in = SoftSpinner(text="pcs", values=UNIT_CHOICES, size_hint_x=0.6)
        qty_row.add_widget(self.qty_in)
        qty_row.add_widget(self.unit_in)
        form.add_widget(labeled("Quantity & unit", qty_row))

        # Expiry date: Day / Month / Year drop-downs (dd-mm-yyyy). Every food has one now - only
        # the built-in Water never expires - so there is no "Never expires" switch any more.
        form.add_widget(WrapLabel(text="Expiry date", color=MUTED, font_size=sp(13)))
        self.date_picker = DatePicker(date.today() + timedelta(days=7), allow_never=False)
        form.add_widget(self.date_picker)

        self.error = WrapLabel(text="", color=DANGER)     # validation messages appear here
        form.add_widget(self.error)

        scroll = ScrollView(do_scroll_x=False)            # scrolls when the keyboard covers it
        scroll.add_widget(form)
        outer = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(6))
        outer.add_widget(scroll)
        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        buttons.add_widget(SoftButton("Cancel", bg=NEUTRAL, fg=INK,
                                      on_release=lambda *_: self.popup.dismiss()))
        buttons.add_widget(SoftButton("Save", on_release=lambda *_: self._save()))
        outer.add_widget(buttons)
        self.popup = light_popup("Add item", outer, size_hint=(0.94, None), height=dp(500))   # scrolls if the screen is smaller
        # Close the suggestion list together with the form, so it can't stay floating on screen.
        self.popup.bind(on_dismiss=lambda *_: self.name_in.close_suggestions())

    def open(self):
        self.popup.open()

    def _show_food_type(self):
        """Colour the Name box by food type and explain the colour underneath."""
        kind = food_type(self.name_in.text)               # "nonveg" / "egg" / "veg" / None
        fill, hint = FOOD_STYLES.get(kind, (None, ""))    # None = normal grey / green-when-selected
        self.name_in.set_tint(fill)
        self.food_hint.text = hint

    def _picked(self, name, info):
        """A suggestion was chosen: pre-fill the usual unit."""
        if info:
            self.unit_in.text = info[0]                   # info = (unit, category)
        self.qty_in.focus = True                          # jump straight to the quantity box

    def _save(self):
        """Validate the form, then add the item to the database."""
        name = self.name_in.text.strip()
        if not name:
            self.error.text = "Please enter a name."
            return
        if is_love(name):                                 # easter egg: "love" is never stored
            self.popup.dismiss()                          # close the form...
            play_hearts()                                 # ...and let the hearts fly instead
            return
        if PantryItem(name, 0, "l").is_water:             # Water is built in
            self.error.text = "Water is always in your fridge - no need to add it."
            return
        try:
            quantity = float(self.qty_in.text)
            if quantity <= 0:
                raise ValueError
        except ValueError:                                # empty or zero quantity
            self.error.text = "Please enter a quantity greater than 0."
            return
        expiry = self.date_picker.get_date()
        if expiry < date.today():
            self.error.text = "That date has already passed - please pick today or later."
            return
        # Two items with the same name stay two separate items (e.g. two packs of milk with
        # different dates). Cooking uses the one that expires soonest first (recipe_engine.py).
        self.app.db.add_pantry_item(PantryItem(name=name, quantity=quantity, unit=self.unit_in.text,
                                               category="Fridge", expiry=expiry,
                                               container=self.container_btn.value))
        self.popup.dismiss()
        self.app.check_expiry()                           # a new item might expire today
        if self.on_saved:
            self.on_saved()
