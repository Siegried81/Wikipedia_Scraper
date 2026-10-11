import requests

from src.http_session import build_session


class ApiError(Exception):
    """The country-leaders API did not give a usable answer.

    Raised instead of returning an empty list, because an empty list is also a
    legitimate answer ("this country has no leaders on record"). When the two
    share a value, an outage of the API quietly produces an empty dataset that
    looks complete. The caller decides what to do with a failure; the client
    only makes sure it cannot be mistaken for data.
    """


class CountryLeadersAPI:
    '''
    Manages connections to the country leaders REST API: endpoints, the
    session cookie the API requires, and the retry when that cookie expires.

    Every call goes through one `requests.Session` built by `build_session()`:
    the API is on free hosting and cold-starts with 503s or timeouts, so the
    session retries transient failures with backoff and carries the project
    User-Agent. A session can be injected, which is how the tests run offline.
    '''

    def __init__(self, base_url="https://country-leaders.onrender.com", timeout=10, session=None):
        self.base_url = base_url
        self.country_endpoint = f"{base_url}/countries"
        self.leaders_endpoint = f"{base_url}/leaders"
        self.cookies_endpoint = f"{base_url}/cookie"
        self.timeout = timeout
        self.session = session if session is not None else build_session()
        self.cookies = None
        self.refresh_cookie()

    def refresh_cookie(self):
        '''
        Fetch a new cookie from the API. The cookie is the API's session
        token; it expires, and 401/403 on a data call is the signal to renew it.
        '''
        response = self.session.get(self.cookies_endpoint, timeout=self.timeout)
        # A cookie taken from an error page is not a cookie: the next data call
        # fails with 401 again and the retry below would spin on it.
        response.raise_for_status()
        self.cookies = response.cookies

    def _get_json(self, url, params=None, expected=list):
        '''
        One GET with the API's own failure modes handled in one place.

        401/403 means the cookie expired: renew it once and retry once. Any
        other non-2xx status, a body that is not JSON, or JSON of the wrong
        shape raises ApiError. A 500 whose body happened to be JSON used to be
        returned as if it were the data.
        '''
        try:
            response = self.session.get(url, params=params, cookies=self.cookies, timeout=self.timeout)
            if response.status_code in (401, 403):
                self.refresh_cookie()
                response = self.session.get(url, params=params, cookies=self.cookies, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ApiError(f"{url}: {exc}") from exc
        if not isinstance(payload, expected):
            raise ApiError(f"{url}: expected {expected.__name__}, got {type(payload).__name__}")
        return payload

    def get_countries(self):
        '''The country codes the API knows, as a list of strings.'''
        return self._get_json(self.country_endpoint)

    def get_leaders(self, country):
        '''The leaders of one country, as a list of dicts. Raises ApiError on failure.'''
        return self._get_json(self.leaders_endpoint, params={"country": country})


if __name__ == "__main__":
    # A manual smoke test against the live API, not part of the test suite.
    print("Testing CountryLeadersAPI...")
    client = CountryLeadersAPI()
    countries = client.get_countries()
    print(f"Countries found: {countries}")
    if countries:
        test_country = countries[0]
        leaders = client.get_leaders(test_country)
        print(f"Fetched {len(leaders)} leaders for {test_country}.")
        if leaders:
            print(f"First leader: {leaders[0].get('first_name')} {leaders[0].get('last_name')}")
