"""
pantry_screen.py
----------------
WHY THIS FILE EXISTS:
    The "Fridge" tab - where the user keeps track of what they have.

    Version 5.0 (testers wanted it simpler): a LIST instead of the fridge drawing.
        * Items are grouped in one coloured box per tag: Fresh produce, Dairy, Meat, Bakery,
          Frozen, Grain, Spice, Pantry, Dry goods (the tag comes from the ingredient catalogue).
        * Each item is a row: a dot in the tag's colour, its name, and "1 L  •  expires in 5 days".
          Items expiring soon are amber, today red; items past their date say "expired".
        * Tap a row to change the amount or remove it; after removing, an "Undo" bar stays for a
          few seconds in case it was a mistake. (A tick-off circle was tried and removed again.)
    Water is always available, so it isn't listed.

    A banner lists items expiring today. The Add form fills in unit, amount, tag and expiry date
    from the catalogue ("Milk" -> 1 L, Fresh produce, 5 days). Easter egg: try adding "love".
"""

from datetime import date, timedelta              # expiry dates

from kivy.clock import Clock                      # hides the Undo bar after a few seconds
from kivy.graphics import Color, Ellipse          # the coloured dot of each row
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior      # makes the tag chip tappable
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen         # one "page" of the app
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from app.dates import format_date                 # shows dates as dd-mm-yyyy
from app.expiry import expiring_soon, expiring_today
from app.ingredient_catalog import FRIDGE_UNITS, TAGS, guess_info   # kg/pcs/L, the tags, the catalogue
from app.models import PantryItem, guess_container
from app.units import pretty_quantity
from app.validation import name_error, parse_quantity   # 4.7.1: shared input rules
from app.ui.autocomplete import AutoCompleteInput
from app.ui.date_picker import DatePicker         # Day / Month / Year drop-downs
from app.ui.easter_egg import is_love, play_hearts   # the "love" surprise
from app.ui.widgets import (TAG_STYLES, Chip,
                            DANGER, DANGER_SOFT, HEX_AMBER, HEX_GREY, HEX_RED, INK, MUTED, NEUTRAL,
                            WHITE, Card, Header, SoftButton, TapBehavior,
                            SoftInput, SoftSpinner, WrapLabel, bg_rect, colored, icon_image, labeled,
                            light_popup, primary_action, scroll_list)

UNDO_SECONDS = 5                                  # how long the "Undo" bar stays after removing an item


def expiry_text(item):
    """'Expires on 25-10-2026 (in 7 days)' for the item popup."""
    left = item.days_left()
    if left is None:
        return "[color=656b70]No expiry date[/color]"
    when = "today" if left == 0 else ("tomorrow" if left == 1 else f"in {left} days")
    text = f"Expires on [b]{format_date(item.expiry)}[/b] ({when})"
    return colored(text, HEX_RED) if left == 0 else text   # red on the last day


def short_expiry(item):
    """The coloured 'when' part of a row: 'expires in 5 days', 'use today', 'expired 2 days ago'."""
    left = item.days_left()
    if left is None:
        return colored("no expiry date", HEX_GREY)
    if left < 0:
        return colored(f"expired {-left} day{'s' if left < -1 else ''} ago", HEX_RED, bold=True)
    if left == 0:
        return colored("use today", HEX_RED, bold=True)   # colored() escapes text, so bold is its own option
    if left <= 2:
        return colored(f"expires {'tomorrow' if left == 1 else 'in 2 days'}", HEX_AMBER)
    if left >= 365:                                   # 5.0 QA: "expires in 365 days" read like a robot
        return colored("keeps for a year", HEX_GREY)
    if left > 60:
        return colored("keeps for months", HEX_GREY)
    return colored(f"expires in {left} days", HEX_GREY)


