"""
dates.py
--------
WHY THIS FILE EXISTS:
    The app shows every date as dd-mm-yyyy (e.g. 04-10-2026). Inside the database dates are still
    stored as yyyy-mm-dd ("ISO" format), because that format sorts correctly as text - so
    "ORDER BY expiry" keeps working. These two helpers convert between what the user sees and
    what the program uses, so the format is defined in ONE place.
"""

from datetime import date, datetime   # date = a calendar day; datetime is used for parsing text

DISPLAY_FORMAT = "%d-%m-%Y"           # %d = day (04), %m = month (10), %Y = 4-digit year (2026)


def format_date(value):
    """date -> '04-10-2026'. Returns '' for None (e.g. an item that never expires)."""
    if value is None:                                  # nothing to show
        return ""                                      # empty text instead of the word "None"
    return value.strftime(DISPLAY_FORMAT)              # strftime = "string FORMAT time"


def parse_date(text):
    """'04-10-2026' (or the older '2026-10-04') -> date. Raises ValueError for anything else."""
    text = str(text).strip()                           # remove spaces around the text
    for pattern in (DISPLAY_FORMAT, "%Y-%m-%d"):       # try dd-mm-yyyy first, then yyyy-mm-dd
        try:                                           # strptime raises ValueError if it doesn't fit
            return datetime.strptime(text, pattern).date()   # text -> datetime -> just the date part
        except ValueError:                             # this pattern didn't match...
            continue                                   # ...so try the next one
    raise ValueError(f"'{text}' is not a date like 25-10-2026")   # no pattern matched


def short_minutes(minutes):
    """A cooking time in a few characters (4.7.1 - prep times can now be up to 14,400 minutes):
    45 -> '45 min', 90 -> '1 h 30', 120 -> '2 h', 14400 -> '10 d', 1500 -> '1 d 1 h'."""
    minutes = int(minutes)
    if minutes < 60:                                   # under an hour: plain minutes
        return f"{minutes} min"
    if minutes < 24 * 60:                              # under a day: hours (+ leftover minutes)
        hours, mins = divmod(minutes, 60)              # divmod(90, 60) -> (1, 30)
        return f"{hours} h {mins}" if mins else f"{hours} h"
    days, rest = divmod(minutes, 24 * 60)              # a day or more: days (+ whole hours)
    hours = rest // 60
    return f"{days} d {hours} h" if hours else f"{days} d"


def today():
    """Today's date (a separate function so tests could replace it)."""
    return date.today()                                # the computer's / phone's current date
