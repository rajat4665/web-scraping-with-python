#!/usr/bin/env python3
# %% [markdown]
# # Web Scraping with Python: requests + BeautifulSoup
#
# This tutorial goes from "download a page" to "scrape many pages and save
# the data to CSV". Each section builds on the one before it.
#
# Install the libraries first:
#
# ```bash
# pip install -r requirements.txt
# ```
#
# We'll mostly scrape **https://quotes.toscrape.com**, a site made for
# practising web scraping, and then a real page on Wikipedia.

# %%
import csv
import json
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# %% [markdown]
# ## 1. Download a page with `requests`
#
# Three habits worth learning right away:
#
# * **Send a User-Agent** so the site knows who's visiting. Many sites
#   (Wikipedia included) block requests that don't send one.
# * **Set a timeout** so your script doesn't hang forever.
# * **Check the status code**. `raise_for_status()` raises an error for
#   404, 500 and so on.

# %%
HEADERS = {
    "User-Agent": "web-scraping-with-python tutorial "
    "(+https://github.com/rajat4665/web-scraping-with-python)"
}

url = "https://quotes.toscrape.com/"
response = requests.get(url, headers=HEADERS, timeout=15)
response.raise_for_status()

print("Status code:", response.status_code)
print("Content type:", response.headers["Content-Type"])
print("First 200 characters of HTML:\n", response.text[:200])

# %% [markdown]
# ## 2. Parse the HTML with BeautifulSoup
#
# BeautifulSoup turns the raw HTML text into a tree you can search.
# `"html.parser"` is built into Python, so it needs no extra install.

# %%
soup = BeautifulSoup(response.text, "html.parser")

# find() returns the FIRST matching tag, or None if there isn't one
title = soup.find("title")
print("With HTML tags:   ", title)
print("Without HTML tags:", title.get_text(strip=True))

# %% [markdown]
# ## 3. `find()` vs `find_all()`
#
# * `find()` returns the first match (or `None`)
# * `find_all()` returns a list of every match

# %%
first_link = soup.find("a")
print("First link:", first_link)

all_links = soup.find_all("a")
print("Total links on the page:", len(all_links))

for link in all_links[:5]:  # slicing: just the first 5
    print(" ", link.get_text(strip=True), "->", link.get("href"))

# %% [markdown]
# ## 4. Read attributes
#
# Use `tag["attr"]` when you're sure the attribute exists, and
# `tag.get("attr")` when it might not (it returns `None` instead of raising
# a `KeyError`).
#
# Links on a page are often *relative* (`/page/2/`). `urljoin` turns them
# into full URLs.

# %%
for link in soup.find_all("a", href=True)[:5]:
    print(link["href"], "->", urljoin(url, link["href"]))

# `class` is special: BeautifulSoup gives it to you as a list,
# because an element can have several classes.
first_quote = soup.find("div", class_="quote")
print("\nclass attribute:", first_quote["class"], type(first_quote["class"]))
print("joined into a string:", " ".join(first_quote["class"]))

# %% [markdown]
# ## 5. Search by class, and look *inside* an element
#
# Calling `find()` on a tag searches only inside that tag, which is how you
# pull structured data out of a page.

# %%
for quote in soup.find_all("div", class_="quote")[:3]:
    text = quote.find("span", class_="text").get_text(strip=True)
    author = quote.find("small", class_="author").get_text(strip=True)
    tags = [tag.get_text() for tag in quote.find_all("a", class_="tag")]
    print(f"{text}\n    - {author}  {tags}\n")

# %% [markdown]
# ## 6. CSS selectors: `select()` and `select_one()`
#
# If you know CSS, selectors are often shorter than chains of `find()`
# calls. Here's the same data again:
#
# | Selector            | Means                                   |
# |---------------------|-----------------------------------------|
# | `div.quote`         | `<div>` with class `quote`              |
# | `span.text`         | `<span>` with class `text`              |
# | `div.tags a.tag`    | `<a class="tag">` inside `<div class="tags">` |
# | `li.next > a`       | an `<a>` directly inside `<li class="next">`  |

# %%
for quote in soup.select("div.quote")[:3]:
    print(quote.select_one("span.text").get_text(strip=True))
    print("   by", quote.select_one("small.author").get_text(strip=True))
    print("   tags:", [a.get_text() for a in quote.select("div.tags a.tag")])