class ItemRow(TapBehavior, BoxLayout):
    """One fridge item as a list row: coloured dot | name + '1 L  •  expires in 5 days'. Tap = edit."""

    def __init__(self, item, color, on_open, **kwargs):
        super().__init__(size_hint_y=None, height=dp(56), spacing=dp(12), padding=(dp(6), dp(6)), **kwargs)
        self.item = item
        dot = Widget(size_hint=(None, None), size=(dp(12), dp(12)), pos_hint={"center_y": 0.5})
        with dot.canvas:                                 # a small dot in the tag's colour
            Color(*color)
            # Sized right away: the dot's size never changes, so a size binding alone would never run
            # and the circle would keep Kivy's default 100 x 100 (the bug seen in testing).
            disc = Ellipse(pos=dot.pos, size=dot.size)
        dot.bind(pos=lambda w, p: setattr(disc, "pos", p))   # follow the dot when the row is laid out
        self.add_widget(dot)
        texts = BoxLayout(orientation="vertical")
        name = Label(text=item.name, bold=True, color=INK, font_size=sp(16), halign="left", valign="bottom",
                     shorten=True, shorten_from="right")
        name.bind(size=lambda l, sz: setattr(l, "text_size", sz))
        texts.add_widget(name)
        amount = pretty_quantity(item.quantity, item.unit)
        detail = Label(text=f"{amount}  •  {short_expiry(item)}", markup=True, color=MUTED,
                       font_size=sp(13), halign="left", valign="top", shorten=True, shorten_from="right")
        detail.bind(size=lambda l, sz: setattr(l, "text_size", sz))
        texts.add_widget(detail)
        self.add_widget(texts)
        self.bind(on_tap=lambda *_: on_open(item))       # tap the row -> change the amount / remove it


class TagBox(Card):
    """One coloured box per tag: '[icon] Fresh produce  3' on top, the item rows below."""

    def __init__(self, tag, items, on_open, **kwargs):
        bg, fg, icon_name = TAG_STYLES[tag]
        super().__init__(color=WHITE, padding=(dp(14), dp(12)), spacing=dp(2), radius=dp(22), **kwargs)
        head = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(10))
        badge = BoxLayout(size_hint=(None, None), size=(dp(32), dp(32)), padding=dp(5), pos_hint={"center_y": 0.5})
        bg_rect(badge, bg, radius=dp(11))
        badge.add_widget(icon_image(icon_name, dp(22)))
        head.add_widget(badge)
        title = Label(text=f"[b]{tag}[/b]", markup=True, color=fg, font_size=sp(16), halign="left",
                      valign="middle")
        title.bind(size=lambda l, sz: setattr(l, "text_size", sz))
        head.add_widget(title)
        count = Chip(str(len(items)), bg, fg)
        count.pos_hint = {"center_y": 0.5}
        head.add_widget(count)
        self.add_widget(head)
        for item in items:
            self.add_widget(ItemRow(item, fg, on_open))


