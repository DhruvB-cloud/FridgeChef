"""
pantry_screen.py
----------------
WHY THIS FILE EXISTS:
    The "Fridge" tab - where the user enters what they have (vegetables, herbs, curd, fruits,
    groceries), with quantity, unit and expiry date.

    Version 4.1 draws it as a real fridge (from Dhruv's own sketch):
        * jars stand on the white shelves at the top,
        * dishes (leftovers) stand on their own shelf,
        * bottles stand in the door rack at the bottom,
        * things kept outside the fridge sit on a wooden "kitchen shelf" underneath.
    Every item is drawn as the container the user picked in the form (bottle / glass jar / dish),
    with its name, amount and a coloured expiry pill. Tap an item to edit or delete it.

    A banner lists items expiring today. The item name box suggests ingredients while you type
    ("oni" -> Onion). Expiry dates are picked from Day / Month / Year drop-downs (dd-mm-yyyy).
    Easter egg: try adding "love".
"""

from datetime import date, timedelta              # expiry dates and "+3 days" buttons

from kivy.graphics import Color, Line, Rectangle  # low-level drawing: shelves and the door rail
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout    # centres the expiry pill under each item
from kivy.uix.behaviors import ButtonBehavior     # makes an item tappable
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image                  # the bottle / jar / dish pictures
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen         # one "page" of the app
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from app.dates import format_date                 # shows dates as dd-mm-yyyy
from app.expiry import expiring_soon, expiring_today
from app.images import icon                       # path of a bundled icon
from app.ingredient_catalog import food_type      # "nonveg" / "egg" / "veg"
from app.models import CATEGORIES, CONTAINER_LABELS, CONTAINERS, PantryItem, guess_container
from app.units import UNIT_CHOICES, pretty_quantity
from app.ui.autocomplete import AutoCompleteInput
from app.ui.date_picker import DatePicker         # Day / Month / Year drop-downs
from app.ui.easter_egg import is_love, play_hearts   # the "love" surprise
from app.ui.widgets import (EGG_FILL, NONVEG_FILL, VEG_FILL,
                            AMBER, AMBER_SOFT, DANGER, DANGER_SOFT, HEX_RED, INK, INPUT_BG, MUTED,
                            NEUTRAL, PRIMARY, PRIMARY_DARK, PRIMARY_SOFT, SELECTED_FILL, WHITE,
                            Card, Header, SoftButton, SoftInput, SoftSpinner, WrapLabel, bg_rect,
                            colored, confirm, escape, labeled, light_popup, scroll_list, set_bg)


# Food type -> (fill colour of the Name box, small coloured explanation under it).
FOOD_STYLES = {
    "nonveg": (NONVEG_FILL, "[color=d0605f][b]Non-veg item[/b][/color]"),
    "egg": (EGG_FILL, "[color=c98a2e][b]Egg[/b][/color]"),
    "veg": (VEG_FILL, "[color=4f8a5b][b]Vegetarian[/b][/color]"),
}

# Colours of the fridge drawing (the blues of the sketch, slightly softened).
FRIDGE_FRAME = (0.70, 0.84, 0.97, 1)              # light blue outer body of the fridge
FRIDGE_INSIDE = (0.29, 0.60, 0.92, 1)             # blue inside
SHELF = (1, 1, 1, 0.95)                           # white glass shelves and the door rail
# ...and of the wooden kitchen shelf for items kept outside the fridge.
WOOD_FRAME = (0.87, 0.75, 0.60, 1)
WOOD_INSIDE = (0.97, 0.92, 0.84, 1)
WOOD_SHELF = (0.74, 0.58, 0.42, 1)

ICON_HEIGHT = {"jar": dp(62), "dish": dp(58), "bottle": dp(78)}   # bottles are tall and thin
TEXT_HEIGHT = dp(76)                              # name (2 lines) + amount + expiry pill
EMPTY_SHELF_HEIGHT = dp(30)                       # an empty shelf is just a low gap with a line


def tile_expiry(item, today=None):
    """Short expiry text and pill colours for an item tile: (text, background, text colour)."""
    left = item.days_left(today)
    if left is None:
        return "No expiry", NEUTRAL, MUTED
    if left < 0:
        return "Expired", NEUTRAL, MUTED
    if left == 0:
        return "Today", DANGER_SOFT, DANGER           # red: use it today
    if left == 1:
        return "Tomorrow", AMBER_SOFT, AMBER
    if left == 2:
        return "2 days", AMBER_SOFT, AMBER
    return format_date(item.expiry), PRIMARY_SOFT, PRIMARY_DARK   # dd-mm-yyyy


