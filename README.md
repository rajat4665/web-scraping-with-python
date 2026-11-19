![web scraping with python](assets/banner.jpg)

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
| 1 | [**Web scraping basics**](lessons/01_web_scraping_basics.ipynb) | `requests`, BeautifulSoup, `find` / `find_all`, CSS selectors, pagination, saving to CSV/JSON, scraping Wikipedia |
| 2 | [**Hidden APIs and embedded JSON**](lessons/02_hidden_apis_and_embedded_json.ipynb) | Finding a site's JSON API in DevTools, data in `<script>` tags, JSON-LD and `__NEXT_DATA__` |
| 3 | [**Reliable requests**](lessons/03_reliable_requests.ipynb) | Timeouts, retries with exponential backoff, `429` and `Retry-After`, encoding bugs (`Â£`), caching, rate limiting |
| 4 | [**Fast scraping with asyncio**](lessons/04_fast_async_crawling.ipynb) | `httpx` + `asyncio`, limiting concurrency with a `Semaphore`, crawling 1,000 pages in about 30 seconds |
| 5 | [**JavaScript pages with Playwright**](lessons/05_javascript_pages_with_playwright.ipynb) | Headless browsers, waiting for content, clicking, infinite scroll, capturing network responses, blocking images |
| 6 | [**Logins and forms**](lessons/06_logins_and_forms.ipynb) | Sessions and cookies, CSRF tokens, keeping passwords out of code, multi-step ASP.NET forms (`__VIEWSTATE`) |
| 7 | [**Scrapy**](lessons/07_scrapy_framework.ipynb) | Spiders, callbacks, item pipelines, AutoThrottle, HTTP cache, feed exports, `scrapy shell` |
| 8 | [**Clean and store your data**](lessons/08_clean_and_store_data.ipynb) | Cleaning with pandas, validation, analysis, SQLite, upserts for repeated scrapes |

New to scraping? Start with Lesson 1. Already comfortable with BeautifulSoup?
Jump to Lesson 2; it will change how you approach every site.

## Project structure

```
web-scraping-with-python/
├── lessons/                      the course: start here
│   ├── 01_web_scraping_basics.ipynb   each lesson is a notebook (with outputs)...
│   ├── 01_web_scraping_basics.py      ...and the same lesson as a plain script
│   ├── 02_ ... 08_                    lessons 2-8, same pattern
│   ├── books_spider.py                the Scrapy spider used in lesson 7
│   └── output/                        files the lessons create (not committed)
├── webscraper/                   the command line tool, as a small package
│   ├── fetch.py                       download pages (User-Agent, timeouts, robots.txt)
│   ├── extract.py                     turn HTML into data
│   ├── storage.py                     the JSON file the results are saved in
│   ├── scrape.py                      fetch + extract + store in one call
│   └── cli.py                         commands and the interactive menu
├── tests/                        tests for webscraper (offline, no network)
├── tools/py_to_notebook.py       builds the notebooks from the lesson scripts
├── assets/                       images used by the README and lessons
├── requirements.txt              lesson 1 + the CLI tool
├── requirements-advanced.txt     lessons 2-8
├── requirements-dev.txt          everything, plus test and lint tools
└── pyproject.toml                package metadata and tool settings
```

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

Run the lessons from inside the `lessons/` folder. They save their files to
`lessons/output/`.

In Jupyter, which is nicer for learning because you can run one cell at a time:

```bash
cd lessons
jupyter notebook          # then open 01_web_scraping_basics.ipynb
```

Or as plain scripts:

```bash
cd lessons
python 01_web_scraping_basics.py
python 04_fast_async_crawling.py
```

Lesson 8 uses the books that Lesson 4 downloads, so run Lesson 4 first.

## Use the command line tool

Run it from the repo's top folder. With no arguments you get the
interactive menu:

```bash
python -m webscraper
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
python -m webscraper scrape https://quotes.toscrape.com --alias quotes

# list everything you've scraped
python -m webscraper list

# summary of one page, or just one field
python -m webscraper show quotes
python -m webscraper show quotes --field all_anchor_href

# export one page's data to its own file, or delete it
python -m webscraper export quotes -o quotes.json
python -m webscraper delete quotes
```

Want a `webscraper` command you can run from any folder? Install the
package with `pip install -e .`, then use `webscraper list`,
`webscraper scrape ...` and so on.

You can also use it from your own Python code:

```python
from webscraper import fetch_html, extract_page_data

html, url = fetch_html("https://quotes.toscrape.com")
data = extract_page_data(html, url)
print(data["title"], len(data["all_anchor_href"]), "links")
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

> **Looking for the old files?** The tutorial used to be
> `Web Scraping with BeautifulSoup.ipynb` in the top folder; it's now
> [`lessons/01_web_scraping_basics.ipynb`](lessons/01_web_scraping_basics.ipynb).
> `web_scraping_command_line_tool.py` became the [`webscraper/`](webscraper)
> package (`python -m webscraper`).

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