class PantryScreen(Screen):
    """The Fridge tab."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app                                    # gives access to app.db and helpers
        self._undo_item = None                            # the item removed last (for Undo)
        self._hide_undo = Clock.create_trigger(lambda dt: self._show_undo(None), UNDO_SECONDS)
        root = BoxLayout(orientation="vertical")
        self.header = Header("My Fridge", icon="tab_fridge")
        root.add_widget(self.header)
        body = BoxLayout(orientation="vertical", padding=(dp(16), dp(4), dp(16), dp(8)), spacing=dp(10))
        # Banner area for "expires today" warnings (filled in refresh()).
        self.banner = BoxLayout(orientation="vertical", size_hint_y=None, height=0)   # height=0: empty = no gap
        self.banner.bind(minimum_height=self.banner.setter("height"))
        body.add_widget(self.banner)
        scroll, self.list_box = scroll_list(spacing=dp(12), padding=(dp(2), dp(2), dp(2), dp(12)))
        body.add_widget(scroll)
        # The "Undo" bar (hidden until an item is removed).
        self.undo_bar = BoxLayout(size_hint_y=None, height=0, opacity=0, padding=(dp(14), dp(6)), spacing=dp(8))
        bg_rect(self.undo_bar, (0.13, 0.16, 0.17, 0.94), radius=dp(16))
        self.undo_label = Label(text="", color=WHITE, font_size=sp(14), halign="left", valign="middle",
                                shorten=True, shorten_from="right")
        self.undo_label.bind(size=lambda l, sz: setattr(l, "text_size", sz))
        self.undo_bar.add_widget(self.undo_label)
        self.undo_bar.add_widget(SoftButton("Undo", size_hint=(None, None), size=(dp(80), dp(36)),
                                            pos_hint={"center_y": 0.5}, on_release=lambda *_: self._undo()))
        body.add_widget(self.undo_bar)
        # The big green button at the bottom (the same main button as on the other tabs).
        body.add_widget(primary_action("+  Add Item", lambda: AddItemPopup(self.app, self.refresh).open()))
        root.add_widget(body)
        self.add_widget(root)

    def on_pre_enter(self, *_):
        """Kivy calls this just before the screen is shown - always show fresh data."""
        self.refresh()

    def refresh(self):
        items = self.app.db.list_pantry()                 # read everything from SQLite, soonest expiry first
        food = [i for i in items if not i.is_water]       # Water is always there - not listed
        today_items = expiring_today(items)
        soon = expiring_soon(items)
        self.header.set_subtitle(f"{len(food)} items • {len(today_items) + len(soon)} expiring soon")
        self.banner.clear_widgets()
        if today_items:                                   # soft red card at the top
            card = Card(color=DANGER_SOFT, shadow=False, radius=dp(18))
            names = ", ".join(i.name for i in today_items)
            card.add_widget(WrapLabel(text=colored(f"Use today: {names}", HEX_RED, True)))
            card.add_widget(WrapLabel(text="Dishes using these are marked [b]Use today[/b] on the Recipes tab.",
                                      font_size=sp(13), color=MUTED))
            self.banner.add_widget(card)

        self.list_box.clear_widgets()
        if not food:                                      # nothing yet: say how to start
            empty = Card(radius=dp(22), padding=dp(18))
            empty.add_widget(WrapLabel(text="[b]Your fridge is empty.[/b]\nTap [b]+ Add Item[/b] and type what "
                                            "you bought - the amount and expiry date fill themselves in.",
                                       color=MUTED, font_size=sp(14)))
            self.list_box.add_widget(empty)
            return
        for tag in TAGS:                                  # one box per tag, in the catalogue's order
            tagged = [i for i in food if (i.tag or guess_info(i.name).tag) == tag]
            if tagged:
                self.list_box.add_widget(TagBox(tag, tagged, self.open_item))

    # ---------------------------------------------------------------- undo after removing
    def _show_undo(self, item):
        """Show the Undo bar for `item` (or hide it when item is None)."""
        self._undo_item = item
        if item is None:
            self.undo_bar.height, self.undo_bar.opacity = 0, 0
            return
        self.undo_label.text = f"{item.name} removed"
        self.undo_bar.height, self.undo_bar.opacity = dp(48), 1
        self._hide_undo()                                 # (re)start the countdown

    def _undo(self):
        """Put the removed item back exactly as it was."""
        item = self._undo_item
        if item is None:
            return
        item.id = None                                    # it is saved as a new row
        self.app.db.add_pantry_item(item)
        self._show_undo(None)
        self.refresh()

    # ---------------------------------------------------------------- tapping an item
    def open_item(self, item):
        """Expired food -> Throw Away, anything else -> change the amount / remove."""
        if item.is_expired():
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
        """Delete the item and offer Undo for a few seconds."""
        self.app.db.delete_pantry_item(item.id)
        self._show_undo(item)
        self.refresh()


class TagChip(ButtonBehavior, Chip):
    """The coloured tag chip in the Add / Edit forms - tap it to choose another tag (5.0 QA)."""

    def __init__(self, text, bg, fg, **kwargs):
        # Kivy's ButtonBehavior runs first and only accepts NAMED values - passing them plainly
        # crashed the Add form (the same trap as the Profile avatar in 4.7.1).
        super().__init__(text=text, bg=bg, fg=fg, **kwargs)

    def show(self, tag):
        bg, fg, _icon = TAG_STYLES[tag]
        self.text = tag
        self._bg_color.rgba, self.color = bg, fg


def tag_row(chip):
    """[chip]  Tap to change   - one line for the forms."""
    row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
    chip.pos_hint = {"center_y": 0.5}
    row.add_widget(chip)
    hint = Label(text="Tap to change", color=MUTED, font_size=sp(12), halign="left", valign="middle")
    hint.bind(size=lambda l, sz: setattr(l, "text_size", sz))
    row.add_widget(hint)
    return row


def pick_tag(current, on_pick):
    """A small popup with all 9 tags as coloured buttons; on_pick(tag) runs for the chosen one."""
    grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
    grid.bind(minimum_height=grid.setter("height"))
    box = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(10))
    box.add_widget(grid)
    popup = light_popup("Choose a tag", box, height=dp(380))
    for tag in TAGS:
        bg, fg, _icon = TAG_STYLES[tag]

        def choose(*_, t=tag):
            popup.dismiss()
            on_pick(t)
        button = SoftButton(("> " if tag == current else "") + tag, bg=bg, fg=fg, height=dp(46),
                            font_size=sp(14), on_release=choose)
        grid.add_widget(button)
    popup.open()


class EditItemPopup:
    """Tapping fresh food: change the quantity, or remove it from the fridge. Nothing else."""

    def __init__(self, app, item, on_saved, on_remove):
        self.app, self.item, self.on_saved = app, item, on_saved
        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
        box.add_widget(WrapLabel(text=expiry_text(item), font_size=sp(14)))   # shown, not changeable
        self.tag = item.tag or guess_info(item.name).tag
        self.tag_chip = TagChip(self.tag, *TAG_STYLES[self.tag][:2])
        self.tag_chip.bind(on_release=lambda *_: pick_tag(self.tag, self._set_tag))
        box.add_widget(tag_row(self.tag_chip))           # 5.0 QA: a wrong tag can be fixed here
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

    def _set_tag(self, tag):
        self.tag = tag
        self.tag_chip.show(tag)

    def _save(self):
        try:
            quantity = parse_quantity(self.qty_in.text)   # 4.7.1: friendly message if empty / 0 / odd
        except ValueError as problem:
            self.error.text = f"{problem} (Or tap Remove from fridge.)"
            return
        self.item.quantity = quantity
        self.item.tag = self.tag                          # the tag may have been changed too
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
        self._tag_chosen = False                          # True once the user picks a tag themselves
        self.tag_chip = TagChip("Pantry", *TAG_STYLES["Pantry"][:2])
        self.tag_chip.bind(on_release=lambda *_: pick_tag(self.tag, self._choose_tag))
        form.add_widget(tag_row(self.tag_chip))           # 5.0 QA: the tag can be changed (optional)
        expiry_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.expiry_label = Label(text="", markup=True, color=INK, font_size=sp(14), halign="left",
                                  valign="middle", shorten=True, shorten_from="right")
        self.expiry_label.bind(size=lambda l, sz: setattr(l, "text_size", sz))
        expiry_row.add_widget(self.expiry_label)
        expiry_row.add_widget(SoftButton("Change", size_hint=(None, None), size=(dp(92), dp(44)),
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
            if not self._tag_chosen:                      # don't overwrite a tag the user picked
                self.tag_chip.show(info.tag)
            if not self._date_changed:                    # don't overwrite a date the user picked
                self._setting_date = True
                self.date_picker.set_date(date.today() + timedelta(days=info.shelf_days))
                self._setting_date = False
        if not self._tag_chosen:
            self.tag = info.tag if info else "Pantry"
        self._show_expiry()

    def _choose_tag(self, tag):
        """The user picked a tag in the picker: it wins over the catalogue's guess."""
        self._tag_chosen = True
        self.tag = tag
        self.tag_chip.show(tag)

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
