# Contributing to searxngr

Contributions are welcome and are accepted through GitHub pull requests: fork
the repository, create a feature branch, and open a pull request against `main`.
Continuous integration runs the offline test suite and a package build on every
pull request (Python 3.10, 3.12, and 3.14), so keep the suite green before
requesting a review.

## Development setup

Requires the [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
package manager and Python >= 3.10 (see `.python-version`).

```shell
git clone https://github.com/scross01/searxngr.git
cd searxngr
uv sync                 # creates .venv, installs the project + dev tools
uv run searxngr --help  # run from the checkout
```

To install your checkout as a tool instead of running it in place:

```shell
uv tool install .
```

## Building

```shell
make build              # equivalent to: uv build
```

Produces `dist/searxngr-<version>.tar.gz` and a matching wheel. The version is
read from `searxngr/__version__.py` by hatchling.

## Running the tests

The offline suite needs no network, no SearXNG server, and no configuration
file:

```shell
make test               # equivalent to: uv run --locked pytest
```

- Tests are deterministic and offline: HTTP interactions are injected with
  `httpx.MockTransport`-style handlers (`tests/test_recovery.py`), CLI behavior
  is exercised with mocked clients (`tests/test_reliability.py`), and one test
  drives the real CLI against a localhost HTTP server
  (`tests/test_cli_recovery.py`).
- Live integration tests live in `tests/integration/` and are skipped
  automatically unless `SEARXNG_URL` is set, so a plain pytest run never
  requires a server.

Run a single file or a subset:

```shell
uv run pytest tests/test_recovery.py -q
uv run pytest tests/test_recovery.py -k retries -v
```

### Integration suite against a real SearXNG

The repository ships a docker compose stack with a SearXNG test instance (JSON
format enabled, limiter disabled, port bound to loopback) — see
`docker/README.md`. This works on a fresh clone:

```shell
make test-integration   # build image, start SearXNG, run tests/integration, tear down
```

To run the same suite from the host against any reachable instance with JSON
output enabled:

```shell
SEARXNG_URL=http://127.0.0.1:8080 make test-live
```

## Formatting and linting

```shell
make lint               # flake8, informational
```

The project follows PEP 8 with a 120-character line limit (configured in
`pyproject.toml` and `.vscode/settings.json`).

> **Note on `make fmt`:** it runs black and mdformat over the whole tree.
> Upstream sources are not yet fully black-clean, so running it today
> reformats many files unrelated to your change. If you want to do a
> tree-wide formatting pass, do it as its own standalone formatting-only
> commit and never mix it with functional changes — otherwise review of
> your actual change becomes impossible.

## Submitting a pull request

1. Fork the repository and create a topic branch from `main`.
1. Make your change, adding or adjusting tests where behavior changes.
1. Run `make test` (and `make test-integration` if you touched search or
   container behavior) and `make build`.
1. Update `CHANGELOG.md` with a user-facing summary of the change.
1. Open a pull request describing the motivation; keep PRs focused on a single
   change.

Commit messages follow the conventional-commit style used in the history
(`feat:`, `fix:`, `chore:`, …).

### Guidelines

- Configuration keys and CLI flags are additive: do not rename existing
  `config.ini` keys or options.
- Diagnostics belong on stderr; stdout carries results only (just JSON in
  `--json` mode).
- New user-visible behavior should be reflected in `README.md` and, when
  reliability-related, in `docs/reliability.md`.
