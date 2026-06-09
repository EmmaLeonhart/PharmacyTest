"""WSGI entry point for production servers.

Exposes a module-level ``app`` built from the same environment configuration as
``python -m pharmacy``, so a production WSGI server can serve the tracker:

    waitress-serve --listen=127.0.0.1:8000 pharmacy.wsgi:app
    gunicorn pharmacy.wsgi:app

See DEPLOYMENT.md. The Flask development server (``python -m pharmacy``) is for
local use only and should not be used in production.
"""

from pharmacy.web import build_app_from_env

app = build_app_from_env()
