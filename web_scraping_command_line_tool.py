#!/usr/bin/env python3
"""
A small command line web scraper built with requests + BeautifulSoup.

It downloads a web page, pulls out the useful bits (title, headings,
paragraphs, links and images) and stores them in a local JSON file so you
can look at them again later.

Usage
-----
Interactive menu (same as the original version of this tool):

    python web_scraping_command_line_tool.py

Or use sub-commands directly:

    python web_scraping_command_line_tool.py scrape https://quotes.toscrape.com --alias quotes
    python web_scraping_command_line_tool.py list
    python web_scraping_command_line_tool.py show quotes
    python web_scraping_command_line_tool.py show quotes --field all_h1_data
    python web_scraping_command_line_tool.py export quotes --output quotes.json
    python web_scraping_command_line_tool.py delete quotes

Run any command with --help to see all options.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import requests
from beautifultable import BeautifulTable
from bs4 import BeautifulSoup

DEFAULT_DB_FILE = "scraped_data.json"
REQUEST_TIMEOUT = 15  # seconds
# Many websites block requests that don't identify themselves, so send a
# User-Agent that says who we are.
USER_AGENT = "web-scraping-with-python/2.0 (+https://github.com/rajat4665/web-scraping-with-python)"


class ScrapeError(Exception):
    """Raised when a page can't be downloaded or parsed."""


# --------------------------------------------------------------------------
# Storage: a single JSON file that looks like {"scraped_data": {alias: {...}}}
# --------------------------------------------------------------------------


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


# --------------------------------------------------------------------------
# Scraping
# --------------------------------------------------------------------------


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


def _texts(soup: BeautifulSoup, tag: str) -> list[str]:
    return [t.get_text(" ", strip=True) for t in soup.find_all(tag) if t.get_text(strip=True)]


def extract_page_data(html: str, base_url: str) -> dict:
    """
    Turn raw HTML into a dictionary of useful data.

    Links and image sources are converted to absolute URLs using base_url,
    so "/about" on https://example.com becomes "https://example.com/about".
    """
    # "html.parser" ships with Python, so there's nothing extra to install.
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    description_tag = soup.find("meta", attrs={"name": "description"})
    anchors = soup.find_all("a")
    images = soup.find_all("img")

    return {
        "title": title_tag.get_text(strip=True) if title_tag else "",
        "description": (description_tag.get("content") or "").strip() if description_tag else "",
        "all_anchor_href": [urljoin(base_url, a["href"]) for a in anchors if a.get("href")],
        "all_anchors": [str(a) for a in anchors],
        "all_images_data": [str(img) for img in images],
        "all_images_source_data": [
            urljoin(base_url, img["src"]) for img in images if img.get("src")
        ],
        "all_h1_data": _texts(soup, "h1"),
        "all_h2_data": _texts(soup, "h2"),
        "all_h3_data": _texts(soup, "h3"),
        "all_p_data": _texts(soup, "p"),
    }


def unique_alias(alias: str, existing) -> str:
    """Return alias, or alias-2, alias-3, ... if it's already taken."""
    if alias not in existing:
        return alias
    n = 2
    while f"{alias}-{n}" in existing:
        n += 1
    return f"{alias}-{n}"


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


# --------------------------------------------------------------------------
# Output helpers
# --------------------------------------------------------------------------

SUMMARY_FIELDS = [
    ("all_h1_data", "H1 headings"),
    ("all_h2_data", "H2 headings"),
    ("all_h3_data", "H3 headings"),
    ("all_p_data", "Paragraphs"),
    ("all_anchor_href", "Links"),
    ("all_images_source_data", "Images"),
]


