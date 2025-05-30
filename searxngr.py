import json
import requests
from rich import print
import textwrap
import os
import argparse
from xdg_base_dirs import xdg_config_home
import configparser

# Default settings. Use config file or command line modify.
SEARXNG_URL = "https://searxng.example.com"  # Example SearXNG instance URL
RESULT_COUNT = 10  # Default number of results to show per page
SAFE_SEARCH = "strict"  # Default safe search setting
ENGINES = None  # Default to all default engines
EXPAND = False  # Default show expand url setting
DEBUG = False  # Debug mode

SAFE_SEARCH_OPTIONS = {
    "none": 0,  # Unsafe search
    "moderate": 1,  # Moderate safe search
    "strict": 2,  # Strict safe search
}

TIME_RANGE_OPTIONS = ["day", "month", "year"]


# print search results to the terminal
def print_results(results, count, expand=False):
    print()
    for i, result in enumerate(results[0:count], start=1):
        title = result.get("title", "No title")
        # truncate the title to 70 characters if it's too long
        title = textwrap.shorten(title, width=70, placeholder="...")

        # extract just the domain name from the URL
        url = result.get("url", "No URL")
        domain = url.split("//")[1].split("/")[0]

        engine = result.get("engine", "No engine")

        # wrap the content to the terminal width with indentation
        content = result.get("content", "No content")
        content = textwrap.wrap(content, width=os.get_terminal_size().columns - 5)

        print(
            f" [cyan]{i:>2}.[/cyan] [bold green]{title}[/bold green] [yellow]\\[{domain}][/yellow]"
        )
        if expand:
            print(f"     [link={url}]{url}[/link]")
        for line in content:
            print(f"     {line}")
        if engine:
            print(f"     [dim]\\[{engine}][/dim]")
        print()


def searxng_search(
    query,
    searxng_url,
    pageno=1,
    safe_search=None,
    engines=None,
    language=None,
    time_range=None,
    site=None,
):
    # searxng does not have a limit option, we will always a fixed number of
    # results per page depending on the searxng instance e.g. 20

    query = f"site:{site} {query}" if site else query

    url = f"{searxng_url}/?q={query}&format=json"
    url += f"&engines={','.join(engines)}" if engines else ""
    url += f"&language={language}" if language else ""
    url += f"&pageno={pageno}" if pageno > 1 else ""
    url += f"&safesearch={SAFE_SEARCH_OPTIONS[safe_search]}" if safe_search else ""
    url += f"&time_range={time_range}" if time_range else ""

    print(f"Searching: {url}") if DEBUG else None

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if data and "results" in data:
            return data["results"]
        else:
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response.")


def main():

    # Load configuration from a file if it exists
    config_file = os.path.join(xdg_config_home(), "searxngr", "config.ini")
    if os.path.exists(config_file):
        config = configparser.ConfigParser()
        config.read(config_file)
        if "searxngr" in config:
            if "searxng_url" in config["searxngr"]:
                global SEARXNG_URL
                SEARXNG_URL = config["searxngr"]["searxng_url"]
            if "results_per_page" in config["searxngr"]:
                global RESULT_COUNT
                RESULT_COUNT = int(config["searxngr"]["results_per_page"])
            if "unsafe" in config["searxngr"]:
                global UNSAFE
                UNSAFE = config["searxngr"].getboolean("unsafe")
            if "engines" in config["searxngr"]:
                global ENGINES
                ENGINES = config["searxngr"]["engines"]
            if "expand" in config["searxngr"]:
                global EXPAND
                EXPAND = config["searxngr"].getboolean("expand")

    parser = argparse.ArgumentParser(description="Perform a search using SearXNG")
    parser.add_argument(
        "query", type=str, nargs="+", metavar="QUERY", help="search query"
    )
    parser.add_argument(
        "--searxng-url",
        type=str,
        default=SEARXNG_URL,
        metavar="SEARXNG_URL",
        help="SearXNG instance URL",
    )
    parser.add_argument(
        "-e",
        "--engines",
        type=str,
        nargs="*",
        default=ENGINES,
        metavar="ENGINE",
        help=f"list of engines to use for the search (default: {ENGINES if ENGINES else 'all available engines'})",
    )
    parser.add_argument(
        "-x",
        "--expand",
        action="store_true",
        default=EXPAND,
        help="Show complete url in search results",
    )
    parser.add_argument(
        "-n",
        "--num",
        type=int,
        default=RESULT_COUNT,
        metavar="N",
        help=f"show N results per page (default: {RESULT_COUNT}); N=0 uses the servers default per page",
    )
    parser.add_argument(
        "--safe-search",
        type=str,
        default=SAFE_SEARCH,
        metavar="FILTER",
        help=f"Filter results for safe search. Use 'none', 'moderate', or 'strict' (default: {SAFE_SEARCH})",
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
        help="search results within a specific time range ('day', 'month', 'year')",
    )
    args = parser.parse_args()

    print(args) if DEBUG else None

    # validate time range format
    if args.time_range and args.time_range not in TIME_RANGE_OPTIONS:
        print("Error: Invalid time range format. Use 'day', 'month', or 'year'")
        return
    if args.safe_search and args.safe_search not in SAFE_SEARCH_OPTIONS:
        print("Error: Invalid safe search option. Use 'none', 'moderate', or 'strict'")
        return

    results = []
    while len(results) < args.num:
        results.extend(
            searxng_search(
                " ".join(args.query),
                searxng_url=args.searxng_url,
                safe_search=args.safe_search,
                engines=args.engines,
                # language=args.language,
                time_range=args.time_range,
                site=args.site,
            )
        )
        if args.num == 0:
            break

    if results:
        print_results(results, count=args.num, expand=args.expand)
    else:
        print("No results found or an error occurred during the search.")


if __name__ == "__main__":
    main()
