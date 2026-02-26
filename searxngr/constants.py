import os
import platform
import shutil
import shlex
from typing import List, Dict, Any, Optional

from .console import InteractiveConsole as Console
from .__version__ import __version__

DEBUG = False

console = Console()

SAMPLE_SEARXNG_URL = "https://searxng.example.com"
SEARXNG_URL = ""
RESULT_COUNT = 10
SAFE_SEARCH = "strict"
ENGINES = None
EXPAND = False
CONFIG_FILE = "config.ini"
HTTP_METHOD = "GET"
HTTP_TIMEOUT = 30.0
USER_AGENT = f"searxngr/{__version__}"
CATEGORIES = None

MAX_CONTENT_WORDS = 128
PREFERENCES_URL_PATH = "/preferences"

SAFE_SEARCH_OPTIONS = {
    "none": "0",
    "moderate": "1",
    "strict": "2",
}

URL_HANDLER = {
    "Darwin": "open",
    "Linux": "xdg-open",
    "Windows": "explorer",
}

SECONDARY_URL_HANDLER = None

DEFAULT_EDITOR = {
    "Darwin": "open -t",
    "Linux": "xdg-open",
    "Windows": "notepad",
}

TIME_RANGE_OPTIONS = ["day", "week", "month", "year"]
TIME_RANGE_SHORT_OPTIONS = ["d", "w", "m", "y"]

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


def parse_engine_command(engine_input: str) -> tuple:
    to_add = []
    to_remove = []
    replacement_list = []
    has_modifiers = False

    engines = []
    for part in engine_input.replace(",", " ").split():
        engines.append(part.strip())

    for engine in engines:
        if engine.startswith("+"):
            to_add.append(engine[1:])
            has_modifiers = True
        elif engine.startswith("-"):
            to_remove.append(engine[1:])
            has_modifiers = True
        else:
            replacement_list.append(engine)

    return to_add, to_remove, replacement_list, has_modifiers


def validate_engines(engines: List[str], searxng_client) -> tuple:
    try:
        available_engines = searxng_client.engines()
        available_engine_names = {engine["name"] for engine in available_engines}
    except Exception as e:
        console.print(
            f"[red]Error:[/red] Could not fetch available engines from SearXNG instance. "
            f"Please check your SearXNG instance URL and network connection. Error: {e}"
        )
        console.print(
            "[yellow]Note:[/yellow] Engine validation skipped, using provided engines as-is."
        )
        return engines, []

    valid_engines = []
    invalid_engines = []

    for engine in engines:
        if engine in available_engine_names:
            valid_engines.append(engine)
        else:
            invalid_engines.append(engine)

    return valid_engines, invalid_engines


def validate_url_handler(url_handler: str) -> bool:
    try:
        command_parts = shlex.split(url_handler)
        if not command_parts:
            return False

        command = command_parts[0]
        return shutil.which(command) is not None
    except (ValueError, IndexError):
        return False
