import json

import httpx
from typing import List, Dict, Any, Optional, Union

from .constants import (
    USER_AGENT,
    SAFE_SEARCH_OPTIONS,
    PREFERENCES_URL_PATH,
    console,
)
from .engines import extract_engines_from_preferences


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


class SearXNGClient:
    def __init__(
        self,
        url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: bool = True,
        no_user_agent: Optional[bool] = None,
        timeout: Union[int, float] = 30,
    ) -> None:
        self.url = url
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

    def get(
        self, path: str, headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        try:
            if headers is None:
                headers = {}
            headers.update(self.default_headers)
            response = self.client.get(
                f"{self.url}{path}", headers=headers, follow_redirects=True
            )
            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            raise SearXNGHTTPError(str(e)) from e
        except httpx.ConnectError as ce:
            raise SearXNGConnectionError(
                f"Could not connect to SearXNG instance at {self.url}{path}"
            ) from ce
        except httpx.TimeoutException as te:
            raise SearXNGTimeoutError(
                f"Request to SearXNG instance at {self.url}{path} "
                f"timed out after {self.timeout} seconds."
            ) from te

    def post(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        try:
            if headers is None:
                headers = {}
            headers.update(self.default_headers)
            response = self.client.post(
                f"{self.url}{path}", data=data, headers=headers, follow_redirects=True
            )
            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            raise SearXNGHTTPError(str(e)) from e
        except httpx.ConnectError as ce:
            raise SearXNGConnectionError(
                f"Could not connect to SearXNG instance at {self.url}{path}"
            ) from ce
        except httpx.TimeoutException as te:
            raise SearXNGTimeoutError(
                f"Request to SearXNG instance at {self.url}{path} "
                f"timed out after {self.timeout} seconds."
            ) from te

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
        query = f"site:{site} {query}" if site else query
        path = None
        body = None

        if engines and categories:
            console.print("Engines setting ignored when using categories")

        if http_method == "POST":
            path = "/search"
            body = {
                "q": query,
                "format": "json",
            }
            if categories:
                if "social+media" in categories:
                    for i in range(len(categories)):
                        if categories[i] == "social+media":
                            categories[i] = "social media"
                body["categories"] = ",".join(categories)
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

        elif http_method == "GET":
            path = f"/search?q={query}&format=json"
            path += f"&categories={','.join(categories)}" if categories else ""
            path += (
                f"&engines={','.join(engines)}" if engines and not categories else ""
            )
            path += f"&language={language}" if language else ""
            path += (
                f"&safesearch={SAFE_SEARCH_OPTIONS[safe_search]}" if safe_search else ""
            )
            path += f"&time_range={time_range}" if time_range else ""
            path += f"&pageno={pageno}" if pageno > 1 else ""
        else:
            raise ValueError("Invalid http_method specified. Use 'GET' or 'POST'.")

        path = "".join(c for c in path if c.isprintable())

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
                data
                and "unresponsive_engines" in data
                and len(data["unresponsive_engines"]) > 0
            ):
                unique_list = [
                    list(item)
                    for item in {
                        tuple(sublist) for sublist in data["unresponsive_engines"]
                    }
                ]
                for engine, error in unique_list:
                    console.print(f"Engine: {engine} [red]{error}[/red]")

            if data and "results" in data:
                return data["results"]
            else:
                return []

        except json.JSONDecodeError as e:
            raise SearXNGJSONError(f"Could not decode JSON response: {e}") from e
        except SearXNGError:
            raise
