"""Shared test helpers. The tests never touch the network: FakeSession stands in for it."""

import pytest

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
    """Stands in for requests.Session: maps URL -> FakeResponse (or an exception to raise)."""

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


@pytest.fixture
def offline(monkeypatch):
    """Make everything that calls make_session() use a fake session serving SAMPLE_HTML."""
    session = FakeSession({"https://example.com": FakeResponse(SAMPLE_HTML)})
    monkeypatch.setattr("webscraper.fetch.make_session", lambda: session)
    return session
