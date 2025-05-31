searxngr
========

SearXNG from the command line, inspired by `ddgr` and `googler`.

Installation
------------

```shell
uv tool install https://github.com/scross01/searxngr.git
```

Configuration
-------------

The `searxngr` configuration is stored in `$XDG_CONFIG_HOME/searxng/config.ini`, on Mac and Linux this is typical under `$HOME/.config` and on Windows its under `%APPDATA%`

If the config file it not found is will be created and populated with a configuration template.  On first run `searxng` will prompt for your SearXNG instance URL to populate the configuation file.

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
$ searxng why is the sky blue
```

### Options

Command line options can be used to modify the output and override the configuraiton defaults.

```txt
usage: searxngr [-h] [--searxng-url SEARXNG_URL] [-d] [-e [ENGINE ...]] [-x] [-n N] [--safe-search FILTER] [-w SITE] [-t TIME_RANGE] QUERY [QUERY ...]

Perform a search using SearXNG

positional arguments:
  QUERY                 search query

options:
  -h, --help            show this help message and exit
  --searxng-url SEARXNG_URL
                        SearXNG instance URL (default: https://searxng.stephencross.site)
  -d, --debug           show debug output
  -e, --engines [ENGINE ...]
                        list of engines to use for the search (default: all available engines)
  -x, --expand          Show complete url in search results
  -n, --num N           show N results per page (default: 10); N=0 uses the servers default per page
  --safe-search FILTER  Filter results for safe search. Use 'none', 'moderate', or 'strict' (default: strict)
  -w, --site SITE       search sites using site: operator
```

## Troubleshooting

### Error:: Client error '429 Too Many Requests' for url 'https://searxng.example.com'

The SearXNG server is limiting access to the search API. Update server limiter setting or disable limiter for private instances in the service `searxng/settings.toml`

### Error: Could not decode JSON response.

The SearXNG instance may be returning the results in html format.  On the SearXNG servers you need to modify the supported search formats to include json in `searxng/settings.yml`.

```yaml
search:
  formats:
    - html
    -json
```
