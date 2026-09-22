# Reliable searches and scripting

This fork hardens the CLI, but it still needs a reachable SearXNG instance and
working upstream engines. It cannot guarantee availability during network
outages, CAPTCHAs, rate limits, or simultaneous engine failures.

## CLI behavior

- GET and POST preserve query characters and use the same filters.
- `--json` returns one server page and writes the result array to stdout.
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

## Recovery and limits

`--retries` (INI: `retries`, default 2, range 0–5) retries transport failures,
timeouts, and HTTP 500/502/503/504 responses. Backoff starts at 0.25 seconds and
is capped at 2 seconds. HTTP 4xx responses, including 401/403/429, are not retried;
CAPTCHAs and invalid JSON do not trigger HTTP retries. `--timeout` applies to each
HTTP attempt, not the whole command. There are at most `1 + retries` attempts per
request, and a backup-engine request can add another such batch.

`--fallback-engines 'google,mwmbl'` (INI: `fallback_engines = google, mwmbl`)
enables one backup-engine batch if default engines return no results and report
failures. It is disabled by default, and an empty CLI value disables a configured
list. Engine names are comma-separated, preserving names containing spaces.

Backup requests use the same server, query, site, language, time, and safe-search
filters. They do not override explicit engine/category/bang selection, retry
authentication failures, or turn a genuine zero-match result into extra traffic.
Successful backup selection persists across pagination; a new search starts
with the server defaults again. If backup engines also fail or return nothing,
the command reports failure rather than falsely claiming success.

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

## Optional local-server health monitor (Linux/systemd)

The files in [`contrib/systemd`](../contrib/systemd) are for a local server at
`http://127.0.0.1:8080` managed by an **existing user** `searxng.service`.
They are not installed or enabled automatically by the Python package.
From a clone of this repository:

```sh
install -d ~/.local/share/searxng ~/.config/systemd/user
install -m 755 contrib/systemd/check-health.sh ~/.local/share/searxng/
install -m 644 contrib/systemd/searxng-healthcheck.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now searxng-healthcheck.timer
```

The timer checks only `/healthz` about once per minute. After two failed probes,
it restarts `searxng.service` and checks readiness. It never sends periodic
search queries or restarts the server because an upstream engine is blocked.
Each probe has a five-second limit; recovery is capped by a 120-second service
timeout. Check failures with:

```sh
journalctl --user -u searxng-healthcheck.service
```

Disable the timer before deliberately stopping the stack, otherwise it will
bring it back:

```sh
systemctl --user disable --now searxng-healthcheck.timer
```

This handles a stopped/unresponsive local HTTP server, not internet loss or
upstream search availability. It requires `curl` and a working stack service.

## Development

```sh
uv run pytest -q
uv build
uv tool install --force .
```

Regression tests use mocked HTTP responses and isolated configuration; they do
not need a running SearXNG instance or depend on live upstream availability.
