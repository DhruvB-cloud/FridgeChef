r"""
server/app.py
-------------
WHY THIS FILE EXISTS:
    The FridgeChef web server (a "REST API"). The Recipes tab of the app calls it every time the
    tab opens. It owns the master recipe catalogue (its own SQLite file) and does the matching /
    filtering / sorting / recommending with the SAME engine as the app (app/recipe_engine.py),
    so results are identical online and offline.

WHERE IT RUNS:
    * On your PC while developing:    .\.venv\Scripts\python server\app.py   (Flask's built-in server)
      (The desktop app also starts it automatically - see main.py.)
    * In the cloud (Google Cloud Run): started by gunicorn through server/wsgi.py - see the
      Dockerfile and docs/CLOUD_DEPLOYMENT.md.

ENDPOINTS:
    GET  /                         a short welcome text (handy to check the server in a browser)
    GET  /api/health               status + number of recipes
    GET  /api/recipes              the full catalogue (optional ?cuisine=Indian&diet=Veg)
    GET  /api/recipes/<uid>        one recipe
    POST /api/recipes/search       the main call - see search() below for the request body
    GET  /images/<file>            a recipe picture
"""

import os                                    # file paths and environment variables (PORT)
import sys                                   # lets us extend the module search path
import threading                             # a lock, because one SQLite connection is shared by threads
from datetime import date, datetime          # the phone sends its own date/time; we parse them

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../FridgeChef
sys.path.insert(0, PROJECT_DIR)              # so "import app..." finds the shared code in FridgeChef/app

from flask import Flask, abort, jsonify, request, send_from_directory   # noqa: E402  the web framework

from app.api_schema import API_VERSION, match_to_dict, pantry_from_dict, recipe_to_dict  # noqa: E402  JSON helpers
from app.database import Database                                                       # noqa: E402  SQLite access
from app.images import RECIPE_IMAGES_DIR                                                # noqa: E402  folder of pictures
from app.meal_time import current_meal                                                  # noqa: E402  "Lunch" etc.
from app.models import SORT_OPTIONS                                                     # noqa: E402  allowed sorts
from app.recipe_engine import filter_matches, match_all, recommend                      # noqa: E402  the logic

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))        # .../FridgeChef/server
SERVER_DB = os.path.join(SERVER_DIR, "data", "catalog.db")      # the server's own database file


