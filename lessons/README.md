# Lessons

Each lesson comes in two versions with the same content:

- **`.ipynb`**: a Jupyter notebook with the outputs already shown, so you can read it right here on GitHub.
- **`.py`**: a plain script you can run or step through in your editor.

| # | Lesson |
|---|--------|
| 1 | [Web scraping basics](01_web_scraping_basics.ipynb) |
| 2 | [Hidden APIs and embedded JSON](02_hidden_apis_and_embedded_json.ipynb) |
| 3 | [Reliable requests](03_reliable_requests.ipynb) |
| 4 | [Fast scraping with asyncio](04_fast_async_crawling.ipynb) |
| 5 | [JavaScript pages with Playwright](05_javascript_pages_with_playwright.ipynb) |
| 6 | [Logins and forms](06_logins_and_forms.ipynb) |
| 7 | [Scrapy](07_scrapy_framework.ipynb) (spider: [`books_spider.py`](books_spider.py)) |
| 8 | [Clean and store your data](08_clean_and_store_data.ipynb) |

## Running them

Install the requirements first (see the [main README](../README.md#setup)), then run the lessons
from **this folder**:

```bash
cd lessons
jupyter notebook                 # open any lesson
python 01_web_scraping_basics.py # or run one as a script
```

Files the lessons create (CSV, JSON, a SQLite database, screenshots) go into `output/`.
Lesson 8 reads the books that Lesson 4 downloads, so run Lesson 4 first.
