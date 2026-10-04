"""
pantry_screen.py
----------------
WHY THIS FILE EXISTS:
    The "Fridge" tab - where the user enters what they have (vegetables, herbs, curd, fruits,
    groceries), with quantity, unit and expiry date. Items are grouped into "Fridge" and
    "Outside" (cupboard / shelf) and get a soft colour chip showing how soon they expire. A banner
    lists items expiring today. The item name box suggests ingredients while you type
    ("oni" -> Onion). Expiry dates are picked from Day / Month / Year drop-downs (dd-mm-yyyy).
    Easter egg: try adding "love".
"""

from datetime import date, timedelta              # expiry dates and "+3 days" buttons

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen         # one "page" of the app
from kivy.uix.scrollview import ScrollView

from app.dates import format_date                 # shows dates as dd-mm-yyyy
from app.expiry import expiring_soon, expiring_today
from app.ingredient_catalog import food_type      # "nonveg" / "egg" / "veg"
from app.models import CATEGORIES, PantryItem
from app.units import UNIT_CHOICES, pretty_quantity
from app.ui.autocomplete import AutoCompleteInput
from app.ui.date_picker import DatePicker         # Day / Month / Year drop-downs
from app.ui.easter_egg import is_love, play_hearts   # the "love" surprise
from app.ui.widgets import (EGG_FILL, NONVEG_FILL, VEG_FILL,
                            AMBER, AMBER_SOFT, DANGER, DANGER_SOFT, HEX_RED, INK, MUTED, NEUTRAL,
                            PRIMARY_DARK, PRIMARY_SOFT, Card, Chip, ChipRow, Header, SoftButton,
                            SoftInput, SoftSpinner, WrapLabel, colored, confirm, escape, labeled,
                            light_popup, scroll_list, section_title)


# Food type -> (fill colour of the Name box, small coloured explanation under it).
FOOD_STYLES = {
    "nonveg": (NONVEG_FILL, "[color=d0605f][b]Non-veg item[/b][/color]"),
    "egg": (EGG_FILL, "[color=c98a2e][b]Egg[/b][/color]"),
    "veg": (VEG_FILL, "[color=4f8a5b][b]Vegetarian[/b][/color]"),
}


def expiry_chip(item, today=None):
    """A coloured pill describing the expiry, e.g. red 'Expires today'."""
    left = item.days_left(today)
    if left is None:
        return Chip("No expiry", NEUTRAL, MUTED)
    if left < 0:
        return Chip(f"Expired {-left}d ago", NEUTRAL, MUTED)
    if left == 0:
        return Chip("Expires today", DANGER_SOFT, DANGER)
    if left <= 2:
        return Chip(f"{left} day{'s' if left > 1 else ''} left", AMBER_SOFT, AMBER)
    return Chip(f"Until {format_date(item.expiry)}", PRIMARY_SOFT, PRIMARY_DARK)   # dd-mm-yyyy


class PantryScreen(Screen):
    """The Fridge tab."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app                                    # gives access to app.db and helpers
        root = BoxLayout(orientation="vertical")
        self.header = Header("My Fridge")
        root.add_widget(self.header)
        body = BoxLayout(orientation="vertical", padding=(dp(16), dp(4), dp(16), dp(8)), spacing=dp(12))
        # Banner area for "expires today" warnings (filled in refresh()).
        self.banner = BoxLayout(orientation="vertical", size_hint_y=None, height=0)   # height=0: empty = no gap
        self.banner.bind(minimum_height=self.banner.setter("height"))
        body.add_widget(self.banner)
        body.add_widget(SoftButton("+  Add item", on_release=lambda *_: self.open_item_popup()))
        scroll, self.list_box = scroll_list(padding=(0, dp(4), 0, dp(12)))   # the scrollable list
        body.add_widget(scroll)
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

        self.list_box.clear_widgets()                     # rebuild the list from scratch
        if not items:
            empty = Card()
            empty.add_widget(WrapLabel(
                text="Your fridge is empty.\nTap [b]+ Add item[/b] to add vegetables, herbs, curd, "
                     "fruits or groceries.", color=MUTED))
            self.list_box.add_widget(empty)
            return
        for category in CATEGORIES:                       # one section per category
            group = [i for i in items if i.category == category]
            if not group:
                continue
            self.list_box.add_widget(section_title(f"{category}  ({len(group)})"))
            for item in group:
                self.list_box.add_widget(self._item_row(item))

    def _item_row(self, item):
        """A rounded card for one pantry item with Edit / Delete buttons."""
        card = Card(spacing=dp(8))
        top = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        name = WrapLabel(text=f"[b]{escape(item.name)}[/b]", font_size=sp(16), shorten=True,
                         max_lines=1)
        top.add_widget(name)
        top.add_widget(Chip(pretty_quantity(item.quantity, item.unit), NEUTRAL, INK,
                            pos_hint={"center_y": 0.5}))
        card.add_widget(top)
        bottom = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        bottom.add_widget(ChipRow([expiry_chip(item)], pos_hint={"center_y": 0.5}))
        bottom.add_widget(SoftButton("Edit", size_hint=(None, None), size=(dp(70), dp(34)),
                                     bg=NEUTRAL, fg=INK, font_size=sp(13),
                                     on_release=lambda *_: self.open_item_popup(item)))
        bottom.add_widget(SoftButton("Delete", size_hint=(None, None), size=(dp(74), dp(34)),
                                     bg=DANGER_SOFT, fg=DANGER, font_size=sp(13),
                                     on_release=lambda *_: self._delete(item)))
        card.add_widget(bottom)
        return card

    def _delete(self, item):
        def _do():
            self.app.db.delete_pantry_item(item.id)
            self.refresh()
        confirm("Delete item", f"Remove {escape(item.name)} from your kitchen?", _do,
                yes_text="Delete", yes_color=DANGER, height=dp(230))

    def open_item_popup(self, item=None):
        """Open the Add (item=None) or Edit (item given) form."""
        ItemPopup(self.app, item, on_saved=self.refresh).open()


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

    def _picked(self, name, info):
        """A suggestion was chosen: pre-fill the usual unit and category."""
        if info:
            self.unit_in.text, self.cat_in.text = info
        self.qty_in.focus = True                          # jump straight to the quantity box

    def _set_days(self, days):
        """A quick button was tapped: set the drop-downs to today + `days`."""
        self.date_picker.set_date(date.today() + timedelta(days=days))

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
                              id=self.item.id if self.item else None)
        if self.item:
            self.app.db.update_pantry_item(new_item)
        else:
            self.app.db.add_pantry_item(new_item)
        self.popup.dismiss()
        self.app.check_expiry()                           # a new item might expire today
        if self.on_saved:
            self.on_saved()
