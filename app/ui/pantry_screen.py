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
from kivy.graphics import (Color, Line, PopMatrix, PushMatrix, Quad, RoundedRectangle,
                           Scale, Translate)          # low-level drawing: shelves, door bin, handle
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty       # values Animation can change smoothly
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
from app.ingredient_catalog import FRIDGE_UNITS, guess_info   # kg/pcs/L + unit, tag, shelf life (5.0)
from app.models import CONTAINER_PLACE, PantryItem, guess_container
from app.validation import name_error, parse_quantity   # 4.7.1: shared input rules
from app.ui.autocomplete import AutoCompleteInput
from app.ui.date_picker import DatePicker         # Day / Month / Year drop-downs
from app.ui.easter_egg import is_love, play_hearts   # the "love" surprise
from app.ui.widgets import (TAG_STYLES, Chip,
                            DANGER, DANGER_SOFT, HEX_RED, INK, MUTED, NEUTRAL,
                            WHITE, Card, Header, Scene, SoftButton, TapBehavior,
                            gradient_texture,
                            SoftInput, SoftSpinner, WrapLabel, bg_rect, colored, labeled,
                            light_popup, primary_action, scroll_list, show_message)


# Food type -> (fill colour of the Name box, small coloured explanation under it).

# The fridge's colours are the "fridge" scene in widgets.SCENES (shared look of all tabs).
SHELF = (1, 1, 1, 0.95)                           # white glass shelves and the door rail

# How tall each picture is drawn (the width follows from its shape). Drinks are a bit taller.
ART_HEIGHT = {"bottle": dp(104), "carton": dp(100), "glass": dp(96)}
DEFAULT_ART_HEIGHT = dp(88)
STICKER = (1, 0.98, 0.93, 0.96)                   # the cream name sticker on each container
SHELF_BASE = dp(12)                               # items stand this high above the bottom of a shelf row
EMPTY_SHELF_HEIGHT = dp(30)                       # an empty shelf is just a low gap with a line


def art_height(kind):
    """The (biggest) height a container picture is drawn at."""
    return ART_HEIGHT.get(kind, DEFAULT_ART_HEIGHT)


def art_size(kind, max_width):
    """(width, height) of a container picture: its normal height, made smaller only if it would be
    wider than `max_width`. The picture's shape is always kept."""
    w, h = CONTAINER_ART[kind]["size"]
    height = art_height(kind)
    width = height * w / h                          # same shape as the picture file
    if width > max_width:                           # too wide for its place on the shelf:
        width, height = max_width, max_width * h / w   # shrink both sides equally
    return width, height


def _text_size(text, font_size, wrap_width=None):
    """(width, height) the text would need in bold at this font size, wrapped at `wrap_width`."""
    label = CoreLabel(text=text, font_size=font_size, bold=True, halign="center",
                      text_size=(wrap_width, None))
    label.refresh()                                   # renders it off-screen
    return label.texture.size


def fit_font(text, width, height, largest=13, smallest=8):
    """The biggest font size at which `text` fits in the box without cutting a word in two (or None)."""
    for size in range(largest, smallest - 1, -1):     # try 13, 12, 11 ... 8
        font = sp(size)
        widest_word = max(_text_size(word, font)[0] for word in (text.split() or [text]))
        if widest_word <= width and _text_size(text, font, width)[1] <= height:
            return font
    return None                                       # does not fit even at the smallest size


def fit_label_text(text, width, height, smallest=8):
    """(text, font) that fits the box: the full name if possible, else a shortened "Long nam..."

    4.7.1: before, a name too long even at the smallest font spilled out of the jar's label.
    """
    font = fit_font(text, width, height, smallest=smallest)
    if font is not None:                              # the whole name fits
        return text, font
    font = sp(smallest)
    for end in range(len(text) - 1, 0, -1):           # drop one character at a time from the end
        short = text[:end].rstrip() + "…"             # "…" = one ellipsis character
        widest = max(_text_size(word, font)[0] for word in short.split())
        if widest <= width and _text_size(short, font, width)[1] <= height:
            return short, font
    return "…", font                                  # a box too tiny for any letter


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
        self.full_name = name                         # kept whole; the label may show a shortened copy
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
        bg_rect(self.name_label, STICKER, radius=dp(7))   # the 3D pictures have no label: add a sticker
        self.name_label.bind(size=self._fit_name)
        self.add_widget(self.name_label)

    def fit(self, max_width):
        """Take the biggest size that fits `max_width` (see art_size)."""
        self.size = art_size(self.kind, max_width)

    def _fit_name(self, label, size):
        """The label changed size: wrap the name inside it with the biggest font that fits."""
        width, height = max(size[0] - dp(6), 1), max(size[1] - dp(2), 1)   # a little inner margin
        label.text_size = (width, height)
        label.text, label.font_size = fit_label_text(self.full_name, width, height)   # 4.7.1: "…" if too long


