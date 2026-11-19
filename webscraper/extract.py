"""Turning HTML into data with BeautifulSoup."""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup


def _texts(soup: BeautifulSoup, tag: str) -> list[str]:
    return [t.get_text(" ", strip=True) for t in soup.find_all(tag) if t.get_text(strip=True)]


def extract_page_data(html: str, base_url: str) -> dict:
    """
    Turn raw HTML into a dictionary of useful data.

    Links and image sources are converted to absolute URLs using base_url,
    so "/about" on https://example.com becomes "https://example.com/about".
    """
    # "html.parser" ships with Python, so there's nothing extra to install.
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    description_tag = soup.find("meta", attrs={"name": "description"})
    anchors = soup.find_all("a")
    images = soup.find_all("img")

    return {
        "title": title_tag.get_text(strip=True) if title_tag else "",
        "description": (description_tag.get("content") or "").strip() if description_tag else "",
        "all_anchor_href": [urljoin(base_url, a["href"]) for a in anchors if a.get("href")],
        "all_anchors": [str(a) for a in anchors],
        "all_images_data": [str(img) for img in images],
        "all_images_source_data": [
            urljoin(base_url, img["src"]) for img in images if img.get("src")
        ],
        "all_h1_data": _texts(soup, "h1"),
        "all_h2_data": _texts(soup, "h2"),
        "all_h3_data": _texts(soup, "h3"),
        "all_p_data": _texts(soup, "p"),
    }
