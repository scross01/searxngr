import json
import httpx
from typing import List, Dict, Optional, Any, Union
from rich.prompt import Prompt
from rich.table import Table
import textwrap
import os
import argparse
from xdg_base_dirs import xdg_config_home
import configparser
import platform
import random
import shlex
import subprocess
from dateutil.parser import parse
from babel.dates import format_date
from html2text import html2text
import pyperclip

from .engines import extract_engines_from_preferences
from .console import InteractiveConsole as Console
from .__version__ import __version__

# Global debug flag
DEBUG = False

console = Console()

# Default settings. Use config file or command line to modify.
SAMPLE_SEARXNG_URL = "https://searxng.example.com"  # Example SearXNG instance URL
SEARXNG_URL = ""  # Will be populated from config file or CLI
RESULT_COUNT = 10  # Default number of results to show per page
SAFE_SEARCH = "strict"  # Default safe search setting
ENGINES = None  # Default to all available engines
EXPAND = False  # Default to not showing full URLs
CONFIG_FILE = "config.ini"  # Configuration filename
HTTP_METHOD = "GET"  # Default HTTP method for search requests
HTTP_TIMEOUT = 30.0  # Default HTTP request timeout
USER_AGENT = f"searxngr/{__version__}"  # User-Agent string
CATEGORIES = None  # Default categories to search in

MAX_CONTENT_WORDS = 128  # Max words to show in content preview
PREFERENCES_URL_PATH = "/preferences"

SAFE_SEARCH_OPTIONS = {
    "none": "0",  # Unsafe search
    "moderate": "1",  # Moderate safe search
    "strict": "2",  # Strict safe search
}

URL_HANDLER = {
    "Darwin": "open",  # Command to open URLs in the default browser on macOS
    "Linux": "xdg-open",  # Command to open URLs in the default browser on Linux
    "Windows": "explorer",  # Command to open URLs in the default browser on Windows
}

DEFAULT_EDITOR = {
    "Darwin": "open -t",
    "Linux": "xdg-open",
    "Windows": "notepad",
}

TIME_RANGE_OPTIONS = ["day", "week", "month", "year"]
TIME_RANGE_SHORT_OPTIONS = ["d", "w", "m", "y"]  # Short options for time range

SEARXNG_CATEGORIES = [
    "general",
    "news",
    "videos",
    "images",
    "music",
    "map",
    "science",
    "it",
    "files",
    "social+media",
]


