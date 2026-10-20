"""
validation.py
-------------
WHY THIS FILE EXISTS (version 4.7.1, from the QA report):
    One place for every input rule, so the forms (typing is blocked as you type) and the Save
    buttons (checked again before saving) always agree. Pure Python - no Kivy - so it is easy to test.

THE RULES (decided by Dhruv):
    * Names (fridge items, recipes, ingredients, your name): at most 126 characters including
      spaces; letters (any language), numbers, spaces and a few everyday marks: ' - , . & ( )
      Emoji and other symbols (< > { } ; @ # $ % ...) are not allowed.
    * Quantities and nutrition numbers: never negative, at most 4 digits before the decimal point
      and 2 after it (e.g. 9999.99). Decimals are allowed, because 0.5 kg or 1.5 l are common.
    * Prep time: whole minutes, 1 to 14,400 (= 10 days).
    * Servings: whole number, 1 to 20 (the same limit as the servings buttons in the app).
"""

import re                                           # regular expressions: patterns for text
import unicodedata                                  # tells letters, marks and digits of ANY language apart

NAME_MAX = 126                                      # longest allowed name, spaces included
STEPS_MAX = 3000                                    # longest allowed "Steps" text for a recipe
QTY_MAX = 9999.99                                   # biggest quantity: 4 digits (+ 2 decimals)
MINUTES_MAX = 14400                                 # longest prep time: 10 days in minutes
SERVINGS_MAX = 20                                   # most people a recipe can be for

NAME_MARKS = "'-,.&() "                             # the only non-letter/number characters allowed
# Unicode sorts every character into a category: L... = letters, M... = marks (e.g. the Hindi vowel
# signs in "पनीर" - without them Hindi names were refused!), N... = numbers. Emoji are "So" (symbol).
_NAME_CATEGORIES = ("L", "M", "N")
# While typing, a number box may hold: up to 4 digits, optionally a dot and up to 2 more digits.
# [0-9] rather than \d: \d would also accept digits of other scripts (e.g. Hindi १२), which is confusing.
QTY_TYPING = re.compile(r"[0-9]{0,4}(\.[0-9]{0,2})?")
INT_TYPING = re.compile(r"[0-9]*")                  # whole-number boxes: digits only (no minus sign)


def clean_name_chars(text):
    """Drop every character that may not appear in a name (used while typing / pasting)."""
    return "".join(ch for ch in text                 # keep only the allowed characters:
                   if ch in NAME_MARKS or unicodedata.category(ch)[0] in _NAME_CATEGORIES)


def name_error(text, what="name"):
    """None if `text` is a valid name, else a friendly message saying what to fix."""
    text = text.strip()                             # spaces at the ends don't count
    if not text:
        return f"Please enter a {what}."
    if len(text) > NAME_MAX:
        return f"The {what} can be at most {NAME_MAX} characters long."
    if clean_name_chars(text) != text:              # something was removed -> it had a bad character
        return f"The {what} can only use letters, numbers, spaces and  ' - , . & ( )"
    return None


def parse_quantity(text, what="quantity", allow_zero=False):
    """Text -> float for quantities / nutrition numbers. Raises ValueError with a friendly message."""
    text = text.strip()
    if not text and allow_zero:                     # optional boxes (nutrition) may stay empty
        return 0.0
    if not text or text == "." or not QTY_TYPING.fullmatch(text):
        raise ValueError(f"Please enter the {what} as a number, e.g. 250 or 1.5.")
    value = float(text)                             # safe now: the pattern only allows digits and one dot
    if value <= 0 and not allow_zero:
        raise ValueError(f"The {what} must be more than 0.")
    return value                                    # never above 9999.99 thanks to the pattern


def parse_whole(text, what, low, high):
    """Text -> int between low and high. Raises ValueError with a friendly message."""
    text = text.strip()
    if not text or not INT_TYPING.fullmatch(text):
        raise ValueError(f"Please enter the {what} as a whole number.")
    value = int(text)
    if not low <= value <= high:                    # outside the allowed range
        raise ValueError(f"The {what} must be between {low:,} and {high:,}.")
    return value
