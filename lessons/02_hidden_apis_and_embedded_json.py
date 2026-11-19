#!/usr/bin/env python3
# %% [markdown]
# # Lesson 2: Hidden APIs and embedded JSON
#
# In Lesson 1 we parsed HTML. But the HTML you see is often just the
# *presentation*: the page's real data comes from a JSON API, or sits as
# JSON inside a `<script>` tag. If you can find that data, you can skip
# HTML parsing entirely. That's usually:
#
# * **simpler**: you get clean fields, not text to pick apart
# * **more reliable**: APIs change less often than page layouts
# * **faster**: JSON is smaller than HTML
#
# **Always look for the data first, and parse HTML only if you can't find it.**
#
# You'll learn to:
# 1. find a page's API with your browser's DevTools
# 2. call the API directly and page through it
# 3. extract JSON embedded in `<script>` tags
# 4. read JSON-LD and `__NEXT_DATA__`, two common formats on real sites

# %%
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

session = requests.Session()
session.headers["User-Agent"] = (
    "web-scraping-with-python tutorial (+https://github.com/rajat4665/web-scraping-with-python)"
)

# %% [markdown]
# ## 1. Finding the API with DevTools
#
# Open https://quotes.toscrape.com/scroll in Chrome or Firefox. More quotes
# load as you scroll. Where do they come from?
#
# 1. Open DevTools (`F12`, or `Cmd+Option+I` on a Mac) and go to the
#    **Network** tab.
# 2. Click the **Fetch/XHR** filter so you only see data requests.
# 3. Reload the page and scroll down.
# 4. Requests like `api/quotes?page=2` appear. Click one and open
#    **Response**: it's JSON with exactly the data we want.
#
# Tip: right-click a request and choose **Copy → Copy as cURL** to get every
# header the browser sent. Sites like https://curlconverter.com turn that
# into Python `requests` code.
#
# First, let's see why plain HTML scraping doesn't work on this page:

# %%
html = session.get("https://quotes.toscrape.com/scroll", timeout=15).text
soup = BeautifulSoup(html, "html.parser")
print("Quotes in the HTML:", len(soup.select("div.quote")))  # 0: JavaScript adds them later

# %% [markdown]
# ## 2. Call the API directly
#
# `response.json()` turns the JSON body into Python dicts and lists.

# %%
response = session.get("https://quotes.toscrape.com/api/quotes", params={"page": 1}, timeout=15)
response.raise_for_status()
data = response.json()

print("Top-level keys:", list(data))
print("has_next:", data["has_next"], " page:", data["page"])
print(json.dumps(data["quotes"][0], indent=2))

# %% [markdown]
# ### Page through the API
#
# The response tells us whether there's a next page (`has_next`), so we keep
# going until there isn't one. Compare this with Lesson 1: no selectors and
# no `get_text()`. The data is already structured, and it even includes the
# author's slug and Goodreads link that the HTML didn't show.


# %%
def fetch_all_quotes_from_api(delay=0.3):
    quotes, page = [], 1
    while True:
        resp = session.get(
            "https://quotes.toscrape.com/api/quotes", params={"page": page}, timeout=15
        )
        resp.raise_for_status()
        payload = resp.json()
        quotes.extend(payload["quotes"])
        if not payload["has_next"]:
            return quotes
        page += 1
        time.sleep(delay)


api_quotes = fetch_all_quotes_from_api()
print(f"Got {len(api_quotes)} quotes with {len(api_quotes) // 10} requests")
print("Fields available:", sorted(api_quotes[0]))
print("Author info:", api_quotes[0]["author"])

(OUTPUT / "quotes_api.json").write_text(json.dumps(api_quotes, indent=2, ensure_ascii=False))

# %% [markdown]
# ## 3. JSON embedded in a `<script>` tag
#
# Some pages make no API calls; the data is written straight into the page
# inside JavaScript. Open https://quotes.toscrape.com/js/ and choose **View
# Page Source** (not Inspect!). You'll see:
#
# ```html
# <script>
#     var data = [ { "tags": [...], "author": {...}, "text": "..." }, ... ];
#     ...
# </script>
# ```
#
# `requests` doesn't run JavaScript, so `div.quote` won't be in the HTML,
# but the data is still in that script. We can cut it out with a regular
# expression and parse it with `json.loads`.

