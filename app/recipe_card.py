"""
recipe_card.py
--------------
WHY THIS FILE EXISTS:
    Requirement: "share the recipe in the format of a simple play card ... in the form of an image".
    This module draws a portrait card (like a playing card / Instagram post, 1080 x 1350 pixels)
    with the dish photo, name, veg marker, time, servings, ingredients and steps, and saves it
    as a PNG file. The PNG can then be shared through any app (WhatsApp, email...) - see share.py.

    It uses Pillow (PIL), the standard Python imaging library. It contains no UI code, so it can
    also be run from tests or the command line.
"""

import os                                              # file paths
from PIL import Image, ImageDraw, ImageFont, ImageOps  # Pillow: create & draw images

# Card geometry (pixels). 4:5 portrait looks good in chat apps and on Instagram.
CARD_W, CARD_H = 1080, 1350
MARGIN = 60                                            # empty space around the content
PHOTO_H = 520                                          # height of the photo area at the top

# Colours as (Red, Green, Blue) tuples - the same soft palette as the app.
BG = (248, 245, 239)                                   # warm cream background
INK = (51, 56, 59)                                     # main text colour (soft charcoal)
MUTED = (138, 143, 147)                                # secondary text colour
ACCENT = (79, 138, 91)                                 # sage green (headings)
ACCENT_SOFT = (227, 242, 229)                          # pale sage (footer band)
VEG_GREEN = (0, 140, 60)                               # standard Indian veg marker colour
NONVEG_RED = (190, 30, 30)                             # standard non-veg marker colour
PHOTO_RADIUS = 48                                      # roundness of the photo corners


def _font(size, bold=False):
    """Find a TrueType font that exists on this device, falling back gracefully.

    Order: Kivy's bundled Roboto (always present when the app runs) -> common system fonts ->
    Pillow's built-in font (always works, needs Pillow >= 10.1 for sizing).
    """
    candidates = []
    try:
        import kivy                                    # Kivy ships Roboto inside its package folder
        font_dir = os.path.join(os.path.dirname(kivy.__file__), "data", "fonts")
        candidates.append(os.path.join(font_dir, "Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf"))
    except ImportError:                                # e.g. running the tests without Kivy
        pass
    candidates += ["arialbd.ttf" if bold else "arial.ttf",                 # Windows
                   "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]   # Linux / Android
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)      # succeeds if the font file is found
        except OSError:                                # not found -> try the next candidate
            continue
    return ImageFont.load_default(size=size)           # last resort


def _wrap(draw, text, font, max_width):
    """Split `text` into lines that fit inside `max_width` pixels (simple word wrapping)."""
    words, lines, line = text.split(), [], ""
    for word in words:
        trial = f"{line} {word}".strip()               # current line plus the next word
        if draw.textlength(trial, font=font) <= max_width:
            line = trial                               # still fits -> keep adding words
        else:
            if line:
                lines.append(line)                     # line is full -> store it
            line = word                                # start a new line with this word
    if line:
        lines.append(line)                             # don't forget the last line
    return lines


def _photo_area(card, recipe, image_file):
    """Paste the recipe photo with rounded corners (cropped to fill), or a soft placeholder."""
    inset = 40                                          # gap between card edge and photo
    box = (CARD_W - 2 * inset, PHOTO_H - inset)         # photo size
    # A rounded-rectangle "mask": white where the photo shows, black where it's hidden.
    mask = Image.new("L", box, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, box[0] - 1, box[1] - 1], radius=PHOTO_RADIUS, fill=255)
    photo = None
    if image_file and os.path.exists(image_file):
        try:
            photo = Image.open(image_file).convert("RGB")             # load the picture
            photo = ImageOps.exif_transpose(photo)                    # respect phone rotation info
            photo = ImageOps.fit(photo, box, method=Image.LANCZOS)    # crop+resize to fill the box
        except Exception as error:                     # corrupt image -> fall back to placeholder
            print(f"[FridgeChef] Could not load photo: {error}")
            photo = None
    if photo is None:                                   # soft green block with the first letter
        photo = Image.new("RGB", box, ACCENT_SOFT)
        draw = ImageDraw.Draw(photo)
        initial = recipe.name[:1].upper() or "?"
        font = _font(260, bold=True)
        w = draw.textlength(initial, font=font)
        draw.text(((box[0] - w) / 2, 70), initial, font=font, fill=ACCENT)
    card.paste(photo, (inset, inset), mask)             # paste only where the mask is white


