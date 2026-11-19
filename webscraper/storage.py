"""
Saving scraped pages in a single JSON file shaped like:

    {"scraped_data": {"<alias>": {...page data...}, ...}}
"""

from __future__ import annotations

import json
import os
import tempfile

from .errors import ScrapeError

DEFAULT_DB_FILE = "scraped_data.json"


def load_db(path: str = DEFAULT_DB_FILE) -> dict:
    """Load the JSON database. Returns an empty database if the file is missing."""
    try:
        with open(path, encoding="utf-8") as fh:
            db = json.load(fh)
    except FileNotFoundError:
        db = {}
    except json.JSONDecodeError as exc:
        raise ScrapeError(f"{path} is not valid JSON ({exc}). Fix or delete it.") from exc

    if not isinstance(db, dict):
        raise ScrapeError(f"{path} does not contain a JSON object.")
    db.setdefault("scraped_data", {})
    return db


def save_db(db: dict, path: str = DEFAULT_DB_FILE) -> None:
    """Write the database to disk safely (a crash mid-write won't corrupt it)."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(db, fh, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except BaseException:
        os.unlink(tmp_path)
        raise


def unique_alias(alias: str, existing) -> str:
    """Return alias, or alias-2, alias-3, ... if it's already taken."""
    if alias not in existing:
        return alias
    n = 2
    while f"{alias}-{n}" in existing:
        n += 1
    return f"{alias}-{n}"
