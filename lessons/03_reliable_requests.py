#!/usr/bin/env python3
# %% [markdown]
# # Lesson 3: Reliable requests
#
# A scraper that works once on your laptop is easy. One that runs every
# night for a year has to handle real-world problems:
#
# * servers that are slow or don't answer → **timeouts**
# * random failures (`500`, `502`, `503`, dropped connections) → **retries with backoff**
# * "slow down!" responses (`429 Too Many Requests`) → **respecting `Retry-After`**
# * text that comes out as `Â£` instead of `£` → **getting the encoding right**
# * downloading the same page again and again while you develop → **caching**
# * sending requests too fast → **rate limiting**
#
# To show failures on demand, this lesson starts a tiny **local practice
# server** that misbehaves on purpose, so the examples work the same way
# every time.

# %%
import random
import threading
import time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests
import requests_cache
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)
HEADERS = {
    "User-Agent": "web-scraping-with-python tutorial "
    "(+https://github.com/rajat4665/web-scraping-with-python)"
}

# %% [markdown]
# ## The practice server
#
# You don't need to understand this cell. It runs a web server on your own
# machine with three test pages:
#
# | Path | Behaviour |
# |------|-----------|
# | `/flaky?...` | fails with `503` the first 2 times, then works |
# | `/rate-limited?...` | answers `429` with `Retry-After: 1` the first time, then works |
# | `/slow` | takes 3 seconds to answer |
#
# Each different query string (`?demo=1`, `?demo=2`) gets its own failure
# counter, so every example starts fresh.

# %%
hits = Counter()


class PracticeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        hits[self.path] += 1
        n = hits[self.path]
        if self.path.startswith("/flaky") and n <= 2:
            return self._send(503, f"Service Unavailable (attempt {n})")
        if self.path.startswith("/rate-limited") and n == 1:
            return self._send(429, "Too Many Requests", {"Retry-After": "1"})
        if self.path.startswith("/slow"):
            time.sleep(3)
        return self._send(200, f"<html><body><p>OK after {n} attempt(s)</p></body></html>")

    def _send(self, status, body, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):  # keep the output quiet
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), PracticeHandler)  # port 0 = any free port
threading.Thread(target=server.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{server.server_port}"
print("Practice server running at", BASE)

# %% [markdown]
# ## 1. Always set a timeout
#
# Without a timeout, `requests` can wait **forever** for a server that never
# answers. You can give one number, or a pair `(connect, read)`:
#
# * **connect**: how long to wait to connect to the server
# * **read**: how long to wait for data once connected

# %%
start = time.perf_counter()
try:
    requests.get(f"{BASE}/slow", timeout=(3, 1))
except requests.Timeout:
    print(f"Gave up after {time.perf_counter() - start:.1f}s instead of waiting forever")

# %% [markdown]
# ## 2. Retry with exponential backoff, written by hand
#
# Some failures are temporary, so it makes sense to try again. But retrying
# straight away just hits a struggling server harder. **Exponential
# backoff** waits longer after each failure (1s, 2s, 4s, …), and **jitter**
# adds a little randomness so many scrapers don't all retry at once.
#
# Which errors are worth retrying?
#
# * **Yes:** timeouts, connection errors, `429`, `500`, `502`, `503`, `504`
# * **No:** `404 Not Found`, `403 Forbidden`, `401 Unauthorized`. Trying
#   again won't change the answer.

# %%
RETRY_STATUSES = {429, 500, 502, 503, 504}


def get_with_retries(url, max_attempts=4, base_delay=0.5, session=None):
    session = session or requests.Session()
    for attempt in range(1, max_attempts + 1):
        try:
            response = session.get(url, timeout=10)
        except (requests.ConnectionError, requests.Timeout) as exc:
            problem, retry_after = type(exc).__name__, None
        else:
            if response.status_code not in RETRY_STATUSES:
                response.raise_for_status()  # 404 etc.: give up right away
                return response
            problem = f"HTTP {response.status_code}"
            retry_after = response.headers.get("Retry-After")

        if attempt == max_attempts:
            raise RuntimeError(f"{url} still failing after {max_attempts} attempts ({problem})")

        if retry_after and retry_after.isdigit():
            delay = int(retry_after)  # the server told us how long to wait
        else:
            delay = base_delay * 2 ** (attempt - 1) + random.uniform(0, 0.3)
        print(f"  attempt {attempt}: {problem}, waiting {delay:.2f}s")
        time.sleep(delay)


print("Flaky page:")
print(" ", get_with_retries(f"{BASE}/flaky?demo=1").text)
print("Rate-limited page:")
print(" ", get_with_retries(f"{BASE}/rate-limited?demo=1").text)

# %% [markdown]
# ## 3. The same thing, built in: `urllib3.Retry`
#
# `requests` is built on `urllib3`, which already knows how to retry. Mount
# a `Retry` policy on a `Session` and **every request through that session**
# gets retries, backoff and `Retry-After` support. Use this in real projects.


# %%
def make_robust_session():
    retry = Retry(
        total=4,
        backoff_factor=0.5,  # the wait doubles after each failed attempt
        status_forcelist=sorted(RETRY_STATUSES),
        allowed_methods={"GET", "HEAD"},  # don't blindly retry POSTs
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    session = requests.Session()
    session.headers.update(HEADERS)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


robust = make_robust_session()
for path in ["/flaky?demo=2", "/rate-limited?demo=2"]:
    start = time.perf_counter()
    r = robust.get(BASE + path, timeout=10)
    print(f"{path:22} -> {r.status_code} {r.text!r} in {time.perf_counter() - start:.1f}s")

# %% [markdown]
# ## 4. Text encoding: why you sometimes see `Â£`
#
# A web page is sent as **bytes**, and `response.text` has to guess how to
# turn them into text. If the server doesn't say which encoding it used,
# `requests` falls back to ISO-8859-1, which is wrong for most modern pages
# (they're UTF-8). The pound sign `£` then shows up as `Â£`.

# %%
r = robust.get("https://books.toscrape.com/", timeout=15)
print("Content-Type header:", r.headers["Content-Type"])
print("requests guessed:   ", r.encoding)

wrong = BeautifulSoup(r.text, "html.parser").select_one("p.price_color").text
print("Using r.text:       ", wrong)

# Fix 1: give BeautifulSoup the raw bytes. It reads <meta charset="..."> itself.
right = BeautifulSoup(r.content, "html.parser").select_one("p.price_color").text
print("Using r.content:    ", right)

# Fix 2: tell requests the right encoding before using r.text
r.encoding = r.apparent_encoding  # detected from the bytes themselves
fixed = BeautifulSoup(r.text, "html.parser").select_one("p.price_color").text
print("apparent_encoding:  ", r.encoding, "->", fixed)

# %% [markdown]
# **Rule of thumb:** pass `response.content` (bytes) to BeautifulSoup.
# (`httpx`, which we use in Lesson 4, defaults to UTF-8, so it gets this
# page right.)

# %% [markdown]
# ## 5. Cache responses while you develop
#
# While writing a scraper you'll run it dozens of times. Downloading the same
# pages every time is slow and unkind to the website. `requests-cache` is a
# drop-in replacement for `requests.Session` that saves responses to a local
# SQLite file.

# %%
cached = requests_cache.CachedSession(
    str(OUTPUT / "http_cache"),
    expire_after=3600,  # seconds; use 0 or clear() to force fresh data
)
cached.headers.update(HEADERS)
cached.cache.clear()  # start empty so the demo is honest

for i in range(1, 4):
    start = time.perf_counter()
    r = cached.get("https://books.toscrape.com/catalogue/page-2.html", timeout=15)
    elapsed_ms = 1000 * (time.perf_counter() - start)
    print(f"request {i}: from_cache={r.from_cache!s:5}  {elapsed_ms:6.1f} ms")

# %% [markdown]
# ## 6. Rate limiting: be a good citizen
#
# Retries handle a server that is struggling; rate limiting stops you from
# being the cause. This small class makes sure at least `min_interval`
# seconds pass between requests, however fast the rest of your code runs.


# %%
class RateLimiter:
    def __init__(self, requests_per_second):
        self.min_interval = 1 / requests_per_second
        self.last = 0.0

    def wait(self):
        sleep_for = self.last + self.min_interval - time.monotonic()
        if sleep_for > 0:
            time.sleep(sleep_for)
        self.last = time.monotonic()


limiter = RateLimiter(requests_per_second=2)
start = time.perf_counter()
for page in range(1, 6):
    limiter.wait()
    robust.get(f"https://books.toscrape.com/catalogue/page-{page}.html", timeout=15)
    print(f"page {page} at {time.perf_counter() - start:.2f}s")

# %% [markdown]
# ## Putting it together
#
# A production-ready "get a page" usually combines all of this:
#
# * a `Session` with a User-Agent and a `Retry` policy (sections 3 and 1)
# * a timeout on every call
# * `response.content` for parsing (section 4)
# * caching while developing (section 5)
# * a rate limiter (section 6)
#
# Frameworks such as **Scrapy** (Lesson 7) handle all of this for you, but
# now you know what's happening underneath.
#
# **Next:** [Lesson 4: Fast scraping with asyncio](04_fast_async_crawling.ipynb)

# %%
server.shutdown()
