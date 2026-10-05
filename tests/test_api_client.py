"""
Tests for CountryLeadersAPI and the shared session factory.
A fake session is injected into the client, so no HTTP request leaves the
machine and the cookie/status logic can be checked without the hosted API.
"""
import pytest
from src.api_client import CountryLeadersAPI
from src.http_session import USER_AGENT, build_session


class FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, status_code=200, payload=None, cookies="cookie-jar"):
        self.status_code = status_code
        self.payload = payload
        self.cookies = cookies

    def json(self):
        return self.payload


class FakeSession:
    """
    Session double returning a scripted response per endpoint path.
    :param: dict of url fragment -> list of responses to serve in order
    """

    def __init__(self, script):
        self.script = script
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        for fragment, responses in self.script.items():
            if url.endswith(fragment):
                return responses.pop(0) if len(responses) > 1 else responses[0]
        raise AssertionError(f"Unexpected url: {url}")


def make_client(script):
    """Build a client wired to a FakeSession, returning both."""
    session = FakeSession(script)
    return CountryLeadersAPI(session=session), session


def test_refresh_cookie_stores_cookies_on_success():
    client, _ = make_client({"/cookie": [FakeResponse(200, cookies="good")]})

    assert client.cookies == "good"


def test_refresh_cookie_ignores_cookies_on_error_status():
    """A 503 cold-start answer carries no valid token, so it must not be kept."""
    client, _ = make_client({"/cookie": [FakeResponse(503, cookies="error-page")]})

    assert client.cookies is None


def test_refresh_cookie_survives_a_network_error():
    class ExplodingSession:
        def get(self, url, **kwargs):
            raise ConnectionError("boom")

    client = CountryLeadersAPI(session=ExplodingSession())

    assert client.cookies is None


def test_get_countries_returns_the_payload():
    client, session = make_client({
        "/cookie": [FakeResponse(200)],
        "/countries": [FakeResponse(200, ["fr", "be"])],
    })

    assert client.get_countries() == ["fr", "be"]
    #Cookie call plus one countries call, nothing more
    assert len(session.calls) == 2


def test_get_countries_refreshes_the_cookie_once_on_401():
    client, session = make_client({
        "/cookie": [FakeResponse(200, cookies="first"), FakeResponse(200, cookies="second")],
        "/countries": [FakeResponse(401), FakeResponse(200, ["fr"])],
    })

    assert client.get_countries() == ["fr"]
    assert client.cookies == "second"


def test_get_countries_returns_empty_list_on_network_error():
    class ExplodingSession:
        def __init__(self):
            self.first = True

        def get(self, url, **kwargs):
            if self.first and url.endswith("/cookie"):
                self.first = False
                return FakeResponse(200)
            raise ConnectionError("boom")

    client = CountryLeadersAPI(session=ExplodingSession())

    assert client.get_countries() == []


def test_get_leaders_passes_the_country_as_a_query_param():
    client, session = make_client({
        "/cookie": [FakeResponse(200)],
        "/leaders": [FakeResponse(200, [{"id": "Q157"}])],
    })

    assert client.get_leaders("fr") == [{"id": "Q157"}]
    assert session.calls[-1][1]["params"] == {"country": "fr"}


def test_get_leaders_returns_empty_list_on_network_error():
    class ExplodingSession:
        def __init__(self):
            self.first = True

        def get(self, url, **kwargs):
            if self.first and url.endswith("/cookie"):
                self.first = False
                return FakeResponse(200)
            raise ConnectionError("boom")

    client = CountryLeadersAPI(session=ExplodingSession())

    assert client.get_leaders("fr") == []


def test_build_session_has_user_agent_with_contact():
    session = build_session()

    assert session.headers["User-Agent"] == USER_AGENT
    assert "contact:" in USER_AGENT


@pytest.mark.parametrize("scheme", ["https://", "http://"])
def test_build_session_mounts_a_retrying_adapter(scheme):
    session = build_session()

    retries = session.get_adapter(f"{scheme}example.org").max_retries

    assert retries.total == 3
    assert retries.backoff_factor == 1
    assert 503 in retries.status_forcelist
