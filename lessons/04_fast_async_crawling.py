#!/usr/bin/env python3
# %% [markdown]
# # Lesson 4: Fast scraping with asyncio and httpx
#
# Scraping is mostly **waiting**: your program sends a request, then sits
# idle for 100–500 ms until the answer arrives. Fetching 1,000 pages one at
# a time means waiting 1,000 times in a row.
#
# With **asyncio**, your program can have many requests in flight at once
# and handle each answer as it arrives. In this lesson we'll crawl all
# **1,000 books** on https://books.toscrape.com (a site built for scraping
# practice) in under a minute.
#
# You'll learn:
# 1. why sequential scraping is slow (and how to measure it)
# 2. `async` / `await` with the `httpx` library
# 3. limiting concurrency with a `Semaphore` so you don't overload the server
# 4. a full two-level crawl: listing pages → detail pages
# 5. handling errors without one bad page stopping the whole crawl

# %%
import asyncio
import json
import time
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)
BASE = "https://books.toscrape.com/catalogue/"
HEADERS = {
    "User-Agent": "web-scraping-with-python tutorial "
    "(+https://github.com/rajat4665/web-scraping-with-python)"
}

# %% [markdown]
# ## 1. The slow way: one page at a time
#
# `httpx` works much like `requests`, but it also has an async API.
# Let's time fetching 10 listing pages one after another.

# %%
listing_urls = [f"{BASE}page-{n}.html" for n in range(1, 11)]

start = time.perf_counter()
with httpx.Client(headers=HEADERS, timeout=15) as client:
    for url in listing_urls:
        client.get(url).raise_for_status()
sequential_time = time.perf_counter() - start
print(f"Sequential: {len(listing_urls)} pages in {sequential_time:.2f}s")

# %% [markdown]
# ## 2. The fast way: `async` and `await`
#
# The key ideas:
#
# * `async def` defines a **coroutine**, a function that can pause.
# * `await` means "pause here until this is done, and run other work meanwhile".
# * `asyncio.gather(...)` runs many coroutines at the same time and returns
#   all their results, in order.
# * `httpx.AsyncClient` is the async version of `httpx.Client`.
#
# > **Running async code:** in a `.py` script you start it with
# > `asyncio.run(main())`. Jupyter already runs an event loop, so in a
# > notebook you write `await main()` instead. The notebook version of this
# > lesson does that for you.


# %%
async def fetch_all(urls):
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        responses = await asyncio.gather(*(client.get(url) for url in urls))
    return responses


start = time.perf_counter()
responses = asyncio.run(fetch_all(listing_urls))
concurrent_time = time.perf_counter() - start
print(f"Concurrent: {len(responses)} pages in {concurrent_time:.2f}s")
print(f"That's {sequential_time / concurrent_time:.1f}x faster")

# %% [markdown]
# ## 3. Don't overload the server: use a `Semaphore`
#
# `gather` on 1,000 URLs would fire 1,000 requests at once. That's rude, and
# it will probably get you blocked. An `asyncio.Semaphore(10)` works like a
# room with 10 seats: only 10 requests can be inside at once, and the rest
# wait at the door.
#
# This `fetch` function also retries temporary errors (see Lesson 3) and
# returns `None` instead of crashing if a page keeps failing.

# %%
CONCURRENCY = 10
RETRYABLE = {429, 500, 502, 503, 504}


async def fetch(client, semaphore, url, attempts=3):
    """Return the page's HTML, or None if it can't be downloaded."""
    async with semaphore:  # wait for a free seat
        for attempt in range(1, attempts + 1):
            try:
                response = await client.get(url)
            except httpx.TransportError as exc:  # timeouts, connection errors
                problem = repr(exc)
            else:
                if response.status_code == 200:
                    return response.text
                problem = f"HTTP {response.status_code}"
                if response.status_code not in RETRYABLE:
                    break  # a 404 won't fix itself
            if attempt < attempts:
                await asyncio.sleep(2 ** (attempt - 1))  # await, not time.sleep!
        print(f"  giving up on {url}: {problem}")
        return None


