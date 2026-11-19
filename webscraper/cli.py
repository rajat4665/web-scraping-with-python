"""
The command line interface: sub-commands plus the original interactive menu.

Interactive menu:

    python -m webscraper

Sub-commands:

    python -m webscraper scrape https://quotes.toscrape.com --alias quotes
    python -m webscraper list
    python -m webscraper show quotes
    python -m webscraper show quotes --field all_h1_data
    python -m webscraper export quotes --output quotes.json
    python -m webscraper delete quotes

After `pip install -e .` you can type `webscraper` instead of `python -m webscraper`.
Run any command with --help to see all options.
"""

from __future__ import annotations

import argparse
import json
import sys

from beautifultable import BeautifulTable

from .errors import ScrapeError
from .scrape import scrape_and_store
from .storage import DEFAULT_DB_FILE, load_db, save_db

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
        prog="webscraper",
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