class Pill(Label):
    """A small rounded label (like widgets.Chip, but smaller, so it fits under a bottle)."""

    def __init__(self, text, bg, fg, **kwargs):
        super().__init__(text=text, color=fg, font_size=sp(11), bold=True, size_hint=(None, None),
                         height=dp(20), **kwargs)
        bg_rect(self, bg, radius=dp(10))
        # Width follows the text: text width + 12dp padding.
        self.bind(texture_size=lambda *_: setattr(self, "width", self.texture_size[0] + dp(12)))


class ItemTile(ButtonBehavior, BoxLayout):
    """One item standing on a shelf: its container picture, then name, amount and expiry."""

    def __init__(self, item, on_open, text_color=WHITE, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(2), **kwargs)
        kind = item.kept_in()                            # "bottle" / "jar" / "dish"
        self.add_widget(Image(source=icon(f"container_{kind}"), fit_mode="contain",
                              size_hint_y=None, height=ICON_HEIGHT[kind]))
        name = Label(text=f"[b]{escape(item.name)}[/b]", markup=True, color=text_color,
                     font_size=sp(12), halign="center", valign="middle", size_hint_y=None,
                     height=dp(30), shorten=True, shorten_from="right", max_lines=2)
        name.bind(width=lambda l, w: setattr(l, "text_size", (w, None)))   # wrap inside the tile
        self.add_widget(name)
        amount = Label(text=pretty_quantity(item.quantity, item.unit), color=text_color,
                       font_size=sp(11), size_hint_y=None, height=dp(16))
        amount.opacity = 0.9                             # a little softer than the name
        self.add_widget(amount)
        holder = AnchorLayout(size_hint_y=None, height=dp(22))   # centres the pill
        holder.add_widget(Pill(*tile_expiry(item)))
        self.add_widget(holder)
        # on_press (finger down), not on_release: inside a scrolling page it reacts at once (4.0.1)
        self.bind(on_press=lambda *_: on_open(item))


class ShelfRow(GridLayout):
    """A row of up to `cols` items standing on a shelf line."""

    def __init__(self, tiles, cols, height, shelf_color=SHELF, **kwargs):
        super().__init__(cols=cols, spacing=dp(6), padding=(0, 0, 0, dp(8)), size_hint_y=None,
                         height=height + dp(8), **kwargs)   # dp(8) at the bottom = room for the shelf
        self.has_items = bool(tiles)                     # False = an empty shelf
        for tile in tiles:
            self.add_widget(tile)
        for _ in range(cols - len(tiles)):               # empty places keep the columns the same width
            self.add_widget(Widget())
        with self.canvas.before:                         # the shelf is drawn behind the items
            Color(*shelf_color)
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
        for line, row in zip(self._lines[2:], self._rows):              # one front rail per row:
            if not row.has_items:
                line.points = []                                         #   (none on an empty shelf)
                continue
            y = row.y + dp(8) + TEXT_HEIGHT + ICON_HEIGHT["bottle"] * 0.3   # across the bottles' lower part
            line.points = [left, y, right, y]


def chunks(items, size):
    """[1,2,3,4,5], 2 -> [[1,2], [3,4], [5]]: splits the items into shelf rows."""
    return [items[i:i + size] for i in range(0, len(items), size)]


