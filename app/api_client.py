"""
api_client.py
-------------
WHY THIS FILE EXISTS:
    "Whenever someone opens the Recipe tab it sends an API request which returns the relevant data."
    This module is the phone-side half of that: it sends HTTP requests to the FridgeChef web
    server (server/app.py) and turns the JSON answers back into Python objects.

    It uses only Python's built-in `urllib`, so nothing extra has to be installed on the phone.

    The network call runs on a BACKGROUND THREAD (fetch_async) so the screen never freezes while
    waiting. If the server can't be reached (no data, server off, wrong address) the caller gets
    an error and the Recipes tab falls back to the offline copy in the local database.

ENDPOINTS USED (see server/app.py for the other side):
    GET  /api/health           -> is the server alive? how many recipes?
    POST /api/recipes/search   -> send pantry + appliances + filters, get matched recipes back
    GET  /images/<file>        -> download a recipe picture we don't have yet
"""

import json                          # encode/decode the request and response bodies
import os
import ssl                           # HTTPS: checks the server's certificate
import threading                     # run the request without freezing the UI
import urllib.error
import urllib.request                # Python's built-in HTTP client


def _make_ssl_context():
    """The rules for HTTPS connections, with a list of trusted certificate authorities.

    On Windows/macOS Python finds that list in the operating system. Python on ANDROID can't, so
    https:// requests would fail with CERTIFICATE_VERIFY_FAILED. The small `certifi` package ships
    the same list Mozilla Firefox uses, so we use it whenever it's installed.
    """
    try:
        import certifi                                     # bundled into the APK via buildozer.spec
        return ssl.create_default_context(cafile=certifi.where())   # trust certifi's list
    except ImportError:                                    # certifi missing (e.g. a minimal PC setup)
        return ssl.create_default_context()                # fall back to the system's list


SSL_CONTEXT = _make_ssl_context()    # created once, reused for every request

from app.api_schema import API_VERSION, match_from_dict, pantry_to_dict
from app.config import DEFAULT_SERVER, REQUEST_TIMEOUT_SECONDS   # server address lives in config.py
from app.images import cache_dir, resolve_image

TIMEOUT_SECONDS = REQUEST_TIMEOUT_SECONDS  # give up after this and go offline instead of hanging


class ApiError(Exception):
    """Raised for any problem talking to the server (network down, bad answer...)."""


class RecipeApiClient:
    def __init__(self, base_url=DEFAULT_SERVER, timeout=TIMEOUT_SECONDS):
        self.base_url = base_url.rstrip("/")               # avoid "http://x:5000//api"
        self.timeout = timeout

    # ------------------------------------------------------------------ low-level HTTP
    def _request(self, method, path, body=None):
        """Send one HTTP request and return the decoded JSON answer."""
        data = json.dumps(body).encode("utf-8") if body is not None else None   # dict -> bytes
        request = urllib.request.Request(
            self.base_url + path, data=data, method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout, context=SSL_CONTEXT) as response:
                return json.loads(response.read().decode("utf-8"))   # bytes -> text -> dict
        except urllib.error.HTTPError as error:            # server answered with 4xx / 5xx
            raise ApiError(f"Server error {error.code}") from error
        except (urllib.error.URLError, OSError, ValueError) as error:   # offline / timeout / bad JSON
            raise ApiError(f"Server unreachable ({getattr(error, 'reason', error)})") from error

    # ------------------------------------------------------------------ API calls
    def health(self):
        """GET /api/health - returns e.g. {"status": "ok", "recipes": 21}."""
        return self._request("GET", "/api/health")

    def search(self, pantry, appliances, filters, servings, today, now):
        """POST /api/recipes/search. Returns (meal, recommended_matches, result_matches)."""
        payload = {
            "api_version": API_VERSION,
            "pantry": [pantry_to_dict(p) for p in pantry],  # what's in the fridge
            "appliances": sorted(appliances),               # which machines the user owns
            "filters": filters,                             # diet / time / nutrition / cuisine / sort...
            "servings": servings,                           # default 1 person
            "today": today.isoformat(),                     # the PHONE's date (expiry checks)
            "now": now.isoformat(timespec="minutes"),       # the PHONE's time (meal slot)
        }
        answer = self._request("POST", "/api/recipes/search", payload)
        return (answer["meal"],
                [match_from_dict(m) for m in answer["recommended"]],
                [match_from_dict(m) for m in answer["results"]])

    def download_image(self, file_name):
        """GET /images/<file> into the local cache folder (so it works offline next time)."""
        folder = cache_dir()
        if not folder or not file_name:
            return None
        target = os.path.join(folder, os.path.basename(file_name))   # basename: no '../' tricks
        try:
            with urllib.request.urlopen(f"{self.base_url}/images/{file_name}", context=SSL_CONTEXT,
                                        timeout=self.timeout) as response:
                with open(target, "wb") as out:
                    out.write(response.read())
            return target
        except (urllib.error.URLError, OSError):
            return None                                    # no picture - the UI shows a placeholder

    # ------------------------------------------------------------------ background helper
    def fetch_async(self, on_done, **search_args):
        """Run search() on a background thread.

        on_done(result, error) is called when finished - from the BACKGROUND thread, so the
        caller must hop back to the UI thread (Kivy: Clock.schedule_once) before touching widgets.
        Missing recipe pictures are downloaded in the same thread.
        """
        def worker():
            try:
                result = self.search(**search_args)
                for match in result[1] + result[2]:        # recommended + all results
                    path = match.recipe.image_path
                    if path and path.startswith("asset:") and resolve_image(path) is None:
                        self.download_image(path[len("asset:"):])
                on_done(result, None)
            except ApiError as error:
                on_done(None, error)
        # daemon=True: the thread won't keep the app alive if the user closes it mid-request.
        threading.Thread(target=worker, daemon=True).start()
