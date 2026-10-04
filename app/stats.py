"""
stats.py
--------
WHY THIS FILE EXISTS:
    The Profile tab shows a Duolingo-style cooking streak, your favourite dish and other numbers.
    The maths lives here (no UI, no database) so it is easy to read and to unit-test.

STREAK RULES (same idea as Duolingo):
    * Every day on which you cooked at least one dish counts.
    * The "current streak" is the number of days in a row up to TODAY.
    * If you haven't cooked yet today but did cook yesterday, the streak is still alive
      ("at risk") - it only resets to 0 once a whole day passes without cooking.
"""

from collections import Counter          # counts how often each dish was cooked
from datetime import date, timedelta


def current_streak(cooked_days, today=None):
    """Return (streak_length, cooked_today).

    cooked_days - a set of date objects on which something was cooked.
    """
    today = today or date.today()
    days = set(cooked_days)
    cooked_today = today in days
    # Start counting from today if cooked today, otherwise from yesterday (streak "at risk").
    day = today if cooked_today else today - timedelta(days=1)
    streak = 0
    while day in days:                    # walk backwards one day at a time
        streak += 1
        day -= timedelta(days=1)
    return streak, cooked_today


def longest_streak(cooked_days):
    """The longest run of consecutive cooking days ever."""
    best = run = 0
    previous = None
    for day in sorted(set(cooked_days)):  # oldest to newest
        # Continue the run if this day directly follows the previous one, else start over.
        run = run + 1 if previous and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    return best


def week_strip(cooked_days, today=None):
    """The current week Monday..Sunday as [(date, cooked?, is_today?), ...] for the 7 circles."""
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())     # weekday(): Monday = 0
    days = set(cooked_days)
    return [(monday + timedelta(days=i), (monday + timedelta(days=i)) in days,
             monday + timedelta(days=i) == today) for i in range(7)]


def favourite_dish(cook_log):
    """Most-cooked dish name and its count, e.g. ("Dal Tadka", 7). (None, 0) when nothing cooked.

    cook_log - list of dicts with at least "recipe_name" and "cooked_on" (ISO datetime text).
    Ties are won by the dish cooked most recently.
    """
    if not cook_log:
        return None, 0
    counts = Counter(entry["recipe_name"] for entry in cook_log)
    latest = {}
    for entry in cook_log:                               # remember the last time each was cooked
        latest[entry["recipe_name"]] = max(latest.get(entry["recipe_name"], ""), entry["cooked_on"])
    # max() with a tuple key: highest count first, then the most recent date.
    name = max(counts, key=lambda n: (counts[n], latest[n]))
    return name, counts[name]


def streak_message(streak, cooked_today):
    """Friendly motivational line under the streak number."""
    if streak == 0:
        return "Cook something today to start a streak!"
    if not cooked_today:
        return "Cook today to keep your streak alive!"
    if streak == 1:
        return "Great start - come back tomorrow!"
    return f"{streak} days in a row - you're on fire!"
