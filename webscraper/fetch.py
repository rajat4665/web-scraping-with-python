"""Downloading pages: URL checks, robots.txt and polite HTTP requests."""

from __future__ import annotations

from urllib import robotparser
from urllib.parse import urlparse

import requests

from .errors import ScrapeError

REQUEST_TIMEOUT = 15  # seconds
# Many websites block requests that don't identify themselves, so send a
# User-Agent that says who we are.
USER_AGENT = "web-scraping-with-python/2.0 (+https://github.com/rajat4665/web-scraping-with-python)"


def normalize_url(url: str) -> str:
    """Add https:// if the scheme is missing and make sure the URL looks valid."""
    url = url.strip()
    if not url:
        raise ScrapeError("Please enter a URL.")
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ScrapeError(f"Not a valid http(s) URL: {url}")
    return url


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def is_allowed_by_robots(url: str, session: requests.Session) -> bool:
    """
    Check the site's robots.txt to see if we're allowed to scrape this URL.
    If robots.txt can't be read we assume scraping is allowed.
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        response = session.get(robots_url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException:
        return True
    if response.status_code != 200:
        return True
    parser = robotparser.RobotFileParser()
    parser.parse(response.text.splitlines())
    return parser.can_fetch(USER_AGENT, url)


def fetch_html(
    url: str,
    session: requests.Session | None = None,
    respect_robots: bool = True,
) -> tuple[str, str]:
    """
    Download a page and return (html, final_url).
    final_url can differ from url when the site redirects.
    """
    session = session or make_session()
    url = normalize_url(url)

    if respect_robots and not is_allowed_by_robots(url, session):
        raise ScrapeError(
            f"robots.txt for {urlparse(url).netloc} does not allow scraping {url}. "
            "Use --ignore-robots only if you have permission."
        )

    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
    except requests.Timeout:
        raise ScrapeError(f"Timed out after {REQUEST_TIMEOUT}s while loading {url}") from None
    except requests.RequestException as exc:
        raise ScrapeError(f"Could not load {url}: {exc}") from None

    if response.status_code != 200:
        raise ScrapeError(f"{url} returned HTTP {response.status_code} {response.reason}")

    content_type = response.headers.get("Content-Type", "")
    if content_type and "html" not in content_type.lower():
        raise ScrapeError(f"{url} is not an HTML page (Content-Type: {content_type})")

    return response.text, response.url
