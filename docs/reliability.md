# Reliable searches and scripting

This fork hardens the CLI, but it still needs a reachable SearXNG instance and
working upstream engines. It cannot guarantee availability during network
outages, CAPTCHAs, rate limits, or simultaneous engine failures.

## CLI behavior

- GET and POST preserve query characters and use the same filters.
- `--json` fetches one server page and writes the result array to stdout.
  `-n` controls text display, not the number of JSON results.
- Search diagnostics and debug output go to stderr. A search that returns no
  results and reports engine failures exits nonzero. A successful zero-match
  response returns `[]` with exit status zero.
- Results from working engines are retained when other engines fail. Previously
  fetched pages are retained if a later request fails.
- Text pagination deduplicates URLs, stops when a page adds no results, and
  fetches at most ten pages per display cycle. HTTP requests use `--timeout`.
- Non-terminal stdin disables interactive prompting; `--np` also disables it
  explicitly.

No queries are silently redirected to public instances. TLS verification stays
on unless explicitly disabled by the user.

## Server configuration

Enable the JSON API in your SearXNG `settings.yml` and select more than one
working web engine. For example, merge the following into your existing settings:

```yaml
use_default_settings: true
search:
  formats:
    - html
    - json
engines:
  - name: google cse
    disabled: false
    weight: 1.5
  - name: naver
    disabled: false
    weight: 0.7
```

These engines worked during verification, but availability and relevance vary
by network, region, language, and time. This snippet enables them in addition to
existing defaults; disable failing engines separately if appropriate. Restart
your SearXNG service after changing settings. SearXNG handles engine cooldowns;
do not repeatedly restart it to evade them.

Probe engines individually before relying on them:

```sh
searxngr --json -q 'python documentation' -e 'google cse'
searxngr --json -q 'site:docs.rs tokio spawn' -e naver
```

Test relevance, not just whether a nonempty result array is returned. Keep any
server secrets, credentials, and machine-specific deployment files private.

## Development

```sh
uv run pytest -q
uv build
uv tool install --force .
```

Regression tests use mocked HTTP responses and isolated configuration; they do
not need a running SearXNG instance or depend on live upstream availability.
