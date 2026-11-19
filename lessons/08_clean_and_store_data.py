#!/usr/bin/env python3
# %% [markdown]
# # Lesson 8: Clean and store your data
#
# Scraped data is almost never ready to use. Prices are strings like
# `"£51.77"`, ratings are words like `"Three"`, stock is
# `"In stock (22 available)"`, and there may be duplicates and gaps.
#
# In this lesson we take the 1,000 books from **Lesson 4** and:
#
# 1. load them into a **pandas** DataFrame
# 2. clean and convert every column to the right type
# 3. check the data with simple validation rules
# 4. analyse it
# 5. store it in a **SQLite** database and query it with SQL
# 6. **upsert**: update the database when you scrape again, without duplicates
#
# Setup: `pip install pandas`. SQLite is built into Python.
# Run Lesson 4 first: it creates `output/books.json`.

# %%
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

OUTPUT = Path("output")
books_file = OUTPUT / "books.json"
if not books_file.exists():
    raise SystemExit("output/books.json not found. Run Lesson 4 (04_fast_async_crawling) first.")

# %% [markdown]
# ## 1. Load and look at the raw data
#
# Always start by *looking*. `head()`, `dtypes` and `isna().sum()` show you
# what you're dealing with.

# %%
raw = pd.DataFrame(json.loads(books_file.read_text()))
print(raw.shape[0], "rows,", raw.shape[1], "columns\n")
print(raw[["title", "price", "rating", "availability", "reviews"]].head())
print("\nColumn types (object or str = text):")
print(raw.dtypes)
print("\nMissing values per column:")
print(raw.isna().sum()[raw.isna().sum() > 0])

# %% [markdown]
# Everything is text (`object`, or `str` in pandas 3). You can't sort by price or calculate an
# average rating until the values are converted.

# %% [markdown]
# ## 2. Clean each column
#
# pandas has **vectorised string methods** under `.str`. They run on the
# whole column at once, with no loops.

# %%
RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

books = raw.copy()

# "£51.77" -> 51.77: remove everything except digits and the dot
books["price"] = books["price"].str.replace(r"[^\d.]", "", regex=True).astype(float)

# "Three" -> 3
books["rating"] = books["rating"].map(RATINGS).astype("Int64")

# "In stock (22 available)" -> 22
books["in_stock"] = books["availability"].str.extract(r"(\d+)", expand=False).fillna(0).astype(int)

# "0" -> 0
books["reviews"] = pd.to_numeric(books["reviews"], errors="coerce").astype("Int64")

# Text: trim whitespace, use "" for a missing description
for column in ["title", "category", "description"]:
    books[column] = books[column].fillna("").str.strip()

# Categories are a small set of repeated values; the category type saves memory
books["category"] = books["category"].astype("category")

books = books.drop(columns=["availability"])
print(books[["title", "price", "rating", "in_stock", "category"]].head())
print()
print(books.dtypes)

# %% [markdown]
# ### Duplicates
#
# If a crawl visits the same page twice, or you merge two crawls, you get
# duplicates. Pick a column that **identifies** a record, here the UPC
# (product code), and keep one row per value.

# %%
before = len(books)
books = books.drop_duplicates(subset="upc", keep="last")
print(f"Removed {before - len(books)} duplicate(s); {len(books)} books left")

# %% [markdown]
# ## 3. Validate
#
# Websites change, and when they do your scraper often keeps running but
# silently produces garbage. A few checks catch that early. Run them after
# every scrape.


# %%
def validate(df):
    problems = []
    if len(df) < 900:
        problems.append(f"only {len(df)} books; expected about 1000")
    if df["price"].isna().any() or (df["price"] <= 0).any():
        problems.append("missing or non-positive prices")
    if not df["rating"].dropna().between(1, 5).all():
        problems.append("ratings outside 1-5")
    if df["rating"].isna().mean() > 0.01:
        problems.append("more than 1% of ratings missing")
    if (df["title"] == "").any():
        problems.append("empty titles")
    if not df["url"].str.startswith("https://").all():
        problems.append("relative URLs")
    return problems


problems = validate(books)
print("Validation:", "all checks passed ✓" if not problems else problems)

# %% [markdown]
# ## 4. Analyse
#
# Now that the types are right, questions are one line each.

# %%
print(f"Average price: £{books['price'].mean():.2f}")
print("Books with 5 stars:", (books["rating"] == 5).sum())
print()

