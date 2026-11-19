![web scraping with python](WEB%20SCRAPING.jpg)

# Web Scraping with Python

[![CI](https://github.com/rajat4665/web-scraping-with-python/actions/workflows/ci.yml/badge.svg)](https://github.com/rajat4665/web-scraping-with-python/actions/workflows/ci.yml)
[![Lessons](https://github.com/rajat4665/web-scraping-with-python/actions/workflows/lessons.yml/badge.svg)](https://github.com/rajat4665/web-scraping-with-python/actions/workflows/lessons.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Web scraping** (also called web harvesting or web data extraction) means
pulling data out of websites. This repo is a hands-on course that takes you
from your first `requests.get()` to fast, reliable crawlers: eight lessons,
each available as a Jupyter notebook (with outputs) and as a plain Python
script, plus a small command line tool you can use and extend.

Every lesson runs against websites made for scraping practice
([quotes.toscrape.com](https://quotes.toscrape.com) and
[books.toscrape.com](https://books.toscrape.com)), so it's legal to run them,
and they're checked automatically every week.

## Learning path

| # | Lesson | You'll learn |
|---|--------|--------------|
| 1 | [**Web scraping basics**](Web%20Scraping%20with%20BeautifulSoup.ipynb) | `requests`, BeautifulSoup, `find` / `find_all`, CSS selectors, pagination, saving to CSV/JSON, scraping Wikipedia |
| 2 | [**Hidden APIs and embedded JSON**](lessons/02_hidden_apis_and_embedded_json.ipynb) | Finding a site's JSON API in DevTools, data in `<script>` tags, JSON-LD and `__NEXT_DATA__` |
| 3 | [**Reliable requests**](lessons/03_reliable_requests.ipynb) | Timeouts, retries with exponential backoff, `429` and `Retry-After`, encoding bugs (`Â£`), caching, rate limiting |
| 4 | [**Fast scraping with asyncio**](lessons/04_fast_async_crawling.ipynb) | `httpx` + `asyncio`, limiting concurrency with a `Semaphore`, crawling 1,000 pages in about 30 seconds |
| 5 | [**JavaScript pages with Playwright**](lessons/05_javascript_pages_with_playwright.ipynb) | Headless browsers, waiting for content, clicking, infinite scroll, capturing network responses, blocking images |
| 6 | [**Logins and forms**](lessons/06_logins_and_forms.ipynb) | Sessions and cookies, CSRF tokens, keeping passwords out of code, multi-step ASP.NET forms (`__VIEWSTATE`) |
| 7 | [**Scrapy**](lessons/07_scrapy_framework.ipynb) | Spiders, callbacks, item pipelines, AutoThrottle, HTTP cache, feed exports, `scrapy shell` |
| 8 | [**Clean and store your data**](lessons/08_clean_and_store_data.ipynb) | Cleaning with pandas, validation, analysis, SQLite, upserts for repeated scrapes |

New to scraping? Start with Lesson 1. Already comfortable with BeautifulSoup?
Jump to Lesson 2; it will change how you approach every site.

## What's inside

| Path | What it is |
|------|------------|
| [`Web Scraping with BeautifulSoup.ipynb`](Web%20Scraping%20with%20BeautifulSoup.ipynb) / [`.py`](Web%20Scraping%20with%20BeautifulSoup.py) | Lesson 1, as a notebook and as a script |
| [`lessons/`](lessons) | Lessons 2–8, each as `.ipynb` and `.py`, plus the Scrapy spider [`books_spider.py`](lessons/books_spider.py) |
| [`web_scraping_command_line_tool.py`](web_scraping_command_line_tool.py) | A CLI that scrapes pages and saves them to a JSON file |
| [`tests/`](tests) | Tests for the CLI tool (they run offline) |
| [`tools/py_to_notebook.py`](tools/py_to_notebook.py) | Builds the notebooks from the lesson scripts |

## Setup

You need Python 3.10 or newer.

```bash
git clone https://github.com/rajat4665/web-scraping-with-python.git
cd web-scraping-with-python

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt            # Lesson 1 and the CLI tool
pip install -r requirements-advanced.txt   # Lessons 2-8 (includes Jupyter)
playwright install chromium                # Lesson 5 needs a browser
```

## Run the lessons

As a script:

```bash
python "Web Scraping with BeautifulSoup.py"
```

Or in Jupyter, which is nicer for learning because you can run one cell at a time:

```bash
pip install jupyter
jupyter notebook "Web Scraping with BeautifulSoup.ipynb"
```

Lesson 1 scrapes [quotes.toscrape.com](https://quotes.toscrape.com), a site
built for practising scraping, then a Wikipedia article. It writes
`quotes.csv` and `quotes.json` to the current folder.

Run Lessons 2–8 from inside the `lessons/` folder. They save their
results to `lessons/output/`.

```bash
cd lessons
jupyter notebook                      # then open any lesson
python 04_fast_async_crawling.py      # or run one as a script
```

Lesson 8 uses the books that Lesson 4 downloads, so run Lesson 4 first.

## Use the command line tool

Run it with no arguments to get the interactive menu:

```bash
python web_scraping_command_line_tool.py
```

```
  ================ Welcome to this scraping program ================
    1  ->  list websites you've already scraped
    2  ->  scrape a website
    3  ->  show data for a scraped website
    4  ->  exit
```

Or use the commands directly:

```bash
# scrape a page and save it as "quotes"
python web_scraping_command_line_tool.py scrape https://quotes.toscrape.com --alias quotes

# list everything you've scraped
python web_scraping_command_line_tool.py list

# summary of one page, or just one field
python web_scraping_command_line_tool.py show quotes
python web_scraping_command_line_tool.py show quotes --field all_anchor_href

# export one page's data to its own file, or delete it
python web_scraping_command_line_tool.py export quotes -o quotes.json
python web_scraping_command_line_tool.py delete quotes
```

For every page the tool saves the title, meta description, h1/h2/h3
headings, paragraphs, links and image URLs. Links and image URLs are saved
as absolute URLs. Data goes into `scraped_data.json`; use `--db other.json`
to choose a different file.

By default the tool checks the site's `robots.txt` and won't scrape pages it
disallows. `--ignore-robots` turns this off; only use it on sites you have
permission to scrape.

## Development

```bash
pip install -r requirements-dev.txt
pytest          # run the tests
ruff check .    # lint
```

GitHub Actions runs both on every push and pull request. A second workflow,
**Lessons**, runs every lesson against the live practice sites each week (and
on pull requests that touch them), so you'll hear about it if a site
changes and an example breaks.

The lesson `.py` files are the source of truth. They're split into cells
with `# %%` markers, which VS Code, PyCharm and Jupytext all understand.
After editing one, rebuild and re-run its notebook:

```bash
cd lessons
python ../tools/py_to_notebook.py 03_reliable_requests.py --execute
```

## Scraping responsibly

- Read the site's `robots.txt` and terms of service before scraping it.
- If there's an official API, use it instead.
- Add delays between requests and don't overload servers.
- Don't collect personal data, or content behind a login, without permission.

## Contributing

Issues and pull requests are welcome. If a tutorial example breaks because a
website changed its HTML, please open an issue, or better yet, send a fix!

## License

[MIT](LICENSE)

---

Originally written as a blog post on [getpython.wordpress.com](https://getpython.wordpress.com/).
**Happy coding!**
