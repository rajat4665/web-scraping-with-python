#!/usr/bin/env python3
# %% [markdown]
# # Lesson 5: JavaScript pages with Playwright
#
# `requests` and `httpx` download the HTML a server sends, and that's all.
# Many modern websites send an almost empty page and build the content in
# your browser with JavaScript. For those, you need a **real browser** that
# your code can control.
#
# **Playwright** is the modern tool for this. It replaces Selenium (which
# Lesson 1 used to use): it installs its own browsers, waits for elements
# automatically, and has a clean async API.
#
# Setup (once):
#
# ```bash
# pip install playwright
# playwright install chromium
# ```
#
# You'll learn to:
# 1. tell whether a page needs a browser
# 2. open a page, wait for content and parse it
# 3. click through pagination
# 4. handle content that loads late
# 5. scroll pages that load more as you scroll
# 6. capture the API responses the page itself uses (link back to Lesson 2)
# 7. speed things up by blocking images and fonts

# %%
import asyncio
import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)
USER_AGENT = (
    "Mozilla/5.0 (compatible; web-scraping-with-python tutorial; "
    "+https://github.com/rajat4665/web-scraping-with-python)"
)

# %% [markdown]
# ## 1. Does this page need a browser?
#
# Compare **View Page Source** (what the server sends) with **Inspect** (the
# page after JavaScript ran). If the data is only in Inspect, the page needs
# JavaScript. In code, fetch the page with `requests` and check for it:

# %%
for url in ["https://quotes.toscrape.com/", "https://quotes.toscrape.com/js/"]:
    html = requests.get(url, timeout=15).text
    found = len(BeautifulSoup(html, "html.parser").select("div.quote"))
    print(f"{url:40} quotes in raw HTML: {found}")

# %% [markdown]
# The `/js/` page has none: JavaScript creates them.
#
# > Before reaching for a browser, re-read Lesson 2. The data is often
# > sitting in a `<script>` tag or a JSON API, which is 10–100x faster
# > than running a browser.

# %% [markdown]
# ## 2. Open a page and read the content
#
# The pattern:
#
# 1. Start Playwright and launch Chromium. `headless=True` means no visible
#    window; set it to `False` to watch what happens, which is great for
#    debugging.
# 2. Open a new page and `goto` the URL.
# 3. Wait for the element you need with `wait_for_selector`.
# 4. Take the HTML after JavaScript ran (`page.content()`) and parse it with
#    BeautifulSoup, just like Lesson 1.
#
# > **Running async code:** in a script, use `asyncio.run(main())`. In
# > Jupyter, write `await main()`; the notebook version does this already.


# %%
def parse_quotes(html):
    soup = BeautifulSoup(html, "html.parser")
    return [
        {
            "text": q.select_one("span.text").get_text(strip=True),
            "author": q.select_one("small.author").get_text(strip=True),
            "tags": [t.get_text() for t in q.select("a.tag")],
        }
        for q in soup.select("div.quote")
    ]


async def first_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=USER_AGENT)
        await page.goto("https://quotes.toscrape.com/js/")
        await page.wait_for_selector("div.quote")
        html = await page.content()
        await page.screenshot(path=str(OUTPUT / "quotes_js.png"))
        await browser.close()
    return parse_quotes(html)


quotes = asyncio.run(first_page())
print(f"{len(quotes)} quotes after JavaScript ran")
print(quotes[0])
print("Screenshot saved to output/quotes_js.png")

# %% [markdown]
# ### Locators: querying the live page
#
# Instead of BeautifulSoup you can also query the page directly with
# **locators**. They wait automatically until the elements exist, and they
# are what you use to click, type and fill in forms.


# %%
async def with_locators():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(user_agent=USER_AGENT)
        await page.goto("https://quotes.toscrape.com/js/")
        texts = await page.locator("div.quote span.text").all_inner_texts()
        authors = await page.locator("div.quote small.author").all_inner_texts()
        await browser.close()
    return list(zip(authors, texts, strict=True))


for author, text in asyncio.run(with_locators())[:3]:
    print(f"{author}: {text[:60]}...")

# %% [markdown]
# ## 3. Click through pagination
#
# Click "Next", wait for the new page to load, and repeat until there's no
# "Next" button.


# %%
async def all_pages(max_pages=10):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(user_agent=USER_AGENT)
        await page.goto("https://quotes.toscrape.com/js/")
        for number in range(1, max_pages + 1):
            await page.wait_for_selector("div.quote")
            results.extend(parse_quotes(await page.content()))
            print(f"page {number}: {page.url}")
            next_button = page.locator("li.next > a")
            if await next_button.count() == 0:
                break
            await next_button.click()
            await page.wait_for_load_state()
        await browser.close()
    return results


