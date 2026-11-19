import pytest
import requests

from conftest import SAMPLE_HTML, FakeResponse, FakeSession
from webscraper.errors import ScrapeError
from webscraper.fetch import fetch_html, normalize_url


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("example.com", "https://example.com"),
        ("  https://example.com/a  ", "https://example.com/a"),
        ("http://example.com", "http://example.com"),
    ],
)
def test_normalize_url(raw, expected):
    assert normalize_url(raw) == expected


@pytest.mark.parametrize("bad", ["", "   ", "ftp://example.com", "https://"])
def test_normalize_url_rejects_bad_input(bad):
    with pytest.raises(ScrapeError):
        normalize_url(bad)


def test_fetch_html_success_follows_final_url():
    session = FakeSession(
        {"https://example.com": FakeResponse(SAMPLE_HTML, url="https://example.com/home")}
    )
    html, final_url = fetch_html("example.com", session=session, respect_robots=False)
    assert "Sample Page" in html
    assert final_url == "https://example.com/home"


def test_fetch_html_http_error():
    with pytest.raises(ScrapeError, match="HTTP 404"):
        fetch_html("https://example.com/missing", session=FakeSession({}), respect_robots=False)


def test_fetch_html_network_error():
    session = FakeSession({"https://example.com": requests.ConnectionError("boom")})
    with pytest.raises(ScrapeError, match="Could not load"):
        fetch_html("https://example.com", session=session, respect_robots=False)


def test_fetch_html_timeout():
    session = FakeSession({"https://example.com": requests.Timeout()})
    with pytest.raises(ScrapeError, match="Timed out"):
        fetch_html("https://example.com", session=session, respect_robots=False)


def test_fetch_html_rejects_non_html():
    session = FakeSession(
        {"https://example.com/a.pdf": FakeResponse("%PDF", content_type="application/pdf")}
    )
    with pytest.raises(ScrapeError, match="not an HTML page"):
        fetch_html("https://example.com/a.pdf", session=session, respect_robots=False)


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
    with pytest.raises(ScrapeError, match="robots.txt"):
        fetch_html("https://example.com/private/page", session=session)
    html, _ = fetch_html("https://example.com/public", session=session)
    assert "Sample Page" in html
    # and it can be switched off
    fetch_html("https://example.com/private/page", session=session, respect_robots=False)


def test_missing_robots_txt_allows_scraping():
    session = FakeSession({"https://example.com/": FakeResponse(SAMPLE_HTML)})
    html, _ = fetch_html("https://example.com/", session=session)
    assert "Sample Page" in html
