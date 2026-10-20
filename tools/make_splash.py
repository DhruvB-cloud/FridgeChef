"""
make_splash.py
--------------
WHY THIS FILE EXISTS (version 5.0 - "when I open the app there should be an animation"):
    While Android loads Python and the app (a few seconds), it shows a "presplash" screen. Instead
    of a still picture, python-for-android can play a LOTTIE animation there: a small JSON file that
    describes shapes, pictures and how they move (Lottie = the animation format made by Airbnb).

    This developer tool writes assets/splash/splash_lottie.json:
        * the app icon gently "breathes" (grows and shrinks a little),
        * the name "FridgeChef" sits underneath,
        * three coloured dots bounce one after another, like a loading indicator.
    The animation loops seamlessly for as long as loading takes. Pictures are embedded inside the
    JSON (as base64 text), so nothing is downloaded and the file works offline.
    buildozer.spec points android.presplash_lottie at this file.

    Run (from the FridgeChef folder):   .venv\\Scripts\\python tools\\make_splash.py
"""

import base64                                       # pictures -> text, so they fit inside the JSON
import io
import json
import os

from PIL import Image, ImageDraw, ImageFont         # resizes the icon and draws the name

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON = os.path.join(PROJECT_DIR, "assets", "app_icon.png")
FONT = os.path.join(PROJECT_DIR, "assets", "fonts", "Poppins-Bold.ttf")
OUT = os.path.join(PROJECT_DIR, "assets", "splash", "splash_lottie.json")

SIZE = 512                                          # the animation's canvas: 512 x 512 (scaled on the phone)
FPS = 60                                            # frames per second
LOOP = 120                                          # one loop = 120 frames = 2 seconds
ICON_PX = 220                                       # the icon's size on the canvas
INK = (34, 41, 43)                                  # the app's dark text colour (widgets.INK)
DOTS = [(0.20, 0.64, 0.46), (0.98, 0.55, 0.24), (0.91, 0.36, 0.48)]   # emerald, orange, raspberry


def png_data_uri(image):
    """A Pillow image -> 'data:image/png;base64,...' (how Lottie embeds a picture)."""
    buffer = io.BytesIO()
    image.save(buffer, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def wordmark():
    """'FridgeChef' drawn in the app's bold font on a transparent background."""
    font = ImageFont.truetype(FONT, 46)
    left, top, right, bottom = font.getbbox("FridgeChef")
    image = Image.new("RGBA", (right - left + 8, bottom - top + 8), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((4 - left, 4 - top), "FridgeChef", font=font, fill=INK + (255,))
    return image


def still(value):
    """A property that doesn't move."""
    return {"a": 0, "k": value}


def moving(keyframes, ease=0.42):
    """A property that moves through [(frame, value), ...] with gentle ease-in-out between steps."""
    k = []
    for (t, v), (t_next, _) in zip(keyframes, keyframes[1:]):
        n = len(v)
        k.append({"t": t, "s": v, "o": {"x": [ease] * n, "y": [0] * n},    # leave this value smoothly...
                  "i": {"x": [1 - ease] * n, "y": [1] * n}})               # ...and arrive at the next smoothly
    k.append({"t": keyframes[-1][0], "s": keyframes[-1][1]})              # the last keyframe has no curve
    return {"a": 1, "k": k}


def image_layer(index, ref, w, h, position, scale):
    """A layer showing one embedded picture, centred on `position`."""
    return {"ddd": 0, "ind": index, "ty": 2, "nm": ref, "refId": ref, "sr": 1, "ao": 0,
            "ks": {"o": still(100), "r": still(0), "p": still(position + [0]),
                   "a": still([w / 2, h / 2, 0]), "s": scale},
            "ip": 0, "op": LOOP, "st": 0, "bm": 0}


def dot_layer(index, color, x, delay):
    """One round dot that hops up and down once per loop, starting `delay` frames late."""
    base, top = 400, 376                                    # resting height and highest point
    hop = [(0, [x, base, 0]), (delay, [x, base, 0]), (delay + 18, [x, top, 0]),
           (delay + 36, [x, base, 0]), (LOOP, [x, base, 0])]
    circle = {"ty": "gr", "nm": "dot", "it": [
        {"ty": "el", "p": still([0, 0]), "s": still([22, 22]), "d": 1},          # a 22 px circle
        {"ty": "fl", "c": still(list(color) + [1]), "o": still(100), "r": 1},    # filled with `color`
        {"ty": "tr", "p": still([0, 0]), "a": still([0, 0]), "s": still([100, 100]),
         "r": still(0), "o": still(100), "sk": still(0), "sa": still(0)}]}
    return {"ddd": 0, "ind": index, "ty": 4, "nm": f"dot{index}", "sr": 1, "ao": 0,
            "ks": {"o": still(100), "r": still(0), "p": moving(hop), "a": still([0, 0, 0]),
                   "s": still([100, 100, 100])},
            "shapes": [circle], "ip": 0, "op": LOOP, "st": 0, "bm": 0}


def main():
    icon = Image.open(ICON).convert("RGBA").resize((ICON_PX, ICON_PX), Image.LANCZOS)
    name = wordmark()
    breathe = moving([(0, [100, 100, 100]), (LOOP // 2, [106, 106, 100]), (LOOP, [100, 100, 100])])
    animation = {
        "v": "5.7.4", "fr": FPS, "ip": 0, "op": LOOP, "w": SIZE, "h": SIZE, "nm": "FridgeChef splash",
        "ddd": 0,
        "assets": [{"id": "icon", "w": ICON_PX, "h": ICON_PX, "u": "", "p": png_data_uri(icon), "e": 1},
                   {"id": "name", "w": name.width, "h": name.height, "u": "", "p": png_data_uri(name), "e": 1}],
        # Layers are listed top-most first.
        "layers": [dot_layer(1, DOTS[0], 226, 0), dot_layer(2, DOTS[1], 256, 10), dot_layer(3, DOTS[2], 286, 20),
                   image_layer(4, "name", name.width, name.height, [256, 338], still([100, 100, 100])),
                   image_layer(5, "icon", ICON_PX, ICON_PX, [256, 188], breathe)],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(animation, f, separators=(",", ":"))     # compact: no spaces
    print(f"Wrote {OUT} ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    main()
