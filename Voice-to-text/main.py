"""Entrypoint for running the FastAPI app from the repo root.

This file keeps a small surface so you can run either:

  uvicorn main:app --reload

or execute `python main.py` which will start uvicorn for development.
"""

from app import app
from config import settings

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=settings.PORT or 8000, reload=True)