class PantryScreen(Screen):
    """The Fridge tab."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app                                    # gives access to app.db and helpers
        root = BoxLayout(orientation="vertical")
        self.header = Header("My Fridge")
        root.add_widget(self.header)
        body = BoxLayout(orientation="vertical", padding=(dp(16), dp(4), dp(16), dp(8)), spacing=dp(10))
        # Banner area for "expires today" warnings (filled in refresh()).
        self.banner = BoxLayout(orientation="vertical", size_hint_y=None, height=0)   # height=0: empty = no gap
        self.banner.bind(minimum_height=self.banner.setter("height"))
        body.add_widget(self.banner)
        scroll, self.list_box = scroll_list(spacing=dp(14), padding=(0, dp(2), 0, dp(8)))   # fridge + shelf
        body.add_widget(scroll)
        # The big green button under the fridge, as in the sketch.
        body.add_widget(SoftButton("+  Add Item", height=dp(58), font_size=sp(22),
                                   on_release=lambda *_: self.open_item_popup()))
        root.add_widget(body)
        self.add_widget(root)

    def on_pre_enter(self, *_):
        """Kivy calls this just before the screen is shown - always show fresh data."""
        self.refresh()

    def refresh(self):
        items = self.app.db.list_pantry()                 # read everything from SQLite
        today_items = expiring_today(items)
        soon = expiring_soon(items)
        self.header.set_subtitle(f"{len(items)} items • {len(today_items) + len(soon)} expiring soon")
        self.banner.clear_widgets()
        if today_items:                                   # soft red card at the top
            card = Card(color=DANGER_SOFT, shadow=False)
            names = ", ".join(i.name for i in today_items)
            card.add_widget(WrapLabel(text=colored(f"Use today: {names}", HEX_RED, True)))
            card.add_widget(WrapLabel(text="Dishes using these are shown first on the Recipes tab.",
                                      font_size=sp(13), color=MUTED))
            self.banner.add_widget(card)

        self.list_box.clear_widgets()                     # rebuild the drawing from scratch
        in_fridge = [i for i in items if i.category == "Fridge"]
        outside = [i for i in items if i.category != "Fridge"]
        self.list_box.add_widget(self._fridge(in_fridge))
        if outside:                                       # the wooden shelf only when it has something
            self.list_box.add_widget(self._kitchen_shelf(outside))

    # ---------------------------------------------------------------- drawing helpers
    def _tiles(self, items, text_color=WHITE):
        return [ItemTile(i, self.open_item_popup, text_color=text_color) for i in items]

    def _rows(self, items, cols, kind, minimum, shelf_color=SHELF, text_color=WHITE):
        """Shelf rows for `items`, `cols` per row; at least `minimum` rows (empty shelves too)."""
        groups = chunks(self._tiles(items, text_color), cols)
        groups += [[] for _ in range(minimum - len(groups))]   # add empty shelves if needed
        return [ShelfRow(g, cols, ICON_HEIGHT[kind] + TEXT_HEIGHT if g else EMPTY_SHELF_HEIGHT,
                         shelf_color) for g in groups]

    @staticmethod
    def _cabinet(frame, inside, radius):
        """(outer body, inner box): two rounded boxes inside each other, like the sketch's fridge."""
        outer = BoxLayout(orientation="vertical", padding=dp(10), size_hint_y=None)
        outer.bind(minimum_height=outer.setter("height"))
        bg_rect(outer, frame, radius=radius + dp(8), shadow=True)
        inner = BoxLayout(orientation="vertical", padding=(dp(12), dp(10)), spacing=dp(6),
                          size_hint_y=None)
        inner.bind(minimum_height=inner.setter("height"))
        bg_rect(inner, inside, radius=radius)
        outer.add_widget(inner)
        return outer, inner

    @staticmethod
    def _caption(text, color=(1, 1, 1, 0.75)):
        """Small faint caption above a part of the fridge ('Shelves', 'Door rack'...)."""
        label = Label(text=text, color=color, font_size=sp(11), bold=True, size_hint_y=None,
                      height=dp(16), halign="left")
        label.bind(size=lambda l, s: setattr(l, "text_size", s))   # left-align
        return label

    def _fridge(self, items):
        """The blue fridge: jars on the shelves, dishes on the leftovers shelf, bottles in the door."""
        outer, inner = self._cabinet(FRIDGE_FRAME, FRIDGE_INSIDE, dp(20))
        by_kind = {kind: [i for i in items if i.kept_in() == kind] for kind in CONTAINERS}
        if not items:                                     # empty fridge: say how to start
            inner.add_widget(WrapLabel(text="Your fridge is empty. Tap [b]+ Add Item[/b] below.",
                                       color=WHITE, halign="center", font_size=sp(14)))
        inner.add_widget(self._caption("Shelves"))
        for row in self._rows(by_kind["jar"], 3, "jar", minimum=2):
            inner.add_widget(row)
        inner.add_widget(self._caption("Leftovers"))
        for row in self._rows(by_kind["dish"], 3, "dish", minimum=1):
            inner.add_widget(row)
        inner.add_widget(self._caption("Door rack"))
        bottle_rows = [ShelfRow(g, 4, ICON_HEIGHT["bottle"] + TEXT_HEIGHT if g else EMPTY_SHELF_HEIGHT)
                       for g in (chunks(self._tiles(by_kind["bottle"]), 4) or [[]])]   # shelf line = rack bottom
        inner.add_widget(DoorRack(bottle_rows))
        return outer

    def _kitchen_shelf(self, items):
        """A wooden shelf for things kept outside the fridge (category 'Outside')."""
        outer, inner = self._cabinet(WOOD_FRAME, WOOD_INSIDE, dp(16))
        inner.add_widget(self._caption("Outside the fridge", color=MUTED))
        tallest = "bottle" if any(i.kept_in() == "bottle" for i in items) else "jar"
        for row in self._rows(items, 3, tallest, minimum=1, shelf_color=WOOD_SHELF, text_color=INK):
            inner.add_widget(row)
        return outer

    def open_item_popup(self, item=None):
        """Open the Add (item=None) or Edit (item given) form."""
        ItemPopup(self.app, item, on_saved=self.refresh).open()


