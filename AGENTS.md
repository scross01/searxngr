# Project Overview: searxngr

`searxngr` is a command-line interface (CLI) tool designed to facilitate web searches directly from the terminal using [SearXNG](https://github.com/searxng/searxng) instances. It offers a rich set of features including colorized output, selection of various search engines and categories, safe search filtering, time-range filtering, and JSON output for scripting. The tool is cross-platform compatible (macOS, Linux, Windows) and includes an automatic configuration setup on first run.

## Key Technologies

*   **Python:** The primary programming language.
*   **SearXNG:** The search engine platform it interacts with.
*   **uv:** The recommended package manager for installation.

## Architecture

The project is structured as a CLI application, with its core logic residing in the `searxngr/` directory. It interacts with SearXNG instances via HTTP requests, processing and displaying results in a terminal-friendly format. Configuration is managed through an INI file.

# Building and Running

## Installation

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

## Basic Usage

To perform a search:

```bash
searxngr why is the sky blue
```

## Configuration

The configuration file is located at `$XDG_CONFIG_HOME/searxng/config.ini`. If not found, it will be created with a template. On first run, `searxngr` will prompt for your SearXNG instance URL.

Example `config.ini`:

```ini
[searxngr]
searxng_url = https://searxng.example.com
results_per_page = 10
safe_mode = moderate
expand = false
engines = duckduckgo google brave
```

# Development Conventions

## Code Style

Follow Python best practices and PEP 8 guidelines. Use Black and Flake8 style rules and limit the line length to 120 characters.

## Testing

`pytest` is used for unit and integration tests.

```bash
uv run pytest
```

## Contribution Guidelines

Contributions follow a standard GitHub flow: forking the repository, creating a feature branch, and submitting pull requests. Adherence to existing code style and the addition of tests for new features is expected.
