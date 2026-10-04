"""
expiry.py
---------
WHY THIS FILE EXISTS:
    Requirement: "If an item is going to expire today, the user gets a notification".
    This module (1) finds items that expire today / soon / already expired, and
    (2) sends a system notification - at most once per day so the user isn't spammed.
    Notifications use the `plyer` library, which talks to the native notification system on
    Android, Windows, macOS and Linux with the same Python call.
"""

from datetime import date      # "today"


def expiring_today(items, today=None):
    """Pantry items whose expiry date is exactly today."""
    return [i for i in items if i.expires_today(today)]


def expiring_soon(items, days=2, today=None):
    """Items expiring within the next `days` days (but not today) - shown as an amber warning."""
    result = []
    for item in items:
        left = item.days_left(today)                     # None for items that never expire
        if left is not None and 0 < left <= days:
            result.append(item)
    return result


def expired(items, today=None):
    """Items already past their expiry date - these are ignored for cooking."""
    return [i for i in items if i.is_expired(today)]


def build_message(items_today):
    """Human-readable notification text, e.g. 'Curd, Coriander expire today - cook them first!'"""
    names = ", ".join(i.name for i in items_today[:4])   # show at most 4 names to keep it short
    extra = len(items_today) - 4                         # how many names we left out
    if extra > 0:
        names += f" +{extra} more"
    verb = "expires" if len(items_today) == 1 else "expire"   # correct grammar for 1 vs many
    return f"{names} {verb} today - check Recommended dishes to use them up!"


def send_notification(title, message):
    """Show a native notification. Returns True if it worked, False otherwise.

    Wrapped in try/except because notifications can fail (missing permission, unsupported
    desktop, plyer not installed). The app must keep working even then - the UI also shows
    an in-app banner as a fallback.
    """
    try:
        from plyer import notification                   # imported here so the app runs without plyer
        notification.notify(title=title, message=message, app_name="FridgeChef", timeout=10)
        return True
    except Exception as error:                           # any failure -> just log it
        print(f"[FridgeChef] Notification not shown: {error}")
        return False


def notify_if_needed(db, items, today=None):
    """Send the 'expires today' notification once per day. Returns the items expiring today.

    `db` is used to remember the date of the last notification (settings table), so restarting
    the app 10 times in a day does not produce 10 notifications.
    """
    today = today or date.today()
    items_today = expiring_today(items, today)           # what needs attention today
    if not items_today:                                  # nothing expiring -> nothing to do
        return []
    last_sent = db.get_setting("last_expiry_notification")   # e.g. '2026-10-04' or None
    if last_sent != today.isoformat():                   # not yet notified today
        send_notification("Use it today!", build_message(items_today))
        db.set_setting("last_expiry_notification", today.isoformat())
    return items_today