def print_results(
    results: List[Dict[str, Any]], count: int, start_at: int = 0, expand: bool = False
) -> None:
    """
    Format and display search results in the terminal

    Args:
        results: List of search result objects
        count: Number of results to display per page
        start_at: Starting index for pagination
        expand: Whether to show full URLs
    """
    console.print()
    for i, result in enumerate(
        results[start_at:(start_at + count)], start=start_at + 1
    ):
        title = result.get("title", "No title")
        # truncate the title to 70 characters if it's too long
        title = textwrap.shorten(title, width=70, placeholder="...")

        # extract just the domain name from the URL
        url = result.get("url", "")
        domain = ""
        if url:
            parsed = url.split("//")
            if len(parsed) > 1:
                domain = parsed[1].split("/")[0]
            else:
                domain = parsed[0].split("/")[0]

        engine = result.get("engine", None)
        template = result.get("template", None)
        category = result.get("category", None)

        # wrap the content to the terminal width with indentation
        content = result.get("content", "")
        content_text = html2text(content).strip() if content else ""
        content_words = content_text.split(" ") if content_text else []
        content = None
        if len(content_words) > MAX_CONTENT_WORDS:
            content = " ".join(content_words[:MAX_CONTENT_WORDS]) + " ..."
        else:
            content = " ".join(content_words)
        content = textwrap.wrap(content, width=os.get_terminal_size().columns - 5)

        # parse the published date if available
        published_date = None
        if result.get("publishedDate"):
            try:
                date_str = result["publishedDate"].strip()
                if date_str:
                    parsed_date = parse(date_str)
                    published_date = format_date(parsed_date)
            except Exception as e:
                if DEBUG:
                    console.print(f"[dim]Error parsing date: {e}[/dim]")

        # output the result in a formatted way
        console.print(
            f" [cyan]{i:>2}.[/cyan] [bold green]{title}[/bold green] [yellow]\\[{domain}][/yellow]",
        )
        if expand:
            console.print(f"     [link={url}]{url}[/link]")
        if content:
            for line in content:
                console.print(f"     {line}", highlight=False)

        # if the result is a news article, output the published date
        if category == "news" and published_date:
            console.print(
                f"     [cyan dim]{published_date}[/cyan dim]", highlight=False
            )
        # if the result is an image, output additioanl image detials
        if category == "images":
            source = result.get("source")
            resolution = result.get("resolution")
            img_src = result.get("img_src")
            if source or resolution:
                console.print(
                    f"     [cyan dim]{resolution if resolution else ''}[/cyan dim] {source if source else ''}"
                )
            console.print(f"     [link={img_src}]{img_src}[/link]", highlight=False)
        # if the result is a video, output the author and length
        if category == "videos":
            author = result.get("author")
            length = result.get("length")
            if isinstance(length, float):
                # if length is not in HH:MM:SS format, convert it to that format
                length = f"{int(length // 60):02}:{int(length % 6):02}"
            if author or length:
                console.print(
                    f"     [cyan dim]{length if length else ''}[/cyan dim] {author if author else ''}"
                )
        # if the result is a music, output the published date
        if category == "music" and result.get("publishedDate"):
            author = result.get("author")
            length = result.get("length")
            if isinstance(length, float):
                # if length is not in HH:MM:SS format, convert it to that format
                length = f"{int(length // 60):02}:{int(length % 6):02}"
            if author or length:
                console.print(
                    f"     [cyan dim]{length if length else ''}[/cyan dim] {author if author else ''}"
                )
            # console.print(f"     [cyan dim]{published_date}[/cyan dim]")
        # if the result is a map, output the coordinates
        if category == "map":
            address = result.get("address")
            if address:
                house_number = address.get("house_number")
                road = address.get("road")
                locality = address.get("locality")
                postcode = address.get("postcode")
                country = address.get("country")
                console.print(
                    f"     {house_number + ' ' if house_number else ''}{road if road else ''}\n",
                    f"    {locality if locality else ''}, {postcode if postcode else ''}\n",
                    f"    {country if country else ''}",
                )
            longitude = result.get("longitude")
            latitude = result.get("latitude")
            console.print(f"     [cyan dim]{latitude}, {longitude}[/cyan dim]")
        # if the result is it category, we do not print anything specific
        if category == "it":
            pass
        # if the result is a science article, output the journal and publisher
        if category == "science":
            journal = result.get("journal")
            publisher = result.get("publisher")
            console.print(
                f"     [cyan dim][bold]{published_date + ' ' if published_date else ''}[/bold]"
                + f"{journal + ' ' if journal else ''}"
                + f"{publisher + ' ' if publisher else ''}[/cyan dim]",
                highlight=False,
            )
        # if the result is a file, output the magnet link or file properties
        if category == "files":
            if template == "torrent.html":
                magnet_link = result.get("magnetlink")
                seed = result.get("seed")
                leech = result.get("leech")
                filesize = result.get("filesize")
                console.print(f"     [dim]{magnet_link}[/dim]", highlight=False)
                console.print(
                    f"     [cyan dim]{filesize}[/cyan dim] ↑{seed} seeders, ↓{leech} leechers"
                )
            elif template == "files.html":
                metadata = result.get("metadata")
                size = result.get("size")
                console.print(f"     [cyan dim]{size} {metadata}[/cyan dim]")
        # if the result is a social media post, output the published date
        if category == "social media":
            if published_date:
                console.print(f"     [cyan dim]{published_date}[/cyan dim]")

        # print the engines that generated the result
        engines = result.get("engines", [])
        engines.remove(engine) if engine in engines else None
        console.print(
            f"     [dim]\\[[bold]{engine}[/bold]{(', ' + ', '.join(engines)) if len(engines) > 0 else ''}][/dim]"
        )
        console.print()


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
        """
        SearXNG client

        Args:
            url: Base URL of SearXNG instance
            username: Username for SearXNG instance (optional)
            password: Password for SearXNG instance (optional)
            verify_ssl: Verify SSL certificates
            no_user_agent: Omit User-Agent header
            timeout: Request timeout in seconds
        """
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
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response

        except httpx.HTTPStatusError as e:
            console.print(f"[red]Error:[/red]: {e}")
            exit(1)
        except httpx.ConnectError as ce:
            console.print(
                f"[red]Error:[/red] Could not connect to SearXNG instance at {self.url}{path}\n{ce}"
            )
            exit(1)
        except httpx.TimeoutException as te:
            console.print(
                f"[red]Error:[/red] Request to SearXNG instance at {self.url}{path} "
                f"timed out after {self.timeout} seconds.\n{te}"
            )
            exit(1)

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
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response

        except httpx.HTTPStatusError as e:
            console.print(f"[red]Error:[/red]: {e}")
            exit(1)
        except httpx.ConnectError as ce:
            console.print(
                f"[red]Error:[/red] Could not connect to SearXNG instance at {self.url}{path}\n{ce}"
            )
            exit(1)
        except httpx.TimeoutException as te:
            console.print(
                f"[red]Error:[/red] Request to SearXNG instance at {self.url}{path} "
                f"timed out after {self.timeout} seconds.\n{te}"
            )
            exit(1)

    def _fetch_preferences(self) -> str:
        """
        Get the content of the searxng instance preferences page

        Returns:
            HTML content for the preferneces page
        """

        headers = {"Accept": "application/html"}
        response = self.get(PREFERENCES_URL_PATH, headers)
        data = response.text
        return data

    def engines(self) -> List[Dict[str, Any]]:
        """
        Get the list of supported engines and !bang keywords
        """
        html = self._fetch_preferences()
        data = extract_engines_from_preferences(html)
        return data

    def categories(self) -> Dict[str, set]:
        """
        Get the list of supported categories and the !bang keywords
        """
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
        """
        Perform a search using a SearXNG instance

        Args:
            query: Search query string
            pageno: Page number (1-based)
            safe_search: Safe search level
            categories: List of categories
            engines: List of search engines
            language: Results language
            time_range: Time filter for results
            site: Site to restrict search to
            http_method: HTTP method (GET/POST)

        Returns:
            List of search results or None on error
        """
        query = f"site:{site} {query}" if site else query
        path = None
        body = None

        if engines and categories:
            console.print("Engines setting ignored when using categories")

        # if http_method is POST, construct the body for the request
        if http_method == "POST":
            path = "/search"
            body = {
                "q": query,
                "format": "json",
            }
            if categories:
                if "social+media" in categories:
                    # replace the list entry
                    for i in range(len(categories)):
                        if categories[i] == "social+media":
                            categories[i] = "social media"
                body["categories"] = ",".join(categories)
            if engines and not categories:
                # only use engines setting if categories if not set
                body["engines"] = ",".join(engines)
            if language:
                body["language"] = language
            if pageno > 1:
                body["pageno"] = str(pageno)
            if safe_search:
                body["safesearch"] = str(SAFE_SEARCH_OPTIONS[safe_search])
            if time_range:
                body["time_range"] = time_range

            console.print(f"Searching: {path} with body: {body}") if DEBUG else None
        # if http_method is GET, construct the query url with parameters
        elif http_method == "GET":
            # construct the query url
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
            console.print(f"Searching: {path}") if DEBUG else None
        else:
            raise ValueError("Invalid http_method specified. Use 'GET' or 'POST'.")

        # remove non printable characters from the URL
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
                (
                    console.print(f"Returned {len(data['results'])} results")
                    if DEBUG
                    else None
                )
                return data["results"]
            else:
                return []

        except json.JSONDecodeError:
            console.print("[red]Error:[/red] Could not decode JSON response.")
            console.print(
                f"[dim]{response.text if response else 'No response received.'}[/dim]"
            )
            exit(1)


