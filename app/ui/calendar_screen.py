"""
calendar_screen.py
------------------
WHY THIS FILE EXISTS:
    "Give a calendar section where I can see what dish I cooked on which day."
    A month grid (Mon-Sun). Days on which you cooked are tinted green and show how many dishes;
    today has a ring; the selected day is filled. Below the grid, the dishes of the selected day
    are listed (with pictures) - tap one to open the recipe. Arrows switch months.
    Data comes from the cook_log table, which is filled when you tap "Finished - update fridge".
    Your own photos of cooked dishes (added in the "Yay!" popup or with "Add photo" here) are shown
    with the dish, and as the background of that day's tile.
"""

import calendar                                  # Python's built-in calendar maths
import os                                        # check that a photo file still exists
from datetime import date, datetime

from kivy.graphics import Color, Line
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout   # day tile: photo, dark layer and text on top of each other
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from app.dates import format_date                # dd-mm-yyyy
from app.images import resolve_image
from app.ui.cooked_popup import attach_photo     # "Add photo" for a calendar entry
from app.ui.widgets import (PEACH_SOFT, INK, MUTED, NEUTRAL, PRIMARY, PRIMARY_DARK, PRIMARY_SOFT, SURFACE, WHITE,
                            Card, Header, RoundImage, SoftButton, TapCard, WrapLabel, bg_rect,
                            escape, scroll_list, section_title)

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class DayCell(ButtonBehavior, RelativeLayout):
    """One day in the month grid: the day number and a small 'n dishes' line.

    If you added a photo of something you cooked that day, the photo fills the tile (with a soft
    dark layer on top so the white day number stays readable).
    """

    def __init__(self, day, count, is_today, is_selected, in_month, on_pick, photo=None, **kwargs):
        super().__init__(**kwargs)                        # RelativeLayout: children fill the tile
        # Background: filled green when selected, pale green when cooked, white otherwise.
        if is_selected:
            bg, fg = PRIMARY, WHITE
        elif count:
            bg, fg = PRIMARY_SOFT, PRIMARY_DARK
        else:
            bg, fg = (SURFACE if in_month else (0, 0, 0, 0)), (INK if in_month else MUTED)
        # The background is a full-size child, not drawn on our own canvas: a RelativeLayout shifts
        # its canvas coordinates, which would push a canvas.before shape out of place.
        base = Widget()
        bg_rect(base, bg, radius=dp(14))
        self.add_widget(base)
        if photo:                                        # the user's photo of that day's dish
            self.add_widget(RoundImage(photo, radius=dp(14)))            # fills the whole tile
            scrim = Widget()                                              # dark layer over the photo
            bg_rect(scrim, (0, 0, 0, 0.25 if is_selected else 0.4), radius=dp(14))
            self.add_widget(scrim)
            fg = WHITE                                                    # white text on the photo
        if is_today and not is_selected:                 # a green ring around today
            with self.canvas.after:
                Color(*PRIMARY)
                self._ring = Line(width=dp(1.4))
            self.bind(pos=self._draw_ring, size=self._draw_ring)
        texts = BoxLayout(orientation="vertical", padding=dp(2))         # number + dots, stacked
        texts.add_widget(Label(text=f"[b]{day.day}[/b]", markup=True, color=fg, font_size=sp(15)))
        dots = " ".join("•" * min(count, 3)) if count else ""   # 1-3 little dots = how many dishes
        texts.add_widget(Label(text=dots, color=fg, font_size=sp(14), size_hint_y=0.5))
        self.add_widget(texts)
        self.bind(on_release=lambda *_: on_pick(day))

    def _draw_ring(self, *_):
        # canvas.after comes after Kivy's "undo the shift" instruction, so it uses window coordinates.
        self._ring.rounded_rectangle = (self.x + dp(1), self.y + dp(1), self.width - dp(2),
                                        self.height - dp(2), dp(13))


class CalendarScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        today = date.today()
        self.year, self.month = today.year, today.month   # month being shown
        self.selected = today                             # day whose dishes are listed
        root = BoxLayout(orientation="vertical")
        self.header = Header("Cooking calendar", "")
        root.add_widget(self.header)
        scroll, self.content = scroll_list(spacing=dp(14), padding=(dp(16), dp(4), dp(16), dp(20)))
        root.add_widget(scroll)
        self.add_widget(root)

    def on_pre_enter(self, *_):
        self.refresh()

    def _shift_month(self, delta):
        """Go to the previous (-1) or next (+1) month."""
        month = self.month + delta
        self.year += (month - 1) // 12                    # e.g. month 13 -> next year
        self.month = (month - 1) % 12 + 1                 # ...and month 1
        self.refresh()

    def _pick(self, day):
        self.selected = day
        self.refresh()

    def refresh(self):
        db = self.app.db
        first = date(self.year, self.month, 1)
        last = date(self.year, self.month, calendar.monthrange(self.year, self.month)[1])
        month_log = db.cook_log(first, last)              # everything cooked this month
        per_day = {}                                      # date -> list of log entries
        for entry in month_log:
            per_day.setdefault(date.fromisoformat(entry["cooked_on"][:10]), []).append(entry)
        days_cooked = len(per_day)
        meals = f"{len(month_log)} meal{'' if len(month_log) == 1 else 's'}"     # 1 meal / 2 meals
        days = f"{days_cooked} day{'' if days_cooked == 1 else 's'}"            # 1 day / 2 days
        self.header.set_subtitle(f"{meals} on {days} this month")

        c = self.content
        c.clear_widgets()
        card = Card(spacing=dp(10))
        # --- month switcher:  <   October 2026   >
        nav = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        nav.add_widget(SoftButton("<", size_hint=(None, None), size=(dp(44), dp(44)), bg=NEUTRAL,
                                  fg=INK, on_release=lambda *_: self._shift_month(-1)))
        nav.add_widget(Label(text=f"[b]{first.strftime('%B %Y')}[/b]", markup=True, color=INK,
                             font_size=sp(18)))
        nav.add_widget(SoftButton(">", size_hint=(None, None), size=(dp(44), dp(44)), bg=NEUTRAL,
                                  fg=INK, on_release=lambda *_: self._shift_month(+1)))
        card.add_widget(nav)

        # --- weekday names + the day grid (Monday first)
        names = GridLayout(cols=7, size_hint_y=None, height=dp(22))
        for name in WEEKDAYS:
            names.add_widget(Label(text=name, color=MUTED, font_size=sp(12)))
        card.add_widget(names)
        grid = GridLayout(cols=7, spacing=dp(5), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        today = date.today()
        # monthdatescalendar gives whole weeks, including days of the neighbouring months.
        for week in calendar.Calendar(firstweekday=0).monthdatescalendar(self.year, self.month):
            for day in week:
                photos = [e["photo_path"] for e in per_day.get(day, []) if e["photo_path"]
                          and os.path.exists(e["photo_path"])]          # that day's dish photos
                grid.add_widget(DayCell(day, len(per_day.get(day, [])), day == today,
                                        day == self.selected, day.month == self.month, self._pick,
                                        photo=photos[0] if photos else None,
                                        size_hint_y=None, height=dp(52)))
        card.add_widget(grid)
        c.add_widget(card)

        # --- dishes of the selected day
        entries = per_day.get(self.selected)
        if entries is None and (self.selected.month, self.selected.year) != (self.month, self.year):
            entries = db.cook_log(self.selected, self.selected)   # selected day is in another month
        weekday_and_date = f"{self.selected.strftime('%A')}, {format_date(self.selected)}"   # "Sunday, 04-10-2026"
        label = f"Today, {format_date(today)}" if self.selected == today else weekday_and_date
        c.add_widget(section_title(label))
        if not entries:
            empty = Card(shadow=False)
            empty.add_widget(WrapLabel(text="Nothing cooked on this day.", color=MUTED, font_size=sp(14)))
            c.add_widget(empty)
            return
        for entry in sorted(entries, key=lambda e: e["cooked_on"]):
            c.add_widget(self._entry_row(entry))

    def _entry_row(self, entry):
        """A card for one cooked dish: picture, name, time, servings, and your photo (if any)."""
        card = TapCard(spacing=dp(10), padding=dp(10))
        row = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(12))
        holder = BoxLayout(size_hint=(None, None), size=(dp(56), dp(56)))
        holder.add_widget(RoundImage(resolve_image(entry["image_path"], small=True), radius=dp(14)))   # recipe picture
        row.add_widget(holder)
        text = BoxLayout(orientation="vertical", spacing=dp(2))
        time_text = datetime.fromisoformat(entry["cooked_on"]).strftime("%H:%M")
        people = "1 person" if entry["servings"] == 1 else f"{entry['servings']} people"
        text.add_widget(WrapLabel(text=f"[b]{escape(entry['recipe_name'])}[/b]", font_size=sp(16),
                                  shorten=True, max_lines=1))
        text.add_widget(WrapLabel(text=f"Cooked at {time_text} • for {people}", color=MUTED, font_size=sp(13)))
        row.add_widget(text)
        photo = entry["photo_path"] if entry["photo_path"] and os.path.exists(entry["photo_path"]) else None
        # "Add photo" / "Change photo" - attach your own picture of the dish to this calendar entry.
        row.add_widget(SoftButton("Change photo" if photo else "Add photo", size_hint=(None, None),
                                  size=(dp(110), dp(36)), pos_hint={"center_y": 0.5},
                                  bg=PEACH_SOFT, fg=(0.70, 0.40, 0.28, 1), font_size=sp(13),
                                  on_release=lambda *_: attach_photo(self.app, entry["id"],
                                                                     on_done=lambda p: self.refresh())))
        card.add_widget(row)
        if photo:                                        # your photo, big, under the dish name
            card.add_widget(RoundImage(photo, radius=dp(16), size_hint_y=None, height=dp(190)))
        if entry["recipe_exists"]:                       # recipe not deleted -> open it on tap
            card.bind(on_press=lambda *_: self.app.open_recipe(entry["recipe_id"]))   # on_press = no delay
        return card