def _diet_marker(draw, x, y, is_veg, size=44):
    """Draw the Indian veg / non-veg symbol: a square outline with a dot (veg) or triangle (non-veg)."""
    color = VEG_GREEN if is_veg else NONVEG_RED
    draw.rectangle([x, y, x + size, y + size], outline=color, width=5)   # the square outline
    pad = size * 0.25
    if is_veg:
        draw.ellipse([x + pad, y + pad, x + size - pad, y + size - pad], fill=color)   # circle
    else:
        draw.polygon([(x + size / 2, y + pad), (x + size - pad, y + size - pad),
                      (x + pad, y + size - pad)], fill=color)                           # triangle


def create_recipe_card(recipe, out_path, image_file=None):
    """Draw the share card for `recipe` and save it as PNG at `out_path`. Returns out_path.

    image_file - the real picture file to use (the app passes images.resolve_image(...) because
                 built-in pictures are stored as "asset:<name>" rather than as a full path).
    """
    card = Image.new("RGB", (CARD_W, CARD_H), BG)       # blank cream canvas
    _photo_area(card, recipe, image_file)               # top part: photo or placeholder
    draw = ImageDraw.Draw(card)                         # a "pen" that draws on the card
    content_w = CARD_W - 2 * MARGIN                     # usable text width
    y = PHOTO_H + 40                                    # current vertical drawing position

    # --- title row: diet marker + dish name (wrapped to max 2 lines)
    _diet_marker(draw, MARGIN, y + 12, recipe.is_veg)
    title_font = _font(64, bold=True)
    for line in _wrap(draw, recipe.name, title_font, content_w - 70)[:2]:
        draw.text((MARGIN + 70, y), line, font=title_font, fill=INK)
        y += 76                                         # move down one line

    # --- info line: cuisine • time • servings • tags
    info = f"{recipe.cuisine}  •  {recipe.prep_minutes} min  •  Serves {recipe.servings}"
    if recipe.protein_g or recipe.carbs_g:              # nutrition per person, when known
        info += f"  •  {recipe.protein_g:g} g protein, {recipe.carbs_g:g} g carbs"
    elif recipe.nutrition_tags:
        info += "  •  " + ", ".join(recipe.nutrition_tags[:2])
    draw.text((MARGIN, y + 6), info, font=_font(32), fill=MUTED)
    y += 70
    draw.line([MARGIN, y, CARD_W - MARGIN, y], fill=(220, 210, 190), width=3)   # divider
    y += 24

    # --- ingredients in two columns
    heading = _font(38, bold=True)
    body = _font(30)
    draw.text((MARGIN, y), "Ingredients", font=heading, fill=ACCENT)
    y += 56
    col_w = content_w // 2                              # each column is half the width
    rows = (len(recipe.ingredients) + 1) // 2           # rows needed for two columns (rounded up)
    rows = min(rows, 6)                                 # keep space for steps: max 12 ingredients
    for idx, ing in enumerate(recipe.ingredients[: rows * 2]):
        col, row = divmod(idx, rows)                    # fill the left column first, then the right
        qty = f"{ing.quantity:g} {ing.unit}"            # ':g' prints 2.0 as '2' and 0.5 as '0.5'
        text = f"• {ing.name} - {qty}" + (" (opt)" if ing.optional else "")
        line = _wrap(draw, text, body, col_w - 20)[0]   # first line only, to keep rows aligned
        draw.text((MARGIN + col * col_w, y + row * 42), line, font=body, fill=INK)
    y += rows * 42 + 24

    # --- steps (as many as fit before the footer)
    draw.text((MARGIN, y), "Method", font=heading, fill=ACCENT)
    y += 56
    footer_top = CARD_H - 90                            # stop before the footer area
    for num, step in enumerate(recipe.steps, start=1):
        lines = _wrap(draw, f"{num}. {step}", body, content_w)
        if y + len(lines) * 40 > footer_top:            # this step would not fit
            draw.text((MARGIN, y), "...", font=body, fill=MUTED)
            break
        for line in lines:
            draw.text((MARGIN, y), line, font=body, fill=INK)
            y += 40
        y += 8                                          # small gap between steps

    # --- footer: a soft rounded "pill" with the app name
    footer = "Shared from FridgeChef"
    f_font = _font(30, bold=True)
    w = draw.textlength(footer, font=f_font)
    pill = [(CARD_W - w) / 2 - 36, CARD_H - 84, (CARD_W + w) / 2 + 36, CARD_H - 30]
    draw.rounded_rectangle(pill, radius=27, fill=ACCENT_SOFT)
    draw.text(((CARD_W - w) / 2, CARD_H - 74), footer, font=f_font, fill=ACCENT)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)   # ensure the folder exists
    card.save(out_path, "PNG")                          # write the image file
    return out_path
