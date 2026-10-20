"""
image_picker.py
---------------
WHY THIS FILE EXISTS:
    "The user can add their own recipe with an image". Picking a photo is platform-specific:
      * Android -> the system photo picker (Android 13+) or the "choose a file" screen (older
                   phones). Version 4.7.1: we read the chosen photo through the temporary access
                   Android grants for that ONE picture, so the app needs NO photo/storage permission
                   (Google Play restricts those permissions - see the QA report).
      * Desktop -> Kivy's built-in file browser in a popup (works on Windows/macOS/Linux
                   without extra dependencies).
    After picking, import_image() copies a resized JPEG into the app's own folder, so the recipe
    keeps its photo even if the original is deleted from the gallery - and it works offline.

LIMITS (version 4.7.1):
    * Photos larger than 5 MB are refused with a friendly message (Dhruv's rule).
    * Big JPEGs are decoded at a reduced size ("draft" mode), so even a large photo needs only a
      few MB of memory instead of ~850 MB (measured in the QA report for a 64-megapixel photo).
"""

import io            # BytesIO: lets Pillow read a photo that is already in memory
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
MAX_BYTES = 5 * 1024 * 1024                       # 5 MB: the biggest photo we accept (4.7.1)
MAX_PIXELS = 40_000_000                           # refuse absurd non-JPEG sizes (e.g. a 20000x20000 PNG)
PICK_REQUEST = 4711                               # our id for the Android "pick a photo" request


class PhotoError(Exception):
    """A photo we cannot use. The message is written for the user (shown as-is in a popup)."""


def pick_image(on_picked):
    """Ask the user for a photo. Calls on_picked(source) on the UI thread when one is chosen.

    source is a file path (PC) or an open binary file (Android) - import_image() accepts both.
    """
    if platform == "android":
        _pick_android(on_picked)
    else:
        _pick_desktop(on_picked)


def _pick_android(on_picked):
    """Open Android's photo picker and hand the chosen photo to on_picked as an open file."""
    from android import activity                  # python-for-android: activity results arrive here
    from jnius import autoclass                   # pyjnius: use Android's Java classes from Python
    Intent = autoclass("android.content.Intent")
    Build = autoclass("android.os.Build$VERSION")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")   # our running app

    if Build.SDK_INT >= 33:                       # Android 13+: the modern system photo picker
        intent = Intent("android.provider.action.PICK_IMAGES")
    else:                                         # older phones: the "choose a file" screen
        intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.addCategory(Intent.CATEGORY_OPENABLE)   # only files we can actually open
    intent.setType("image/*")                     # pictures only

    def _result(request_code, result_code, data):
        if request_code != PICK_REQUEST:          # an answer to some other request - not ours
            return
        activity.unbind(on_activity_result=_result)   # one answer per request
        if result_code != -1 or data is None or data.getData() is None:   # -1 = RESULT_OK
            return                                # the user cancelled
        try:
            resolver = PythonActivity.mActivity.getContentResolver()
            pfd = resolver.openFileDescriptor(data.getData(), "r")   # read access to THIS photo only
            source = os.fdopen(pfd.detachFd(), "rb")   # hand the file to Python as a normal file
        except Exception as error:                # e.g. the photo lives in the cloud and is offline
            print(f"[FridgeChef] Could not open the chosen photo: {error!r}")
            source = None
        # The answer arrives on Android's thread; UI work must happen on Kivy's main thread.
        Clock.schedule_once(lambda dt: on_picked(source) if source else _could_not_open())

    activity.bind(on_activity_result=_result)     # listen for the picker's answer
    PythonActivity.mActivity.startActivityForResult(intent, PICK_REQUEST)


def _could_not_open():
    from app.ui.widgets import show_message      # local import: only needed on this rare path
    show_message("Photo problem", "That photo could not be opened. Please try another one.")


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


def read_limited(source):
    """Read the photo's bytes (a path or an open file), refusing anything over 5 MB."""
    if isinstance(source, str):                   # a path (PC)
        with open(source, "rb") as f:
            data = f.read(MAX_BYTES + 1)          # read one byte MORE than allowed...
    else:                                         # an open file (Android)
        with source:                              # 'with' closes it afterwards
            data = source.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:                     # ...so a too-big file is noticed without reading it all
        raise PhotoError("This photo is larger than 5 MB. Please choose a smaller photo "
                         "(or take one with a lower camera resolution).")
    return data


def import_image(source, images_dir):
    """Copy a resized JPEG version of `source` (path or open file) into `images_dir`; return the new path.

    Raises PhotoError (with a message for the user) if the photo is too big or not a picture.
    """
    try:
        data = read_limited(source)
        with PILImage.open(io.BytesIO(data)) as img:   # 'with' closes the picture afterwards
            img.draft("RGB", (MAX_SIDE, MAX_SIDE))     # JPEG: decode at a reduced size (saves memory)
            if img.width * img.height > MAX_PIXELS:    # still enormous (e.g. a huge PNG) -> refuse
                raise PhotoError("This picture is too large. Please choose a normal photo.")
            img.thumbnail((MAX_SIDE, MAX_SIDE))        # shrink FIRST, keeping the aspect ratio...
            img = ImageOps.exif_transpose(img)         # ...then fix sideways phone photos...
            img = img.convert("RGB")                   # ...and drop transparency (JPEG can't store it)
            os.makedirs(images_dir, exist_ok=True)
            out_path = os.path.join(images_dir, f"{uuid.uuid4().hex}.jpg")   # random unique name
            img.save(out_path, "JPEG", quality=85)     # 85 = good quality, small file
        return out_path
    except PhotoError:
        raise                                          # already has a friendly message
    except Exception as error:                         # not a picture, damaged, unreadable...
        print(f"[FridgeChef] Photo import failed: {error!r}")   # details for the developer log
        raise PhotoError("This file isn't a photo we can open. Please choose a JPG or PNG picture.")
