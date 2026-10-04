"""
meal_time.py
------------
WHY THIS FILE EXISTS:
    The "Recommended" column must show dishes for the NEAREST meal time. This module decides
    which meal slot (Breakfast, Brunch, Lunch, Snacks, Dinner) is nearest to the current clock time.
    It is kept separate so the rule is easy to find and change, and easy to unit-test.

THE RULE:
    Each meal has a "typical time" (below). We measure how far the current time is from each
    typical time - going round the clock, so 23:30 is close to Breakfast at 08:00 next day
    rather than far from it - and pick the closest one. A meal we are already past by more than
    45 minutes is skipped, because at 13:50 you are planning snacks, not lunch.
"""

from datetime import datetime   # gives us the current time

# Typical time of each meal as minutes after midnight (hour * 60 + minute).
MEAL_CENTERS = {
    "Breakfast": 8 * 60,        # 08:00
    "Brunch": 11 * 60,          # 11:00
    "Lunch": 13 * 60,           # 13:00
    "Snacks": 16 * 60 + 30,     # 16:30
    "Dinner": 20 * 60,          # 20:00
}

GRACE_MINUTES = 45              # how long after a meal's typical time it still counts as "now"
MINUTES_PER_DAY = 24 * 60       # 1440 - used for wrapping around midnight


def current_meal(now=None):
    """Return the name of the meal to recommend for `now` (defaults to the real clock)."""
    now = now or datetime.now()                          # tests can pass a fixed datetime
    minutes = now.hour * 60 + now.minute                 # current time as minutes after midnight
    best_meal, best_distance = None, None                # we look for the smallest distance
    for meal, center in MEAL_CENTERS.items():
        # How many minutes until this meal's typical time, wrapping round midnight.
        # Python's % always returns a positive number, so -30 % 1440 == 1410.
        ahead = (center - minutes) % MINUTES_PER_DAY
        behind = (minutes - center) % MINUTES_PER_DAY    # how long ago it was
        if behind <= GRACE_MINUTES:                      # we are in (or just after) this meal
            distance = behind
        else:                                            # otherwise: time left until it starts
            distance = ahead
        if best_distance is None or distance < best_distance:
            best_meal, best_distance = meal, distance    # remember the closest meal so far
    return best_meal
