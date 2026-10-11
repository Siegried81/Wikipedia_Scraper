"""The API client against a mocked `requests.get`: no network, no cookie server.

What matters is the difference between "the API has nothing" and "the API is
down". Both used to come back as `[]`, so an outage produced an empty dataset
that looked complete.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api_client import ApiError, CountryLeadersAPI  # noqa: E402


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
    with patch("src.api_client.requests.get", side_effect=[_response()] + list(responses)) as get:
        client = CountryLeadersAPI("https://api.test")
        yield client, get


def test_a_server_error_is_an_error_not_an_empty_list():
    for client, _ in _client_with([_response(500, payload={"message": "boom"})]):
        with pytest.raises(ApiError):
            client.get_countries()


def test_an_expired_cookie_is_renewed_once_and_the_call_retried():
    for client, get in _client_with([
        _response(401, payload={"message": "cookie expired"}),  # first data call
        _response(200, payload={"user_cookie": "new"}),          # cookie refresh
        _response(200, payload=["be", "fr", "us"]),              # retried data call
    ]):
        assert client.get_countries() == ["be", "fr", "us"]
    assert get.call_count == 4  # constructor cookie + 401 + refresh + retry


def test_a_body_that_is_not_json_is_an_error():
    for client, _ in _client_with([_response(200, json_error=True)]):
        with pytest.raises(ApiError):
            client.get_leaders("be")


def test_the_wrong_shape_is_an_error_even_under_200():
    for client, _ in _client_with([_response(200, payload={"error": "unexpected"})]):
        with pytest.raises(ApiError, match="expected list"):
            client.get_countries()


def test_a_genuinely_empty_answer_is_still_an_empty_list():
    for client, _ in _client_with([_response(200, payload=[])]):
        assert client.get_leaders("xx") == []


def test_a_network_failure_is_an_error():
    for client, _ in _client_with([requests.ConnectionError("DNS failure")]):
        with pytest.raises(ApiError):
            client.get_countries()
