import json

import pytest

from conftest import SAMPLE_HTML, FakeResponse, FakeSession
from webscraper.cli import print_record, websites_table
from webscraper.errors import ScrapeError
from webscraper.scrape import default_alias, scrape_and_store
from webscraper.storage import load_db, save_db, unique_alias


def test_load_db_missing_file(tmp_path):
    assert load_db(str(tmp_path / "nope.json")) == {"scraped_data": {}}


def test_load_db_corrupt_file(tmp_path):
    path = tmp_path / "db.json"
    path.write_text("{not json")
    with pytest.raises(ScrapeError, match="not valid JSON"):
        load_db(str(path))


def test_save_and_load_round_trip(tmp_path):
    path = str(tmp_path / "db.json")
    db = {"scraped_data": {"a": {"title": "ü"}}}
    save_db(db, path)
    assert load_db(path) == db
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
    db = load_db(str(path))
    assert "qwerty" in str(websites_table(db))
    print_record("qwerty", db["scraped_data"]["qwerty"])  # missing fields don't crash


def test_unique_alias():
    assert unique_alias("site", {}) == "site"
    assert unique_alias("site", {"site": 1}) == "site-2"
    assert unique_alias("site", {"site": 1, "site-2": 1}) == "site-3"


def test_default_alias_strips_www():
    assert default_alias("https://www.example.com/x") == "example.com"


def test_scrape_and_store():
    session = FakeSession({"https://example.com": FakeResponse(SAMPLE_HTML)})
    db = {"scraped_data": {"example.com": {}}}
    alias, record = scrape_and_store(
        "https://example.com", db, session=session, respect_robots=False
    )
    assert alias == "example.com-2"
    assert db["scraped_data"][alias] is record
    assert record["domain"] == "example.com"
    assert record["title"] == "Sample Page"
    assert record["status"] is True
