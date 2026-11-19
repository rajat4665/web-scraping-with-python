"""Tests for the command line scraper. No network access needed."""

import json
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import web_scraping_command_line_tool as tool  # noqa: E402

SAMPLE_HTML = """
<html>
  <head>
    <title> Sample Page </title>
    <meta name="description" content="A page for tests">
  </head>
  <body>
    <h1>Main heading</h1>
    <h2>Section one</h2><h2>Section two</h2>
    <h3>Sub</h3>
    <p>First paragraph.</p>
    <p>   </p>
    <a href="/about">About</a>
    <a href="https://other.example/x">Other</a>
    <a name="anchor-without-href">No href</a>
    <img src="/logo.png" alt="logo">
    <img alt="no src">
  </body>
</html>
"""


class FakeResponse:
    def __init__(self, text="", status_code=200, url="", content_type="text/html", reason="OK"):
        self.text = text
        self.status_code = status_code
        self.url = url
        self.reason = reason
        self.headers = {"Content-Type": content_type}


class FakeSession:
    """Stands in for requests.Session: maps URL -> FakeResponse (or an exception)."""

    def __init__(self, pages):
        self.pages = pages
        self.headers = {}
        self.requested = []

    def get(self, url, timeout=None):
        self.requested.append(url)
        page = self.pages.get(url, FakeResponse(status_code=404, url=url, reason="Not Found"))
        if isinstance(page, Exception):
            raise page
        if not page.url:
            page.url = url
        return page


# --- extract_page_data ----------------------------------------------------


def test_extract_page_data():
    data = tool.extract_page_data(SAMPLE_HTML, "https://example.com/page")

    assert data["title"] == "Sample Page"
    assert data["description"] == "A page for tests"
    assert data["all_h1_data"] == ["Main heading"]
    assert data["all_h2_data"] == ["Section one", "Section two"]
    assert data["all_h3_data"] == ["Sub"]
    assert data["all_p_data"] == ["First paragraph."]  # blank <p> skipped
    # relative links become absolute, anchors without href are skipped
    assert data["all_anchor_href"] == ["https://example.com/about", "https://other.example/x"]
    assert len(data["all_anchors"]) == 3
    # images without src don't crash
    assert data["all_images_source_data"] == ["https://example.com/logo.png"]
    assert len(data["all_images_data"]) == 2


def test_extract_page_without_title():
    data = tool.extract_page_data("<p>hi</p>", "https://example.com")
    assert data["title"] == ""
    assert data["description"] == ""
    assert data["all_p_data"] == ["hi"]


# --- URLs and aliases -----------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("example.com", "https://example.com"),
        ("  https://example.com/a  ", "https://example.com/a"),
        ("http://example.com", "http://example.com"),
    ],
)
def test_normalize_url(raw, expected):
    assert tool.normalize_url(raw) == expected


@pytest.mark.parametrize("bad", ["", "   ", "ftp://example.com", "https://"])
def test_normalize_url_rejects_bad_input(bad):
    with pytest.raises(tool.ScrapeError):
        tool.normalize_url(bad)


def test_unique_alias():
    assert tool.unique_alias("site", {}) == "site"
    assert tool.unique_alias("site", {"site": 1}) == "site-2"
    assert tool.unique_alias("site", {"site": 1, "site-2": 1}) == "site-3"


def test_default_alias_strips_www():
    assert tool.default_alias("https://www.example.com/x") == "example.com"


# --- fetching -------------------------------------------------------------


def test_fetch_html_success_follows_final_url():
    session = FakeSession(
        {
            "https://example.com": FakeResponse(SAMPLE_HTML, url="https://example.com/home"),
        }
    )
    html, final_url = tool.fetch_html("example.com", session=session, respect_robots=False)
    assert "Sample Page" in html
    assert final_url == "https://example.com/home"


def test_fetch_html_http_error():
    with pytest.raises(tool.ScrapeError, match="HTTP 404"):
        tool.fetch_html(
            "https://example.com/missing", session=FakeSession({}), respect_robots=False
        )


def test_fetch_html_network_error():
    session = FakeSession({"https://example.com": requests.ConnectionError("boom")})
    with pytest.raises(tool.ScrapeError, match="Could not load"):
        tool.fetch_html("https://example.com", session=session, respect_robots=False)


def test_fetch_html_timeout():
    session = FakeSession({"https://example.com": requests.Timeout()})
    with pytest.raises(tool.ScrapeError, match="Timed out"):
        tool.fetch_html("https://example.com", session=session, respect_robots=False)


def test_fetch_html_rejects_non_html():
    session = FakeSession(
        {"https://example.com/a.pdf": FakeResponse("%PDF", content_type="application/pdf")}
    )
    with pytest.raises(tool.ScrapeError, match="not an HTML page"):
        tool.fetch_html("https://example.com/a.pdf", session=session, respect_robots=False)


