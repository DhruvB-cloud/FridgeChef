"""
cookbook_screen.py
------------------
WHY THIS FILE EXISTS:
    The "Cookbook" tab (previously "My Recipes"): every recipe the user created plus every dish
    they tapped "Save" on, shown as a grid of picture cards. All of it is read from the local
    SQLite file, so it is available with no internet at all. The "+ New recipe" button opens the
    AddRecipeScreen.
"""

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen

from app.recipe_engine import build_pantry_index, match_recipe
from app.ui.widgets import (MUTED, Card, Header, RecipeCard, SoftButton, WrapLabel, scroll_list,
                            section_title)


class CookbookScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        root = BoxLayout(orientation="vertical")
        self.header = Header("Cookbook", "Your recipes and saved dishes")
        root.add_widget(self.header)
        body = BoxLayout(orientation="vertical", padding=(dp(16), dp(4), dp(16), dp(8)), spacing=dp(12))
        body.add_widget(SoftButton("+  New recipe", on_release=lambda *_: self.app.open_add_recipe()))
        scroll, self.list_box = scroll_list(padding=(0, dp(4), 0, dp(16)))
        body.add_widget(scroll)
        root.add_widget(body)
        self.add_widget(root)
        self.bind(width=lambda *_: self.refresh() if self.manager and self.manager.current == self.name else None)

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        db = self.app.db
        index = build_pantry_index(db.list_pantry())      # so cards can show "Ready to cook" etc.
        owned = db.owned_appliances()
        servings = db.default_servings()
        recipes = db.list_my_recipes()
        mine = [r for r in recipes if r.is_user]          # created by the user
        saved = [r for r in recipes if not r.is_user]     # built-in recipes the user saved
        self.header.set_subtitle(f"{len(mine)} created • {len(saved)} saved")
        cols = max(2, int(self.width // dp(190)))         # 2 columns on phones, more when wider
        self.list_box.clear_widgets()
        for title, group, hint in (
                ("Created by you", mine, "Tap '+ New recipe' to add your first dish."),
                ("Saved dishes", saved, "Open any recipe and tap 'Save' to keep it here.")):
            self.list_box.add_widget(section_title(f"{title}  ({len(group)})"))
            if not group:
                empty = Card(shadow=False)
                empty.add_widget(WrapLabel(text=hint, color=MUTED, font_size=sp(14)))
                self.list_box.add_widget(empty)
                continue
            grid = GridLayout(cols=cols, spacing=dp(12), size_hint_y=None, col_force_default=True)
            grid.bind(minimum_height=grid.setter("height"))
            # Fixed, equal column widths - otherwise a single card would stretch across the row.
            grid.bind(width=lambda g, w, n=cols: setattr(g, "col_default_width", (w - dp(12) * (n - 1)) / n))
            for recipe in group:
                match = match_recipe(recipe, index, owned, servings)
                grid.add_widget(RecipeCard(match, on_open=self.app.open_recipe))
            self.list_box.add_widget(grid)
