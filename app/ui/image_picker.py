"""
image_picker.py
---------------
WHY THIS FILE EXISTS:
    "The user can add their own recipe with an image". Picking a photo is platform-specific:
      * Android -> the system gallery/file picker, via the `plyer` library.
      * Desktop -> Kivy's built-in file browser in a popup (works on Windows/macOS/Linux
                   without extra dependencies).
    After picking, import_image() copies a resized JPEG into the app's own folder, so the recipe
    keeps its photo even if the original is deleted from the gallery - and it works offline.
"""

import os            # paths
import uuid          # generates unique file names so two photos never overwrite each other

from kivy.clock import Clock                      # run code on Kivy's main (UI) thread
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserIconView   # desktop file browser widget
from kivy.utils import platform                  # 'android', 'win', 'linux', 'macosx'
from PIL import Image as PILImage, ImageOps       # Pillow, for resizing the chosen photo

from app.ui.widgets import NEUTRAL, INK, FlatButton, bg_rect, light_popup

IMAGE_EXTENSIONS = ["*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp"]   # what the desktop picker shows
MAX_SIDE = 1280                                   # longest side after resizing (keeps files small)


def pick_image(on_picked):
    """Ask the user for a photo. Calls on_picked(path) on the UI thread when one is chosen."""
    if platform == "android":
        _pick_android(on_picked)
    else:
        _pick_desktop(on_picked)


def _pick_android(on_picked):
    from plyer import filechooser                 # only needed (and available) on the phone

    def _selected(selection):
        # plyer calls this from a background thread; UI changes must happen on the main
        # thread, so we hand the result over with Clock.schedule_once.
        if selection:                             # empty list = user cancelled
            Clock.schedule_once(lambda dt: on_picked(selection[0]))
    filechooser.open_file(on_selection=_selected)


def _pick_desktop(on_picked):
    box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(6))
    start = os.path.join(os.path.expanduser("~"), "Pictures")         # start in the Pictures folder
    chooser = FileChooserIconView(path=start if os.path.isdir(start) else os.path.expanduser("~"),
                                  filters=IMAGE_EXTENSIONS)
    # Kivy's file browser draws white file names, so give it a dark rounded panel to sit on.
    panel = BoxLayout(padding=dp(8))
    bg_rect(panel, (0.27, 0.29, 0.30, 1), radius=dp(16))
    panel.add_widget(chooser)
    box.add_widget(panel)
    buttons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
    popup = light_popup("Choose a photo", box, size_hint=(0.95, 0.9))

    def _use(*_):
        if chooser.selection:                     # the file the user clicked on
            popup.dismiss()
            on_picked(chooser.selection[0])
    buttons.add_widget(FlatButton("Cancel", bg=NEUTRAL, fg=INK, on_release=lambda *_: popup.dismiss()))
    buttons.add_widget(FlatButton("Use photo", on_release=_use))
    box.add_widget(buttons)
    popup.open()


def import_image(source_path, images_dir):
    """Copy a resized JPEG version of `source_path` into `images_dir` and return the new path.

    Raises an exception if the file is not a readable image, so the caller can show an error.
    """
    os.makedirs(images_dir, exist_ok=True)
    with PILImage.open(source_path) as img:       # 'with' closes the file automatically
        img = ImageOps.exif_transpose(img)        # fix sideways phone photos
        img = img.convert("RGB")                  # JPEG can't store transparency
        img.thumbnail((MAX_SIDE, MAX_SIDE))       # shrink in place, keeping the aspect ratio
        out_path = os.path.join(images_dir, f"{uuid.uuid4().hex}.jpg")   # random unique name
        img.save(out_path, "JPEG", quality=85)    # 85 = good quality, small file
    return out_path