# %% [markdown]
# > **Important:** inside async code, use `await asyncio.sleep()`, never
# > `time.sleep()`. `time.sleep()` freezes *everything*, including all the
# > other requests in flight.

# %% [markdown]
# ## 4. Parsing functions
#
# These are ordinary (non-async) functions. Parsing is fast; it's the
# downloading that we needed to speed up. We keep raw values such as
# `"£51.77"` and `"Three"` on purpose: cleaning them up is Lesson 8.


# %%
def parse_listing(html, page_url):
    """Return the book detail URLs on a listing page."""
    soup = BeautifulSoup(html, "html.parser")
    return [urljoin(page_url, a["href"]) for a in soup.select("article.product_pod h3 a")]


def parse_book(html, url):
    """Pull the details out of a single book page."""
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table tr")
    table = {row.th.get_text(strip=True): row.td.get_text(strip=True) for row in rows}
    description = soup.select_one("#product_description + p")
    # <p class="star-rating Three"> -> "Three"
    rating = soup.select_one("p.star-rating")["class"][-1]
    return {
        "title": soup.h1.get_text(strip=True),
        "category": soup.select("ul.breadcrumb li")[2].get_text(strip=True),
        "price": table.get("Price (incl. tax)"),
        "availability": table.get("Availability"),
        "rating": rating,
        "upc": table.get("UPC"),
        "reviews": table.get("Number of reviews"),
        "description": description.get_text(strip=True) if description else None,
        "image": urljoin(url, soup.select_one("#product_gallery img")["src"]),
        "url": url,
    }


# %% [markdown]
# ## 5. The full crawl
#
# Two levels:
#
# 1. Fetch the first listing page to find how many pages there are
#    (it says "Page 1 of 50"), then fetch all listing pages at once.
# 2. Collect every book URL, then fetch all book pages, at most 10 at a time.


# %%
async def crawl_books():
    semaphore = asyncio.Semaphore(CONCURRENCY)
    limits = httpx.Limits(max_connections=CONCURRENCY)
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, limits=limits) as client:
        first_url = f"{BASE}page-1.html"
        first = await fetch(client, semaphore, first_url)
        pages = int(BeautifulSoup(first, "html.parser").select_one("li.current").text.split()[-1])
        print(f"{pages} listing pages")

        page_urls = [f"{BASE}page-{n}.html" for n in range(2, pages + 1)]
        listing_html = await asyncio.gather(*(fetch(client, semaphore, u) for u in page_urls))

        book_urls = parse_listing(first, first_url)
        for url, html in zip(page_urls, listing_html, strict=True):
            if html:
                book_urls.extend(parse_listing(html, url))
        print(f"{len(book_urls)} book URLs found, downloading details...")

        books, done = [], 0

        async def fetch_book(url):
            nonlocal done
            html = await fetch(client, semaphore, url)
            done += 1
            if done % 250 == 0:
                print(f"  {done}/{len(book_urls)}")
            return parse_book(html, url) if html else None

        results = await asyncio.gather(*(fetch_book(u) for u in book_urls))
        books = [b for b in results if b]
        print(f"Parsed {len(books)} books ({len(book_urls) - len(books)} failed)")
        return books


start = time.perf_counter()
books = asyncio.run(crawl_books())
print(f"Crawled {len(books)} books in {time.perf_counter() - start:.1f}s")

# %%
print(json.dumps(books[0], indent=2, ensure_ascii=False))

(OUTPUT / "books.json").write_text(json.dumps(books, indent=2, ensure_ascii=False))
print("Saved output/books.json (used in Lesson 8)")

# %% [markdown]
# ## How fast is too fast?
#
# More concurrency isn't always better:
#
# * Practice sites are fine with 10 parallel requests. For real websites,
#   start with **2–5** and add delays.
# * If you get `429`s or more errors, **lower** the concurrency.
# * Check the site's `robots.txt` for a `Crawl-delay`.
# * A scraper that takes 10 minutes and keeps working beats one that takes
#   1 minute and gets your IP blocked.
#
# **Next:** [Lesson 5: JavaScript pages with Playwright](05_javascript_pages_with_playwright.ipynb)
