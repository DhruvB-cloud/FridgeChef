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

import math                                  # isfinite(): refuse NaN / Infinity numbers (4.7.1)
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

# ---- Limits for what a caller may send (version 4.7.1, from the QA report) ----
MAX_BODY_BYTES = 256 * 1024          # a real request is a few KB; bigger ones are refused (HTTP 413)
MAX_PANTRY_ITEMS = 1000              # far more than any real fridge
MAX_NAME_CHARS = 200                 # the app allows 126; a little slack for older app versions
MAX_SERVINGS = 20                    # same limit as the app
MAX_MINUTES = 14400                  # same limit as the app (10 days)


class BadInput(ValueError):
    """A request we refuse. Its message is shown to the caller, so it is written in plain English."""


def _number(value, what, low=None, high=None, whole=False):
    """Check one number from the request and return it (raises BadInput with a clear message)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):   # True/False also count as ints in Python
        raise BadInput(f"'{what}' must be a number.")
    if not math.isfinite(value):                       # NaN or Infinity
        raise BadInput(f"'{what}' must be a normal number.")
    if whole and value != int(value):
        raise BadInput(f"'{what}' must be a whole number.")
    if (low is not None and value < low) or (high is not None and value > high):
        limits = f"at least {low}" if high is None else f"between {low} and {high}"
        raise BadInput(f"'{what}' must be {limits}.")
    return int(value) if whole else float(value)


def _text(value, what, default):
    """Check an optional text field: missing -> default; anything that is not short text -> refused."""
    if value is None:
        return default
    if not isinstance(value, str) or len(value) > MAX_NAME_CHARS:
        raise BadInput(f"'{what}' must be a short piece of text.")
    return value


def _date(value, what, parse):
    """Check an optional date / date-time text (YYYY-MM-DD...). Missing -> None."""
    if not value:
        return None
    if not isinstance(value, str):
        raise BadInput(f"'{what}' must be a date like 2026-10-20.")
    try:
        return parse(value)
    except ValueError:
        raise BadInput(f"'{what}' must be a date like 2026-10-20.") from None


def read_search_request(body):
    """Validate the JSON body of POST /api/recipes/search; return everything search() needs."""
    if not isinstance(body, dict):
        raise BadInput("The request body must be a JSON object.")
    items = body.get("pantry", [])
    if not isinstance(items, list) or len(items) > MAX_PANTRY_ITEMS:
        raise BadInput(f"'pantry' must be a list of at most {MAX_PANTRY_ITEMS} items.")
    pantry = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise BadInput(f"Pantry item {i + 1} must be an object with name, quantity and unit.")
        name = _text(item.get("name"), f"pantry item {i + 1} name", "")
        if not name.strip():
            raise BadInput(f"Pantry item {i + 1} needs a name.")
        quantity = _number(item.get("quantity"), f"pantry item {i + 1} quantity", low=0)
        unit = _text(item.get("unit"), f"pantry item {i + 1} unit", "pcs")
        expiry = _date(item.get("expiry"), f"pantry item {i + 1} expiry", date.fromisoformat)
        pantry.append(pantry_from_dict({"name": name, "quantity": quantity, "unit": unit,
                                        "expiry": expiry.isoformat() if expiry else None}, i))
    machines = body.get("appliances", [])
    if not isinstance(machines, list) or not all(isinstance(a, str) for a in machines):
        raise BadInput("'appliances' must be a list of names, e.g. [\"Stove\"].")
    servings = _number(body.get("servings", 1), "servings", low=1, high=MAX_SERVINGS, whole=True)
    today = _date(body.get("today"), "today", date.fromisoformat) or date.today()
    now = _date(body.get("now"), "now", datetime.fromisoformat) or datetime.now()
    f = body.get("filters") or {}
    if not isinstance(f, dict):
        raise BadInput("'filters' must be an object.")
    max_minutes = f.get("max_minutes")                 # older app versions still send this
    if max_minutes is not None:
        max_minutes = _number(max_minutes, "max_minutes", low=1, high=MAX_MINUTES, whole=True)
    sort = f.get("sort") if f.get("sort") in SORT_OPTIONS else "Best match"   # unknown sorts are ignored
    filters = dict(diet=_text(f.get("diet"), "diet", "All"),
                   max_minutes=max_minutes,
                   nutrition=_text(f.get("nutrition"), "nutrition", "Any"),
                   cuisine=_text(f.get("cuisine"), "cuisine", "Any"),
                   search=_text(f.get("search"), "search", ""),
                   sort=sort)
    return pantry, set(machines), servings, today, now, filters, bool(f.get("only_cookable", False))
SERVER_DB = os.path.join(SERVER_DIR, "data", "catalog.db")      # the server's own database file


def create_app(db_path=SERVER_DB):
    """Build and return the Flask app. (A function, so tests can pass a temporary database.)"""
    app = Flask(__name__)                                       # the web application object
    app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES           # 4.7.1: refuse huge request bodies
    db = Database(db_path, check_same_thread=False)             # opens/creates + seeds the catalogue
    app.extensions["fridgechef_db"] = db                        # lets tests close the database file
    lock = threading.Lock()                                     # only one thread uses SQLite at a time

    # ---- 4.7.1: every error is answered with a short JSON message - never a Python error page.
    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error="Not found."), 404

    @app.errorhandler(405)
    def wrong_method(_error):
        return jsonify(error="This address does not support that kind of request."), 405

    @app.errorhandler(413)
    def too_big(_error):
        return jsonify(error="The request is too large."), 413

    @app.errorhandler(Exception)
    def unexpected(error):
        code = getattr(error, "code", 500)                      # Flask's own HTTP errors carry a code
        if isinstance(code, int) and code < 500:
            return jsonify(error="The request could not be processed."), code
        print(f"[FridgeChef server] Unexpected error: {error!r}")   # details go to the server log only
        return jsonify(error="Something went wrong on the server. Please try again later."), 500

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
        try:
            body = request.get_json(silent=True)                # parsed JSON, or None if invalid
            # 4.7.1: every field is checked (type, range, size) - see read_search_request() above.
            pantry, appliances, servings, today, now, filters, only_cookable = read_search_request(body)
        except BadInput as problem:                             # a clear message for the caller
            return jsonify(error=str(problem)), 400             # HTTP 400 = "bad request"
        except RecursionError:                                  # absurdly deeply nested JSON
            return jsonify(error="The request is not valid JSON."), 400

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
