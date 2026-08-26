"""Entry point for cPanel's "Setup Python App" (Phusion Passenger).

Passenger's classic mode expects a WSGI callable named `application` in this exact
file at the application root. This project's app (app/main.py) is a FastAPI app,
which speaks ASGI, not WSGI — a2wsgi bridges the two so Passenger can run it
unmodified. See README.md's "Deploying on cPanel shared hosting" section for the
full setup steps.

If your host's Passenger version is new enough to run ASGI apps directly (6.0+,
with an explicit `passenger_app_type asgi` setting available to you), you can skip
this adapter entirely and point Passenger straight at `app.main:app` instead — but
most cPanel "Setup Python App" UIs only expose the WSGI path, which is what this
file is for.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from a2wsgi import ASGIMiddleware

from app.main import app as _asgi_app

application = ASGIMiddleware(_asgi_app)
