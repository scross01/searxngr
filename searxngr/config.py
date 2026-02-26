import os
import platform
import shlex
import shutil
import textwrap
import configparser
import httpx
from typing import Optional, List
from xdg_base_dirs import xdg_config_home

from .constants import (
    SAMPLE_SEARXNG_URL,
    RESULT_COUNT,
    SAFE_SEARCH,
    ENGINES,
    EXPAND,
    CONFIG_FILE,
    HTTP_METHOD,
    HTTP_TIMEOUT,
    URL_HANDLER,
    SECONDARY_URL_HANDLER,
    SEARXNG_CATEGORIES,
    console,
)


class SearxngrConfig:
    def __init__(
        self,
        config_path: Optional[str] = None,
        config_file: Optional[str] = None,
        skip_config_creation: bool = False,
    ) -> None:
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = os.path.join(xdg_config_home(), "searxngr")

        if config_file:
            self.config_file = config_file
        else:
            self.config_file = os.path.join(self.config_path, CONFIG_FILE)

        if not os.path.exists(self.config_file):
            if not skip_config_creation:
                self.create_config_file()

        self.load_config()

    def create_config_file(self):
        file = os.path.join(self.config_path, self.config_file)
        console.print(f"[dim]creating initial configuration file {file}[/dim]")

        if not os.path.isdir(self.config_path):
            os.makedirs(self.config_path)

        searxng_url = input(f"Enter your SearXNG instance URL [{SAMPLE_SEARXNG_URL}]: ")
        if not searxng_url:
            searxng_url = SAMPLE_SEARXNG_URL

        no_verify_ssl = False
        if searxng_url.startswith("https://"):
            no_verify_ssl = (
                input("Disable SSL verification (y/N)? ").strip().lower() == "y"
            )

        valid, message = self.validate_searxng_url(searxng_url, not no_verify_ssl)
        if not valid:
            console.print(f"[red]Error:[/red] {message}")
            console.print("Please check the URL and try again.")
            exit(1)
        else:
            console.print("Connection successful.")

        default_handler = URL_HANDLER.get(platform.system(), "open")
        from .constants import validate_url_handler

        if validate_url_handler(default_handler):
            console.print(f"Using default URL handler: {default_handler}")
            url_handler = default_handler
        else:
            console.print(f"Default URL handler '{default_handler}' not found.")
            while True:
                url_handler = input("Enter command to open URLs in browser: ").strip()
                if not url_handler:
                    console.print("[red]Error:[/red] Command cannot be empty.")
                    continue
                command_parts = shlex.split(url_handler)
                command = command_parts[0]
                full_path = shutil.which(command)
                if full_path is None:
                    console.print(
                        f"[red]Error:[/red] Command '{command}' not found. "
                        "Please enter a valid command."
                    )
                else:
                    if full_path != command:
                        url_handler = url_handler.replace(command, full_path, 1)
                    console.print(f"Using URL handler: {url_handler}")
                    break

        no_verify_ssl_line = (
            f"no_verify_ssl = {str(no_verify_ssl).lower()}"
            if no_verify_ssl
            else "# no_verify_ssl = false"
        )

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
            {no_verify_ssl_line}
            # no_user_agent = false
            # no_color = false
            url_handler = {url_handler}
            # secondary_url_handler =
        """
        ).split("\n", 1)[1:][0]

        try:
            with open(file, "w") as f:
                f.write(default_config)
        except OSError as e:
            console.print(f"[red]Error:[/red] Could not write config file: {e}")
            exit(1)

        console.print(
            "Initial settings created. Run 'searxngr --config' again to edit all settings."
        )
        exit(0)

    def validate_searxng_url(self, url: str, verify_ssl: bool) -> tuple[bool, str]:
        try:
            client = httpx.Client(verify=verify_ssl, timeout=10)
            response = client.get(f"{url.rstrip('/')}/search?q=test&format=json")
            response.raise_for_status()
            response.json()
            return (True, "")
        except httpx.ConnectError as ce:
            return (False, f"Could not connect to {url}. {ce}")
        except httpx.TimeoutException as te:
            return (False, f"Connection to {url} timed out. {te}")
        except httpx.HTTPStatusError as he:
            return (
                False,
                f"Invalid response from {url} (HTTP {he.response.status_code}). {he}",
            )
        except Exception as e:
            return (False, f"Unable to access JSON API for {url}. {e}")

    def get_config_list(
        self, parser: configparser.ConfigParser, key: str, default: Optional[List[str]]
    ) -> Optional[List[str]]:
        entry = (
            parser["searxngr"][key]
            if "searxngr" in parser and key in parser["searxngr"]
            else default
        )
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
        try:
            return (
                parser["searxngr"][key]
                if "searxngr" in parser and key in parser["searxngr"]
                else default
            )
        except (ValueError, KeyError) as ve:
            console.print(
                f'[red]Error:[/red] unable to set value for "{key}", using default setting "{default}". [dim]{ve}[/dim]'
            )
            return default

    def get_config_int(
        self, parser: configparser.ConfigParser, key: str, default: int
    ) -> int:
        try:
            return (
                int(parser["searxngr"][key])
                if "searxngr" in parser and key in parser["searxngr"]
                else default
            )
        except (ValueError, KeyError) as ve:
            console.print(
                f'[red]Error:[/red] unable to set value for "{key}", using default setting "{default}". [dim]{ve}[/dim]'
            )
            return default

    def get_config_float(
        self, parser: configparser.ConfigParser, key: str, default: float
    ) -> float:
        try:
            return (
                float(parser["searxngr"][key])
                if "searxngr" in parser and key in parser["searxngr"]
                else default
            )
        except (ValueError, KeyError) as ve:
            console.print(
                f'[red]Error:[/red] unable to set value for "{key}", using default setting "{default}". [dim]{ve}[/dim]'
            )
            return default

    def get_config_bool(
        self, parser: configparser.ConfigParser, key: str, default: bool
    ) -> bool:
        try:
            result = (
                parser["searxngr"].getboolean(key)
                if "searxngr" in parser and key in parser["searxngr"]
                else default
            )
            return result if result else default
        except (ValueError, KeyError) as ve:
            console.print(
                f'[red]Error:[/red] unable to set value for "{key}", using default setting "{default}". [dim]{ve}[/dim]'
            )
            return default

    @classmethod
    def validate_category(cls, category: str) -> bool:
        if category not in SEARXNG_CATEGORIES:
            console.print(
                f"[red]Error:[/red] Invalid category '{category}'. "
                f"Supported categories are: {', '.join(SEARXNG_CATEGORIES)}"
            )
            return False
        return True

    def load_config(self) -> None:
        parser = configparser.ConfigParser()

        if os.path.exists(self.config_file):
            parser.read(self.config_file)
            if "searxngr" not in parser:
                self.create_config_file()
                parser.read(self.config_file)

        self.searxng_url = self.get_config_str(parser, "searxng_url", None)
        self.searxng_username = self.get_config_str(parser, "searxng_username", None)
        self.searxng_password = self.get_config_str(parser, "searxng_password", None)
        self.result_count = self.get_config_int(parser, "result_count", RESULT_COUNT)
        self.safe_search = self.get_config_str(parser, "safe_search", SAFE_SEARCH)
        self.categories = self.get_config_list(parser, "categories", None)
        self.engines = self.get_config_list(parser, "engines", ENGINES)
        self.expand = self.get_config_bool(parser, "expand", EXPAND)
        self.language = self.get_config_str(parser, "language", None)
        self.url_handler = self.get_config_str(
            parser, "url_handler", URL_HANDLER.get(platform.system())
        )
        self.secondary_url_handler = self.get_config_str(
            parser, "secondary_url_handler", SECONDARY_URL_HANDLER
        )
        self.debug = self.get_config_bool(parser, "debug", False)
        self.http_method = self.get_config_str(parser, "http_method", HTTP_METHOD)
        self.http_timeout = self.get_config_float(parser, "timeout", HTTP_TIMEOUT)
        self.no_user_agent = self.get_config_bool(parser, "no_user_agent", False)
        self.no_verify_ssl = self.get_config_bool(parser, "no_verify_ssl", False)
        self.no_color = self.get_config_bool(parser, "no_color", False)
