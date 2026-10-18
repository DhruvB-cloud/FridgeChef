YOUR OWN FRIDGE CONTAINER PICTURES
==================================

Put a PNG here to replace one of the fridge container pictures. The file name decides which one:

    jar.png      bottle.png   dish.png     carton.png
    can.png      tub.png      box.png      basket.png
    pot.png      glass.png    greens.png   takeout.png

Picture tips
    * PNG with a TRANSPARENT background (no white box around the object).
    * Square-ish, at least 256 x 256 pixels (bigger is fine - it is shrunk automatically).
    * The object seen from the front, standing upright.
    * Leave a calm area in the lower-middle part: the app puts the cream name sticker there.

Then run (from the FridgeChef folder):

    .\.venv\Scripts\python tools\make_assets.py containers

That trims your picture, makes its mouldy "expired" version and updates containers.json.
Pictures without a custom file keep using Google's free Noto Emoji 2D set.
To move the name sticker, change that container's numbers in CONTAINER_SOURCES in
tools/make_assets.py (centre x, centre y, width, height - as fractions of the picture) and run it again.