def _shorten(text: str, width: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= width else text[: width - 1] + "…"


def websites_table(db: dict) -> BeautifulTable:
    table = BeautifulTable(maxwidth=120)
    table.columns.header = ["#", "Alias", "Domain", "Title", "Scraped at"]
    table.set_style(BeautifulTable.STYLE_BOX_DOUBLED)
    for i, (alias, rec) in enumerate(db["scraped_data"].items(), start=1):
        table.rows.append(
            [
                i,
                alias,
                rec.get("domain", ""),
                _shorten(rec.get("title", ""), 40),
                rec.get("scraped_at", ""),
            ]
        )
    return table


def summary_table(record: dict) -> BeautifulTable:
    table = BeautifulTable(maxwidth=120)
    table.columns.header = ["What", "Count", "Example"]
    table.set_style(BeautifulTable.STYLE_BOX_DOUBLED)
    for key, label in SUMMARY_FIELDS:
        values = record.get(key, [])
        table.rows.append([label, len(values), _shorten(values[0], 60) if values else "-"])
    return table


def print_record(alias: str, record: dict) -> None:
    print(f"\n{record.get('title') or '(no title)'}")
    print(f"  alias:   {alias}")
    print(f"  url:     {record.get('url', '')}")
    print(f"  scraped: {record.get('scraped_at', '')}")
    if record.get("description"):
        print(f"  about:   {_shorten(record['description'], 100)}")
    print(summary_table(record))


# --------------------------------------------------------------------------
# Command line interface
# --------------------------------------------------------------------------


def cmd_scrape(args) -> int:
    db = load_db(args.db)
    alias, record = scrape_and_store(
        args.url, db, alias=args.alias, respect_robots=not args.ignore_robots
    )
    save_db(db, args.db)
    print_record(alias, record)
    print(f"\nSaved to {args.db} as '{alias}'.")
    return 0


def cmd_list(args) -> int:
    db = load_db(args.db)
    if not db["scraped_data"]:
        print("No scraped websites yet. Try: scrape https://quotes.toscrape.com")
        return 0
    print(websites_table(db))
    return 0


def _get_record(db: dict, alias: str) -> dict:
    try:
        return db["scraped_data"][alias]
    except KeyError:
        known = ", ".join(db["scraped_data"]) or "none"
        raise ScrapeError(f"No data saved as '{alias}'. Saved aliases: {known}") from None


def cmd_show(args) -> int:
    db = load_db(args.db)
    record = _get_record(db, args.alias)
    if args.field:
        if args.field not in record:
            raise ScrapeError(f"Unknown field '{args.field}'. Fields: {', '.join(record)}")
        value = record[args.field]
        for item in value if isinstance(value, list) else [value]:
            print(item)
    else:
        print_record(args.alias, record)
    return 0


def cmd_export(args) -> int:
    db = load_db(args.db)
    record = _get_record(db, args.alias)
    output = args.output or f"{args.alias}.json"
    with open(output, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)
    print(f"Exported '{args.alias}' to {output}")
    return 0


def cmd_delete(args) -> int:
    db = load_db(args.db)
    _get_record(db, args.alias)
    del db["scraped_data"][args.alias]
    save_db(db, args.db)
    print(f"Deleted '{args.alias}'.")
    return 0


MENU = """
  ================ Welcome to this scraping program ================
    1  ->  list websites you've already scraped
    2  ->  scrape a website
    3  ->  show data for a scraped website
    4  ->  exit
"""


def interactive(db_path: str, respect_robots: bool = True) -> int:
    """The original menu-driven interface."""
    while True:
        print(MENU)
        try:
            choice = input("==>> Please enter your choice: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            choice = "4"

        try:
            if choice == "1":
                cmd_list(argparse.Namespace(db=db_path))
            elif choice == "2":
                url = input("===> URL to scrape: ")
                alias = input("===> Alias to save it as (Enter for the domain name): ")
                cmd_scrape(
                    argparse.Namespace(
                        db=db_path, url=url, alias=alias, ignore_robots=not respect_robots
                    )
                )
            elif choice == "3":
                alias = input("===> Alias to show: ").strip()
                cmd_show(argparse.Namespace(db=db_path, alias=alias, field=None))
            elif choice == "4":
                print("Thank you for using!")
                return 0
            else:
                print("Please enter 1, 2, 3 or 4.")
        except ScrapeError as exc:
            print(f"Error: {exc}")
        except KeyboardInterrupt:
            print("\nCancelled.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape web pages and keep the results in a local JSON file.",
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_FILE,
        help=f"JSON file to store data in (default: {DEFAULT_DB_FILE})",
    )
    parser.add_argument(
        "--ignore-robots",
        action="store_true",
        help="don't check robots.txt (only do this for sites you have permission to scrape)",
    )
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("scrape", help="scrape a URL and save the result")
    p.add_argument("url")
    p.add_argument("--alias", help="name to save it under (default: the domain name)")
    p.set_defaults(func=cmd_scrape)

    p = sub.add_parser("list", help="list saved websites")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="show a saved website")
    p.add_argument("alias")
    p.add_argument("--field", help="print just one field, e.g. all_h2_data or all_anchor_href")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("export", help="export a saved website to its own JSON file")
    p.add_argument("alias")
    p.add_argument("--output", "-o", help="output file (default: <alias>.json)")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("delete", help="delete a saved website")
    p.add_argument("alias")
    p.set_defaults(func=cmd_delete)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        return interactive(args.db, respect_robots=not args.ignore_robots)

    try:
        return args.func(args)
    except ScrapeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