def test_robots_txt_is_respected():
    session = FakeSession(
        {
            "https://example.com/robots.txt": FakeResponse(
                "User-agent: *\nDisallow: /private", content_type="text/plain"
            ),
            "https://example.com/private/page": FakeResponse(SAMPLE_HTML),
            "https://example.com/public": FakeResponse(SAMPLE_HTML),
        }
    )
    with pytest.raises(tool.ScrapeError, match="robots.txt"):
        tool.fetch_html("https://example.com/private/page", session=session)
    html, _ = tool.fetch_html("https://example.com/public", session=session)
    assert "Sample Page" in html
    # and it can be switched off
    tool.fetch_html("https://example.com/private/page", session=session, respect_robots=False)


def test_missing_robots_txt_allows_scraping():
    session = FakeSession({"https://example.com/": FakeResponse(SAMPLE_HTML)})
    html, _ = tool.fetch_html("https://example.com/", session=session)
    assert "Sample Page" in html


# --- storage --------------------------------------------------------------


def test_load_db_missing_file(tmp_path):
    assert tool.load_db(str(tmp_path / "nope.json")) == {"scraped_data": {}}


def test_load_db_corrupt_file(tmp_path):
    path = tmp_path / "db.json"
    path.write_text("{not json")
    with pytest.raises(tool.ScrapeError, match="not valid JSON"):
        tool.load_db(str(path))


def test_save_and_load_round_trip(tmp_path):
    path = str(tmp_path / "db.json")
    db = {"scraped_data": {"a": {"title": "ü"}}}
    tool.save_db(db, path)
    assert tool.load_db(path) == db
    assert list(tmp_path.iterdir()) == [tmp_path / "db.json"]  # no temp files left


def test_old_database_format_still_loads(tmp_path):
    """Files written by the original version of the tool must keep working."""
    old = {
        "scraped_data": {
            "qwerty": {
                "title": "World War II - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/World_War_II",
                "name": "qwerty",
                "alias": "qwerty",
                "domain": "en.wikipedia.org",
                "scraped_at": "18/02/2022 23:10:01",
                "status": True,
                "all_h1_data": ["World War II"],
            }
        }
    }
    path = tmp_path / "scraped_data.json"
    path.write_text(json.dumps(old))
    db = tool.load_db(str(path))
    assert "qwerty" in str(tool.websites_table(db))
    tool.print_record("qwerty", db["scraped_data"]["qwerty"])  # missing fields don't crash


def test_scrape_and_store():
    session = FakeSession({"https://example.com": FakeResponse(SAMPLE_HTML)})
    db = {"scraped_data": {"example.com": {}}}
    alias, record = tool.scrape_and_store(
        "https://example.com", db, session=session, respect_robots=False
    )
    assert alias == "example.com-2"
    assert db["scraped_data"][alias] is record
    assert record["domain"] == "example.com"
    assert record["title"] == "Sample Page"
    assert record["status"] is True


# --- command line ---------------------------------------------------------


@pytest.fixture
def offline(monkeypatch):
    """Make the CLI use a fake session instead of the network."""
    session = FakeSession({"https://example.com": FakeResponse(SAMPLE_HTML)})
    monkeypatch.setattr(tool, "make_session", lambda: session)
    return session


def test_cli_full_flow(tmp_path, offline, capsys):
    db = str(tmp_path / "db.json")

    assert tool.main(["--db", db, "scrape", "https://example.com", "--alias", "ex"]) == 0
    assert "Saved to" in capsys.readouterr().out

    assert tool.main(["--db", db, "list"]) == 0
    assert "Sample Page" in capsys.readouterr().out

    assert tool.main(["--db", db, "show", "ex", "--field", "all_h2_data"]) == 0
    assert capsys.readouterr().out.splitlines() == ["Section one", "Section two"]

    out_file = tmp_path / "ex.json"
    assert tool.main(["--db", db, "export", "ex", "-o", str(out_file)]) == 0
    assert json.loads(out_file.read_text())["title"] == "Sample Page"

    assert tool.main(["--db", db, "delete", "ex"]) == 0
    assert tool.load_db(db)["scraped_data"] == {}


def test_cli_reports_errors(tmp_path, capsys):
    db = str(tmp_path / "db.json")
    assert tool.main(["--db", db, "show", "missing"]) == 1
    assert "No data saved as 'missing'" in capsys.readouterr().err


def test_interactive_menu_handles_bad_input(tmp_path, offline, monkeypatch, capsys):
    db = str(tmp_path / "db.json")
    answers = iter(["abc", "1", "2", "https://example.com", "", "3", "example.com", "4"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    assert tool.interactive(db) == 0
    out = capsys.readouterr().out
    assert "Please enter 1, 2, 3 or 4." in out
    assert "No scraped websites yet" in out
    assert "Saved to" in out
    assert "Thank you for using!" in out
