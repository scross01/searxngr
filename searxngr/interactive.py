import json
import shlex
import subprocess
import textwrap
from typing import List, Dict, Any
from rich.prompt import Prompt
import pyperclip
from html2text import html2text

from .constants import (
    TIME_RANGE_OPTIONS,
    TIME_RANGE_SHORT_OPTIONS,
    SAFE_SEARCH_OPTIONS,
    console,
    DEBUG,
)
from .formatter import print_results
from .client import SearXNGClient


def run_interactive_loop(
    args,
    results: List[Dict[str, Any]],
    query: str,
    start_at: int,
    pageno: int,
    searxng: SearXNGClient,
):
    while True:
        try:
            new_query = Prompt.ask(
                "[bold]searxngr[/bold] [dim](? for help)[/dim] ", console=console
            )
        except KeyboardInterrupt:
            exit(1)
        except EOFError:
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
                - Type 'o' plus the index ('o 1', 'o 2') to open the result using the secondary URL handler.
                - Type 'c' plus the index ('c 1', 'c 2') to copy the result URL to clipboard.
                - Type 'C' plus the index ('C 1', 'C 2') to copy the result content to clipboard.
                - Type 't timerange' to change the search time range (e.g. `t week`).
                - Type 'F filter' to change safe search filter (e.g `F moderate`).
                - Type 'site:example.com' to filter results by a specific site.
                - Type 'e' plus engine names to change search engines
                           (e.g., 'e duckduckgo brave', 'e +google -bing').
                - Type 'x' to toggle showing to result URL.
                - Type 's' to show the current configuration settings.
                - Type 'm words' to change the number of words to display per result before truncating
                           (e.g., `m 200` or `m 0` to disable truncation).
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
            index = int(new_query.strip()) - 1
            url = results[index].get("url")
            if url:
                try:
                    subprocess.run(shlex.split(args.url_handler) + [url], check=True)
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    if isinstance(e, FileNotFoundError):
                        console.print(
                            f"[yellow]Warning:[/yellow] URL handler '{args.url_handler}' not found, "
                            "update configuration or set --url-handler"
                        )
                    else:
                        console.print(f"[red]Error opening URL:[/red] {e}")
            else:
                console.print("[red]Error:[/red] No URL found for the selected result.")
            continue
        elif new_query.strip() == "o" or new_query.strip().startswith("o "):
            index = new_query[2:].strip()
            if not index:
                console.print("[red]Error:[/red] No index specified. Usage: o <number>")
                continue
            if index.isdigit() and int(index) in range(1, len(results) + 1):
                index = int(index) - 1
                url = results[index].get("url")
                if url:
                    handler = (
                        args.secondary_url_handler
                        if args.secondary_url_handler
                        else args.url_handler
                    )
                    try:
                        subprocess.run(shlex.split(handler) + [url], check=True)
                    except (subprocess.CalledProcessError, FileNotFoundError) as e:
                        if isinstance(e, FileNotFoundError):
                            console.print(
                                f"[yellow]Warning:[/yellow] URL handler '{handler}' not found, "
                                "update configuration or set --url-handler"
                            )
                        else:
                            console.print(f"[red]Error opening URL:[/red] {e}")
                else:
                    console.print(
                        "[red]Error:[/red] No URL found for the selected result."
                    )
            else:
                console.print("[red]Error:[/red] Invalid index specified.")
            continue
        elif new_query.strip() == "c" or new_query.strip().startswith("c "):
            index = new_query[2:].strip()
            if not index:
                console.print("[red]Error:[/red] No index specified. Usage: c <number>")
                continue
            result = results[int(index) - 1]
            if index.isdigit() and int(index) in range(1, len(results) + 1):
                url = result.get("url")
                if url:
                    pyperclip.copy(url)
                else:
                    console.print(
                        "[red]Error:[/red] No URL found for the selected result."
                    )
            else:
                console.print("[red]Error:[/red] Invalid index specified.")
            continue
        elif new_query.strip() == "C" or new_query.strip().startswith("C "):
            index = new_query[2:].strip()
            if not index:
                console.print("[red]Error:[/red] No index specified. Usage: C <number>")
                continue
            result = results[int(index) - 1]
            if index.isdigit() and int(index) in range(1, len(results) + 1):
                category = result.get("category", None)
                template = result.get("template", None)

                if category == "images":
                    content = result.get("img_src")
                elif category == "files" and template == "torrent.html":
                    content = result.get("magnetlink")
                else:
                    content_raw = result.get("content", "")
                    content = html2text(content_raw).strip() if content_raw else ""

                if content:
                    pyperclip.copy(content)
                else:
                    console.print("No content found for the selected result.")
            else:
                console.print("[red]Error:[/red] Invalid index specified.")
            continue
        elif new_query.strip() == "n":
            start_at += args.num
            if len(results) >= (start_at + args.num):
                print_results(
                    results,
                    count=args.num,
                    start_at=start_at,
                    expand=args.expand,
                    max_content_words=args.max_content_words,
                )
                continue
            else:
                new_query = query
                pageno += 1
                break
        elif new_query.strip() == "p":
            start_at -= args.num if start_at >= args.num else 0
            print_results(
                results,
                count=args.num,
                start_at=start_at,
                expand=args.expand,
                max_content_words=args.max_content_words,
            )
            continue
        elif new_query.strip() == "f":
            start_at = 0
            print_results(
                results,
                count=args.num,
                start_at=start_at,
                expand=args.expand,
                max_content_words=args.max_content_words,
            )
            continue
        elif new_query.strip() == "t" or new_query.strip().startswith("t "):
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
        elif new_query.strip() == "F" or new_query.strip().startswith("F "):
            safe_search_filter = new_query[2:].strip()
            if safe_search_filter not in SAFE_SEARCH_OPTIONS:
                console.print(
                    f"[red]Error:[/red] Invalid safe search filter '{safe_search_filter}'. "
                    f"Use one of: {', '.join(SAFE_SEARCH_OPTIONS.keys())}"
                )
                continue
            else:
                args.safe_search = safe_search_filter
                console.print(
                    f"[green]Safe search filter set to:[/green] {safe_search_filter}"
                )
                new_query = query
                start_at = 0
                pageno = 1
                results = []
                break
        elif new_query.strip() == "e" or new_query.strip().startswith("e "):
            from .constants import parse_engine_command, validate_engines

            engine_input = new_query[2:].strip()
            if not engine_input:
                console.print(
                    "[red]Error:[/red] No engine names specified. Usage: 'e +engine1 -engine2 engine3'"
                )
                continue

            to_add, to_remove, replacement_list, has_modifiers = parse_engine_command(
                engine_input
            )

            if has_modifiers and replacement_list:
                console.print(
                    "[yellow]Warning:[/yellow] Plain engine names ignored when using + or - prefixes"
                )
                replacement_list = []

            current_engines = args.engines.copy() if args.engines else []

            if has_modifiers:
                engines_to_add = []
                engines_to_remove = []

                if to_add:
                    valid_add, invalid_add = validate_engines(to_add, searxng)
                    engines_to_add.extend(valid_add)
                    if invalid_add:
                        console.print(
                            f"[yellow]Warning:[/yellow] Invalid engines to add: {', '.join(invalid_add)}"
                        )

                if to_remove:
                    valid_remove, invalid_remove = validate_engines(to_remove, searxng)
                    engines_to_remove.extend(valid_remove)
                    if invalid_remove:
                        console.print(
                            f"[yellow]Warning:[/yellow] Invalid engines to remove: "
                            f"{', '.join(invalid_remove)}"
                        )

                if engines_to_add or engines_to_remove:
                    for engine in engines_to_remove:
                        if engine in current_engines:
                            current_engines.remove(engine)

                    for engine in engines_to_add:
                        if engine not in current_engines:
                            current_engines.append(engine)

                    args.engines = current_engines
                    console.print(
                        f"[green]Engines updated:[/green] {', '.join(current_engines)}"
                    )
                else:
                    console.print(
                        "[yellow]Warning:[/yellow] No valid engines to add or remove"
                    )
            else:
                if replacement_list:
                    valid_engines, invalid_engines = validate_engines(
                        replacement_list, searxng
                    )

                    if valid_engines:
                        args.engines = valid_engines
                        console.print(
                            f"[green]Engines set to:[/green] {', '.join(valid_engines)}"
                        )
                        if invalid_engines:
                            console.print(
                                f"[yellow]Warning:[/yellow] Invalid engines ignored: "
                                f"{', '.join(invalid_engines)}"
                            )
                    else:
                        console.print(
                            "[yellow]Warning:[/yellow] No valid engines provided, "
                            "keeping current selection"
                        )
                else:
                    console.print("[yellow]Warning:[/yellow] No engines specified")

            continue
        elif new_query.strip().startswith("site:"):
            site = new_query[5:].strip()
            args.site = site
            new_query = query
            start_at = 0
            pageno = 1
            results = []
            break
        elif new_query.strip() == "x":
            args.expand = not args.expand
            print_results(
                results, count=args.num, start_at=start_at, expand=args.expand
            )
            continue
        elif new_query.strip() == "s":
            console.print(
                textwrap.dedent(
                    f"""
                    SearXNG URL:       {args.searxng_url}
                    HTTP method:       {args.http_method}
                    Timeout:           {args.timeout}
                    Verify SSL:        {
                        "enabled" if not args.no_verify_ssl else "disabled"
                    }
                    Result per page:   {
                        args.num if args.num > 0 else "[dim]default[/dim]"
                    }
                    Engines:           {
                        args.engines if args.engines else "[dim]not set[/dim]"
                    }
                    Categories:        {
                        args.categories if args.categories else "[dim]not set[/dim]"
                    }
                    Language:          {
                        args.language if args.language else "[dim]not set[/dim]"
                    }
                    Safe search:       {args.safe_search}
                    Site filter:       {
                        args.site if args.site else "[dim]not set[/dim]"
                    }
                    Time range filter: {
                        args.time_range if args.time_range else "[dim]not set[/dim]"
                    }
                    Expand URLs:       {
                        "enabled" if args.expand else "[dim]disabled[/dim]"
                    }
                    Max Content Words: {
                        args.max_content_words if args.max_content_words != 0 else "[dim]disabled[/dim]"
                    }
                    URL Handler:       {args.url_handler}
                    Secondary Handler: {
                        args.secondary_url_handler
                        if args.secondary_url_handler
                        else "[dim]not set[/dim]"
                    }
                    """
                )
            )
            continue
        elif new_query.strip() == "m" or new_query.strip().startswith("m "):
            max_words_str = new_query[2:].strip()
            if not max_words_str:
                console.print(
                    "[red]Error:[/red] No max words value specified. Usage: m <number>"
                )
                continue
            try:
                max_words = int(max_words_str)
                if max_words < 0:
                    raise ValueError
                args.max_content_words = max_words
                console.print(f"[green]Max content words set to:[/green] {max_words}")
                print_results(
                    results,
                    count=args.num,
                    start_at=start_at,
                    expand=args.expand,
                    max_content_words=args.max_content_words,
                )
            except ValueError:
                console.print(
                    "[red]Error:[/red] Invalid value. Please enter a non-negative integer."
                )
                continue
        elif new_query.strip() == "d":
            global DEBUG
            DEBUG = not DEBUG
            console.print(f"Debug mode {'enabled' if DEBUG else 'disabled'}")
            continue
        elif new_query.strip() == "j" or new_query.strip().startswith("j "):
            index = new_query[2:].strip()
            if not index:
                console.print("[red]Error:[/red] No index specified. Usage: j <number>")
                continue
            if index.isdigit() and int(index) in range(1, len(results) + 1):
                index = int(index) - 1
                console.print(json.dumps(results[index], indent=2, ensure_ascii=False))
            continue
        elif new_query.strip() != "":
            query = new_query.strip()
            start_at = 0
            pageno = 1
            results = []
            break

    return new_query, start_at, pageno, results
