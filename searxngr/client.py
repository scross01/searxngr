import json
import time
from urllib.parse import urlencode

import httpx
from rich.console import Console
from typing import List, Dict, Any, Optional, Union

from .constants import (
    USER_AGENT,
    SAFE_SEARCH_OPTIONS,
    PREFERENCES_URL_PATH,
)
from .engines import extract_engines_from_preferences

# Diagnostics must not corrupt machine-readable JSON on stdout.
error_console = Console(stderr=True)


class SearXNGError(Exception):
    """Base exception for SearXNG client errors"""

    pass


class SearXNGConnectionError(SearXNGError):
    """Connection error to SearXNG instance"""

    pass


class SearXNGTimeoutError(SearXNGError):
    """Timeout error when connecting to SearXNG instance"""

    pass


class SearXNGHTTPError(SearXNGError):
    """HTTP error response from SearXNG instance"""

    pass


class SearXNGJSONError(SearXNGError):
    """JSON decode error from SearXNG response"""

    pass


class SearXNGEngineError(SearXNGError):
    """No results were returned and one or more engines failed."""


class SearXNGClient:
    def __init__(
        self,
        url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: bool = True,
        no_user_agent: Optional[bool] = None,
        timeout: Union[int, float] = 30,
        retries: int = 2,
        fallback_engines: Optional[List[str]] = None,
    ) -> None:
        if not isinstance(retries, int) or not 0 <= retries <= 5:
            raise ValueError("retries must be an integer between 0 and 5")
        self.retries = retries
        self.fallback_engines = list(fallback_engines or [])
        self._fallback_search_key = None
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.no_user_agent = no_user_agent
        self.timeout = timeout
        self.default_headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": USER_AGENT,
        }

        if username and password:
            auth = httpx.BasicAuth(username, password)
            self.client = httpx.Client(
                verify=verify_ssl,
                timeout=httpx.Timeout(timeout),
                auth=auth,
            )
        else:
            self.client = httpx.Client(
                verify=verify_ssl, timeout=httpx.Timeout(timeout)
            )

        if no_user_agent:
            del self.client.headers["User-Agent"]
            del self.default_headers["User-Agent"]

    def _request(
        self, method: str, path: str, headers: Optional[Dict[str, str]] = None, **kwargs
    ) -> httpx.Response:
        headers = {**self.default_headers, **(headers or {})}
        for attempt in range(self.retries + 1):
            try:
                response = getattr(self.client, method)(
                    f"{self.url}{path}",
                    headers=headers,
                    follow_redirects=True,
                    **kwargs,
                )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in (500, 502, 503, 504):
                    raise SearXNGHTTPError(str(exc)) from exc
                error = SearXNGHTTPError(str(exc))
                cause = exc
            except httpx.TimeoutException as exc:
                error = SearXNGTimeoutError(
                    f"Request to {self.url} timed out (timeout: {self.timeout}s)."
                )
                cause = exc
            except httpx.TransportError as exc:
                error = SearXNGConnectionError(f"Request to {self.url} failed: {exc}")
                cause = exc
            except httpx.RequestError as exc:
                raise SearXNGConnectionError(str(exc)) from exc

            if attempt == self.retries:
                raise error from cause
            delay = min(0.25 * 2**attempt, 2.0)
            error_console.print(
                f"Transient request failure; retry {attempt + 1}/{self.retries} "
                f"in {delay:g}s.",
                markup=False,
            )
            time.sleep(delay)

    def get(
        self, path: str, headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        return self._request("get", path, headers)

    def post(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        return self._request("post", path, headers, data=data)

    def _fetch_preferences(self) -> str:
        headers = {"Accept": "application/html"}
        response = self.get(PREFERENCES_URL_PATH, headers)
        data = response.text
        return data

    def engines(self) -> List[Dict[str, Any]]:
        html = self._fetch_preferences()
        data = extract_engines_from_preferences(html)
        return data

    def categories(self) -> Dict[str, set]:
        html = self._fetch_preferences()
        data = extract_engines_from_preferences(html)
        unique_categories = dict()
        for engine in data:
            for category in engine["categories"]:
                if category not in unique_categories.keys():
                    unique_categories[category] = set()
                if engine["name"] not in unique_categories[category]:
                    unique_categories[category].add(engine["name"])

        sorted_categories = dict(sorted(unique_categories.items()))
        return sorted_categories

    def search(
        self,
        query: str,
        pageno: int = 0,
        safe_search: Optional[str] = None,
        categories: Optional[List[str]] = None,
        engines: Optional[List[str]] = None,
        language: Optional[str] = None,
        time_range: Optional[str] = None,
        site: Optional[str] = None,
        http_method: str = "GET",
    ) -> List[Dict[str, Any]]:
        if http_method not in ("GET", "POST"):
            raise ValueError("Invalid http_method specified. Use 'GET' or 'POST'.")
        if engines and categories:
            error_console.print("Engines setting ignored when using categories")

        body = {"q": f"site:{site} {query}" if site else query, "format": "json"}
        if categories:
            body["categories"] = ",".join(
                "social media" if c == "social+media" else c for c in categories
            )
        if engines and not categories:
            body["engines"] = ",".join(engines)
        if language:
            body["language"] = language
        if pageno > 1:
            body["pageno"] = str(pageno)
        if safe_search:
            body["safesearch"] = str(SAFE_SEARCH_OPTIONS[safe_search])
        if time_range:
            body["time_range"] = time_range

        search_key = (
            http_method,
            tuple((k, v) for k, v in body.items() if k != "pageno"),
        )
        if pageno <= 1:
            self._fallback_search_key = None
        elif self._fallback_search_key == search_key:
            body["engines"] = ",".join(self.fallback_engines)
        try:
            return self._search_once(body, http_method)
        except SearXNGEngineError:
            # Never override explicit engine/category/bang selection or switch
            # engines halfway through pagination. Only one backup batch is tried.
            if (
                not self.fallback_engines
                or engines
                or categories
                or pageno > 1
                or "!" in query
            ):
                raise
            error_console.print(
                "Default engines failed; trying configured backup engines: "
                + ", ".join(self.fallback_engines),
                markup=False,
            )
            body["engines"] = ",".join(self.fallback_engines)
            results = self._search_once(body, http_method)
            if not results:
                raise
            self._fallback_search_key = search_key
            return results

    def _search_once(
        self, body: Dict[str, str], http_method: str
    ) -> List[Dict[str, Any]]:
        path = "/search"
        if http_method == "GET":
            path += "?" + urlencode(body)

        try:
            response = None

            if http_method == "POST":
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                response = self.post(path, data=body, headers=headers)
            else:
                response = self.get(path)

            data = response.json()
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("results"), list)
                or any(not isinstance(r, dict) for r in data["results"])
            ):
                raise SearXNGJSONError(
                    "Invalid SearXNG response: expected a list of result objects"
                )
            failures = data.get("unresponsive_engines", [])
            if not isinstance(failures, list) or any(
                not isinstance(f, (list, tuple))
                or len(f) != 2
                or not all(isinstance(v, str) for v in f)
                for f in failures
            ):
                raise SearXNGJSONError("Invalid SearXNG engine diagnostics")
            for engine, error in sorted({tuple(f) for f in failures}):
                error_console.print(f"Engine: {engine} {error}", markup=False)

            if not data["results"] and failures:
                raise SearXNGEngineError(
                    "No results returned and search engines failed. "
                    "Try another engine with -e or retry after its cooldown."
                )
            return data["results"]

        except json.JSONDecodeError as e:
            raise SearXNGJSONError(f"Could not decode JSON response: {e}") from e
