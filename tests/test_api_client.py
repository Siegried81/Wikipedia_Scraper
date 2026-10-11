"""The API client and the shared session, with no network and no cookie server.

What matters is the difference between "the API has nothing" and "the API is
down". Both used to come back as `[]`, so an outage produced an empty dataset
that looked complete. A fake session is injected into the client, the way the
client now makes every call, so nothing leaves the machine.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api_client import ApiError, CountryLeadersAPI  # noqa: E402
from src.http_session import USER_AGENT, build_session  # noqa: E402


def _response(status=200, payload=None, json_error=False):
    response = MagicMock()
    response.status_code = status
    response.cookies = {"user_cookie": "abc"}
    if json_error:
        response.json.side_effect = ValueError("not JSON")
    else:
        response.json.return_value = payload
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status}")
    else:
        response.raise_for_status.return_value = None
    return response


def _client_with(responses):
    """A client whose constructor cookie call and later calls replay `responses`."""
    session = MagicMock()
    session.get.side_effect = [_response()] + list(responses)
    return CountryLeadersAPI("https://api.test", session=session), session


def test_a_server_error_is_an_error_not_an_empty_list():
    client, _ = _client_with([_response(500, payload={"message": "boom"})])
    with pytest.raises(ApiError):
        client.get_countries()


def test_an_expired_cookie_is_renewed_once_and_the_call_retried():
    client, session = _client_with([
        _response(401, payload={"message": "cookie expired"}),  # first data call
        _response(200, payload={"user_cookie": "new"}),          # cookie refresh
        _response(200, payload=["be", "fr", "us"]),              # retried data call
    ])
    assert client.get_countries() == ["be", "fr", "us"]
    assert session.get.call_count == 4  # constructor cookie + 401 + refresh + retry


def test_a_body_that_is_not_json_is_an_error():
    client, _ = _client_with([_response(200, json_error=True)])
    with pytest.raises(ApiError):
        client.get_leaders("be")


def test_the_wrong_shape_is_an_error_even_under_200():
    client, _ = _client_with([_response(200, payload={"error": "unexpected"})])
    with pytest.raises(ApiError, match="expected list"):
        client.get_countries()


def test_a_genuinely_empty_answer_is_still_an_empty_list():
    client, _ = _client_with([_response(200, payload=[])])
    assert client.get_leaders("xx") == []


def test_a_network_failure_is_an_error():
    client, _ = _client_with([requests.ConnectionError("DNS failure")])
    with pytest.raises(ApiError):
        client.get_countries()


def test_a_cookie_from_an_error_page_is_refused():
    session = MagicMock()
    session.get.side_effect = [_response(503)]
    with pytest.raises(requests.HTTPError):
        CountryLeadersAPI("https://api.test", session=session)


def test_get_leaders_passes_the_country_as_a_query_param():
    client, session = _client_with([_response(200, payload=[{"id": "Q157"}])])
    assert client.get_leaders("fr") == [{"id": "Q157"}]
    assert session.get.call_args.kwargs["params"] == {"country": "fr"}


def test_build_session_identifies_the_project():
    session = build_session()
    assert session.headers["User-Agent"] == USER_AGENT
    assert "github.com/Siegried81/Wikipedia_Scraper" in USER_AGENT


@pytest.mark.parametrize("scheme", ["https://", "http://"])
def test_build_session_mounts_a_retrying_adapter(scheme):
    retries = build_session().get_adapter(f"{scheme}example.org").max_retries
    assert retries.total == 3
    assert retries.backoff_factor == 1
    assert 503 in retries.status_forcelist
