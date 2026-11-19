"""
A Scrapy spider that crawls https://books.toscrape.com (Lesson 7).

Run it from the lessons/ folder:

    scrapy runspider books_spider.py -O output/books_scrapy.json
    scrapy runspider books_spider.py -a max_pages=3 -O output/books_scrapy.csv

-O writes the results to a file (overwriting it); the format comes from the
extension (.json, .jsonl, .csv, .xml). -a passes arguments to the spider.
"""

import re

import scrapy
from scrapy.exceptions import DropItem

RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


# --------------------------------------------------------------------------
# Item pipelines: every scraped item passes through these, in order
# (lowest number first). Use them to clean, validate, deduplicate or store.
# --------------------------------------------------------------------------


class CleanBookPipeline:
    """Turn raw strings like '£51.77', 'Three' and 'In stock (22 available)' into numbers."""

    def process_item(self, item, spider):
        if not item.get("title"):
            raise DropItem(f"Missing title on {item.get('url')}")
        item["price"] = float(re.sub(r"[^\d.]", "", item["price"]))
        item["rating"] = RATINGS.get(item["rating"])
        stock = re.search(r"\d+", item["availability"] or "")
        item["in_stock"] = int(stock.group()) if stock else 0
        del item["availability"]
        return item


class DuplicatesPipeline:
    """Drop books we've already seen (matched on UPC, the book's product code)."""

    def __init__(self):
        self.seen = set()

    def process_item(self, item, spider):
        if item["upc"] in self.seen:
            raise DropItem(f"Duplicate book {item['upc']}")
        self.seen.add(item["upc"])
        return item


# --------------------------------------------------------------------------
# The spider
# --------------------------------------------------------------------------


class BooksSpider(scrapy.Spider):
    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/catalogue/page-1.html"]

    # Settings for this spider. In a full Scrapy project these usually live
    # in settings.py instead.
    custom_settings = {
        "USER_AGENT": (
            "web-scraping-with-python tutorial "
            "(+https://github.com/rajat4665/web-scraping-with-python)"
        ),
        "ROBOTSTXT_OBEY": True,
        # Politeness: AutoThrottle adjusts the speed to how fast the server responds.
        "CONCURRENT_REQUESTS_PER_DOMAIN": 8,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 4,
        # Retries for temporary errors are on by default; this makes them explicit.
        "RETRY_TIMES": 3,
        # Cache pages on disk (in .scrapy/) so re-running while developing is instant.
        "HTTPCACHE_ENABLED": True,
        "HTTPCACHE_EXPIRATION_SECS": 24 * 3600,
        "ITEM_PIPELINES": {CleanBookPipeline: 300, DuplicatesPipeline: 400},
        "FEED_EXPORT_ENCODING": "utf-8",
        "LOG_LEVEL": "INFO",
    }

    def __init__(self, max_pages=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Arguments from -a always arrive as strings.
        self.max_pages = int(max_pages) if max_pages else None
        self.pages_seen = 0

    def parse(self, response):
        """Called for each listing page: follow every book, then the next page."""
        self.pages_seen += 1
        for href in response.css("article.product_pod h3 a::attr(href)").getall():
            # response.follow resolves relative URLs for us.
            yield response.follow(href, callback=self.parse_book)

        next_page = response.css("li.next a::attr(href)").get()
        if next_page and (self.max_pages is None or self.pages_seen < self.max_pages):
            yield response.follow(next_page, callback=self.parse)

    def parse_book(self, response):
        """Called for each book page: yield one item (a dict)."""
        table = {
            row.css("th::text").get(): row.css("td::text").get()
            for row in response.css("table.table-striped tr")
        }
        rating_classes = response.css("p.star-rating::attr(class)").get(default="").split()
        yield {
            "title": response.css("div.product_main h1::text").get(),
            "category": response.css("ul.breadcrumb li:nth-child(3) a::text").get(),
            "price": table.get("Price (incl. tax)"),
            "availability": table.get("Availability"),
            "rating": rating_classes[-1] if rating_classes else None,
            "upc": table.get("UPC"),
            "description": response.css("#product_description + p::text").get(),
            "image": response.urljoin(response.css("#product_gallery img::attr(src)").get()),
            "url": response.url,
        }