all_quotes = asyncio.run(all_pages())
print(f"Total: {len(all_quotes)} quotes")

# %% [markdown]
# ## 4. Content that loads late
#
# On https://quotes.toscrape.com/js-delayed/ the quotes appear after **10
# seconds**. `wait_for_selector` waits up to 30 seconds by default, and you
# can change that with `timeout=` (in milliseconds). If the element never
# appears, it raises `TimeoutError`, so you can handle that.
#
# **Never** use a fixed `sleep()` to "wait for the page". It's too short on
# a slow day and wastes time on a fast one. Wait for the thing you need.


# %%
async def delayed_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(user_agent=USER_AGENT)
        await page.goto("https://quotes.toscrape.com/js-delayed/")
        try:
            await page.wait_for_selector("div.quote", timeout=2_000)
        except Exception as exc:  # playwright's TimeoutError
            print("After 2s:", type(exc).__name__, "- not there yet")
        await page.wait_for_selector("div.quote", timeout=20_000)
        count = await page.locator("div.quote").count()
        await browser.close()
    return count


print("Quotes once loaded:", asyncio.run(delayed_page()))

# %% [markdown]
# ## 5. Infinite scroll, and capturing the page's own API calls
#
# https://quotes.toscrape.com/scroll loads 10 more quotes each time you
# reach the bottom. We'll scroll until no new quotes appear.
#
# At the same time, we listen to **network responses** with
# `page.on("response", ...)`. Each scroll triggers a request to
# `/api/quotes?page=N`, and we can grab that JSON directly. This is how
# you discover an API from code, and often the best of both worlds: let the
# browser handle the JavaScript, and read the clean data it receives.


# %%
async def infinite_scroll():
    captured = []

    async def on_response(response):
        if "/api/quotes" in response.url:
            captured.append(await response.json())

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(user_agent=USER_AGENT)
        page.on("response", on_response)
        await page.goto("https://quotes.toscrape.com/scroll")
        await page.wait_for_selector("div.quote")

        previous = 0
        while True:
            count = await page.locator("div.quote").count()
            if count == previous:
                break
            previous = count
            await page.mouse.wheel(0, 20_000)  # scroll down
            try:  # wait until more quotes appear (or give up after 3s)
                await page.wait_for_function(
                    f"document.querySelectorAll('div.quote').length > {count}", timeout=3_000
                )
            except Exception:
                pass
        await browser.close()
    return previous, captured


count, api_pages = asyncio.run(infinite_scroll())
print(f"Quotes on the page after scrolling: {count}")
print(f"API responses captured: {len(api_pages)}")
print("First captured quote:", api_pages[0]["quotes"][0]["text"][:60], "...")

# %% [markdown]
# ## 6. Go faster: block what you don't need
#
# Browsers download images, fonts and stylesheets you don't need for
# scraping. `page.route` lets you intercept every request and abort the
# unneeded ones.


# %%
async def fast_page():
    blocked = []

    async def block(route):
        if route.request.resource_type in {"image", "font", "stylesheet", "media"}:
            blocked.append(route.request.url)
            await route.abort()
        else:
            await route.continue_()

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(user_agent=USER_AGENT)
        await page.route("**/*", block)
        await page.goto("https://books.toscrape.com/")
        titles = await page.locator("article.product_pod h3 a").evaluate_all(
            "links => links.map(a => a.title)"
        )
        await browser.close()
    return titles, blocked


titles, blocked = asyncio.run(fast_page())
print(f"Got {len(titles)} titles, blocked {len(blocked)} image/font/CSS requests")
print(titles[:3])

(OUTPUT / "quotes_playwright.json").write_text(json.dumps(all_quotes, indent=2, ensure_ascii=False))

# %% [markdown]
# ## Tips
#
# * **Debug visually:** `launch(headless=False, slow_mo=500)` opens a window
#   and slows every action down so you can watch.
# * **Record a script:** `playwright codegen https://quotes.toscrape.com/js/`
#   opens a browser and writes the code as you click around.
# * **Reuse the browser:** launching one is slow (about 1 second), so for
#   many pages open several pages or tabs in the same browser.
# * **Browsers are heavy:** each one uses hundreds of MB of RAM. Use them only
#   for pages that really need JavaScript.
# * Sites that actively block bots will often detect automated browsers too.
#   Respect that: if a site doesn't want to be scraped, don't scrape it.
#
# **Next:** [Lesson 6: Logins and forms](06_logins_and_forms.ipynb)