class ContainerOption(ButtonBehavior, BoxLayout):
    """One choice in the container picker: a picture with its name under it."""

    def __init__(self, kind, on_pick, **kwargs):
        super().__init__(orientation="vertical", padding=dp(6), spacing=dp(2), **kwargs)
        self.kind = kind
        bg_rect(self, INPUT_BG, radius=dp(14))            # grey box, green when chosen
        with self.canvas.after:                           # a green ring around the chosen one
            self._ring_color = Color(*PRIMARY[:3], 0)     # invisible (alpha 0) until chosen
            self._ring = Line(width=dp(1.5))
        self.bind(pos=self._draw_ring, size=self._draw_ring)
        self.add_widget(Image(source=icon(f"container_{kind}"), fit_mode="contain"))
        self.label = Label(text=CONTAINER_LABELS[kind], color=INK, font_size=sp(13),
                           size_hint_y=None, height=dp(20))
        self.add_widget(self.label)
        self.bind(on_press=lambda *_: on_pick(kind))

    def _draw_ring(self, *_):
        self._ring.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(14))

    def set_selected(self, selected):
        set_bg(self, SELECTED_FILL if selected else INPUT_BG)
        self._ring_color.a = 1 if selected else 0
        self.label.color = PRIMARY_DARK if selected else INK
        self.label.bold = selected


class ContainerPicker(BoxLayout):
    """Bottle / Glass jar / Dish - what the item is kept in (and how it is drawn in the fridge)."""

    def __init__(self, value, on_change=None, **kwargs):
        super().__init__(spacing=dp(8), **kwargs)
        self.on_change = on_change                        # called when the USER taps an option
        self.options = [ContainerOption(kind, self._tapped) for kind in CONTAINERS]
        for option in self.options:
            self.add_widget(option)
        self.select(value)

    def _tapped(self, kind):
        self.select(kind)
        if self.on_change:
            self.on_change(kind)

    def select(self, kind):
        self.value = kind
        for option in self.options:
            option.set_selected(option.kind == kind)


