import json
import httpx
from rich import print
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

from .__version__ import __version__

# Default settings. Use config file or command line to modify.
SAMPLE_SEARXNG_URL = "https://searxng.example.com"  # Example SearXNG instance URL
SEARXNG_URL = ""
RESULT_COUNT = 10  # Default number of results to show per page
SAFE_SEARCH = "strict"  # Default safe search setting
ENGINES = None  # Default to all default engines
EXPAND = False  # Default show expand url setting
CONFIG_FILE = "config.ini"
HTTP_METHOD = "GET"  # Default HTTP method for search requests
USER_AGENT = f"searxngr/{__version__}"
CATEGORIES = "general"  # Default categories to search in
MAX_CONTENT_WORDS = 128  # Maximum number of words to show in content

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


# print search results to the terminal
def print_results(results, count, expand=False):
    print()
    for i, result in enumerate(results[0:count], start=1):

        # print(f"Result {json.dumps(result, indent=2)}") if DEBUG else None  # XXX

        title = result.get("title", "No title")
        # truncate the title to 70 characters if it's too long
        title = textwrap.shorten(title, width=70, placeholder="...")

        # extract just the domain name from the URL
        url = result.get("url", None)
        domain = url.split("//")[1].split("/")[0]

        engine = result.get("engine", None)
        template = result.get("template", None)
        category = result.get("category", None)

        # wrap the content to the terminal width with indentation
        content_words = html2text(result.get("content", None).strip()).split(" ")
        content = None
        if len(content_words) > MAX_CONTENT_WORDS:
            content = " ".join(content_words[:MAX_CONTENT_WORDS]) + " ..."
        else:
            content = " ".join(content_words)
        content = textwrap.wrap(content, width=os.get_terminal_size().columns - 5)

        published_date = (
            format_date(parse(result.get("publishedDate").strip()))
            if result.get("publishedDate")
            else None
        )

        print(
            f" [cyan]{i:>2}.[/cyan] [bold green]{title}[/bold green] [yellow]\\[{domain}][/yellow]"
        )
        if expand:
            print(f"     [link={url}]{url}[/link]")
        if content:
            for line in content:
                print(f"     {line}")

        # if the result is a news article, output the published date
        if category == "news" and published_date:
            print(f"     [cyan dim]{published_date}[/cyan dim]")
        # if the result is an image, output additioanl image detials
        if category == "images":
            source = result.get("source")
            resolution = result.get("resolution")
            img_src = result.get("img_src")
            if source or resolution:
                print(
                    f"     [cyan dim]{resolution if resolution else ''}[/cyan dim] {source if source else ''}"
                )
            print(f"     [link={img_src}]{img_src}[/link]")
        # if the result is a video, output the author and length
        if category == "videos":
            author = result.get("author")
            length = result.get("length")
            if isinstance(length, float):
                # if length is not in HH:MM:SS format, convert it to that format
                length = f"{int(length // 60):02}:{int(length % 6):02}"
            if author or length:
                print(
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
                print(
                    f"     [cyan dim]{length if length else ''}[/cyan dim] {author if author else ''}"
                )
            # published_date = format_date(parse(result.get("publishedDate")))
            # print(f"     [cyan dim]{published_date}[/cyan dim]")
        # if the result is a map, output the coordinates
        if category == "map":
            if result.get("address"):
                address = result.get("address")
                house_number = address.get("house_number")
                road = address.get("road")
                locality = address.get("locality")
                postcode = address.get("postcode")
                country = address.get("country")
                print(
                    f"     {house_number + ' ' if house_number else ''}{road if road else ''}\n",
                    f"    {locality if locality else ''}, {postcode if postcode else ''}\n",
                    f"    {country if country else ''}",
                )
            longitude = result.get("longitude")
            latitude = result.get("latitude")
            print(f"     [cyan dim]{latitude}, {longitude}[/cyan dim]")
        if category == "it":
            pass
        if category == "science":
            journal = result.get("journal")
            publisher = result.get("publisher")
            print(
                f"     [cyan dim][bold]{published_date + ' ' if published_date else ''}[/bold]{journal + ' ' if journal else ''}{publisher + ' ' if publisher else ''}[/cyan dim]"
            )
        if category == "files":
            if template == "torrent.html":
                magnet_link = result.get("magnetlink")
                seed = result.get("seed")
                leech = result.get("leech")
                filesize = result.get("filesize")
                print(
                    f"     [cyan dim][link={magnet_link}]{magnet_link}[/link][/cyan dim]"
                )
                print(
                    f"     [cyan dim]{filesize}[/cyan dim]] ↑{seed} seeders, ↓{leech} leechers"
                )
            elif template == "files.html":
                metadata = result.get("metadata")
                size = result.get("size")
                print(f"     [cyan dim]{size} {metadata}[/cyan dim]")
        if category == "social media":
            if published_date:
                print(f"     [cyan dim]{published_date}[/cyan dim]")

        if engine:
            print(f"     [dim]\\[{engine}][/dim]")
        print()


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
):
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
            body["categories"] = categories.replace("social+media", "social media")
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

        print(f"Searching: {url} with body: {body}") if DEBUG else None
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
        print(f"Searching: {url}") if DEBUG else None
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

        client = httpx.Client(verify=verify_ssl)
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

        # print(f"Response: {json.dumps(data)}") if DEBUG else None  # XXX

        if data and "results" in data:
            print(f"Returned {len(data['results'])} results") if DEBUG else None
            return data["results"]
        else:
            return None

    except httpx.HTTPStatusError as e:
        print(f"[red]Error:[/red]: {e}")
        exit(1)
    except httpx.ConnectError as ce:
        print(
            f"[red]Error:[/red] Could not connect to SearXNG instance at {searxng_url}\n{ce}"
        )
        exit(1)
    except json.JSONDecodeError:
        print("[red]Error:[/red] Could not decode JSON response.")
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
        # no_verify_ssl = false
        # no_user_agent = false
    """
    ).split("\n", 1)[1:][0]

    with open(config_file, "w") as f:
        f.write(default_config)

    print(f"[dim]created {config_file}[/dim]")


def get_config_str(config, key, default):
    return config["searxngr"][key] if key in config["searxngr"] else default


def get_config_int(config, key, default):
    return int(config["searxngr"][key]) if key in config["searxngr"] else default


def get_config_bool(config, key, default):
    return config["searxngr"].getboolean(key) if key in config["searxngr"] else default


def main():
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

    # command line settings
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
        "--no-verify-ssl",
        action="store_true",
        help="do not verify SSL certificates when making requests (not recommended)",
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
        "--np",
        "--noprompt",
        action="store_true",
        help="just search and exit, do not prompt",
    )
    parser.add_argument(
        "--noua",
        action="store_true",
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

    global DEBUG
    DEBUG = args.debug
    print(f"Config: {args}") if DEBUG else None

    # validate that searxng url is set
    if not args.searxng_url:
        print(f"[red]Error:[/red] searxng_url is not set in {config_file}")
        return
    # validate safe search is a valid value
    if args.safe_search and args.safe_search not in SAFE_SEARCH_OPTIONS:
        print(
            "[red]Error:[/red] Invalid safe search option. Use 'none', 'moderate', or 'strict'"
        )
        return
    # validate only one of --news or --videos is set
    if args.news and args.videos:
        print("[red]Error:[/red] You can only use one of --news or --videos at a time.")
        exit(1)
    # validate time range format
    if args.time_range and args.time_range not in set(TIME_RANGE_OPTIONS).union(
        TIME_RANGE_SHORT_OPTIONS
    ):
        print(
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
                print(
                    f"[red]Error:[/red] Invalid category '{category}'. Supported categories are: {', '.join(SEARXNG_CATEGORIES)}"
                )
                exit(1)
    # if news is requested, set categories to just 'news'
    if args.news:
        args.categories = ["news"]
    # if videos is requested, set categories to just 'videos'
    if args.videos:
        args.categories = ["videos"]
    # override results count if first option is requested
    if args.first:
        args.num = 1
    # set safe-search to 'none' if unsafe option is set
    if args.unsafe:
        args.safe_search = "none"
    # show version and exit
    if args.version:
        print(__version__)
        exit(0)
    # if no query is provided, show usage and exit
    if not args.query:
        parser.print_usage()
        exit(0)

    query = " ".join(args.query)

    # load results and loop for prompt
    while True:
        results = []
        pageno = 1
        # searxng does not have a limit option, we will always get a varied number of
        # results per page.Interate until we have enough results.
        while len(results) <= args.num:
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
            )
            results.extend(query_results)
            # if no results found or number of results is not set just return all initial results
            if args.num == 0 or len(query_results) == 0:
                break
            pageno += 1

        if results:
            if args.first:
                # if first or lucky search is requested, open the first result and exit
                url = results[0].get("url")
                os.system(f"{args.url_handler} '{url}'")
                exit(0)

            if args.lucky:
                # open a random result in the browser and exit
                url = random.choice(results).get("url")
                os.system(f"{args.url_handler} '{url}'")
                exit(0)

            # print the results
            print_results(results, count=args.num, expand=args.expand)
        else:
            # no results found or an error occurred
            print("\nNo results found or an error occurred during the search.\n")

        # if no prompt is requested, just exit after the search
        if args.np:
            exit(0)

        # process prompt commands
        while True:
            try:
                new_query = Prompt.ask("[bold]searxngr[/bold] [dim](? for help)[/dim] ")
            except KeyboardInterrupt:
                exit(0)
            if new_query.lower() in ["q", "quit", "exit"]:
                exit(0)
            elif new_query.lower() in ["?"]:
                print(
                    textwrap.dedent(
                        """
                        - Enter a search query to perform a new search.
                        - Type the index (1, 2, 3, etc) open the search index page in a browser.
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
                    os.system(f"{args.url_handler} '{url}'")
                else:
                    print("[red]Error:[/red] No URL found for the selected result.")
                continue
            else:
                # run the new query
                query = new_query.strip()
                break


if __name__ == "__main__":
    main()
