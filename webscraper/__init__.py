"""
webscraper: a small web scraper built with requests + BeautifulSoup.

It downloads a web page, pulls out the useful bits (title, headings,
paragraphs, links and images) and stores them in a local JSON file so you
can look at them again later.

Modules:
    fetch.py    download pages politely (User-Agent, timeouts, robots.txt)
    extract.py  turn HTML into a dict of data
    storage.py  load and save the JSON database
    scrape.py   fetch + extract + store, in one call
    cli.py      the command line interface and interactive menu

Use it from the command line (see cli.py), or from Python:

    from webscraper import fetch_html, extract_page_data

    html, url = fetch_html("https://quotes.toscrape.com")
    data = extract_page_data(html, url)
    print(data["title"], len(data["all_anchor_href"]), "links")
"""

from .errors import ScrapeError
from .extract import extract_page_data
from .fetch import fetch_html, normalize_url
from .scrape import scrape_and_store
from .storage import load_db, save_db

__version__ = "2.0.0"
__all__ = [
    "ScrapeError",
    "extract_page_data",
    "fetch_html",
    "load_db",
    "normalize_url",
    "save_db",
    "scrape_and_store",
]
