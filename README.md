# searxngr

SearXNG from the command line, inspired by `ddgr` and `googler`.

![demo](demo/demo.gif)

`searxngr` is a command-line interface (CLI) tool that allows you to perform web
searches using [SearXNG](https://github.com/searxng/searxng) instances directly
from your terminal. It provides rich-formatted search results with support for
various search categories and advanced filtering options.

## Key Features

- 💻 **Terminal-based interface** with colorized output
- 🚂 **Search engines selection** (bing, duckduckgo, google, etc)
- 📰 Support for **search categories** (general, news, images, videos, science,
  etc.)
- 👷 **Safe search filtering** (none, moderate, strict)
- 📅 **Time-range filtering** (day, week, month, year)
- 👨‍💻 **JSON output** option for scripting
- 🤖 **Automatic configuration** with first-time setup
- 🐧 **Cross-platform** support (macOS, Linux, Windows)

## Installation

Installation requires the
[`uv`](https://docs.astral.sh/uv/getting-started/installation/) package manager.

```shell
uv tool install https://github.com/scross01/searxngr.git
```

To install from source

```shell
git clone https://github.com/scross01/searxngr.git
cd searxngr
uv venv && source .venv/bin/activate # (optional)
uv sync
uv tool install .
```

## Configuration

The `searxngr` configuration is stored in `$XDG_CONFIG_HOME/searxng/config.ini`,
on Mac and Linux this is typical under `$HOME/.config` and on Windows its under
`%APPDATA%`

If the config file it not found is will be created and populated with a
configuration template. On first run `searxngr` will prompt for your SearXNG
instance URL to populate the configuation file.

```ini
[searxngr]
searxng_url = https://searxng.example.com
results_per_page = 10
safe_mode = moderate
expand = false
engines = duckduckgo google brave
```

### Configuration options

- `searxng_url` - set the URL of your SearXNG instance.
- `searxng_user` - username for basic auth. Optional
- `searxng_password` - password for basic auth. Optional
- `results_per_page` - the number results to output per page on the terminal.
  Default is `10`.
- `categories` - the categories to use for the search. Options include `news`,
  `videos`, `images`, `music`, `map`, `science`, `it`, `files`, `social+media`.
  Uses `general` search if not set.
- `safe_search` - set the safe search level to `none`, `moderate`, or `strict`.
  Uses server default if not set.
- `engines` - use the specified engines for the search. Uses server default if
  not set.
- `expand` - show the result URL in the results list. Default is `false`.
- `language` - set the search language, e.g. `en`, `en-CA`, `fr`, `es`, `de`,
  etc.
- `http_method` - use either `GET` or `POST` requests to the SearXNG API.
  Default is `GET`
- `timeout` - Timeout in seconds. Default is `30`.
- `no_verify_ssl` - disable SSL verification if you are hosting SearXNG with
  self-signed certificated. Default is `false`.
- `no_user_agent` - Clear the user agent. Default is `false`.
- `no_color` - disable color terminal output. Default is `false`.

## Usage

```shell
searxngr why is the sky blue
```

### Options

Command line options can be used to modify the output and override the
configuraiton defaults.

```txt
usage: searxngr [-h] [--searxng-url SEARXNG_URL] [-c [CATEGORY ...]] [--config] [-d] [-e [ENGINE ...]] [-x] [-j]
                [--http-method METHOD] [--timeout SECONDS] [--json] [-l LANGUAGE] [--list-categories] [--list-engines]
                [--lucky] [--no-verify-ssl] [--nocolor] [--np] [--noua] [-n N] [--safe-search FILTER] [-w SITE]
                [-t TIME_RANGE] [--unsafe] [--url-handler UTIL] [-v] [-F] [-M] [-N] [-S] [-V]
                [QUERY ...]

Perform a search using SearXNG

positional arguments:
  QUERY                 search query

options:
  -h, --help            show this help message and exit
  --searxng-url SEARXNG_URL
                        SearXNG instance URL (default: NOT SET)
  -c, --categories [CATEGORY ...]
                        list of categories to search in: general, news, videos, images, music, map, science, it,
                        files, social+media (default: None)
  --config              open the default configuration file using system text editor
  -d, --debug           show debug output
  -e, --engines [ENGINE ...]
                        list of engines to use for the search (default: NOT SET)
  -x, --expand          Show complete url in search results
  -j, --first           open the first result in web browser and exit
  --http-method METHOD  HTTP method to use for search requests. GET or POST (default: GET)
  --timeout SECONDS     HTTP request timeout in seconds (default: 30.0)
  --json                output the search results in JSON format and exit
  -l, --language LANGUAGE
                        search results in a specific language (e.g., 'en', 'de', 'fr')
  --list-categories     list available categories
  --list-engines        list available engines
  --lucky               opens a random result in web browser and exit
  --no-verify-ssl       do not verify SSL certificates of server (not recommended)
  --nocolor             disable colored output
  --np, --noprompt      just search and exit, do not prompt
  --noua                disable user agent
  -n, --num N           show N results per page (default: 10); N=0 uses the servers default per page
  --safe-search FILTER  Filter results for safe search. Use 'none', 'moderate', or 'strict' (default: strict)
  -w, --site SITE       search sites using site: operator
  -t, --time-range TIME_RANGE
                        search results within a specific time range (day, week, month, year)
  --unsafe              allow unsafe search results (same as --safe-search none)
  --url-handler UTIL    Command to open URLs in the browser (default: open)
  -v, --version         show program's version number and exit
  -F, --files           show results from files section. (same as --categories files)
  -M, --music           show results from music section. (same as --categories music)
  -N, --news            show results from news section. (same as --categories news)
  -S, --social          show results from videos section. (same as --categories social+media)
  -V, --videos          show results from videos section. (same as --categories videos)
```

### Listing Available Engines and Categories

You can view the available search engines and categories supported by your
SearXNG instance using the following options:

```shell
# List all available search engines
searxngr --list-engines

# List all available search categories
searxngr --list-categories
```

These options fetch the current list of engines and categories directly from
your configured SearXNG instance and display them in a formatted table. The
engine listing includes the engine name, URL, supported bang commands,
categories, and reliability score. The category listing shows each category
along with the engines that support it.

## Interactive Console Engine Management

When you run `searxngr` without the `--noprompt` flag, you enter an interactive
console where you can dynamically change search engines during your session.

### Engine Management Commands

Use the `e` command followed by engine names to modify your search engine
selection:

#### Basic Engine Replacement

```shell
# Replace current engines with specific ones
e duckduckgo google brave

# Add engines to current selection
e +bing +yahoo

# Remove engines from current selection
e -bing -yahoo
```

## Troubleshooting

**Error:: Client error '429 Too Many Requests' for url
'<https://searxng.example.com>'**

The SearXNG server is limiting access to the search API. Update server limiter
setting or disable limiter for private instances in the service
`searxng/settings.toml`

**Error: Could not decode JSON response.**

The SearXNG instance may be returning the results in html format. On the SearXNG
servers you need to modify the supported search formats to include json in
`searxng/settings.yml`.

```yaml
search:
  formats:
    - html
    - json
```