class SearxngrConfig:

    def __init__(
        self, config_path: Optional[str] = None, config_file: Optional[str] = None
    ) -> None:
        # Load default configuration from a file if it exists
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = os.path.join(xdg_config_home(), "searxngr")

        if config_file:
            self.config_file = config_file
        else:
            self.config_file = os.path.join(self.config_path, CONFIG_FILE)

        if not os.path.exists(self.config_file):
            # first time setup, create new configuration file
            self.create_config_file()

        self.load_config()

    def create_config_file(self):

        if not os.path.isdir(self.config_path):
            os.makedirs(self.config_path)

        file = os.path.join(self.config_path, self.config_file)

        # request user to input the searxng instance url
        searxng_url = input(f"Enter your SearXNG instance URL [{SAMPLE_SEARXNG_URL}]: ")

        # construct the initial config file
        default_config = textwrap.dedent(
            f"""
            [searxngr]
            searxng_url = {searxng_url}
            # result_count = {RESULT_COUNT}
            # categories = general news social+media
            # safe_search = {SAFE_SEARCH}
            # engines = google duckduckgo brave
            # expand = false
            # language = en
            # http_method = {HTTP_METHOD}
            # timeout = {HTTP_TIMEOUT}
            # no_verify_ssl = false
            # no_user_agent = false
            # no_color = false
        """
        ).split("\n", 1)[1:][0]

        with open(file, "w") as f:
            f.write(default_config)

        console.print(f"[dim]created {file}[/dim]")

    # Config helper functions with type-specific handling
    def get_config_list(
        self, parser: configparser.ConfigParser, key: str, default: Optional[List[str]]
    ) -> Optional[List[str]]:
        """Get list of strings from config with fallback"""
        entry = parser["searxngr"][key] if key in parser["searxngr"] else default
        if isinstance(entry, str):
            if "," in entry:
                entry = entry.strip().split(",")
                entry = [e.strip() for e in entry]
            else:
                entry = entry.strip().split()
                entry = [e.strip() for e in entry]
        if entry == "" or entry == [] or entry == [""]:
            entry = None
        return entry

    def get_config_str(
        self, parser: configparser.ConfigParser, key: str, default: Optional[str]
    ) -> Optional[str]:
        """Get string value from config with fallback"""
        try:
            return parser["searxngr"][key] if key in parser["searxngr"] else default
        except ValueError as ve:
            print(
                f'[red]Error:[/red] unable to set value for "{key}", using default setting "{default}". [dim]{ve}[/dim]'
            )
            return default

    def get_config_int(
        self, parser: configparser.ConfigParser, key: str, default: int
    ) -> int:
        """Get integer value from config with fallback"""
        try:
            return (
                int(parser["searxngr"][key]) if key in parser["searxngr"] else default
            )
        except ValueError as ve:
            console.print(
                f'[red]Error:[/red] unable to set value for "{key}", using default setting "{default}". [dim]{ve}[/dim]'
            )
            return default

    def get_config_float(
        self, parser: configparser.ConfigParser, key: str, default: float
    ) -> float:
        """Get float value from config with fallback"""
        try:
            return (
                float(parser["searxngr"][key]) if key in parser["searxngr"] else default
            )
        except ValueError as ve:
            console.print(
                f'[red]Error:[/red] unable to set value for "{key}", using default setting "{default}". [dim]{ve}[/dim]'
            )
            return default

    def get_config_bool(
        self, parser: configparser.ConfigParser, key: str, default: bool
    ) -> bool:
        """Get boolean value from config with fallback"""
        try:
            result = (
                parser["searxngr"].getboolean(key)
                if key in parser["searxngr"]
                else default
            )
            return result if result else default
        except ValueError as ve:
            console.print(
                f'[red]Error:[/red] unable to set value for "{key}", using default setting "{default}". [dim]{ve}[/dim]'
            )
            return default

    @classmethod
    def validate_category(cls, category: str) -> bool:
        if category not in SEARXNG_CATEGORIES:
            console.print(
                f"[red]Error:[/red] Invalid category '{category}'. " + ""
                f"Supported categories are: {', '.join(SEARXNG_CATEGORIES)}"
            )
            return False
        return True

    def load_config(self) -> None:
        # read the settings from the config file
        parser = configparser.ConfigParser()
        parser.read(self.config_file)
        if "searxngr" not in parser:
            # config file content is missing, create new configuration file
            self.create_config_file()
            parser.read(self.config_file)

        self.searxng_url = self.get_config_str(parser, "searxng_url", None)
        self.searxng_username = self.get_config_str(parser, "searxng_username", None)
        self.searxng_password = self.get_config_str(parser, "searxng_password", None)
        self.result_count = self.get_config_int(parser, "result_count", RESULT_COUNT)
        self.safe_search = self.get_config_str(parser, "safe_search", SAFE_SEARCH)
        self.categories = self.get_config_list(parser, "categories", CATEGORIES)
        self.engines = self.get_config_list(parser, "engines", ENGINES)
        self.expand = self.get_config_bool(parser, "expand", EXPAND)
        self.language = self.get_config_str(parser, "language", None)
        self.url_handler = self.get_config_str(
            parser, "url_handler", URL_HANDLER.get(platform.system())
        )
        self.debug = self.get_config_bool(parser, "debug", False)
        self.http_methed = self.get_config_str(parser, "http_method", HTTP_METHOD)
        self.http_timeout = self.get_config_float(parser, "timeout", HTTP_TIMEOUT)
        self.no_user_agent = self.get_config_bool(parser, "no_user_agent", False)
        self.no_verify_ssl = self.get_config_bool(parser, "no_verify_ssl", False)
        self.no_color = self.get_config_bool(parser, "no_color", False)


