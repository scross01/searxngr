import argparse
import json
import os
import platform
import random
import shlex
import shutil
import subprocess

from rich.table import Table

from .__version__ import __version__
from .console import InteractiveConsole as Console
from .config import SearxngrConfig
from .client import (
    SearXNGClient,
    SearXNGError,
    SearXNGConnectionError,
    SearXNGTimeoutError,
    SearXNGHTTPError,
    SearXNGJSONError,
)
from .formatter import print_results
from .interactive import run_interactive_loop
from .constants import (
    SEARXNG_CATEGORIES,
    TIME_RANGE_OPTIONS,
    TIME_RANGE_SHORT_OPTIONS,
    SAFE_SEARCH_OPTIONS,
    URL_HANDLER,
    DEFAULT_EDITOR,
    DEBUG,
    console,
)


def parse_pre_args() -> argparse.Namespace:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--searxng-url", type=str, dest="searxng_url")
    pre_parser.add_argument("--version", "-v", action="store_true", dest="version")
    pre_parser.add_argument("--config", action="store_true", dest="config")
    pre_parser.add_argument(
        "--list-categories", action="store_true", dest="list_categories"
    )
    pre_parser.add_argument("--list-engines", action="store_true", dest="list_engines")
    pre_parser.add_argument("--help", "-h", action="store_true", dest="help")
    return pre_parser.parse_known_args()[0]


def open_url(url: str, url_handler: str) -> bool:
    try:
        command = shlex.split(url_handler)
        command.append(url)
        subprocess.run(command, check=True)
        return True
    except FileNotFoundError:
        console.print(
            f"[yellow]Warning:[/yellow] URL handler '{url_handler}' not found, "
            "update configuration or set --url-handler"
        )
        return False
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error opening URL:[/red] {e}")
        return False


def handle_results(results: list, args: argparse.Namespace) -> tuple[bool, list]:
    if args.json:
        print(json.dumps(results, indent=2))
        return (False, results)

    if not results:
        console.print("\nNo results found or an error occurred during the search.\n")
        return (True, results)

    if args.first:
        url = results[0].get("url")
        if url:
            open_url(url, args.url_handler)
        else:
            console.print("[red]Error:[/red] No URL found in result")
        return (False, results)

    if args.lucky:
        result = random.choice(results)
        url = result.get("url")
        if url:
            open_url(url, args.url_handler)
        else:
            console.print(f"[red]Error:[/red] No URL found in result {result}")
        return (False, results)

    print_results(results, count=args.num, start_at=0, expand=args.expand)
    return (True, results)


