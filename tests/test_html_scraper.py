"""
Tests for WikipediaScraper.
Every request goes through a fake session object, so the suite never touches
Wikipedia: the scraper must be testable without being polite to a real server.
"""
import json
from src.html_scraper import WikipediaScraper


class FakeResponse:
    """Minimal stand-in for requests.Response, only what fetch_html reads."""

    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


class FakeSession:
    """
    Session double recording the calls it received.
    :param: the response to return, or an exception instance to raise
    """

    def __init__(self, result):
        self.result = result
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_fetch_html_returns_text_on_success():
    session = FakeSession(FakeResponse(200, "<html><p><b>Hi</b> there</p></html>"))
    scraper = WikipediaScraper(session)

    html = scraper.fetch_html("https://fr.wikipedia.org/wiki/Test")

    #A string, never the Response object
    assert html == "<html><p><b>Hi</b> there</p></html>"


def test_fetch_html_sends_user_agent_with_contact():
    session = FakeSession(FakeResponse(200, "<html></html>"))
    scraper = WikipediaScraper(session)

    scraper.fetch_html("https://fr.wikipedia.org/wiki/Test")

    user_agent = session.calls[0][1]["headers"]["User-Agent"]
    assert "WikipediaScraperBot" in user_agent
    assert "contact:" in user_agent


def test_fetch_html_returns_empty_string_on_bad_status():
    scraper = WikipediaScraper(FakeSession(FakeResponse(404, "not found")))

    assert scraper.fetch_html("https://fr.wikipedia.org/wiki/Nope") == ""


def test_fetch_html_returns_empty_string_on_network_error():
    scraper = WikipediaScraper(FakeSession(ConnectionError("boom")))

    assert scraper.fetch_html("https://fr.wikipedia.org/wiki/Nope") == ""


def test_get_first_paragraph_survives_a_failed_fetch():
    """The error path of fetch_html must not crash the caller downstream."""
    scraper = WikipediaScraper(FakeSession(FakeResponse(500, "")))

    html = scraper.fetch_html("https://fr.wikipedia.org/wiki/Nope")

    assert scraper.get_first_paragraph(html) == "failed"


def test_get_first_paragraph_picks_the_bold_paragraph_and_cleans_it():
    html = (
        "<html><p>Navigation</p>"
        "<p><b>François Hollande</b>, né le 12 août 1954[1], est un homme d'État.</p>"
        "</html>"
    )
    scraper = WikipediaScraper(FakeSession(FakeResponse(200, html)))

    paragraph = scraper.get_first_paragraph(html)

    assert paragraph.startswith("François Hollande")
    assert "[1]" not in paragraph


def test_clean_text_removes_multi_character_citations():
    scraper = WikipediaScraper(FakeSession(FakeResponse()))

    #The old single-character pattern missed all of these
    text = "Leader[1][12][n 3][citation needed] was born."

    assert scraper.clean_text(text) == "Leader was born."


def test_clean_text_removes_audio_markers_and_collapses_whitespace():
    scraper = WikipediaScraper(FakeSession(FakeResponse()))

    text = "Mark Rutte (uitspraakⓘ)\n is  Dutch.\n\nÉcouterⓘ"

    assert scraper.clean_text(text) == "Mark Rutte is Dutch."


def test_to_json_file_is_utf8_and_keeps_accents(tmp_path):
    scraper = WikipediaScraper(FakeSession(FakeResponse()))
    path = tmp_path / "leaders.json"

    scraper.to_json_file(str(path), {"fr": [{"first_name": "François"}]})

    raw = path.read_bytes()
    #Real accented bytes, not an ANSI codepage nor a ç escape
    assert "François".encode("utf-8") in raw
    assert b"\\u" not in raw
    assert json.loads(path.read_text(encoding="utf-8"))["fr"][0]["first_name"] == "François"


def test_to_csv_file_writes_one_header_and_one_row_per_leader(tmp_path):
    scraper = WikipediaScraper(FakeSession(FakeResponse()))
    path = tmp_path / "leaders.csv"
    leaders = {
        "fr": [{"id": "Q157", "last_name": "Hollande"}],
        "be": [{"id": "Q12978", "last_name": "Verhofstadt"}],
    }

    scraper.to_csv_file(str(path), leaders)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "country,id,last_name"
    assert lines[1] == "fr,Q157,Hollande"
    assert lines[2] == "be,Q12978,Verhofstadt"


def test_to_csv_file_quotes_commas_and_keeps_accents(tmp_path):
    """A paragraph full of commas must not shift the columns."""
    import csv

    scraper = WikipediaScraper(FakeSession(FakeResponse()))
    path = tmp_path / "leaders.csv"
    paragraph = "François Hollande, né le 12 août 1954, est un homme d'État."

    scraper.to_csv_file(str(path), {"fr": [{"id": "Q157", "first_paragraph": paragraph}]})

    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["first_paragraph"] == paragraph
    assert rows[0]["country"] == "fr"


def test_to_csv_file_handles_leaders_with_different_keys(tmp_path):
    scraper = WikipediaScraper(FakeSession(FakeResponse()))
    path = tmp_path / "leaders.csv"
    leaders = {"fr": [{"id": "Q1"}], "us": [{"id": "Q23", "place_of_birth": "Virginia"}]}

    scraper.to_csv_file(str(path), leaders)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "country,id,place_of_birth"
    #Missing key written as an empty field rather than raising
    assert lines[1] == "fr,Q1,"
