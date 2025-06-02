import json
import httpx
from rich.prompt import Prompt
import textwrap
import os
import argparse
from xdg_base_dirs import xdg_config_home
import configparser
import platform
import random
from dateutil.parser import parse
from babel.dates import format_date
from html2text import html2text
import pyperclip

from .console import InteractiveConsole as Console
from .__version__ import __version__

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
CATEGORIES = ""  # Default categories to search in
MAX_CONTENT_WORDS = 128  # Max words to show in content preview

SAFE_SEARCH_OPTIONS = {
    "none": 0,  # Unsafe search
    "moderate": 1,  # Moderate safe search
    "strict": 2,  # Strict safe search
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


def print_results(results, count, start_at=0, expand=False):
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
            if result.get("address"):
                address = result.get("address")
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
        engines = result.get("engines", None)
        engines.remove(engine) if engine in engines else None
        console.print(
            f"     [dim]\\[[bold]{engine}[/bold]{(', ' + ', '.join(engines)) if len(engines) > 0 else ''}][/dim]"
        )
        console.print()


def searxng_search(
    query,
    searxng_url,
    pageno=0,
    safe_search=None,
    categories=None,
    engines=None,
    language=None,
    time_range=None,
    site=None,
    verify_ssl=True,
    http_method="GET",
    no_user_agent=False,
    timeout=30.0,
):
    """
    Perform a search using a SearXNG instance

    Args:
        query: Search query string
        searxng_url: Base URL of SearXNG instance
        pageno: Page number (1-based)
        safe_search: Safe search level
        categories: Comma-separated categories
        engines: Comma-separated search engines
        language: Results language
        time_range: Time filter for results
        site: Site to restrict search to
        verify_ssl: Verify SSL certificates
        http_method: HTTP method (GET/POST)
        no_user_agent: Omit User-Agent header
        timeout: Request timeout in seconds

    Returns:
        List of search results or None on error
    """
    query = f"site:{site} {query}" if site else query
    url = None
    body = None

    # if http_method is POST, construct the body for the request
    if http_method == "POST":
        url = f"{searxng_url}/search"
        body = {
            "q": query,
            "format": "json",
        }
        if categories:
            body["categories"] = (
                categories.replace("social+media", "social media")
                if "social+media" in categories
                else categories
            )
        if engines:
            body["engines"] = engines
        if language:
            body["language"] = language
        if pageno > 1:
            body["pageno"] = pageno
        if safe_search:
            body["safesearch"] = SAFE_SEARCH_OPTIONS[safe_search]
        if time_range:
            body["time_range"] = time_range

        console.print(f"Searching: {url} with body: {body}") if DEBUG else None
    # if http_method is GET, construct the query url with parameters
    elif http_method == "GET":
        # construct the query url
        url = f"{searxng_url}/?q={query}&format=json"
        url += f"&categories={categories}" if categories else ""
        url += f"&engines={engines}" if engines else ""
        url += f"&language={language}" if language else ""
        url += f"&safesearch={SAFE_SEARCH_OPTIONS[safe_search]}" if safe_search else ""
        url += f"&time_range={time_range}" if time_range else ""
        url += f"&pageno={pageno}" if pageno > 1 else ""
        console.print(f"Searching: {url}") if DEBUG else None
    else:
        raise ValueError("Invalid http_method specified. Use 'GET' or 'POST'.")

    # remove non printable characters from the URL
    url = "".join(c for c in url if c.isprintable())

    try:
        response = None
        default_headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": USER_AGENT,
        }

        client = httpx.Client(verify=verify_ssl, timeout=httpx.Timeout(timeout))
        if no_user_agent:
            del client.headers["User-Agent"]
            del default_headers["User-Agent"]

        if http_method == "POST":
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }.update(default_headers)
            response = client.post(
                url, data=body, headers=headers, follow_redirects=True
            )
        else:
            headers = default_headers
            response = client.get(url, headers=headers, follow_redirects=True)

        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if data and "results" in data:
            console.print(f"Returned {len(data['results'])} results") if DEBUG else None
            return data["results"]
        else:
            return None

    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error:[/red]: {e}")
        exit(1)
    except httpx.ConnectError as ce:
        console.print(
            f"[red]Error:[/red] Could not connect to SearXNG instance at {searxng_url}\n{ce}"
        )
        exit(1)
    except httpx.TimeoutException as te:
        console.print(
            f"[red]Error:[/red] Request to SearXNG instance at {searxng_url} timed out after {timeout} seconds.\n{te}"
        )
        exit(1)
    except json.JSONDecodeError:
        console.print("[red]Error:[/red] Could not decode JSON response.")
        console.print(
            f"[dim]{response.text if response else 'No response received.'}[/dim]"
        )
        exit(1)