def create_parser(cfg: SearxngrConfig) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Perform a search using SearXNG")
    parser.add_argument(
        "query",
        type=str,
        nargs="*",
        metavar="QUERY",
        help="search query (optional if -q/--query is used)",
    )
    parser.add_argument(
        "-q",
        "--query",
        type=str,
        dest="query_opt",
        metavar="QUERY",
        help="explicit search query (alternative to positional query)",
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
        f"(default: {' '.join(cfg.engines) if cfg.engines else 'NOT SET'})",
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
        default=cfg.http_method,
        choices=["GET", "POST"],
        metavar="METHOD",
        help="HTTP method to use for search requests. GET or POST "
        f"(default: {cfg.http_method.upper() if cfg.http_method else 'GET'})",
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
        "--secondary-url-handler",
        type=str,
        default=cfg.secondary_url_handler,
        metavar="UTIL",
        help=(
            "Command to open URLs using secondary handler "
            f"(default: {cfg.secondary_url_handler if cfg.secondary_url_handler else 'not set'})"
        ),
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
    return parser


def main() -> None:
    pre_args = parse_pre_args()

    skip_config_creation = not pre_args.config

    cfg = SearxngrConfig(skip_config_creation=skip_config_creation)

    parser = create_parser(cfg)
    args = parser.parse_args()

    query = ""
    if args.query:
        query = " ".join(args.query)
    if hasattr(args, "query_opt") and args.query_opt:
        query = args.query_opt

    global console
    if args.nocolor:
        console = Console(history=[query], color_system=None, force_terminal=True)
    else:
        console = Console(history=[query])

    global DEBUG
    DEBUG = args.debug
    console.print(f"Config: {args}") if DEBUG else None

    if args.config:
        if not os.path.exists(cfg.config_file):
            cfg.create_config_file()
            exit(0)
        console.print(f"opening {cfg.config_file}")
        editor = os.environ.get("EDITOR")
        if not editor:
            system = platform.system()
            if system == "Linux":
                fallback = "xdg-open"
            elif system == "Darwin":
                fallback = "open"
            elif system == "Windows":
                fallback = "notepad"
            else:
                fallback = None

            if fallback and shutil.which(fallback):
                editor = fallback
            else:
                console.print(
                    "[red]Error:[/red] No editor found. Set $EDITOR environment variable "
                    "or install an editor."
                )
                exit(1)
        try:
            subprocess.run(shlex.split(editor) + [cfg.config_file], check=True)
        except FileNotFoundError:
            console.print(f"[red]Error:[/red] Editor '{editor}' not found.")
            console.print("Set the EDITOR environment variable or install an editor.")
            exit(1)
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error opening editor:[/red] {e}")
            exit(1)
        exit(0)
    if args.version:
        console.print(__version__)
        exit(0)
    if pre_args.help:
        parser.print_help()
        exit(0)

    if not args.searxng_url:
        console.print(
            "[red]Error:[/red] No SearXNG instance URL set. Use --searxng-url or run `searxngr --config`"
        )
        console.print("Run `searxngr --help` for more options")
        exit(1)
    if args.safe_search and args.safe_search not in SAFE_SEARCH_OPTIONS:
        console.print(
            "[red]Error:[/red] Invalid safe search option. Use 'none', 'moderate', or 'strict'"
        )
        return
    if args.news and args.videos:
        console.print(
            "[red]Error:[/red] You can only use one of --news or --videos at a time."
        )
        exit(1)
    if args.time_range and args.time_range not in set(TIME_RANGE_OPTIONS).union(
        TIME_RANGE_SHORT_OPTIONS
    ):
        console.print(
            "[red]Error:[/red] Invalid time range format. Use 'd', 'day', 'w', 'week', 'm', 'month', or 'y', 'year'"
        )
        return
    if args.time_range in TIME_RANGE_SHORT_OPTIONS:
        args.time_range = (
            args.time_range.replace("y", "year")
            .replace("m", "month")
            .replace("w", "week")
            .replace("d", "day")
        )
    if isinstance(args.categories, list):
        for category in args.categories:
            if not cfg.validate_category(category):
                exit(1)
    elif isinstance(args.categories, str):
        if not cfg.validate_category(args.categories):
            exit(1)
        args.categories = [args.categories]
    if args.files:
        args.categories = ["files"]
    if args.music:
        args.categories = ["music"]
    if args.news:
        args.categories = ["news"]
    if args.social:
        args.categories = ["social+media"]
    if args.videos:
        args.categories = ["videos"]
    if args.first:
        args.num = 1
    if args.unsafe:
        args.safe_search = "none"

    from .constants import validate_url_handler

    if args.url_handler and not validate_url_handler(args.url_handler):
        console.print(
            f"[yellow]Warning:[/yellow] The url-handler command '{args.url_handler}' is not found or not executable."
        )
        console.print(
            "Make sure the command exists in your PATH or provide a full path to the executable."
        )
        console.print(
            f"[dim]Default commands for your platform: {URL_HANDLER.get(platform.system(), 'unknown')}[/dim]"
        )
    if args.secondary_url_handler and not validate_url_handler(
        args.secondary_url_handler
    ):
        console.print(
            f"[yellow]Warning:[/yellow] The secondary-url-handler command "
            f"'{args.secondary_url_handler}' is not found or not executable."
        )
        console.print(
            "Make sure the command exists in your PATH or provide a full path to the executable."
        )
        console.print(
            f"[dim]Default commands for your platform: {URL_HANDLER.get(platform.system(), 'unknown')}[/dim]"
        )

    searxng = SearXNGClient(
        url=args.searxng_url,
        username=cfg.searxng_username,
        password=cfg.searxng_password,
        verify_ssl=not args.no_verify_ssl,
        no_user_agent=args.noua,
        timeout=args.timeout,
    )

    if args.list_engines:
        try:
            engines = searxng.engines()
        except SearXNGError as e:
            console.print(f"[red]Error:[/red] {e}")
            exit(1)

        table = Table()
        table.add_column("Engine", style="cyan", no_wrap=True)
        table.add_column("URL")
        table.add_column("!bang", style="green", no_wrap=True)
        table.add_column("Categories")
        table.add_column("Reliability", justify="right")

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
                + (f" [red]({engine['errors']})[red]" if engine["errors"] else ""),
                engine["url"],
                " ".join(engine["bangs"]),
                " ".join(engine["categories"]),
                reliability,
            )
        console.print(table)
        exit(0)
    if args.list_categories:
        try:
            categories = searxng.categories()
        except SearXNGError as e:
            console.print(f"[red]Error:[/red] {e}")
            exit(1)
        table = Table(leading=True)
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Engines")
        for category in categories.keys():
            c = list(categories[category])
            c.sort()
            table.add_row(category, ",".join(c))
        console.print(table)
        exit(0)

    if query == "":
        parser.print_usage()
        exit(0)

    pageno = 1
    start_at = 0
    results = []

    while True:
        while len(results) <= (start_at + args.num):
            try:
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
            except SearXNGError as e:
                console.print(f"[red]Error:[/red] {e}")
                exit(1)
            results.extend(query_results)
            if args.num == 0 or len(query_results) == 0:
                break
            pageno += 1

        continue_loop, results = handle_results(results, args)
        if not continue_loop:
            exit(0)

        if args.np:
            exit(0)

        new_query, start_at, pageno, results = run_interactive_loop(
            args, results, query, start_at, pageno, searxng
        )
        query = new_query


if __name__ == "__main__":
    main()
