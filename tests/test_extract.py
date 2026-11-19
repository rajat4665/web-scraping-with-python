from conftest import SAMPLE_HTML
from webscraper.extract import extract_page_data


def test_extract_page_data():
    data = extract_page_data(SAMPLE_HTML, "https://example.com/page")

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
    data = extract_page_data("<p>hi</p>", "https://example.com")
    assert data["title"] == ""
    assert data["description"] == ""
    assert data["all_p_data"] == ["hi"]
