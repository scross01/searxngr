searxngr
========

SearXNG from the command line, inspired by `ddgr` and `googler`.

![demo](demo/demo.gif)

Installation
------------

```shell
uv tool install https://github.com/scross01/searxngr.git
```

Configuration
-------------

The `searxngr` configuration is stored in `$XDG_CONFIG_HOME/searxng/config.ini`, on Mac and Linux this is typical under `$HOME/.config` and on Windows its under `%APPDATA%`

If the config file it not found is will be created and populated with a configuration template.  On first run `searxngr` will prompt for your SearXNG instance URL to populate the configuation file.

```ini
[searxngr]
searxng_url = https://searxng.example.com
results_per_page = 10
safe_mode = moderate
expand = false
engines = duckduckgo google brave
```

Usage
-----

```shell
$ searxngr why is the sky blue
```

### Options

Command line options can be used to modify the output and override the configuraiton defaults.

```txt
usage: searxngr [-h] [--searxng-url SEARXNG_URL] [-d] [-e [ENGINE ...]] [-x] [--no-verify-ssl] 
                [-j] [--http-method METHOD] [-l LANGUAGE] [--lucky] [--np] [--noua] [-n N]
                [--safe-search FILTER] [-w SITE] [-t TIME_RANGE] [--unsafe] [--url_handler UTIL] [-v]
                [QUERY ...]

Perform a search using SearXNG

positional arguments:
  QUERY                 search query

options:
  -h, --help            show this help message and exit
  --searxng-url SEARXNG_URL
                        SearXNG instance URL (default: https://searxng.example.com)
  -d, --debug           show debug output
  -e, --engines [ENGINE ...]
                        list of engines to use for the search (default: all available engines)
  -x, --expand          Show complete url in search results
  --no-verify-ssl       do not verify SSL certificates when making requests (not recommended)
  -j, --first           open the first result in web browser and exit
  --http-method METHOD  HTTP method to use for search requests. GET or POST (default: GET)
  -l, --language LANGUAGE
                        search results in a specific language (e.g., 'en', 'de', 'fr')
  --lucky               opens a random result in web browser and exit
  --np, --noprompt      just search and exit, do not prompt
  --noua                disable user agent
  -n, --num N           show N results per page (default: 10); N=0 uses the servers default per page
  --safe-search FILTER  Filter results for safe search. Use 'none', 'moderate', or 'strict' (default: strict)
  -w, --site SITE       search sites using site: operator
  -t, --time-range TIME_RANGE
                        search results within a specific time range (day, week, month, year)
  --unsafe              allow unsafe search results (same as --safe-search none)
  --url_handler UTIL    Command to open URLs in the browser (default: open)
  -v, --version         show program's version number and exit
```

## Troubleshooting

**Error:: Client error '429 Too Many Requests' for url 'https://searxng.example.com'**

The SearXNG server is limiting access to the search API. Update server limiter setting or disable limiter for private instances in the service `searxng/settings.toml`

**Error: Could not decode JSON response.**

The SearXNG instance may be returning the results in html format.  On the SearXNG servers you need to modify the supported search formats to include json in `searxng/settings.yml`.

```yaml
search:
  formats:
    - html
    - json
```
