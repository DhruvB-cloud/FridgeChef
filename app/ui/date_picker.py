"""
date_picker.py
--------------
WHY THIS FILE EXISTS:
    "The date should be in dd-mm-yyyy format and the user should be able to select a particular
    date from a dropdown option." DatePicker shows three rounded drop-downs side by side:

        [ Day: 04 ]  [ Month: 10 - Oct ]  [ Year: 2026 ]      ->  "Expires on 04-10-2026 (Sunday)"

    plus a "Never expires" switch for things like salt or rice. The list of days always matches
    the chosen month (28/29/30/31), so impossible dates like 31-02 can't be picked.
"""

import calendar                                    # calendar.monthrange tells how many days a month has
from datetime import date                          # the date type we return

from kivy.metrics import dp, sp                    # density-independent sizes
from kivy.uix.boxlayout import BoxLayout           # lays out widgets in a row / column
from kivy.uix.label import Label                   # small captions above each drop-down

from app.dates import format_date, today           # dd-mm-yyyy formatting + "today"
from app.ui.widgets import MUTED, SoftSpinner, SoftToggle, WrapLabel   # rounded widgets

# Month drop-down entries: "01 - Jan" ... "12 - Dec" (number first, so it matches dd-mm-yyyy).
MONTHS = [f"{m:02d} - {calendar.month_abbr[m]}" for m in range(1, 13)]


class DatePicker(BoxLayout):
    """Day / Month / Year drop-downs + 'Never expires' switch. Use get_date() / set_date()."""

    def __init__(self, value=None, allow_never=True, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(8), **kwargs)   # stacked rows
        self.bind(minimum_height=self.setter("height"))   # our height = height of our rows
        self._updating = False                            # True while WE change the spinners (no loops)
        start = value or today()                          # what the drop-downs show first

        captions = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(8))   # "Day  Month  Year" row
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))         # the three drop-downs
        self.day = SoftSpinner(size_hint_x=0.28)          # 01..31
        self.month = SoftSpinner(size_hint_x=0.42)        # "01 - Jan".."12 - Dec"
        self.year = SoftSpinner(size_hint_x=0.30)         # this year - 1 ... this year + 5
        for caption, spinner in (("Day", self.day), ("Month", self.month), ("Year", self.year)):
            label = Label(text=caption, color=MUTED, font_size=sp(12), halign="left",
                          size_hint_x=spinner.size_hint_x)                     # same width as its spinner
            label.bind(size=lambda l, s: setattr(l, "text_size", s))         # left-align the caption
            captions.add_widget(label)                                        # add caption to row 1
            row.add_widget(spinner)                                           # add drop-down to row 2
        self.add_widget(captions)                         # captions on top...
        self.add_widget(row)                              # ...drop-downs below

        self.month.values = MONTHS                        # the 12 month entries
        years = list(range(today().year - 1, today().year + 6))   # e.g. 2025..2031
        if start.year not in years:                       # editing an item with an unusual year
            years = sorted(years + [start.year])          # make sure that year can be shown
        self.year.values = [str(y) for y in years]        # spinner values must be text

        self.never = None                                 # stays None if "never" isn't allowed
        if allow_never:
            self.never = SoftToggle("Never expires", size_hint_y=None, height=dp(40))   # e.g. salt
            self.never.bind(state=lambda *_: self._refresh_state())   # grey out drop-downs when on
            self.add_widget(self.never)

        self.preview = WrapLabel(text="", font_size=sp(14))   # "Expires on 04-10-2026 (Sunday)"
        self.add_widget(self.preview)

        for spinner in (self.day, self.month, self.year):     # any change -> fix days + preview
            spinner.bind(text=lambda *_: self._on_change())
        self.set_date(value)                              # show the starting value

    # ------------------------------------------------------------------ public API
    def set_date(self, value):
        """Show `value` (a date), or switch on "Never expires" when value is None."""
        self._updating = True                             # don't react to our own changes
        shown = value or today()                          # None -> keep today's date in the boxes
        self.year.text = str(shown.year)                  # e.g. "2026"
        self.month.text = MONTHS[shown.month - 1]         # e.g. "10 - Oct" (list index starts at 0)
        self._fill_days()                                 # 28-31 entries for that month
        self.day.text = f"{shown.day:02d}"                # e.g. "04" (02d = two digits, leading zero)
        if self.never is not None:
            self.never.state = "down" if value is None else "normal"   # None means "never expires"
        self._updating = False                            # back to normal
        self._refresh_state()                             # update preview + enabled state

    def get_date(self):
        """The chosen date, or None when "Never expires" is switched on."""
        if self.never is not None and self.never.state == "down":
            return None                                   # no expiry date
        return date(int(self.year.text), int(self.month.text[:2]), int(self.day.text))   # "10 - Oct" -> 10

    # ------------------------------------------------------------------ internals
    def _fill_days(self):
        """Offer exactly the days that exist in the selected month (handles leap years too)."""
        year, month = int(self.year.text), int(self.month.text[:2])   # currently selected
        days_in_month = calendar.monthrange(year, month)[1]           # e.g. 29 for Feb 2028
        self.day.values = [f"{d:02d}" for d in range(1, days_in_month + 1)]   # "01".."29"
        if self.day.text and int(self.day.text) > days_in_month:      # e.g. 31 chosen, then Feb
            self.day.text = f"{days_in_month:02d}"                    # move to the last valid day

    def _on_change(self):
        if self._updating:                                # set_date() is busy - ignore
            return
        self._updating = True
        self._fill_days()                                 # month/year may have changed the day count
        self._updating = False
        self._refresh_state()

    def _refresh_state(self):
        """Grey out the drop-downs when 'Never expires' is on, and update the preview line."""
        never = self.never is not None and self.never.state == "down"
        for spinner in (self.day, self.month, self.year):
            spinner.disabled = never                      # can't pick a date that isn't used
            spinner.opacity = 0.45 if never else 1        # look faded when disabled
        chosen = self.get_date()                          # None when "never"
        if chosen is None:
            self.preview.text = "[color=8a8f93]No expiry date[/color]"
        else:
            left = (chosen - today()).days                # days from today (negative = past)
            when = "today" if left == 0 else (f"in {left} days" if left > 0 else f"{-left} days ago")
            self.preview.text = f"Expires on [b]{format_date(chosen)}[/b] ({chosen.strftime('%A')}, {when})"