print("Most expensive books:")
print(books.nlargest(5, "price")[["title", "price", "rating"]].to_string(index=False))
print()

print("Categories with the most books:")
summary = (
    books.groupby("category", observed=True)
    .agg(books=("title", "count"), avg_price=("price", "mean"), avg_rating=("rating", "mean"))
    .sort_values("books", ascending=False)
    .round(2)
)
print(summary.head(8))

# %%
print("Does a higher rating mean a higher price?")
print(books.groupby("rating")["price"].agg(["count", "mean"]).round(2))

# %% [markdown]
# ## 5. Store in SQLite
#
# A CSV file is fine for sharing, but a **database** lets you query, filter
# and update data without loading everything into memory. SQLite is a full
# SQL database stored in a single file, and Python includes it.
#
# `to_sql` writes a DataFrame to a table in one line.

# %%
books.to_csv(OUTPUT / "books_clean.csv", index=False)

db_path = OUTPUT / "books.db"
db_path.unlink(missing_ok=True)  # start fresh for this lesson
with sqlite3.connect(db_path) as conn:
    books.assign(category=books["category"].astype(str)).to_sql("books", conn, index=False)
    conn.execute("CREATE UNIQUE INDEX idx_books_upc ON books(upc)")
    count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
print(f"Stored {count} books in {db_path}")

# %% [markdown]
# ### Query with SQL
#
# `pd.read_sql` runs a query and gives you a DataFrame back. Use `?`
# placeholders for values. **Never** build SQL by pasting strings together:
# that's how SQL injection happens.

# %%
query = """
    SELECT title, price, rating, in_stock
    FROM books
    WHERE category = ? AND rating >= ?
    ORDER BY price
"""
with sqlite3.connect(db_path) as conn:
    print(pd.read_sql(query, conn, params=("Travel", 3)).to_string(index=False))

# %% [markdown]
# ## 6. Scraping again: upserts
#
# Scrapers usually run again and again (every day, say). Each time, prices
# and stock change, and new books appear. You want to **update existing
# rows and insert new ones**. That's an *upsert*:
# `INSERT ... ON CONFLICT(upc) DO UPDATE`.
#
# We also record **when** each row was last seen, so you can tell which
# books disappeared from the site.

# %%
UPSERT = """
    INSERT INTO books (upc, title, category, price, rating, in_stock, reviews,
                       description, image, url, last_seen)
    VALUES (:upc, :title, :category, :price, :rating, :in_stock, :reviews,
            :description, :image, :url, :last_seen)
    ON CONFLICT(upc) DO UPDATE SET
        price = excluded.price,
        in_stock = excluded.in_stock,
        rating = excluded.rating,
        last_seen = excluded.last_seen
"""


def save_books(conn, records):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.executemany(UPSERT, [{**r, "last_seen": now} for r in records])


with sqlite3.connect(db_path) as conn:
    conn.execute("ALTER TABLE books ADD COLUMN last_seen TEXT")

    # Pretend this is tomorrow's scrape: one price changed, one book is new.
    tomorrow = books.head(2).assign(category=lambda d: d["category"].astype(str))
    tomorrow = tomorrow.astype(object).where(tomorrow.notna(), None).to_dict("records")
    tomorrow[0]["price"] = 9.99
    tomorrow[1] = {**tomorrow[1], "upc": "NEW-BOOK-001", "title": "A Brand New Book"}

    save_books(conn, tomorrow)
    total = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    rows = conn.execute(
        "SELECT title, price, last_seen FROM books WHERE last_seen IS NOT NULL"
    ).fetchall()

print(f"Books in database: {total} (one more than before)")
for row in rows:
    print(row)

# %% [markdown]
# ## Where to go from here
#
# * **More data?** Swap SQLite for PostgreSQL. The SQL is almost the same.
# * **Track history:** instead of overwriting prices, add a
#   `price_history(upc, price, seen_at)` table and insert a row on every
#   scrape. Then you can chart prices over time.
# * **Automate:** run your scraper on a schedule (cron, or GitHub Actions
#   with `schedule:`), validate the results, and get alerted when checks fail.
# * **Stricter validation:** libraries like `pydantic` or `pandera` let you
#   declare the shape your data must have.
#
# 🎉 **That's the series!** You can now find a site's data (Lesson 2),
# fetch it reliably (3) and quickly (4), handle JavaScript (5) and logins
# (6), use a framework (7), and turn the results into clean, queryable
# data (8).
