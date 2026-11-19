![web scraping with python](WEB%20SCRAPING.jpg)

# Web Scraping with Python

[![CI](https://github.com/rajat4665/web-scraping-with-python/actions/workflows/ci.yml/badge.svg)](https://github.com/rajat4665/web-scraping-with-python/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Web scraping** (also called web harvesting or web data extraction) means
pulling data out of websites by reading their HTML. This repo teaches the
basics with two popular Python libraries, **requests** and **BeautifulSoup**,
and includes a small command line tool you can use and extend.

## What you'll learn

- How to download a web page with `requests`, the polite way (User-Agent, timeouts, status codes)
- How to parse HTML with BeautifulSoup: `find()`, `find_all()`, attributes and classes
- How to use CSS selectors with `select()` and `select_one()`
- How to turn a page into structured data (a list of dicts)
- How to follow "Next" links to scrape many pages
- How to save results to CSV and JSON
- How to scrape a real site (Wikipedia) and cope with HTML that changes
- How to scrape responsibly (robots.txt, rate limiting)

## What's inside

| File | What it is |
|------|------------|
| [`Web Scraping with BeautifulSoup.ipynb`](Web%20Scraping%20with%20BeautifulSoup.ipynb) | The tutorial as a Jupyter notebook, with outputs |
| [`Web Scraping with BeautifulSoup.py`](Web%20Scraping%20with%20BeautifulSoup.py) | The same tutorial as a plain Python script |
| [`web_scraping_command_line_tool.py`](web_scraping_command_line_tool.py) | A CLI that scrapes pages and saves them to a JSON file |
| [`tests/`](tests) | Tests for the CLI tool (they run offline) |

## Setup

You need Python 3.10 or newer.

```bash
git clone https://github.com/rajat4665/web-scraping-with-python.git
cd web-scraping-with-python

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Run the tutorial

As a script:

```bash
python "Web Scraping with BeautifulSoup.py"
```

Or in Jupyter, which is nicer for learning because you can run one cell at a time:

```bash
pip install jupyter
jupyter notebook "Web Scraping with BeautifulSoup.ipynb"
```

The tutorial scrapes [quotes.toscrape.com](https://quotes.toscrape.com), a site
built for practising scraping, then a Wikipedia article. It writes
`quotes.csv` and `quotes.json` to the current folder.

## Use the command line tool

Run it with no arguments to get the interactive menu:

```bash
python web_scraping_command_line_tool.py
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
python web_scraping_command_line_tool.py scrape https://quotes.toscrape.com --alias quotes

# list everything you've scraped
python web_scraping_command_line_tool.py list

# summary of one page, or just one field
python web_scraping_command_line_tool.py show quotes
python web_scraping_command_line_tool.py show quotes --field all_anchor_href

# export one page's data to its own file, or delete it
python web_scraping_command_line_tool.py export quotes -o quotes.json
python web_scraping_command_line_tool.py delete quotes
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

GitHub Actions runs both on every push and pull request.

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
