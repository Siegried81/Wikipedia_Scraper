import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# One descriptive User-Agent for every request this project sends.
# Wikipedia's robot policy asks for a tool name and a way to reach the operator,
# so the contact address is part of the string and not optional.
USER_AGENT = (
    "WikipediaScraperBot/1.0 (BeCode student project; "
    "contact: csiegried@yahoo.fr) python-requests"
)


def build_session() -> requests.Session:
    """
    Build a requests.Session that retries transient failures with backoff.
    :returns: a configured requests.Session
    Both the country-leaders API (free hosting, so it cold-starts and answers
    503 or times out on the first hit) and Wikipedia can fail once and work on
    the next try, so a single retrying session is shared instead of calling
    requests.get directly. It also keeps the connection and the User-Agent in
    one place for every call.
    """
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,                       # waits ~1s, 2s, 4s between tries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,                  # let the caller read the status code
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session