# %%
js_html = session.get("https://quotes.toscrape.com/js/", timeout=15).text
js_soup = BeautifulSoup(js_html, "html.parser")
print("Quotes in the HTML:", len(js_soup.select("div.quote")))

script = next(s.string for s in js_soup.find_all("script") if s.string and "var data" in s.string)
match = re.search(r"var data\s*=\s*(\[.*?\]);", script, re.DOTALL)
embedded = json.loads(match.group(1))

print("Quotes in the <script>:", len(embedded))
print(embedded[0]["text"], "-", embedded[0]["author"]["name"])

# %% [markdown]
# > **Watch out:** JavaScript isn't always valid JSON. Single quotes,
# > trailing commas and unquoted keys make `json.loads` fail. For simple
# > cases a bit of string cleanup works. For messy ones, the `chompjs`
# > library parses JavaScript objects into Python. Or use a real browser
# > (Lesson 5).

# %% [markdown]
# ## 4. Two formats you'll see on real websites
#
# ### JSON-LD (structured data)
#
# Many shops, recipe sites, news sites and job boards add
# `<script type="application/ld+json">` blocks so that Google can
# understand the page. They contain clean data (product name, price, rating,
# author, date) in a standard format described at https://schema.org.
#
# Here's what one looks like on a typical product page:

# %%
product_page = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Mechanical Keyboard",
  "sku": "KB-1001",
  "offers": {"@type": "Offer", "price": "89.99", "priceCurrency": "USD",
             "availability": "https://schema.org/InStock"},
  "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.6", "reviewCount": "312"}
}
</script>
</head><body><h1>Mechanical Keyboard</h1></body></html>
"""


def extract_json_ld(html):
    """Return every JSON-LD object on a page as a list of dicts."""
    page = BeautifulSoup(html, "html.parser")
    items = []
    for tag in page.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except json.JSONDecodeError:
            continue  # broken JSON-LD exists in the wild; skip it
        # A block can hold a single object, a list, or {"@graph": [...]}
        if isinstance(data, dict) and "@graph" in data:
            data = data["@graph"]
        items.extend(data if isinstance(data, list) else [data])
    return items


for item in extract_json_ld(product_page):
    print(
        item["@type"],
        "|",
        item["name"],
        "|",
        item["offers"]["price"],
        item["offers"]["priceCurrency"],
    )
    print("rating:", item["aggregateRating"]["ratingValue"])

# %% [markdown]
# ### `__NEXT_DATA__` (Next.js sites)
#
# Websites built with Next.js, a very popular React framework, embed the
# whole page's data in `<script id="__NEXT_DATA__">`. If you see that in the
# page source, you've found the data:

# %%
next_js_page = """
<html><body><div id="__next">...</div>
<script id="__NEXT_DATA__" type="application/json">
{"props": {"pageProps": {"jobs": [
  {"title": "Python Developer", "location": "Remote", "salary": 95000},
  {"title": "Data Engineer", "location": "Berlin", "salary": 80000}
]}}, "page": "/jobs"}
</script></body></html>
"""

tag = BeautifulSoup(next_js_page, "html.parser").find("script", id="__NEXT_DATA__")
next_data = json.loads(tag.string)
for job in next_data["props"]["pageProps"]["jobs"]:
    print(job)

# %% [markdown]
# ## Checklist: before you write a single CSS selector
#
# 1. **Network tab → Fetch/XHR.** Is there a JSON API?
# 2. **View Page Source, then search (Ctrl+F)** for a value you can see on
#    the page. Is it inside a `<script>`?
# 3. Look for `application/ld+json` and `__NEXT_DATA__`.
# 4. Only if none of these work, parse the HTML (Lesson 1), or use a
#    browser if the page needs JavaScript (Lesson 5).
#
# **Be careful with private APIs.** They're meant for the website's own
# pages, not for you. Follow the site's terms, keep your request rate low,
# and don't use login tokens that belong to someone else.
#
# **Next:** [Lesson 3: Reliable requests](03_reliable_requests.ipynb)