class ItemPopup:
    """Form for adding / editing one pantry item.

    (A plain class that *builds* a Popup, rather than subclassing Popup, keeps the code simple.)
    """

    def __init__(self, app, item=None, on_saved=None):
        self.app, self.item, self.on_saved = app, item, on_saved
        form = GridLayout(cols=1, spacing=dp(10), padding=dp(6), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        # Type-ahead name box: picking "Onion" also fills in the unit (pcs) and category (Outside).
        self.name_in = AutoCompleteInput(text=item.name if item else "",
                                         hint_text="Start typing, e.g. oni...",
                                         extra_names=app.db.ingredient_names(),
                                         on_pick=self._picked)
        form.add_widget(labeled("Name", self.name_in))
        # Food-type colouring: light red = non-veg, light yellow = egg, light green = veg.
        self.food_hint = WrapLabel(text="", font_size=sp(12))   # e.g. "Non-veg item" under the box
        form.add_widget(self.food_hint)
        self.name_in.bind(text=lambda *_: self._show_food_type())
        self._show_food_type()                            # colour an existing name when editing

        self.cat_in = SoftSpinner(text=item.category if item else "Fridge", values=CATEGORIES)
        form.add_widget(labeled("Where is it?", self.cat_in))

        qty_row = BoxLayout(spacing=dp(8))
        self.qty_in = SoftInput(text=f"{item.quantity:g}" if item else "",
                                input_filter="float", hint_text="Quantity")   # numbers only
        self.unit_in = SoftSpinner(text=item.unit if item else "pcs", values=UNIT_CHOICES,
                                   size_hint_x=0.6)
        qty_row.add_widget(self.qty_in)
        qty_row.add_widget(self.unit_in)
        form.add_widget(labeled("Quantity & unit", qty_row))

        # Container picker: how the item is drawn in the fridge. Until the user taps one, it follows
        # the name and unit ("Soy sauce" in ml -> Bottle); after a tap, the user's choice stays.
        self.container_chosen = bool(item and item.container)
        self.container_in = ContainerPicker(item.kept_in() if item else "jar",
                                            on_change=lambda kind: setattr(self, "container_chosen", True))
        form.add_widget(labeled("Keep it in", self.container_in, height=dp(96)))
        self.name_in.bind(text=lambda *_: self._guess_container())
        self.unit_in.bind(text=lambda *_: self._guess_container())

        # Expiry date: Day / Month / Year drop-downs (dd-mm-yyyy) + "Never expires" switch.
        form.add_widget(WrapLabel(text="Expiry date", color=MUTED, font_size=sp(13)))
        new_item_default = date.today() + timedelta(days=7)          # new items: one week from today
        self.date_picker = DatePicker(item.expiry if item else new_item_default)   # editing: its own date
        form.add_widget(self.date_picker)
        # Quick buttons: one tap for the most common choices.
        quick = GridLayout(cols=3, spacing=dp(6), size_hint_y=None, height=dp(2 * 36 + 6))
        for label, days in [("Today", 0), ("+1 day", 1), ("+3 days", 3), ("+1 week", 7),
                            ("+2 weeks", 14), ("+1 month", 30)]:
            quick.add_widget(SoftButton(label, height=dp(36), bg=NEUTRAL, fg=INK, font_size=sp(13),
                                        bold=False, on_release=lambda _b, d=days: self._set_days(d)))
            # 'd=days' freezes the current value - otherwise every button would use the last one.
        form.add_widget(quick)

        self.error = WrapLabel(text="", color=DANGER)     # validation messages appear here
        form.add_widget(self.error)

        scroll = ScrollView(do_scroll_x=False)            # scrolls when the keyboard covers it
        scroll.add_widget(form)
        outer = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(6))
        outer.add_widget(scroll)
        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        if item:                                          # editing: the items have no buttons any more,
            buttons.add_widget(SoftButton("Delete", bg=DANGER_SOFT, fg=DANGER,   # so Delete lives here
                                          on_release=lambda *_: self._delete()))
        buttons.add_widget(SoftButton("Cancel", bg=NEUTRAL, fg=INK,
                                      on_release=lambda *_: self.popup.dismiss()))
        buttons.add_widget(SoftButton("Save", on_release=lambda *_: self._save()))
        outer.add_widget(buttons)
        self.popup = light_popup("Edit item" if item else "Add item", outer, size_hint=(0.94, 0.9))
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

    def _guess_container(self):
        """Name or unit changed: update the container - unless the user already picked one."""
        if not self.container_chosen:
            self.container_in.select(guess_container(self.name_in.text, self.unit_in.text))

    def _picked(self, name, info):
        """A suggestion was chosen: pre-fill the usual unit and category."""
        if info:
            self.unit_in.text, self.cat_in.text = info
        self.qty_in.focus = True                          # jump straight to the quantity box

    def _set_days(self, days):
        """A quick button was tapped: set the drop-downs to today + `days`."""
        self.date_picker.set_date(date.today() + timedelta(days=days))

    def _delete(self):
        """Ask first, then remove the item being edited."""
        item = self.item

        def _do():
            self.app.db.delete_pantry_item(item.id)
            if self.on_saved:
                self.on_saved()                           # redraw the fridge
        self.popup.dismiss()                              # close the form, then ask
        confirm("Delete item", f"Remove {escape(item.name)} from your kitchen?", _do,
                yes_text="Delete", yes_color=DANGER, height=dp(230))

    def _save(self):
        """Validate the form, then insert or update the item in the database."""
        name = self.name_in.text.strip()
        if not name:
            self.error.text = "Please enter a name."
            return
        if is_love(name):                                 # easter egg: "love" is never stored
            self.popup.dismiss()                          # close the form...
            play_hearts()                                 # ...and let the hearts fly instead
            return
        try:
            quantity = float(self.qty_in.text)
            if quantity <= 0:
                raise ValueError
        except ValueError:                                # empty or zero quantity
            self.error.text = "Please enter a quantity greater than 0."
            return
        expiry = self.date_picker.get_date()              # a date, or None for "Never expires"
        new_item = PantryItem(name=name, quantity=quantity, unit=self.unit_in.text,
                              category=self.cat_in.text, expiry=expiry,
                              id=self.item.id if self.item else None,
                              container=self.container_in.value)   # bottle / jar / dish
        if self.item:
            self.app.db.update_pantry_item(new_item)
        else:
            self.app.db.add_pantry_item(new_item)
        self.popup.dismiss()
        self.app.check_expiry()                           # a new item might expire today
        if self.on_saved:
            self.on_saved()