class ItemTile(TapBehavior, Widget):
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
        # on_tap (4.7.1): opens on a real tap only, so resting a thumb to scroll no longer opens it
        self.bind(on_tap=lambda *_: on_open(item))

    def _place(self, *_):
        """Stand the picture on the bottom of the tile, centred, as wide as fits."""
        self.art.fit(self.width)
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
    """A row of up to `cols` items standing on a 3D glass shelf (version 4.4).

    The shelf is drawn in layers: a soft shadow on the fridge wall below it, the see-through glass
    top (narrower at the back = perspective), a bright frosted front edge, and two small support
    pegs at the ends.
    """

    def __init__(self, tiles, cols, height, **kwargs):
        super().__init__(cols=cols, spacing=dp(6), padding=(0, 0, 0, SHELF_BASE), size_hint_y=None,
                         height=height + SHELF_BASE, **kwargs)
        self.has_items = bool(tiles)                     # False = an empty shelf
        for tile in tiles:
            self.add_widget(tile)
        for _ in range(cols - len(tiles)):               # empty places keep the columns the same width
            self.add_widget(Widget())
        with self.canvas.before:                         # the shelf is drawn behind the items
            Color(1, 1, 1, 1)
            self._shadow = RoundedRectangle(radius=[1], texture=gradient_texture(
                (0.02, 0.14, 0.36, 0.30), (0.02, 0.14, 0.36, 0)))   # shadow fading down the wall
            Color(0.86, 0.94, 1, 0.30)
            self._glass = Quad()                          # the glass top, seen slightly from above
            Color(0.80, 0.88, 0.98, 1)
            self._pegs = [RoundedRectangle(radius=[dp(2)]) for _ in range(2)]
            Color(1, 1, 1, 1)
            self._front = RoundedRectangle(radius=[dp(2.5)], texture=gradient_texture(
                (1, 1, 1, 1), (0.80, 0.90, 1, 0.95)))      # frosted front edge
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        x, y, w = self.x, self.y, self.width
        self._shadow.pos, self._shadow.size = (x, y - dp(12)), (w, dp(14))
        self._glass.points = [x - dp(2), y + dp(7), x + w + dp(2), y + dp(7),     # front edge...
                              x + w - dp(12), y + dp(17), x + dp(12), y + dp(17)]   # ...back edge
        self._front.pos, self._front.size = (x - dp(3), y + dp(3)), (w + dp(6), dp(5))
        for peg, px in zip(self._pegs, (x - dp(3), x + w - dp(7))):
            peg.pos, peg.size = (px, y - dp(1)), (dp(10), dp(5))


class DoorRack(BoxLayout):
    """The door shelf: items stand in a clear acrylic bin - you see them through its front panel."""

    def __init__(self, rows, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(8), size_hint_y=None,
                         padding=(dp(4), dp(4), dp(4), 0), **kwargs)
        self.bind(minimum_height=self.setter("height"))  # as tall as its rows
        for row in rows:
            self.add_widget(row)
        self._rows = rows
        self._bins = []
        with self.canvas.after:                          # drawn IN FRONT of the items, like real plastic
            for _ in rows:
                Color(1, 1, 1, 1)
                panel = RoundedRectangle(radius=[dp(10)], texture=gradient_texture(
                    (0.92, 0.97, 1, 0.42), (0.85, 0.93, 1, 0.20)))      # clear, slightly frosted panel
                Color(1, 1, 1, 0.95)
                rim = Line(width=dp(1.4))                 # its bright top edge
                Color(1, 1, 1, 0.5)
                gleam = Line(width=dp(1))                 # a small reflection
                self._bins.append((panel, rim, gleam))
        self.bind(pos=self._draw, size=self._draw)
        for row in rows:                                 # rows are placed and sized AFTER the rack, so
            row.bind(pos=self._draw, size=self._draw)    # redraw the bins when they move or resize too

    def _draw(self, *_):
        for (panel, rim, gleam), row in zip(self._bins, self._rows):
            x, w = row.x - dp(6), row.width + dp(12)
            height = min(dp(40), row.height - dp(2))     # the bin covers the lower part of the items
            y = row.y + dp(2)
            panel.pos, panel.size = (x, y), (w, height)
            rim.rounded_rectangle = (x, y, w, height, dp(10))
            gleam.points = [x + dp(14), y + height - dp(7), x + dp(60), y + height - dp(7)]


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
    def _rows(self, items, cols, minimum=1):
        """Shelf rows for `items`, `cols` per row; at least `minimum` rows (empty shelves too).
        Each row is as tall as its tallest container (a can and a jar can share a shelf)."""
        tiles = [ItemTile(i, self.open_item) for i in items]
        self.tiles.update({t.item.id: t for t in tiles})  # remembered for the remove animation
        groups = chunks(tiles, cols)
        groups += [[] for _ in range(minimum - len(groups))]   # add empty shelves if needed
        return [ShelfRow(g, cols, max(art_height(t.art.kind) for t in g) if g else EMPTY_SHELF_HEIGHT)
                for g in groups]

    def _fill_fridge(self, items, empty):
        """Jars on the shelves, dishes on the leftovers shelf, bottles in the door rack."""
        inner = self.list_box                             # the scrolling inside of the fridge
        caption = self.scene.caption                      # the shared caption style, in white
        place = {p: [i for i in items if CONTAINER_PLACE[i.kept_in()] == p]   # shelves / leftovers / door
                 for p in ("shelves", "leftovers", "door")}
        if empty:                                         # only Water: say how to start
            inner.add_widget(WrapLabel(text="Your fridge is empty. Tap [b]+ Add Item[/b] below.",
                                       color=WHITE, halign="center", font_size=sp(14)))
        inner.add_widget(caption("Shelves"))
        for row in self._rows(place["shelves"], 3, minimum=2):
            inner.add_widget(row)
        inner.add_widget(caption("Leftovers"))
        for row in self._rows(place["leftovers"], 3):
            inner.add_widget(row)
        inner.add_widget(caption("Door rack"))
        inner.add_widget(DoorRack(self._rows(place["door"], 3)))

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
        # 4.7.1: rule="qty" = positive, max 4 digits + 2 decimals; the old value is rounded to fit.
        self.qty_in = SoftInput(text=f"{round(item.quantity, 2):g}", rule="qty", hint_text="Quantity")
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
            quantity = parse_quantity(self.qty_in.text)   # 4.7.1: friendly message if empty / 0 / odd
        except ValueError as problem:
            self.error.text = f"{problem} (Or tap Remove from fridge.)"
            return
        self.item.quantity = quantity
        self.app.db.update_pantry_item(self.item)
        self.popup.dismiss()
        self.on_saved()


