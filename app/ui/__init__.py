# Marks "app/ui" as a Python package. Each screen of the app lives in its own module here:
#   widgets.py              - soft colours + rounded building blocks (buttons, inputs, cards, chips,
#                             rounded images, popups, recipe tiles)
#   autocomplete.py         - text box with an ingredient suggestion drop-down ("oni" -> Onion)
#   image_picker.py         - choosing a photo for a recipe (Android + desktop)
#   pantry_screen.py        - "Fridge" tab: items, quantities, expiry dates
#   recipes_screen.py       - "Recipes" tab: calls the web API, filters, sort, Recommended
#   recipe_detail_screen.py - one recipe: nutrition, servings, cooking mode, share card, save
#   add_recipe_screen.py    - form to create your own recipe with a photo
#   cookbook_screen.py      - "Cookbook" tab: your own + saved dishes
#   calendar_screen.py      - "Calendar" tab: what you cooked on which day
#   profile_screen.py       - "Profile" tab: streak, favourite dish, stats, settings, appliances
