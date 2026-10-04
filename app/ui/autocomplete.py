"""
autocomplete.py
---------------
WHY THIS FILE EXISTS:
    "When entering an ingredient name, when I start typing (oni), it should give me a drop down to
    select the ingredient automatically." AutoCompleteInput is a text box that opens a small
    drop-down of suggestions while you type. Tapping a suggestion fills the box and calls
    on_pick(name, info) so the form can also fill in the usual unit / category.
    Used by the Fridge "Add item" form and by the ingredient rows of "Add your recipe".
"""

from kivy.clock import Clock
from kivy.metrics import dp

from app.ingredient_catalog import info_for, suggest
from app.ui.widgets import SoftDropDown, SoftInput, SoftOption   # rounded base widgets


class SuggestionDropDown(SoftDropDown):
    """A drop-down that does NOT swallow taps outside of it.

    Kivy's normal DropDown captures every touch on the screen while it is open: tapping another
    text box would only close the list, and you'd have to tap a second time. Here a tap outside
    closes the list AND still reaches the widget you tapped.
    """

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):                 # tap inside the list -> normal handling
            return super().on_touch_down(touch)
        self.dismiss()                                     # tap outside -> close the list...
        return False                                       # ...and let the tap continue to its target

    def dismiss(self, *args):
        """Close IMMEDIATELY.

        Kivy's DropDown closes a moment *later* (Clock.schedule_once). While typing that is a
        problem: "o" (no suggestions) asks to close, "on" opens the list - and then the late close
        from "o" arrives and hides the list again. Closing right away avoids that race.
        """
        Clock.unschedule(self._real_dismiss)               # cancel any close that is still waiting
        self._real_dismiss()                               # remove the list from the screen now

    def open(self, widget):
        Clock.unschedule(self._real_dismiss)               # a pending close must not hide the new list
        super().open(widget)                               # normal opening below the text box


class AutoCompleteInput(SoftInput):
    """A SoftInput with a suggestion drop-down."""

    def __init__(self, extra_names=(), on_pick=None, **kwargs):
        super().__init__(**kwargs)
        self.extra_names = list(extra_names)            # names the user typed before (pantry/recipes)
        self.on_pick = on_pick                          # callback(name, (unit, category) or None)
        self._dropdown = SuggestionDropDown(auto_width=True, max_height=dp(240))
        self._dropdown.bind(on_select=lambda _dd, name: self._pick(name))
        self._ignore_change = False                     # True while WE set the text (no re-open)
        # NOTE: the focus handler must NOT be called "_on_focus" - Kivy's FocusBehavior already
        # has a method with that name which connects the keyboard. Overriding it (the bug in
        # version 2) made the box look focused while every key press was silently ignored.
        self.bind(text=self._on_text, focus=self._close_when_unfocused)

    def _on_text(self, _instance, text):
        if self._ignore_change or not self.focus:       # only react to the user's own typing
            return
        names = suggest(text, self.extra_names)
        self._dropdown.clear_widgets()
        if not names:
            self._dropdown.dismiss()
            return
        for name in names:
            option = SoftOption(text=name)
            # on_press (finger DOWN) rather than on_release: it fires before the text box loses
            # focus, so the choice is never lost. select() then fires on_select above.
            option.bind(on_press=lambda btn: self._dropdown.select(btn.text))
            self._dropdown.add_widget(option)
        if self._dropdown.attach_to is None:            # not open yet -> open it under the box
            self._dropdown.open(self)

    def _close_when_unfocused(self, _instance, focused):
        if not focused:
            # Close a little later, so a tap on a suggestion still registers before closing.
            Clock.schedule_once(lambda dt: self._dropdown.dismiss(), 0.2)

    def close_suggestions(self):
        """Close the list (called when the form/screen holding this box goes away)."""
        self._dropdown.dismiss()

    def _pick(self, name):
        self._ignore_change = True
        self.text = name                                # fill the box with the chosen name
        self._ignore_change = False
        self._dropdown.dismiss()
        if self.on_pick:
            self.on_pick(name, info_for(name))          # e.g. ("pcs", "Outside") for Onion
