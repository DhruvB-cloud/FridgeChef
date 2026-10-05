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


def _save_to_gallery(activity, path):
    """Copy the PNG into the phone's gallery (Pictures/FridgeChef) and return its content:// link.

    Other apps (WhatsApp, Gmail...) may not read our app's private folder, but they may read the
    gallery. Android 10+ (API 29+) uses the modern MediaStore way: create an entry, then write the
    bytes into it. Older phones use the classic insertImage() call.
    """
    from jnius import autoclass                          # pyjnius: bridge from Python to Java
    Build = autoclass("android.os.Build$VERSION")        # which Android version is this?
    Images = autoclass("android.provider.MediaStore$Images$Media")   # the gallery's picture table
    Uri = autoclass("android.net.Uri")
    resolver = activity.getContentResolver()             # Android's door to shared storage
    name = os.path.basename(path)                        # e.g. recipe_card_5_2026....png
    if Build.SDK_INT >= 29:                              # Android 10 or newer
        ContentValues = autoclass("android.content.ContentValues")
        values = ContentValues()                         # the new picture's details:
        values.put("_display_name", name)                #   file name     (MediaStore DISPLAY_NAME)
        values.put("mime_type", "image/png")             #   file type     (MediaStore MIME_TYPE)
        values.put("relative_path", "Pictures/FridgeChef")   # folder in the gallery (RELATIVE_PATH)
        uri = resolver.insert(Images.EXTERNAL_CONTENT_URI, values)   # create the empty entry
        if uri is None:
            raise RuntimeError("the gallery refused to create the picture")
        stream = resolver.openOutputStream(uri)          # open it for writing...
        with open(path, "rb") as f:
            stream.write(f.read())                       # ...copy our PNG's bytes into it...
        stream.close()                                   # ...and finish
        return uri
    link = Images.insertImage(resolver, path, name, "FridgeChef recipe card")   # Android 7-9
    if link is None:
        raise RuntimeError("could not save the card to the gallery (storage permission?)")
    return Uri.parse(link)                               # text link -> Android Uri object


def _share_android(path, text):
    """Open Android's share sheet for an image file."""
    from jnius import autoclass, cast                    # pyjnius: bridge from Python to Java
    PythonActivity = autoclass("org.kivy.android.PythonActivity")   # the running Kivy app
    Intent = autoclass("android.content.Intent")
    JString = autoclass("java.lang.String")              # Java's own text type
    activity = PythonActivity.mActivity                  # the current Android screen of our app
    uri = _save_to_gallery(activity, path)               # a link other apps are allowed to read

    intent = Intent(Intent.ACTION_SEND)                  # "send this to another app"
    intent.setType("image/png")                          # tells Android which apps can accept it
    intent.putExtra(Intent.EXTRA_STREAM, cast("android.os.Parcelable", uri))   # the picture
    intent.putExtra(Intent.EXTRA_TEXT, cast("java.lang.CharSequence", JString(text)))   # caption
    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)   # let the receiving app read it
    # Texts are converted to Java's CharSequence explicitly: passing a plain Python string here is
    # a common pyjnius pitfall and a likely cause of the 4.0.0 share bug.
    chooser = Intent.createChooser(intent, cast("java.lang.CharSequence", JString("Share recipe card")))
    activity.startActivity(chooser)                      # show the familiar share sheet


def _open_desktop(path):
    """Open the PNG in the computer's default image viewer."""
    if sys.platform.startswith("win"):
        os.startfile(path)                              # Windows: same as double-clicking the file
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])                # macOS
    else:
        subprocess.Popen(["xdg-open", path])            # Linux desktops


def share_image(path, text="Try this recipe!"):
    """Share (phone) or open (PC) the image.

    Returns (ok, message): ok=True when the share sheet / image viewer opened. On failure the
    message contains the real error, so a problem can be diagnosed instead of being hidden.
    """
    try:
        if KIVY_PLATFORM == "android":
            _share_android(path, text)
            return True, "Choose an app to share your recipe card."
        _open_desktop(path)
        return True, "Card opened in your image viewer.\nSaved at: " + path
    except Exception as error:                           # never crash the app because sharing failed
        print(f"[FridgeChef] Sharing failed: {error!r}")   # also visible in Android's log (logcat)
        return False, f"Sharing did not work: {error}\n\nThe card is saved at:\n{path}"
