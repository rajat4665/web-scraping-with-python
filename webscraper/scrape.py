"""The whole pipeline: fetch a page, extract its data, add it to the database."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

import requests

from .extract import extract_page_data
from .fetch import fetch_html
from .storage import unique_alias


def default_alias(url: str) -> str:
    netloc = urlparse(url).netloc
    return netloc[4:] if netloc.startswith("www.") else netloc


def scrape_and_store(
    url: str,
    db: dict,
    alias: str | None = None,
    session: requests.Session | None = None,
    respect_robots: bool = True,
) -> tuple[str, dict]:
    """Scrape url, add the result to db and return (alias, record)."""
    html, final_url = fetch_html(url, session=session, respect_robots=respect_robots)
    record = extract_page_data(html, final_url)

    alias = (alias or "").strip() or default_alias(final_url)
    alias = unique_alias(alias, db["scraped_data"])

    record.update(
        {
            "url": final_url,
            "name": alias,
            "alias": alias,
            "domain": urlparse(final_url).netloc,
            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": True,
        }
    )
    db["scraped_data"][alias] = record
    return alias, record
