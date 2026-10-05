"""
config.py
---------
WHY THIS FILE EXISTS:
    One place for the recipe server address, so switching from "my own PC" to "the cloud" is a
    one-line change.

    * NOW (developing on your PC): CLOUD_SERVER is empty, so the app uses LOCAL_SERVER. On a PC the
      app even starts that local server for you automatically (see main.py).
    * LATER (GitHub / app store / sending the APK to a friend): deploy the server to Google Cloud
      Run (docs/CLOUD_DEPLOYMENT.md), paste the https://... address it gives you into CLOUD_SERVER,
      and rebuild the APK. Every new install then talks to the cloud server.
    Users can still override the address in Profile -> Recipe server.
"""

LOCAL_SERVER = "http://127.0.0.1:5000"     # the Flask server running on this same computer

CLOUD_SERVER = "https://fridgechef-api-847387196162.asia-south1.run.app"   # Google Cloud Run (project fridgechef-56971, Mumbai) - set "" to go back to the local server

DEFAULT_SERVER = CLOUD_SERVER or LOCAL_SERVER   # 'or' picks CLOUD_SERVER when it's filled in, else the local one

REQUEST_TIMEOUT_SECONDS = 8                # a cloud server that was asleep needs a few seconds to wake up


def is_local(url):
    """True when the address points to this computer (then main.py may start the server itself)."""
    return "127.0.0.1" in url or "localhost" in url   # the two common names for "this computer"
