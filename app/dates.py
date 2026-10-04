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


def today():
    """Today's date (a separate function so tests could replace it)."""
    return date.today()                                # the computer's / phone's current date