def create_config_file(config_path):

    if not os.path.isdir(config_path):
        os.makedirs(config_path)

    config_file = os.path.join(config_path, CONFIG_FILE)

    # request user to input the searxng instance url
    searxng_url = input(f"Enter your SearXNG instance URL [{SAMPLE_SEARXNG_URL}]: ")

    # construct the initial config file
    default_config = textwrap.dedent(
        f"""
        [searxngr]
        searxng_url = {searxng_url}
        # result_count = {RESULT_COUNT}
        # categories = {CATEGORIES}
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

    with open(config_file, "w") as f:
        f.write(default_config)

    console.print(f"[dim]created {config_file}[/dim]")


# Config helper functions with type-specific handling
def get_config_str(config, key, default):
    """Get string value from config with fallback"""
    return config["searxngr"][key] if key in config["searxngr"] else default


def get_config_int(config, key, default):
    """Get integer value from config with fallback"""
    return int(config["searxngr"][key]) if key in config["searxngr"] else default


def get_config_float(config, key, default):
    """Get float value from config with fallback"""
    return float(config["searxngr"][key]) if key in config["searxngr"] else default


def get_config_bool(config, key, default):
    """Get boolean value from config with fallback"""
    return config["searxngr"].getboolean(key) if key in config["searxngr"] else default


def main():
    """
    Main entry point for searxngr CLI

    Handles:
    - Configuration loading
    - Command-line argument parsing
    - Search execution
    - Interactive result navigation
    """
    # Load configuration from a file if it exists
    config_path = os.path.join(xdg_config_home(), "searxngr")
    config_file = os.path.join(config_path, CONFIG_FILE)

    if not os.path.exists(config_file):
        # first time setup, create new configuration file
        create_config_file(config_path)

    # read the settings frm the config file
    config = configparser.ConfigParser()
    config.read(config_file)
    if "searxngr" not in config:
        # config file content is missing, create new configuration file
        create_config_file(config_path)
        config.read(config_file)

    searxng_url = get_config_str(config, "searxng_url", None)
    result_count = get_config_int(config, "result_count", RESULT_COUNT)
    safe_search = get_config_str(config, "safe_search", SAFE_SEARCH)
    categories = get_config_str(config, "categories", CATEGORIES).strip().split(" ")
    engines = get_config_str(config, "engines", ENGINES)
    expand = get_config_bool(config, "expand", EXPAND)
    language = get_config_str(config, "language", None)
    url_handler = get_config_str(
        config, "url_handler", URL_HANDLER.get(platform.system())
    )
    debug = get_config_bool(config, "debug", False)
    http_methed = get_config_str(config, "http_method", HTTP_METHOD)
    http_timeout = get_config_float(config, "timeout", HTTP_TIMEOUT)
    no_user_agent = get_config_bool(config, "no_user_agent", False)
    no_verify_ssl = get_config_bool(config, "no_verify_ssl", False)
    no_color = get_config_bool(config, "no_color", False)

    # Command line argument definitions
    parser = argparse.ArgumentParser(description="Perform a search using SearXNG")
    parser.add_argument(
        "query", type=str, nargs="*", metavar="QUERY", help="search query"
    )
    parser.add_argument(
        "--searxng-url",
        type=str,
        default=searxng_url,
        metavar="SEARXNG_URL",
        help=f"SearXNG instance URL (default: {searxng_url if searxng_url else 'NOT SET'})",
    )
    parser.add_argument(
        "-c",
        "--categories",
        type=str,
        nargs="*",
        default=categories,
        metavar="CATEGORY",
        help=f"list of categories to search in: {', '.join(SEARXNG_CATEGORIES)} (default: {categories})",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="open the configuration file in a default system text editor",
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", default=debug, help="show debug output"
    )
    parser.add_argument(
        "-e",
        "--engines",
        type=str,
        nargs="*",
        default=engines,
        metavar="ENGINE",
        help=f"list of engines to use for the search (default: {engines if engines else 'all available engines'})",
    )
    parser.add_argument(
        "-x",
        "--expand",
        action="store_true",
        default=expand,
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
        default=http_methed,
        choices=["GET", "POST"],
        metavar="METHOD",
        help=f"HTTP method to use for search requests. GET or POST (default: {http_methed.upper()})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=http_timeout,
        metavar="SECONDS",
        help=f"HTTP request timeout in seconds (default: {http_timeout})",
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
        metavar="LANGUAGE",
        help="search results in a specific language (e.g., 'en', 'de', 'fr')"
        + (f" (default: {language})" if language else ""),
    )
    parser.add_argument(
        "--lucky",
        action="store_true",
        help="opens a random result in web browser and exit",
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        default=no_verify_ssl,
        help="do not verify SSL certificates of server  (not recommended)",
    )
    parser.add_argument(
        "--nocolor",
        action="store_true",
        default=no_color,
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
        default=no_user_agent,
        help="disable user agent",
    )
    parser.add_argument(
        "-n",
        "--num",
        type=int,
        default=result_count,
        metavar="N",
        help=f"show N results per page (default: {result_count}); N=0 uses the servers default per page",
    )
    parser.add_argument(
        "--safe-search",
        type=str,
        default=safe_search,
        metavar="FILTER",
        help=f"Filter results for safe search. Use 'none', 'moderate', or 'strict' (default: {safe_search})",
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
        "--url_handler",
        type=str,
        default=url_handler,
        metavar="UTIL",
        help=f"Command to open URLs in the browser (default: {url_handler})",
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

    query = " ".join(args.query) if args.query else None

    # if no color is requested, disable rich console color output
    global console
    if args.nocolor:
        console = Console(history=[query], color_system=None, force_terminal=True)
    else:
        console = Console(history=[query])

    global DEBUG
    DEBUG = args.debug
    console.print(f"Config: {args}") if DEBUG else None

    # validate that searxng url is set
    if not args.searxng_url:
        console.print(f"[red]Error:[/red] searxng_url is not set in {config_file}")
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
    # update engines to a comma-separated string if it's a list
    if isinstance(args.engines, list):
        args.engines = ",".join(args.engines).strip()
    else:
        args.engines = args.engines.strip().replace(" ", ",") if args.engines else None
    # update categories to a comma-separated string if it's a list
    if isinstance(args.categories, list):
        args.categories = (
            ",".join(args.categories)
            if isinstance(args.categories, list)
            else args.categories
        )
    # validate categories are supported
    if args.categories:
        categories = [c.strip() for c in args.categories.split(",")]
        # check if categories are valid
        for category in categories:
            if category not in SEARXNG_CATEGORIES:
                console.print(
                    f"[red]Error:[/red] Invalid category '{category}'. " + ""
                    f"Supported categories are: {', '.join(SEARXNG_CATEGORIES)}"
                )
                exit(1)
    # if news is requested, set categories to just 'news'
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
        editor = os.environ.get("EDITOR", DEFAULT_EDITOR[platform.system()])
        os.system(f"{editor} {config_file}")
        exit(0)
    # show version and exit
    if args.version:
        console.print(__version__)
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
            query_results = searxng_search(
                query,
                searxng_url=args.searxng_url,
                safe_search=args.safe_search,
                engines=args.engines,
                language=args.language,
                time_range=args.time_range,
                site=args.site,
                pageno=pageno,
                verify_ssl=not args.no_verify_ssl,
                http_method=args.http_method.upper(),
                no_user_agent=args.noua,
                categories=args.categories,
                timeout=args.timeout,
            )
            results.extend(query_results)
            # if no results found or number of results is not set just return all initial results
            if args.num == 0 or len(query_results) == 0:
                break
            pageno += 1

        if results:
            if args.json:
                # output the results in JSON format and exit
                print(json.dumps(results, indent=2))
                exit(0)

            if args.first:
                # if first or lucky search is requested, open the first result and exit
                url = results[0].get("url")
                if url:
                    # Use subprocess to avoid command injection
                    import subprocess
                    try:
                        subprocess.run([args.url_handler, url], check=True)
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
                    # Use subprocess to avoid command injection
                    import subprocess
                    try:
                        subprocess.run([args.url_handler, url], check=True)
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
                1, (len(results) if args.num == 0 else args.num) + 1
            ):
                # open the selected result in the browser
                index = int(new_query.strip()) - 1
                url = results[index].get("url")
                if url:
                    # Use subprocess to avoid command injection
                    import subprocess
                    try:
                        subprocess.run([args.url_handler, url], check=True)
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
