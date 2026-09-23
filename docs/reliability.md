# Reliability

> Adapted from the reliability work of [wawow830](https://github.com/wawow830/searxngr).

`searxngr` needs a reachable SearXNG server with JSON output enabled and working
search engines. It cannot guarantee results during outages or upstream blocks.
There are no background monitors, automatic server restarts, or hidden public
instance fallbacks.

## Request handling

- `--retries` defaults to 2 (range 0–5). Only transport failures, timeouts, and
  HTTP 500/502/503/504 are retried. Backoff starts at 0.25 seconds, capped at 2.
- HTTP 4xx responses, CAPTCHAs, and invalid JSON do not trigger HTTP retries.
- `--timeout` applies per HTTP attempt, not to the whole command.
- `--fallback-engines 'google,mwmbl'` enables one backup batch when default web
  engines return no results and report failures. It is disabled by default.
  An empty value disables a configured list; commas preserve spaces in names.
- Backup requests keep the same server and filters. Explicit engine, category,
  or bang selection is never overridden. Pagination stays with the selected
  engines; a new search starts with the defaults again.

These options can also be set in `config.ini`:

```ini
[searxngr]
searxng_url = http://127.0.0.1:8080
retries = 2
fallback_engines = google, mwmbl
```

## Output and pagination

`--json` returns one server page; `-n` controls text display, not JSON length.
Search diagnostics go to stderr. Failure without results exits nonzero; a
successful zero-match search returns `[]`. Partial results are preserved.
Text pagination deduplicates URLs, stops repeated pages, and fetches at most
ten pages per display cycle. Non-terminal stdin disables interactive prompting.

## Server setup

Enable `json` in SearXNG's `search.formats` and select multiple working engines
in its `settings.yml`. Google CSE and Naver worked during verification; availability
and relevance vary by network, region, language, and time. Probe them individually:

```sh
searxngr --json -q 'python documentation' -e 'google cse'
searxngr --json -q 'site:docs.rs tokio spawn' -e naver
```

Check relevance, not just nonempty results. Let SearXNG manage engine cooldowns;
do not repeatedly restart it to evade them. Keep TLS verification enabled and
server credentials private.
