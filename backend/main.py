"""
main.py — Convenience entry point for the UFC Analytics backend.

The FastAPI application is defined in api/main.py.
This file re-exports `app` so uvicorn can be invoked from backend/ as:

    uvicorn main:app --reload --port 8000

The canonical import path (api.main:app) still works and is used in the
GitHub Actions workflow and gunicorn production command documented in
api/main.py.
"""

from api.main import app  # noqa: F401  (re-export)
