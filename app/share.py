"""
share.py
--------
WHY THIS FILE EXISTS:
    After recipe_card.py creates the PNG, we need to hand it to the operating system's
    "Share" sheet. That works very differently on Android vs. a desktop PC, so the
    platform-specific code is isolated here and the rest of the app just calls share_image(path).

    * Android : saves the card to the phone gallery, then opens the native share sheet
                (WhatsApp, Gmail, Bluetooth, Nearby Share...). Sharing to nearby devices works
                without mobile data. Uses `pyjnius`, which lets Python call Android's Java classes.
    * Desktop : there is no universal share sheet, so we open the image with the default viewer
                and the user can share/send it from there. The file path is also shown in the app.
"""

import os            # file paths and os.startfile on Windows
import subprocess    # opening files on macOS / Linux
import sys           # sys.platform tells us which desktop OS we're on

try:
    from kivy.utils import platform as KIVY_PLATFORM    # 'android', 'win', 'linux', 'macosx', 'ios'
except ImportError:                                     # tests run without Kivy
    KIVY_PLATFORM = sys.platform


def _share_android(path, text):
    """Open Android's share sheet for an image file."""
    from jnius import autoclass, cast                   # pyjnius: bridge from Python to Java

    # Load the Java classes we need by their full names.
    PythonActivity = autoclass("org.kivy.android.PythonActivity")   # the running Kivy app
    Intent = autoclass("android.content.Intent")
    Uri = autoclass("android.net.Uri")
    MediaStoreImages = autoclass("android.provider.MediaStore$Images$Media")  # the phone gallery

    activity = PythonActivity.mActivity                 # the current Android screen of our app
    # Our app's private folder can't be read by WhatsApp & co. on Android 11+. So we first copy
    # the card into the phone's gallery (MediaStore). That returns a "content://" link which ANY
    # app is allowed to read - and as a bonus the card is now saved in the user's Photos too.
    uri_string = MediaStoreImages.insertImage(activity.getContentResolver(), path,
                                              os.path.basename(path), "FridgeChef recipe card")
    uri = Uri.parse(uri_string)                         # text link -> Android Uri object
    intent = Intent()
    intent.setAction(Intent.ACTION_SEND)                # "send this to another app"
    intent.setType("image/png")                         # tells Android which apps can accept it
    intent.putExtra(Intent.EXTRA_STREAM, cast("android.os.Parcelable", uri))  # the image itself
    intent.putExtra(Intent.EXTRA_TEXT, text)            # optional caption text
    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)  # let the receiver read our file
    chooser = Intent.createChooser(intent, "Share recipe card")   # the familiar share sheet
    activity.startActivity(chooser)                     # show it


def _open_desktop(path):
    """Open the PNG in the computer's default image viewer."""
    if sys.platform.startswith("win"):
        os.startfile(path)                              # Windows: same as double-clicking the file
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])                # macOS
    else:
        subprocess.Popen(["xdg-open", path])            # Linux desktops


def share_image(path, text="Try this recipe!"):
    """Share/open the image. Returns a short status message for the UI to display."""
    try:
        if KIVY_PLATFORM == "android":
            _share_android(path, text)
            return "Choose an app to share your recipe card."
        _open_desktop(path)
        return f"Card saved to:\n{path}"
    except Exception as error:                          # never crash the app because sharing failed
        return f"Card saved to:\n{path}\n(Could not open share: {error})"