# %% [markdown]
# ## 7. Scrape every page (pagination)
#
# Most sites split data across pages. Keep following the "Next" link until
# there isn't one. `time.sleep()` between requests keeps the load on the
# server low. Please be polite!


# %%
def parse_quotes(page_soup):
    """Return a list of dicts, one per quote on the page."""
    return [
        {
            "text": q.select_one("span.text").get_text(strip=True),
            "author": q.select_one("small.author").get_text(strip=True),
            "tags": [a.get_text() for a in q.select("a.tag")],
        }
        for q in page_soup.select("div.quote")
    ]


def scrape_all_quotes(start_url, max_pages=10, delay=0.5):
    session = requests.Session()  # reuses the connection: faster and kinder
    session.headers.update(HEADERS)

    quotes, page_url, pages = [], start_url, 0
    while page_url and pages < max_pages:
        page = session.get(page_url, timeout=15)
        page.raise_for_status()
        page_soup = BeautifulSoup(page.text, "html.parser")

        quotes.extend(parse_quotes(page_soup))
        pages += 1
        print(f"page {pages}: {page_url} ({len(quotes)} quotes so far)")

        next_link = page_soup.select_one("li.next > a")
        page_url = urljoin(page_url, next_link["href"]) if next_link else None
        time.sleep(delay)
    return quotes


all_quotes = scrape_all_quotes("https://quotes.toscrape.com/")
print("\nTotal quotes scraped:", len(all_quotes))

# %% [markdown]
# ## 8. Save the data (CSV and JSON)

# %%
with open("quotes.csv", "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=["text", "author", "tags"])
    writer.writeheader()
    for q in all_quotes:
        writer.writerow({**q, "tags": ", ".join(q["tags"])})

with open("quotes.json", "w", encoding="utf-8") as fh:
    json.dump(all_quotes, fh, indent=2, ensure_ascii=False)

print("Saved quotes.csv and quotes.json")

# %% [markdown]
# ## 9. A real website: Wikipedia
#
# Real sites are messier. Some tips:
#
# * Open the page in your browser, right-click and choose **Inspect** to find
#   the tags and classes you need.
# * Websites change their HTML over time, so selectors that worked last year
#   may not work today. (This tutorial used to read Wikipedia's
#   `div.toc`, which no longer exists.) Always check for `None`.

# %%
wiki_url = "https://en.wikipedia.org/wiki/World_War_II"
wiki = requests.get(wiki_url, headers=HEADERS, timeout=15)
wiki.raise_for_status()
wiki_soup = BeautifulSoup(wiki.text, "html.parser")

print("Title:", wiki_soup.find("title").get_text(strip=True))

# Section headings
headings = [h.get_text(strip=True) for h in wiki_soup.select("div.mw-heading2 h2")]
print("\nSections:", headings)

# %% [markdown]
# ### Turn the infobox table into a dictionary
#
# The infobox is the summary box at the top right of a Wikipedia article.
# Each row has a label (`<th>`) and a value (`<td>`).

# %%
infobox = wiki_soup.select_one("table.infobox")
facts = {}
if infobox is None:
    print("No infobox found. Wikipedia's HTML may have changed.")
else:
    for row in infobox.find_all("tr"):
        label, value = row.find("th"), row.find("td")
        if label and value:
            # remove citation markers like [1]
            for sup in value.find_all("sup", class_="reference"):
                sup.decompose()
            facts[label.get_text(" ", strip=True)] = value.get_text(" ", strip=True)

for key, value in list(facts.items())[:6]:
    print(f"{key}: {value[:100]}")

# %% [markdown]
# ### Images
#
# Image `src` values on Wikipedia start with `//`, so `urljoin` is useful
# again.

# %%
images = [urljoin(wiki_url, img["src"]) for img in wiki_soup.find_all("img", src=True)]
print("Images found:", len(images))
for src in images[:5]:
    print(" ", src)

# %% [markdown]
# ## Scraping responsibly
#
# * Check the site's `robots.txt` (e.g. https://en.wikipedia.org/robots.txt)
#   and its terms of service.
# * If the site has an API (Wikipedia does), prefer it.
# * Add a delay between requests and don't hammer servers.
# * Don't scrape personal data, or content behind a login, without permission.
#
# **Next:** [Lesson 2](lessons/02_hidden_apis_and_embedded_json.ipynb): hidden APIs and
# embedded JSON.
# Before writing selectors, check whether the data is already available as JSON.
#
# Also try `web_scraping_command_line_tool.py` in this repo, which wraps
# these ideas into a reusable command line tool.
