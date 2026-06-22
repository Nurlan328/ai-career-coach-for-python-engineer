"""Convenience entrypoint so `uvicorn main:app` works.

The real application lives in app.main. Prefer running:
    uvicorn app.main:app --reload
"""
from app.main import app

__all__ = ["app"]
