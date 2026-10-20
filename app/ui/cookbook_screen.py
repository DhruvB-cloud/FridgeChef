"""
cookbook_screen.py
------------------
WHY THIS FILE EXISTS:
    The "Cookbook" tab (previously "My Recipes"): every recipe the user created plus every dish
    they tapped "Save" on. All of it is read from the local SQLite file, so it is available with
    no internet at all. The "+ New recipe" button opens the AddRecipeScreen.

    Version 4.2 shows it as a real BOOK: each time you open the tab, the leather cover swings
    open and shows the cream pages inside. The pages read like a cookbook's table of contents -
    two chapters ("Created by you", "Saved dishes"), one line per recipe with a small picture,
    its name, time and cuisine. A ribbon bookmark hangs from the top of the page.
"""

from kivy.animation import Animation              # the cover opening
from kivy.clock import Clock
from kivy.graphics import Color, Line, PopMatrix, PushMatrix, Rectangle, Scale, Triangle
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty       # a value Animation can change smoothly
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout      # lets the cover lie ON TOP of the pages
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from app.dates import short_minutes                  # "2 h 30" style cooking times (4.7.1)
from app.images import resolve_image
from app.recipe_engine import build_pantry_index, match_recipe
from app.ui.widgets import (HEX_GREY, SCENES, Header, RoundImage, Scene, TapBehavior, bg_rect, escape,
                            icon_image, primary_action, scroll_list, thumb_status)

BOOK = SCENES["book"]                             # leather + paper colours (shared scene styles)
INK_BROWN = (0.30, 0.20, 0.15, 1)                 # "printed" text colour on the pages
GOLD = (0.93, 0.80, 0.52, 1)                      # gold lettering / lines on the cover
RIBBON = (0.80, 0.33, 0.30, 1)                    # the red bookmark ribbon


class BookCover(BoxLayout):
    """The closed leather cover. `fold` goes 1 -> 0 as it swings open around its left edge."""

    fold = NumericProperty(1)

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(28), spacing=dp(10), **kwargs)
        with self.canvas.before:
            PushMatrix()                                  # everything below is squeezed by Scale...
            self._scale = Scale()
        bg_rect(self, (1, 1, 1, 1), radius=dp(28), shadow=True, texture="leather.jpg")
        with self.canvas.before:                          # a gold double border, like an old book
            Color(*GOLD)
            self._border = Line(width=dp(1.2))
            self._border2 = Line(width=dp(0.8))
            Color(0, 0, 0, 0.18)                          # darker strip on the left = the spine
            self._spine = Rectangle()
        with self.canvas.after:
            PopMatrix()                                   # ...until here
        self.add_widget(BoxLayout())                      # empty space above the title
        badge = BoxLayout(size_hint_y=None, height=dp(64))
        badge.add_widget(BoxLayout())
        badge.add_widget(icon_image("tab_cookbook", dp(64)))
        badge.add_widget(BoxLayout())
        self.add_widget(badge)
        for text, size in (("My Cookbook", 30), ("FRIDGECHEF", 13)):
            self.add_widget(Label(text=text, bold=True, font_size=sp(size), color=GOLD,
                                  size_hint_y=None, height=dp(size * 1.6)))
        self.add_widget(BoxLayout())                      # empty space below
        self.bind(pos=self._draw, size=self._draw, fold=self._draw)

    def _draw(self, *_):
        self._scale.origin = (self.x, self.center_y)      # hinge: the left edge (the spine)
        self._scale.x = max(self.fold, 0.001)             # 1 = closed, ~0 = fully open
        x, y, w, h = self.x, self.y, self.width, self.height
        self._border.rounded_rectangle = (x + dp(14), y + dp(14), w - dp(28), h - dp(28), dp(16))
        self._border2.rounded_rectangle = (x + dp(19), y + dp(19), w - dp(38), h - dp(38), dp(12))
        self._spine.pos, self._spine.size = (x, y + dp(8)), (dp(16), h - dp(16))

    def open(self, on_done):
        """Swing the cover open (it gets thinner and fades, as if turning away from you)."""
        self.fold, self.opacity = 1, 1
        # It fades out completely (opacity 0): the window may keep showing the LAST frame of the
        # animation for a while, and a cover squeezed to 1 pixel would stay visible as a thin line.
        anim = Animation(fold=0, duration=0.65, t="in_out_cubic") & \
            Animation(opacity=0, duration=0.65, t="in_quad")
        anim.bind(on_complete=lambda *_: on_done())
        anim.start(self)


class IndexLine(TapBehavior, BoxLayout):
    """One recipe in the book's contents: small picture, name, details - and a dotted line under it."""

    def __init__(self, match, on_open, **kwargs):
        super().__init__(size_hint_y=None, height=dp(66), spacing=dp(12), padding=(0, dp(7)), **kwargs)
        recipe = match.recipe
        holder = BoxLayout(size_hint=(None, None), size=(dp(52), dp(52)), pos_hint={"center_y": 0.5})
        holder.add_widget(RoundImage(resolve_image(recipe.picture, small=True), radius=dp(26)))   # round
        self.add_widget(holder)
        texts = BoxLayout(orientation="vertical")
        name = Label(text=f"[b]{escape(recipe.name)}[/b]", markup=True, color=INK_BROWN, font_size=sp(15),
                     halign="left", valign="bottom", shorten=True)
        status, hex_color = thumb_status(match)
        details = Label(text=f"[color={HEX_GREY}]{short_minutes(recipe.prep_minutes)} • {escape(recipe.cuisine)}"
                             f"[/color]   [color={hex_color}][b]{escape(status)}[/b][/color]",
                        markup=True, font_size=sp(12), halign="left", valign="top", shorten=True)
        for label in (name, details):
            label.bind(size=lambda l, s: setattr(l, "text_size", s))   # left-align
            texts.add_widget(label)
        self.add_widget(texts)
        with self.canvas.after:                           # a fine printed line between entries
            Color(*INK_BROWN[:3], 0.14)
            self._dots = Line(width=1)
        self.bind(pos=self._draw, size=self._draw)
        self.bind(on_tap=lambda *_: on_open(recipe.id))     # on_tap = real taps only, not swipes

    def _draw(self, *_):
        self._dots.points = [self.x + dp(64), self.y, self.right, self.y]


class CookbookScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        root = BoxLayout(orientation="vertical")
        self.header = Header("Cookbook", "Your recipes and saved dishes", icon="tab_cookbook")
        root.add_widget(self.header)
        body = BoxLayout(orientation="vertical", padding=(dp(16), dp(4), dp(16), dp(8)), spacing=dp(10))

        # The book: the open pages (a "book" scene), with the cover lying on top until it opens.
        self.book = FloatLayout()
        self.pages = Scene("book", pos_hint={"x": 0, "y": 0})
        self._decorate_pages(self.pages.inner)
        scroll, self.list_box = scroll_list(spacing=dp(2), padding=(dp(14), dp(4), dp(8), dp(8)))
        self.pages.inner.add_widget(scroll)
        self.book.add_widget(self.pages)
        self.cover = BookCover(pos_hint={"x": 0, "y": 0})
        body.add_widget(self.book)
        body.add_widget(primary_action("+  New recipe", self.app.open_add_recipe))
        root.add_widget(body)
        self.add_widget(root)

    @staticmethod
    def _decorate_pages(page):
        """The spine's shadow on the left of the page and a ribbon bookmark at the top right."""
        with page.canvas.before:                          # after the paper colour, behind the text
            shades = [Color(0.35, 0.22, 0.14, a) for a in (0.16, 0.10, 0.06, 0.03)]
            strips = [Rectangle() for _ in shades]        # 4 strips, darker near the spine
        with page.canvas.after:                           # the ribbon lies ON the page
            Color(*RIBBON)
            ribbon = Rectangle()
            Color(*BOOK["surface"])
            notch = Triangle()                            # the "V" cut at the ribbon's end

        def draw(*_):
            for i, strip in enumerate(strips):
                strip.pos, strip.size = (page.x + i * dp(4), page.y + dp(6)), (dp(4), page.height - dp(12))
            x, top = page.right - dp(40), page.top
            ribbon.pos, ribbon.size = (x, top - dp(58)), (dp(16), dp(58))
            notch.points = [x, top - dp(58), x + dp(16), top - dp(58), x + dp(8), top - dp(50)]
        page.bind(pos=draw, size=draw)

    def on_pre_enter(self, *_):
        self.refresh()
        if self.cover.parent is None:                     # close the book again before it is shown
            self.book.add_widget(self.cover)
        self.cover.fold, self.cover.opacity = 1, 1

    def on_enter(self, *_):
        # A short moment to see the closed book, then the cover swings open. When it is open it is
        # REMOVED (not just hidden), so taps reach the recipes on the pages.
        Clock.schedule_once(lambda dt: self.cover.open(on_done=lambda: self.book.remove_widget(self.cover)), 0.25)

    def refresh(self):
        db = self.app.db
        index = build_pantry_index(db.list_pantry())      # so lines can show "Ready to cook" etc.
        owned = db.owned_appliances()
        servings = db.default_servings()
        recipes = db.list_my_recipes()
        mine = [r for r in recipes if r.is_user]          # created by the user
        saved = [r for r in recipes if not r.is_user]     # built-in recipes the user saved
        self.header.set_subtitle(f"{len(mine)} created • {len(saved)} saved")
        self.list_box.clear_widgets()
        contents = Label(text="Contents", bold=True, font_size=sp(24), color=INK_BROWN,
                         size_hint_y=None, height=dp(46), halign="left", valign="middle")
        contents.bind(size=lambda l, s: setattr(l, "text_size", s))   # left-align
        self.list_box.add_widget(contents)
        for number, (title, group, hint) in enumerate((
                ("Created by you", mine, "Tap '+ New recipe' to write your first dish here."),
                ("Saved dishes", saved, "Open any recipe and tap 'Save' to keep it in this book.")), 1):
            self.list_box.add_widget(self._chapter(f"Chapter {number}", f"{title}  ({len(group)})"))
            if not group:
                self.list_box.add_widget(self._hint(hint))
            for recipe in group:
                match = match_recipe(recipe, index, owned, servings)
                self.list_box.add_widget(IndexLine(match, on_open=self.app.open_recipe))

    @staticmethod
    def _chapter(kicker, title):
        """'CHAPTER 1' (small) above 'Created by you (2)' (big)."""
        box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(58), padding=(0, dp(10), 0, 0))
        for text, size, bold, color in ((kicker.upper(), 11, True, BOOK["caption"]),
                                        (title, 18, True, INK_BROWN)):
            label = Label(text=escape(text), font_size=sp(size), bold=bold, color=color,
                          halign="left", valign="middle")
            label.bind(size=lambda l, s: setattr(l, "text_size", s))
            box.add_widget(label)
        return box

    @staticmethod
    def _hint(text):
        label = Label(text=text, italic=True, font_size=sp(14), color=(*INK_BROWN[:3], 0.6),
                      size_hint_y=None, height=dp(44), halign="left", valign="middle")
        label.bind(size=lambda l, s: setattr(l, "text_size", s))
        return label
