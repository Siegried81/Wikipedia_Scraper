"""
Tests for the main pipeline.
The API client and the session are replaced by doubles, so the orchestration
(one fetch per leader, a pause between fetches, the right writer) is checked
without a single HTTP request.
"""
import json
import main as main_module


class FakeAPI:
    """Stand-in for CountryLeadersAPI with two countries and two leaders."""

    def __init__(self, *args, **kwargs):
        pass

    def get_countries(self):
        return ["fr", "be"]

    def get_leaders(self, country):
        return [{"id": f"{country}-1", "wikipedia_url": f"https://x/{country}"}]


class FakeSession:
    """Context manager double: main() uses the session through a with block."""

    def get(self, url, **kwargs):
        raise AssertionError("main() must not reach the network in tests")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def patch_pipeline(monkeypatch, argv):
    """
    Wire main() to doubles and record the sleeps it performs.
    :param: pytest monkeypatch fixture
    :param: list of command line arguments
    Returns the list that collects the sleep durations.
    """
    sleeps = []
    monkeypatch.setattr(main_module, "CountryLeadersAPI", FakeAPI)
    monkeypatch.setattr(main_module, "build_session", lambda: FakeSession())
    monkeypatch.setattr(main_module.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(
        main_module.WikipediaScraper, "fetch_html", lambda self, url: "<p><b>X</b> y</p>"
    )
    monkeypatch.setattr("sys.argv", argv)
    return sleeps


def test_main_sleeps_between_every_fetch(monkeypatch, tmp_path):
    sleeps = patch_pipeline(monkeypatch, ["main.py"])
    monkeypatch.chdir(tmp_path)

    main_module.main()

    #Two leaders fetched, so two pauses, each the configured delay
    assert sleeps == [main_module.REQUEST_DELAY_SECONDS] * 2
    assert main_module.REQUEST_DELAY_SECONDS > 0


def test_main_writes_a_utf8_json_file_by_default(monkeypatch, tmp_path):
    patch_pipeline(monkeypatch, ["main.py"])
    monkeypatch.chdir(tmp_path)

    main_module.main()

    data = json.loads((tmp_path / "leaders.json").read_text(encoding="utf-8"))
    assert data["fr"][0]["first_paragraph"] == "X y"


def test_main_writes_a_real_csv_with_the_csv_flag(monkeypatch, tmp_path):
    patch_pipeline(monkeypatch, ["main.py", "--file", "csv"])
    monkeypatch.chdir(tmp_path)

    main_module.main()

    lines = (tmp_path / "leaders.csv").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "country,id,wikipedia_url,first_paragraph"
    assert len(lines) == 3
