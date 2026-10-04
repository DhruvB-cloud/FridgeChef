"""
server/wsgi.py
--------------
WHY THIS FILE EXISTS:
    In the cloud the server is not started with "python server/app.py" (Flask's small development
    server) but by gunicorn, a production web server that handles many visitors reliably.
    Gunicorn looks for a variable called `application` - this file creates it.
    The Dockerfile runs:   gunicorn ... server.wsgi:application
"""

from server.app import create_app   # the function that builds our Flask app

application = create_app()          # gunicorn serves this object ("WSGI" = the Python web-server standard)