def create_app(db_path=SERVER_DB):
    """Build and return the Flask app. (A function, so tests can pass a temporary database.)"""
    app = Flask(__name__)                                       # the web application object
    db = Database(db_path, check_same_thread=False)             # opens/creates + seeds the catalogue
    app.extensions["fridgechef_db"] = db                        # lets tests close the database file
    lock = threading.Lock()                                     # only one thread uses SQLite at a time

    @app.after_request                                          # runs after EVERY request
    def allow_cross_origin(response):
        """Allow browser-based clients (e.g. a future web version) to call this API too."""
        response.headers["Access-Control-Allow-Origin"] = "*"   # any website may call us
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"   # and send JSON
        return response                                         # hand the response back to Flask

    # -------------------------------------------------------------- GET /
    @app.get("/")                                               # the root address
    def home():
        return "FridgeChef API is running. Try /api/health"     # plain text for a quick browser check

    # -------------------------------------------------------------- GET /api/health
    @app.get("/api/health")                                     # "are you alive?"
    def health():
        with lock:                                              # take the lock while reading SQLite
            count = len(db.list_catalog_recipes())              # how many recipes we serve
        return jsonify(status="ok", api_version=API_VERSION, recipes=count)   # dict -> JSON response

    # -------------------------------------------------------------- GET /api/recipes
    @app.get("/api/recipes")                                    # the whole catalogue
    def list_recipes():
        with lock:
            recipes = db.list_catalog_recipes()                 # every built-in recipe
        cuisine = request.args.get("cuisine")                   # ?cuisine=Indian (or None)
        diet = request.args.get("diet")                         # ?diet=Veg / Non-Veg (or None)
        if cuisine:                                             # filter by cuisine if asked
            recipes = [r for r in recipes if r.cuisine.lower() == cuisine.lower()]
        if diet in ("Veg", "Non-Veg"):                          # filter by diet if asked
            recipes = [r for r in recipes if r.is_veg == (diet == "Veg")]
        return jsonify(count=len(recipes), recipes=[recipe_to_dict(r) for r in recipes])

    # -------------------------------------------------------------- GET /api/recipes/<uid>
    @app.get("/api/recipes/<uid>")                              # <uid> becomes the function argument
    def get_recipe(uid):
        with lock:
            recipe = db.get_recipe_by_uid(uid)                  # e.g. "dal-tadka"
        if recipe is None or recipe.is_user:                    # unknown id (or a private user recipe)
            abort(404)                                          # HTTP 404 = "not found"
        return jsonify(recipe_to_dict(recipe))                  # the recipe as JSON

    # -------------------------------------------------------------- POST /api/recipes/search
    @app.post("/api/recipes/search")                            # the call the Recipes tab makes
    def search():
        """Match the catalogue against the caller's fridge.

        Request JSON:
          {"pantry": [{"name": "Curd", "quantity": 500, "unit": "g", "expiry": "2026-10-04"}, ...],
           "appliances": ["Stove", "Rice Cooker"],
           "servings": 1,
           "filters": {"diet": "Veg", "max_minutes": 30, "nutrition": "Any", "cuisine": "Any",
                       "only_cookable": false, "search": "", "sort": "Most protein"},
           "today": "2026-10-04", "now": "2026-10-04T13:05"}
        Response JSON:
          {"meal": "Lunch", "recommended": [match...], "results": [match...], "count": 12}
        """
        body = request.get_json(silent=True)                    # parsed JSON, or None if invalid
        if not isinstance(body, dict):                          # must be a JSON object {...}
            return jsonify(error="Body must be a JSON object"), 400   # HTTP 400 = "bad request"
        try:                                                    # any malformed field -> 400 below
            pantry = [pantry_from_dict(p, i) for i, p in enumerate(body.get("pantry", []))]   # fridge items
            appliances = set(body.get("appliances", []))        # machines the user owns
            servings = max(1, int(body.get("servings", 1)))     # at least 1 person
            today = date.fromisoformat(body["today"]) if body.get("today") else date.today()     # phone's date
            now = datetime.fromisoformat(body["now"]) if body.get("now") else datetime.now()     # phone's time
            f = body.get("filters", {}) or {}                   # the filter settings (may be missing)
            sort = f.get("sort") if f.get("sort") in SORT_OPTIONS else "Best match"   # ignore unknown sorts
            filters = dict(diet=f.get("diet", "All"),           # "All" / "Veg" / "Non-Veg"
                           max_minutes=f.get("max_minutes"),    # None = any time
                           nutrition=f.get("nutrition", "Any"),
                           cuisine=f.get("cuisine", "Any"),
                           search=str(f.get("search", "")),
                           sort=sort)
            only_cookable = bool(f.get("only_cookable", False)) # "Cook-now only" switch
        except (KeyError, TypeError, ValueError) as error:      # e.g. "today": "yesterday"
            return jsonify(error=f"Invalid request: {error}"), 400

        with lock:
            recipes = db.list_catalog_recipes()                 # the catalogue
        matches = match_all(recipes, pantry, appliances, today=today, servings=servings)   # check each recipe
        meal = current_meal(now)                                # uses the CALLER's clock, not the server's
        recommended = recommend(filter_matches(matches, **filters), meal)   # the Recommended list
        results = filter_matches(matches, only_cookable=only_cookable, **filters)   # the main list
        return jsonify(meal=meal, count=len(results),           # send everything back as JSON
                       recommended=[match_to_dict(m) for m in recommended],
                       results=[match_to_dict(m) for m in results])

    # -------------------------------------------------------------- GET /images/<file>
    @app.get("/images/<path:file_name>")                        # e.g. /images/dal-tadka.jpg
    def image(file_name):
        # send_from_directory refuses paths like "../secret", so only files in that folder are served.
        return send_from_directory(RECIPE_IMAGES_DIR, file_name, max_age=7 * 24 * 3600)   # cache 1 week

    return app                                                  # the finished application


if __name__ == "__main__":                                      # only when run as "python server/app.py"
    port = int(os.environ.get("PORT", 5000))                    # override with: $env:PORT=8000
    print(f"FridgeChef API running. On this PC: http://127.0.0.1:{port}/api/health")   # helpful hint
    print(f"On your phone (same Wi-Fi): http://<this-PC's-IP-address>:{port}")          # helpful hint
    # host 0.0.0.0 = accept connections from other devices; threaded = several requests at once.
    create_app().run(host="0.0.0.0", port=port, threaded=True)  # Flask's built-in development server
