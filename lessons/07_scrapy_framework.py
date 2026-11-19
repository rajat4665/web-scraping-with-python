#!/usr/bin/env python3
# %% [markdown]
# # Lesson 7: Scrapy, a framework for crawling
#
# In Lessons 3 and 4 we wrote retries, rate limiting, concurrency, caching
# and error handling ourselves. **Scrapy** is a framework that does all of
# that for you, so you only write the part that's specific to your site:
# *which links to follow* and *what data to extract*.
#
# | You wrote it yourself (Lessons 1–4) | Scrapy has it built in |
# |---|---|
# | `asyncio` + `Semaphore` | concurrent requests with per-domain limits |
# | retry with backoff | `RetryMiddleware` |
# | `RateLimiter` | `DOWNLOAD_DELAY` and **AutoThrottle** |
# | `requests-cache` | `HTTPCACHE_ENABLED` |
# | robots.txt check | `ROBOTSTXT_OBEY` |
# | "don't fetch the same URL twice" | duplicate request filter |
# | `json.dump` / `csv` | feed exports: `-O books.json` or `.csv` |
#
# **When to use Scrapy:** crawls of many pages, scrapers you'll run
# regularly, or projects with several spiders. For a quick one-page script,
# `requests` + BeautifulSoup is simpler.
#
# Setup: `pip install scrapy`

# %%
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

# %% [markdown]
# ## 1. The spider
#
# Our spider lives in [`books_spider.py`](books_spider.py). Here it is:

# %%
print(Path("books_spider.py").read_text())

# %% [markdown]
# ### How it works
#
# * **`start_urls`**: Scrapy requests these first and calls `parse()` with
#   each response.
# * **`parse()`** is a *generator*: it `yield`s either **new requests**
#   (`response.follow(...)`) or **items** (dicts of data). Scrapy schedules
#   the requests and sends the items to the pipelines.
# * **`callback=`** tells Scrapy which method should handle that response:
#   listing pages go to `parse`, book pages go to `parse_book`.
# * **Selectors:** `response.css("h1::text").get()` gets the first match's
#   text, `.getall()` gets all of them, and `::attr(href)` reads an
#   attribute. (`response.xpath(...)` works too.)
# * **Item pipelines** clean and validate every item after it's scraped.
#   `CleanBookPipeline` turns `"£51.77"` into `51.77`, and
#   `DuplicatesPipeline` drops repeats.
# * **`custom_settings`** turn on politeness (AutoThrottle, robots.txt) and
#   caching.

# %% [markdown]
# ## 2. Run it
#
# From a terminal in the `lessons/` folder:
#
# ```bash
# scrapy runspider books_spider.py -a max_pages=5 -O output/books_scrapy.json
# ```
#
# * `-a max_pages=5` passes an argument to the spider (5 listing pages = 100
#   books; leave it out to crawl all 1,000).
# * `-O` writes the items to a file, overwriting it. Use `.csv`, `.jsonl` or
#   `.xml` for other formats.
#
# Here we run the same command from Python:

# %%
result = subprocess.run(
    [
        sys.executable,
        "-m",
        "scrapy",
        "runspider",
        "books_spider.py",
        "-a",
        "max_pages=5",
        "-O",
        str(OUTPUT / "books_scrapy.json"),
    ],
    capture_output=True,
    text=True,
)
# Scrapy logs to stderr. Show the summary statistics at the end.
log = result.stderr
stats_start = log.find("Dumping Scrapy stats")
print(log[stats_start:][:1500] if stats_start != -1 else log[-3000:])
print("exit code:", result.returncode)

# %% [markdown]
# The stats are worth reading: number of requests, responses by status
# code, items scraped and dropped, retries, cache hits and how long it took.
# Run the cell again and you'll see `httpcache/hit` go up and the run get
# much faster: the pages came from the cache in `.scrapy/`.

# %%
books = json.loads((OUTPUT / "books_scrapy.json").read_text())
print(f"{len(books)} books scraped")
print(json.dumps(books[0], indent=2, ensure_ascii=False))

# %%
print("Books per rating:", dict(sorted(Counter(b["rating"] for b in books).items())))
cheapest = min(books, key=lambda b: b["price"])
print(f"Cheapest: {cheapest['title']} at £{cheapest['price']}")

# %% [markdown]
# ## 3. Exploring a page with `scrapy shell`
#
# Writing selectors is easiest interactively. In a terminal, run:
#
# ```bash
# scrapy shell "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
# ```
#
# and try selectors on the live page:
#
# ```python
# >>> response.css("div.product_main h1::text").get()
# 'A Light in the Attic'
# >>> response.css("p.price_color::text").get()
# '£51.77'
# >>> view(response)   # opens the page Scrapy downloaded in your browser
# ```

# %% [markdown]
# ## 4. Going further
#
# * **A full project:** `scrapy startproject bookstore` creates a folder with
#   `settings.py`, `pipelines.py`, `items.py` and a `spiders/` folder. Use
#   this once you have more than one spider.
# * **Crawl rules:** `CrawlSpider` with `Rule(LinkExtractor(...))` follows
#   links matching a pattern automatically.
# * **Storing items:** write a pipeline that saves items to a database
#   (Lesson 8 shows SQLite).
# * **JavaScript pages:** the `scrapy-playwright` plugin lets Scrapy render
#   pages with Playwright (Lesson 5).
# * **Scheduling:** run spiders on a schedule with cron, GitHub Actions or
#   Scrapyd.
#
# **Next:** [Lesson 8: Clean and store your data](08_clean_and_store_data.ipynb)
