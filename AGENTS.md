# Project Overview: searxngr

`searxngr` is a command-line interface (CLI) tool designed to facilitate web
searches directly from the terminal using
[SearXNG](https://github.com/searxng/searxng) instances. It offers a rich set of
features including colorized output, selection of various search engines and
categories, safe search filtering, time-range filtering, and JSON output for
scripting. The tool is cross-platform compatible (macOS, Linux, Windows) and
includes an automatic configuration setup on first run.

## Key Technologies

- **Python:** The primary programming language.
- **SearXNG:** The search engine platform it interacts with.
- **uv:** The recommended package manager for installation.

## Architecture

The project is structured as a CLI application, with its core logic residing in
the `searxngr/` directory. It interacts with SearXNG instances via HTTP
requests, processing and displaying results in a terminal-friendly format.
Configuration is managed through an INI file.

Detailed design documentation — component map, data flow, retry semantics, and
the fork-heritage section tracking what was merged from wawow830's fork (and
what was deliberately excluded, such as `--fallback-engines`) — lives in
[ARCHITECTURE.md](ARCHITECTURE.md). Development setup, test commands, and PR
conventions are in [CONTRIBUTING.md](CONTRIBUTING.md). When cherry-picking or
porting commits from forks, preserve the original commit authorship.

## Building and Running

### Installation

The recommended way to install `searxngr` is using the `uv` package manager:

```bash
uv tool install https://github.com/scross01/searxngr.git
```

To install from source:

```bash
git clone https://github.com/scross01/searxngr.git
cd searxngr
uv venv && source .venv/bin/activate # (optional)
uv sync
uv tool install .
```

### Basic Usage

To perform a search:

```bash
searxngr why is the sky blue
```

### Configuration

The configuration file is located at `$XDG_CONFIG_HOME/searxngr/config.ini`. If
not found, it will be created with a template. On first run, `searxngr` will
prompt for your SearXNG instance URL.

Example `config.ini`:

```ini
[searxngr]
searxng_url = https://searxng.example.com
result_count = 10
safe_search = moderate
expand = false
engines = duckduckgo google brave
retries = 2
```

## Development Conventions

### Code Style

Follow Python best practices and PEP 8 guidelines. Use ruff for formatting and
linting (flake8-equivalent rules plus import sorting, pyupgrade typing
modernization, and PLR1722 `sys.exit()` enforcement) and limit the line length
to 120 characters.

### Testing

`pytest` is used for unit and integration tests. The offline suite needs no
network, server, or configuration file and must stay deterministic:

```bash
make test # offline suite (also: uv run --locked pytest)
make test-integration # docker SearXNG stack + tests/integration
make lint # ruff check (gates)
make fmt # ruff format + mdformat
```

The live integration tests in `tests/integration/` are skipped unless the
`SEARXNG_URL` environment variable is set, so a plain pytest run never needs a
server.

### Contribution Guidelines

Contributions follow a standard GitHub flow: forking the repository, creating a
feature branch, and submitting pull requests. Adherence to existing code style
and the addition of tests for new features is expected.