class AddItemPopup:
    """Quick "Add item" form (version 5.0 - testers wanted less typing).

    Type a name: the unit (kg / pcs / L), a usual amount, the tag (Fresh produce, Meat, ...) and the
    expiry date are filled in from the ingredient catalogue. Only the amount usually needs a look;
    the date can be changed with "Change", but never has to be.
    (A plain class that *builds* a Popup, rather than subclassing Popup, keeps the code simple.)
    """

    def __init__(self, app, on_saved=None):
        self.app, self.on_saved = app, on_saved
        self._auto_qty = ""                               # the amount WE filled in (so we may replace it)
        self._date_changed = False                        # True once the user picks a date themselves
        form = GridLayout(cols=1, spacing=dp(12), padding=dp(6), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        self.name_in = AutoCompleteInput(text="", hint_text="What did you buy? e.g. Milk", rule="name",
                                         extra_names=app.db.ingredient_names(), on_pick=self._picked)
        form.add_widget(labeled("Item", self.name_in))
        self.name_in.bind(text=lambda *_: self._fill_from_catalogue())

        qty_row = BoxLayout(spacing=dp(8))
        self.qty_in = SoftInput(text="", rule="qty", hint_text="Amount")   # positive, max 9999.99
        self.qty_in.bind(text=lambda *_: setattr(self, "_auto_qty", None)
                         if self.qty_in.text != self._auto_qty else None)   # the user typed their own
        self.unit_in = SoftSpinner(text="pcs", values=FRIDGE_UNITS, size_hint_x=0.55)
        qty_row.add_widget(self.qty_in)
        qty_row.add_widget(self.unit_in)
        form.add_widget(labeled("Amount", qty_row))

        # The tag chip, then "Expires 27-10-2026 (in 6 days)  [Change]" on its own line.
        tag_row = BoxLayout(size_hint_y=None, height=dp(26))
        self.tag_chip = Chip("Pantry", *TAG_STYLES["Pantry"][:2])
        tag_row.add_widget(self.tag_chip)
        tag_row.add_widget(Widget())                      # pushes the chip to the left
        form.add_widget(tag_row)
        expiry_row = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        self.expiry_label = Label(text="", markup=True, color=INK, font_size=sp(14), halign="left",
                                  valign="middle", shorten=True, shorten_from="right")
        self.expiry_label.bind(size=lambda l, sz: setattr(l, "text_size", sz))
        expiry_row.add_widget(self.expiry_label)
        expiry_row.add_widget(SoftButton("Change", size_hint=(None, None), size=(dp(84), dp(34)),
                                         bg=NEUTRAL, fg=INK, font_size=sp(13),
                                         on_release=lambda *_: self._toggle_date_picker()))
        form.add_widget(expiry_row)

        # The date picker stays hidden until "Change" is tapped.
        self.date_picker = DatePicker(date.today() + timedelta(days=7), allow_never=False)
        self._setting_date = False                        # True while WE change the date
        for spinner in (self.date_picker.day, self.date_picker.month, self.date_picker.year):
            spinner.bind(text=lambda *_: self._date_spinner_changed())
        self.form = form

        self.error = WrapLabel(text="", color=DANGER)     # validation messages appear here
        form.add_widget(self.error)

        scroll = ScrollView(do_scroll_x=False)            # scrolls when the keyboard covers it
        scroll.add_widget(form)
        outer = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(6))
        outer.add_widget(scroll)
        buttons = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        buttons.add_widget(SoftButton("Cancel", bg=NEUTRAL, fg=INK,
                                      on_release=lambda *_: self.popup.dismiss()))
        buttons.add_widget(SoftButton("Add to fridge", on_release=lambda *_: self._save()))
        outer.add_widget(buttons)
        self.popup = light_popup("Add item", outer, size_hint=(0.94, None), height=dp(400))
        # Close the suggestion list together with the form, so it can't stay floating on screen.
        self.popup.bind(on_dismiss=lambda *_: self.name_in.close_suggestions())
        self._fill_from_catalogue()

    def open(self):
        self.popup.open()

    # ------------------------------------------------------------------ automatic filling
    def _fill_from_catalogue(self):
        """Use the catalogue (or a sensible guess) for unit, amount, tag and expiry date."""
        name = self.name_in.text.strip()
        info = guess_info(name) if name else None
        if info:
            self.unit_in.text = info.unit
            if self._auto_qty is not None:                # the user hasn't typed an amount of their own
                self._auto_qty = f"{info.default_qty:g}"  # e.g. "1" (L of milk) or "0.25" (kg)
                self.qty_in.text = self._auto_qty
            bg, fg, _icon = TAG_STYLES[info.tag]
            self.tag_chip.text = info.tag
            self.tag_chip._bg_color.rgba, self.tag_chip.color = bg, fg
            if not self._date_changed:                    # don't overwrite a date the user picked
                self._setting_date = True
                self.date_picker.set_date(date.today() + timedelta(days=info.shelf_days))
                self._setting_date = False
        self.tag = info.tag if info else "Pantry"
        self._show_expiry()

    def _show_expiry(self):
        """'Expires 27-10-2026 (in 6 days)' in the summary line."""
        if not self.date_picker.day.text:                 # the picker is still being built
            return
        expiry = self.date_picker.get_date()
        left = (expiry - date.today()).days
        when = "today" if left == 0 else ("tomorrow" if left == 1 else f"in {left} days")
        self.expiry_label.text = f"Expires [b]{format_date(expiry)}[/b] ({when})"

    def _date_spinner_changed(self):
        """A Day / Month / Year drop-down changed: by the user (their date now wins) or by us."""
        if not self._setting_date:
            self._date_changed = True
        self._show_expiry()

    def _toggle_date_picker(self):
        """Show / hide the Day-Month-Year picker under the expiry line."""
        if self.date_picker.parent is None:               # hidden -> show it just above the error line
            self.form.add_widget(self.date_picker, index=1)
        else:
            self.form.remove_widget(self.date_picker)

    def _picked(self, name, info):
        """A suggestion was chosen: the text change already filled everything in - go to the amount."""
        self.qty_in.focus = True

    # ------------------------------------------------------------------ saving
    def _save(self):
        """Validate the form, then add the item to the database."""
        name = self.name_in.text.strip()
        problem = name_error(name, "name")                # 4.7.1: empty, over 126 characters, odd symbols
        if problem:
            self.error.text = problem
            return
        if is_love(name):                                 # easter egg: "love" is never stored
            self.popup.dismiss()                          # close the form...
            play_hearts()                                 # ...and let the hearts fly instead
            return
        if PantryItem(name, 0, "L").is_water:             # Water is built in
            self.error.text = "Water is always in your fridge - no need to add it."
            return
        try:
            quantity = parse_quantity(self.qty_in.text)   # 4.7.1: positive number, max 9999.99
        except ValueError as problem:
            self.error.text = str(problem)
            return
        expiry = self.date_picker.get_date()
        if expiry < date.today():
            self.error.text = "That date has already passed - please pick today or later."
            return
        unit = self.unit_in.text
        # Two items with the same name stay two separate items (e.g. two packs of milk with
        # different dates). Cooking uses the one that expires soonest first (recipe_engine.py).
        self.app.db.add_pantry_item(PantryItem(name=name, quantity=quantity, unit=unit,
                                               category="Fridge", expiry=expiry, tag=self.tag,
                                               container=guess_container(name, unit, self.tag)))
        self.popup.dismiss()
        self.app.check_expiry()                           # a new item might expire today
        if self.on_saved:
            self.on_saved()