def main() -> None:
    """
    Main entry point for searxngr CLI

    Handles:
    - Configuration loading
    - Command-line argument parsing
    - Search execution
    - Interactive result navigation
    """
    cfg = SearxngrConfig()

    # Command line argument definitions
    parser = argparse.ArgumentParser(description="Perform a search using SearXNG")
    parser.add_argument(
        "query", type=str, nargs="*", metavar="QUERY", help="search query"
    )
    parser.add_argument(
        "--searxng-url",
        type=str,
        default=cfg.searxng_url,
        metavar="SEARXNG_URL",
        help=f"SearXNG instance URL (default: {cfg.searxng_url if cfg.searxng_url else 'NOT SET'})",
    )
    parser.add_argument(
        "-c",
        "--categories",
        type=str,
        nargs="*",
        default=cfg.categories,
        metavar="CATEGORY",
        help=f"list of categories to search in: {', '.join(SEARXNG_CATEGORIES)} (default: {cfg.categories})",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="open the default configuration file using system text editor",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=cfg.debug,
        help="show debug output",
    )
    parser.add_argument(
        "-e",
        "--engines",
        type=str,
        nargs="*",
        default=cfg.engines,
        metavar="ENGINE",
        help="list of engines to use for the search "
        f"(default: {" ".join(cfg.engines) if cfg.engines else 'NOT SET'})",
    )
    parser.add_argument(
        "-x",
        "--expand",
        action="store_true",
        default=cfg.expand,
        help="Show complete url in search results",
    )
    parser.add_argument(
        "-j",
        "--first",
        action="store_true",
        help="open the first result in web browser and exit",
    )
    parser.add_argument(
        "--http-method",
        type=str,
        default=cfg.http_methed,
        choices=["GET", "POST"],
        metavar="METHOD",
        help="HTTP method to use for search requests. GET or POST "
        f"(default: {cfg.http_methed.upper() if cfg.http_methed else HTTP_METHOD})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=cfg.http_timeout,
        metavar="SECONDS",
        help=f"HTTP request timeout in seconds (default: {cfg.http_timeout})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="output the search results in JSON format and exit",
    )
    parser.add_argument(
        "-l",
        "--language",
        type=str,
        default=cfg.language,
        metavar="LANGUAGE",
        help="search results in a specific language (e.g., 'en', 'de', 'fr')"
        + (f" (default: {cfg.language})" if cfg.language else ""),
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="list available categories",
    )
    parser.add_argument(
        "--list-engines",
        action="store_true",
        help="list available engines",
    )
    parser.add_argument(
        "--lucky",
        action="store_true",
        help="opens a random result in web browser and exit",
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        default=cfg.no_verify_ssl,
        help="do not verify SSL certificates of server  (not recommended)",
    )
    parser.add_argument(
        "--nocolor",
        action="store_true",
        default=cfg.no_color,
        help="disable colored output",
    )
    parser.add_argument(
        "--np",
        "--noprompt",
        action="store_true",
        help="just search and exit, do not prompt",
    )
    parser.add_argument(
        "--noua",
        action="store_true",
        default=cfg.no_user_agent,
        help="disable user agent",
    )
    parser.add_argument(
        "-n",
        "--num",
        type=int,
        default=cfg.result_count,
        metavar="N",
        help=f"show N results per page (default: {cfg.result_count}); N=0 uses the servers default per page",
    )
    parser.add_argument(
        "--safe-search",
        type=str,
        default=cfg.safe_search,
        metavar="FILTER",
        help=f"Filter results for safe search. Use 'none', 'moderate', or 'strict' (default: {cfg.safe_search})",
    )
    parser.add_argument(
        "-w",
        "--site",
        type=str,
        metavar="SITE",
        help="search sites using site: operator",
    )
    parser.add_argument(
        "-t",
        "--time-range",
        type=str,
        metavar="TIME_RANGE",
        help=f"search results within a specific time range ({', '.join(TIME_RANGE_OPTIONS)})",
    )
    parser.add_argument(
        "--unsafe",
        action="store_true",
        help="allow unsafe search results (same as --safe-search none)",
    )
    parser.add_argument(
        "--url-handler",
        type=str,
        default=cfg.url_handler,
        metavar="UTIL",
        help=f"Command to open URLs in the browser (default: {cfg.url_handler})",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="show program's version number and exit",
    )
    parser.add_argument(
        "-F",
        "--files",
        action="store_true",
        help="show results from files section. (same as --categories files)",
    )
    parser.add_argument(
        "-M",
        "--music",
        action="store_true",
        help="show results from music section. (same as --categories music)",
    )
    parser.add_argument(
        "-N",
        "--news",
        action="store_true",
        help="show results from news section. (same as --categories news)",
    )
    parser.add_argument(
        "-S",
        "--social",
        action="store_true",
        help="show results from videos section. (same as --categories social+media)",
    )
    parser.add_argument(
        "-V",
        "--videos",
        action="store_true",
        help="show results from videos section. (same as --categories videos)",
    )

    args = parser.parse_args()

    query = " ".join(args.query) if args.query else ""

    # if no color is requested, disable rich console color output
    global console
    if args.nocolor:
        console = Console(history=[query], color_system=None, force_terminal=True)
    else:
        console = Console(history=[query])

    DEBUG = args.debug
    console.print(f"Config: {args}") if DEBUG else None

    # validate that searxng url is set
    if not args.searxng_url:
        console.print(f"[red]Error:[/red] searxng_url is not set in {cfg.config_file}")
        return
    # validate safe search is a valid value
    if args.safe_search and args.safe_search not in SAFE_SEARCH_OPTIONS:
        console.print(
            "[red]Error:[/red] Invalid safe search option. Use 'none', 'moderate', or 'strict'"
        )
        return
    # validate only one of --news or --videos is set
    if args.news and args.videos:
        console.print(
            "[red]Error:[/red] You can only use one of --news or --videos at a time."
        )
        exit(1)
    # validate time range format
    if args.time_range and args.time_range not in set(TIME_RANGE_OPTIONS).union(
        TIME_RANGE_SHORT_OPTIONS
    ):
        console.print(
            "[red]Error:[/red] Invalid time range format. Use 'd', 'day', 'w', 'week', 'm', 'month', or 'y', 'year'"
        )
        return
    # update time range option to the full keyword
    if args.time_range in TIME_RANGE_SHORT_OPTIONS:
        args.time_range = (
            args.time_range.replace("y", "year")
            .replace("m", "month")
            .replace("w", "week")
            .replace("d", "day")
        )
    # check categories and ensure result is a list
    if isinstance(args.categories, list):
        # check if all categories are valid
        for category in args.categories:
            if not cfg.validate_category(category):
                exit(1)
    elif isinstance(args.categories, str):
        # validate teh single category is supported
        if not cfg.validate_category(args.categories):
            exit(1)
        args.categories = [args.categories]
    # if files is requested, set categories to just 'files'
    if args.files:
        args.categories = ["files"]
    # if music is requested, set categories to just 'music'
    if args.music:
        args.categories = ["music"]
    # if news is requested, set categories to just 'news'
    if args.news:
        args.categories = ["news"]
    # if social is requested, set categories to just 'social+media'
    if args.social:
        args.categories = ["social+media"]
    # if videos is requested, set categories to just 'videos'
    if args.videos:
        args.categories = ["videos"]
    # override results count if first option is requested
    if args.first:
        args.num = 1
    # set safe-search to 'none' if unsafe option is set
    if args.unsafe:
        args.safe_search = "none"

    # open the configuration file and edit
    if args.config:
        console.print(f"opening {cfg.config_file}")
        editor = os.environ.get("EDITOR", DEFAULT_EDITOR[platform.system()])
        try:
            subprocess.run(shlex.split(editor) + [cfg.config_file], check=True)
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error opening editor:[/red] {e}")
        exit(0)
    # show version and exit
    if args.version:
        console.print(__version__)
        exit(0)

    searxng = SearXNGClient(
        url=args.searxng_url,
        username=cfg.searxng_username,
        password=cfg.searxng_password,
        verify_ssl=not args.no_verify_ssl,
        no_user_agent=args.noua,
        timeout=args.timeout,
    )

    # list the available engines and exit
    if args.list_engines:
        engines = searxng.engines()

        table = Table()
        table.add_column("Engine", style="cyan", no_wrap=True)
        table.add_column("URL")
        table.add_column("!bang", style="green", no_wrap=True)
        table.add_column("Categories")
        table.add_column("Reliability", justify="right")
        # table.add_column("Errors", style="red")

        for engine in engines:

            reliability = None
            if engine["reliability"]:
                r = int(engine["reliability"])
                if r == 0:
                    reliability = f"[red]{r}[/red]"
                elif r < 100:
                    reliability = f"[yellow]{r}[/yellow]"
                else:
                    reliability = f"[green]{r}[/green]"

            table.add_row(
                engine["name"]
                + (f' [red]({engine["errors"]})[red]' if engine["errors"] else ""),
                engine["url"],
                " ".join(engine["bangs"]),
                " ".join(engine["categories"]),
                reliability,
                # engine["errors"],
            )
        console.print(table)
        exit(0)
    # list the available engines and exit
    if args.list_categories:
        categories = searxng.categories()
        table = Table(leading=True)
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Engines")
        for category in categories.keys():
            c = list(categories[category])
            c.sort()
            table.add_row(category, ",".join(c))
        console.print(table)
        exit(0)

    # if no query is provided, show usage and exit
    if not args.query:
        parser.print_usage()
        exit(0)

    # Main processing loop handles:
    # - Pagination
    # - Result fetching
    # - Output formatting
    pageno = 1
    start_at = 0
    results = []

    while True:
        # searxng does not have a limit option, we will always get a varied number of
        # results per page.Interate until we have enough results.
        while len(results) <= (start_at + args.num):
            query_results = searxng.search(
                query,
                safe_search=args.safe_search,
                engines=args.engines,
                language=args.language,
                time_range=args.time_range,
                site=args.site,
                pageno=pageno,
                http_method=args.http_method.upper(),
                categories=args.categories,
            )
            results.extend(query_results)
            # if no results found or number of results is not set just return all initial results
            if args.num == 0 or len(query_results) == 0:
                break
            pageno += 1

        if args.json:
            print(json.dumps(results, indent=2))
            exit(0)

        if results:
            if args.first:
                # if first or lucky search is requested, open the first result and exit
                url = results[0].get("url")
                if url:
                    try:
                        command = shlex.split(args.url_handler)
                        command.append(url)
                        subprocess.run(command, check=True)
                    except subprocess.CalledProcessError as e:
                        console.print(f"[red]Error opening URL:[/red] {e}")
                else:
                    console.print("[red]Error:[/red] No URL found in result")
                exit(0)

            if args.lucky:
                # open a random result in the browser and exit
                result = random.choice(results)
                url = result.get("url")
                if url:
                    try:
                        subprocess.run(
                            shlex.split(args.url_handler) + [url], check=True
                        )
                    except subprocess.CalledProcessError as e:
                        console.print(f"[red]Error opening URL:[/red] {e}")
                else:
                    console.print(f"[red]Error:[/red] No URL found in result {result}")
                exit(0)

            # print the results
            print_results(
                results, count=args.num, start_at=start_at, expand=args.expand
            )
        else:
            # no results found or an error occurred
            console.print(
                "\nNo results found or an error occurred during the search.\n"
            )

        # if no prompt is requested, just exit after the search
        if args.np:
            exit(0)

        # Interactive command prompt supports:
        # n: Next page    p: Previous page    f: First page
        # [num]: Open result   c [num]: Copy URL   t [range]: Time filter
        # x: Toggle URLs   s: Show settings   d: Toggle debug   ?: Help
        while True:
            try:
                new_query = Prompt.ask(
                    "[bold]searxngr[/bold] [dim](? for help)[/dim] ", console=console
                )
            except KeyboardInterrupt:
                # Handle Ctrl+C gracefully
                exit(1)
            except EOFError:
                # Handle Ctrl+D gracefully
                exit(0)

            if new_query.strip().lower() in ["q", "quit", "exit"]:
                exit(0)
            elif new_query.strip() in ["?"]:
                console.print(
                    textwrap.dedent(
                        """
                        - Enter a search query to perform a new search.
                        - Type 'n', 'p', and 'f' to navigate to the next, previos and first page of results.
                        - Type the index (1, 2, 3, etc) open the search index page in a browser.
                        - Type 'c' plus the index ('c 1', 'c 2') to copy the result URL to clipboard.
                        - Type 't timerange' to change the search time range (e.g. `t week`).
                        - Type 'site:example.com' to filter results by a specific site.
                        - Type 'x' to toggle showing to result URL.
                        - Type 's' to show the current configuration settings.
                        - Type 'd' to toggle debug output.
                        - Type 'j' plus the index ('j 1', 'j 2') to show the JSON result for the specified index.
                        - Type 'q', 'quit', or 'exit' to exit the program.
                        - Type '?' for this help message.
                        """
                    )
                )
                continue
            elif new_query.strip().isdigit() and int(new_query.strip()) in range(
                1, (len(results)) + 1
            ):
                # open the selected result in the browser
                index = int(new_query.strip()) - 1
                url = results[index].get("url")
                if url:
                    try:
                        subprocess.run(
                            shlex.split(args.url_handler) + [url], check=True
                        )
                    except subprocess.CalledProcessError as e:
                        console.print(f"[red]Error opening URL:[/red] {e}")
                else:
                    console.print(
                        "[red]Error:[/red] No URL found for the selected result."
                    )
                continue
            elif new_query.strip().startswith("c "):
                # copy the result URL to clipboard
                index = new_query[2:].strip()
                if index.isdigit() and int(index) in range(1, len(results) + 1):
                    url = results[int(index) - 1].get("url")
                    if url:
                        pyperclip.copy(url)
                    else:
                        console.print(
                            "[red]Error:[/red] No URL found for the selected result."
                        )
                else:
                    console.print("[red]Error:[/red] Invalid index specified.")
                continue
            # n: Next page
            elif new_query.strip() == "n":
                # get the next page of results, query if we don't have enough results
                start_at += args.num
                if len(results) >= (start_at + args.num):
                    # we already have enough results for the next page
                    print_results(
                        results, count=args.num, start_at=start_at, expand=args.expand
                    )
                    continue
                else:
                    new_query = query
                    pageno += 1
                    break
            # p: Previous page
            elif new_query.strip() == "p":
                # show the previous page of results
                start_at -= args.num if start_at >= args.num else 0
                print_results(
                    results, count=args.num, start_at=start_at, expand=args.expand
                )
                continue
            # f: First page
            elif new_query.strip() == "f":
                # go back to the first page of results
                start_at = 0
                print_results(
                    results, count=args.num, start_at=start_at, expand=args.expand
                )
                continue
            # t: Change time range filter
            elif new_query.strip().startswith("t "):
                # change the time range filter
                time_range = new_query[2:].strip()
                if (
                    time_range not in TIME_RANGE_OPTIONS
                    and time_range not in TIME_RANGE_SHORT_OPTIONS
                ):
                    console.print(
                        f"[red]Error:[/red] Invalid time range '{time_range}'. "
                        f"Use one of: {', '.join(TIME_RANGE_OPTIONS)}"
                    )
                    continue
                else:
                    if time_range in TIME_RANGE_SHORT_OPTIONS:
                        args.time_range = (
                            time_range.replace("y", "year")
                            .replace("m", "month")
                            .replace("w", "week")
                            .replace("d", "day")
                        )
                    else:
                        args.time_range = time_range
                    new_query = query
                    start_at = 0
                    pageno = 1
                    results = []
                    break
            # site: Change site filter
            elif new_query.strip().startswith("site:"):
                # etranct the new site filter and re-query
                site = new_query[5:].strip()
                args.site = site
                new_query = query
                start_at = 0
                pageno = 1
                results = []
                break
            # x: Toggle expand URLs
            elif new_query.strip() == "x":
                # toggle the expand URL setting and re-show results
                args.expand = not args.expand
                print_results(
                    results, count=args.num, start_at=start_at, expand=args.expand
                )
                continue
            # s: Show current configuration settings
            elif new_query.strip() == "s":
                # format the current configuration settings
                console.print(
                    textwrap.dedent(
                        f"""
                        SearXNG URL:       {args.searxng_url}
                        HTTP method:       {args.http_method}
                        Timeout:           {args.timeout}
                        Verify SSL:        {'enabled' if not args.no_verify_ssl else 'disabled'}
                        Result per page:   {args.num if args.num > 0 else '[dim]default[/dim]'}
                        Engines:           {args.engines if args.engines else '[dim]not set[/dim]'}
                        Categories:        {args.categories if args.categories else '[dim]not set[/dim]'}
                        Language:          {args.language if args.language else '[dim]not set[/dim]'}
                        Safe search:       {args.safe_search}
                        Site filter:       {args.site if args.site else '[dim]not set[/dim]'}
                        Time range filter: {args.time_range if args.time_range else '[dim]not set[/dim]'}
                        Expand URLs:       {'enabled' if args.expand else '[dim]disabled[/dim]'}
                        """
                    )
                )
                continue
            # d: Toggle debug mode
            elif new_query.strip() == "d":
                # toggle debug mode on or off
                DEBUG = not DEBUG
                console.print(f"Debug mode {'enabled' if DEBUG else 'disabled'}")
                continue
            # j: Show JSON result for a specific index
            elif new_query.strip().startswith("j "):
                # pretty prin the raw json for the specified index
                index = new_query[2:].strip()
                if index.isdigit() and int(index) in range(1, len(results) + 1):
                    index = int(index) - 1
                    console.print(
                        json.dumps(results[index], indent=2, ensure_ascii=False)
                    )
                continue
            # If the input is not recognized and not empty, treat it as a new query
            elif new_query.strip() != "":
                # run the new query
                query = new_query.strip()
                start_at = 0
                pageno = 1
                results = []
                break


if __name__ == "__main__":
    main()
