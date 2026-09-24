# Architecture Documentation

This document describes the architecture of **searxngr**, a command-line
interface tool for performing web searches using SearXNG instances.

## Table of Contents

1. [Overview](#overview)
1. [Core Components](#core-components)
1. [Component Relationships](#component-relationships)
1. [Data Flow](#data-flow)
1. [Configuration Architecture](#configuration-architecture)
1. [Search Categories](#search-categories)
1. [Fork Heritage and Active Fork Tracking](#fork-heritage-and-active-fork-tracking)
1. [External Dependencies](#external-dependencies)
1. [Error Handling](#error-handling)
1. [Interactive Features](#interactive-features)

## Overview

**searxngr** is a Python-based CLI application that provides a rich terminal
interface for searching the web through SearXNG instances. The application
follows a layered architecture pattern with clear separation between
presentation, business logic, and data access layers.

### Key Architectural Principles

- **Configuration-Driven Design**: All aspects configurable through INI files
  and command-line arguments
- **Modular Component Architecture**: Each component has a single responsibility
- **XDG Compliance**: Follows XDG Base Directory specification for configuration
  management
- **Graceful Degradation**: Handles missing data and network failures gracefully

## Core Components

### 1. CLI Entry Point (`searxngr/cli.py`)

The central orchestrator that coordinates all application functionality:

- **`main()`**: Primary entry point handling argument parsing and execution flow

### 2. HTTP Client (`searxngr/client.py`)

Abstracts all communication with SearXNG instances:

- Supports both GET and POST HTTP methods
- Configurable timeouts and SSL verification
- Custom User-Agent headers
- JSON response parsing with error handling
- Basic authentication support
- Bounded retry loop for transient failures (retries default 2, range 0–5): only
  transport failures, timeouts, and HTTP 500/502/503/504 are retried, with
  exponential backoff starting at 0.25 seconds and capped at 2 seconds. HTTP 4xx
  responses, CAPTCHAs, and invalid JSON do **not** trigger retries. `--timeout`
  applies per HTTP attempt, not to the whole command.
- Custom exception hierarchy for testable error handling:
  - `SearXNGError` - base exception
  - `SearXNGConnectionError` - connection failures
  - `SearXNGTimeoutError` - timeout errors
  - `SearXNGHTTPError` - HTTP error responses
  - `SearXNGJSONError` - JSON decode errors
  - `SearXNGEngineError` - search-engine failures

### 3. Configuration Management (`searxngr/config.py`)

Handles all configuration aspects:

- XDG-compliant configuration file management
- First-time setup wizard
- Environment variable integration
- Default value management
- Configuration validation

### 4. Engine Management (`engines.py`)

Dynamically discovers and manages search engines:

- Parses SearXNG preferences HTML
- Extracts engine capabilities and metadata
- Manages engine categories and reliability scores
- Handles bang commands and engine switching

### 5. Console Interface (`searxngr/console.py`)

Provides enhanced terminal interaction:

- Rich console formatting
- Command history navigation
- Password input support
- Interactive engine management

### 6. Result Formatter (`searxngr/formatter.py`)

Handles search result display:

- `print_results()`: Formats and displays search results
- Category-specific output (news, images, videos, music, maps, files, science)
- URL parsing using `urllib.parse`
- Content truncation and HTML-to-text conversion
- Terminal width-aware formatting

### 7. Interactive Commands (`searxngr/interactive.py`)

Manages interactive console session:

- `run_interactive_loop()`: Handles interactive command processing
- Navigation commands (n, p, f for next/previous/first page)
- Result opening (index to open, c to copy URL, o for secondary handler)
- Dynamic configuration (e for engines, t for time range, F for safe search)
- Debug toggle and settings display

### 8. Constants and Helpers (`searxngr/constants.py`)

Global constants and utility functions:

- Default settings and configuration values
- Helper functions: `parse_engine_command()`, `validate_engines()`,
  `validate_url_handler()`, `validate_result_url()` (scheme allowlist for
  opening result URLs), `validate_url_syntax()` (zero-network URL syntax check
  at startup)
- Platform-specific default editors and time-range definitions
- Search category definitions

## Component Relationships

```mermaid
graph TB
    A[CLI Arguments] --> B[cli.py main]
    B --> C[config.py SearxngrConfig]
    B --> D[client.py SearXNGClient]
    B --> E[formatter.py print_results]
    B --> F[interactive.py run_interactive_loop]
    B --> G[constants.py]
    
    C --> H[Configuration File]
    C --> I[XDG Directories]
    
    D --> J[HTTP Requests]
    D --> K[JSON Parsing]
    D --> L[Custom Exceptions]
    
    M[engines.py] --> N[Engine Discovery]
    M --> O[Category Management]
    
    P[console.py] --> Q[Rich Formatting]
    P --> R[History Navigation]
    
    E --> Q
    E --> S[Result Processing]
    
    F --> T[Prompt Input]
    F --> U[Command Parsing]
    F --> Q
    
    G --> V[Constants]
    G --> W[Helper Functions]
    
    style B fill:#e1f5fe
    style C fill:#f3e5f5
    style D fill:#e8f5e8
    style M fill:#fff3e0
    style P fill:#fce4ec
    style E fill:#fff8e1
    style F fill:#e0f7fa
```

## Data Flow

### Search Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI as main()
    participant Config as SearxngrConfig
    participant Client as SearXNGClient
    participant SearXNG as SearXNG Instance
    participant Display as print_results()
    
    User->>CLI: Execute search command
    CLI->>Config: Load configuration
    Config-->>CLI: Return settings
    CLI->>Client: Initialize HTTP client
    Client->>SearXNG: HTTP request
    SearXNG-->>Client: JSON response
    Client-->>CLI: Parsed results
    CLI->>Display: Format results
    Display-->>User: Rich terminal output
```

### Configuration Loading Sequence

```mermaid
flowchart TD
    A[Application Start] --> B[XDG Config Directory Check]
    B --> C{Config File Exists?}
    C -->|No| D[Run Setup Wizard]
    C -->|Yes| E[Load Configuration]
    D --> F[Create Config File]
    F --> E
    E --> G[Validate Settings]
    G --> H{Valid Configuration?}
    H -->|No| I[Show Error & Exit]
    H -->|Yes| J[Application Ready]
    
    style D fill:#ffcdd2
    style I fill:#ffcdd2
    style J fill:#c8e6c9
```

## Configuration Architecture

### Configuration File Structure

```ini
[searxngr]
searxng_url = https://searxng.example.com
result_count = 10
safe_search = strict
engines = duckduckgo google brave
categories = general
expand = false
language = en
http_method = GET
timeout = 30
retries = 2
max_content_words = 128
no_verify_ssl = false
no_user_agent = false
no_color = false
url_handler = open
secondary_url_handler =
searxng_username =
searxng_password =
```

### Configuration Precedence

1. **Command-line arguments** (highest priority)
1. **Configuration file**
1. **Default values** (lowest priority)

### XDG Directory Compliance

- **Primary**: `$XDG_CONFIG_HOME/searxngr/config.ini`
- **Fallback**: `~/.config/searxngr/config.ini`
- **Development**: Local `config.ini` for testing

## Search Categories

The architecture provides specialized handling for different result types:

### Category-Specific Processing

```mermaid
graph LR
    A[Raw Results] --> B{Category Detection}
    
    B -->|News| C[Date Formatting<br/>Publication Metadata]
    B -->|Images| D[Resolution Display<br/>Source Information]
    B -->|Videos| E[Duration Processing<br/>Author Metadata]
    B -->|Music| F[Length Information<br/>Author Details]
    B -->|Maps| G[Address Parsing<br/>Coordinate Display]
    B -->|General| H[Standard Formatting]
    
    C --> I[Terminal Output]
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I
    
    style B fill:#e3f2fd
    style I fill:#e8f5e8
```

### Content Processing Pipeline

1. **HTML to Text Conversion**: Uses `html2text` for content previews
1. **Content Truncation**: Limits to `MAX_CONTENT_WORDS` (128 words)
1. **Date Parsing**: `dateutil.parser` with `babel` localization
1. **Terminal Formatting**: Dynamic width adjustment using
   `os.get_terminal_size()`

## Fork Heritage and Active Fork Tracking

searxngr's 0.9.0 release incorporates the reliability work of
[wawow830](https://github.com/wawow830/searxngr)'s fork, merged locally from
per-fork-commit cherry-picks (original authorship preserved in git history;
credit recorded in the CHANGELOG 0.9.0 entry). This section tracks what was
brought across and what was deliberately not.

### Initial hardening brought across from wawow830

- **Bounded retries with backoff** — `--retries` flag and `retries` config key
  (default 2, max 5), retrying only transport failures, timeouts, and HTTP
  500/502/503/504; 0.25 s initial backoff capped at 2 s.
- **Diagnostic stream discipline** — search diagnostics and warnings belong on
  stderr; stdout carries results only (just JSON in `--json` mode).
- **Pagination hardening** — text pagination deduplicates URLs, stops on
  repeated pages, and fetches at most ten pages per display cycle; `--json`
  always returns exactly one server page (`-n` controls text display only).
- **Partial-result preservation** — a failed engine contributes an error
  diagnostic while results from healthy engines are still shown; a successful
  zero-match search returns `[]`, a failure without results exits nonzero.
- **Non-interactive safety** — interactive prompting is disabled when stdin or
  stdout is not a terminal (pipes and file redirects); `--np` forces it off.

### Deliberately not ported

- **`--fallback-engines`** — wawow830's backup-engine option was specifically
  excluded from being ported back. It duplicated `--engines`, and hidden engine
  substitution contradicts the tool's explicit-selection philosophy (maintainer
  decision, 2026-09-23; the fork's `fallback_engines` config keys are silently
  ignored).
- **Watchdog / systemd recovery service** — the fork itself removed this
  infrastructure in its final commit; no background monitors, automatic server
  restarts, or hidden public-instance fallbacks exist, by design.

### Fork tracking status

| Fork | Status | |---|---| |
[wawow830/searxngr](https://github.com/wawow830/searxngr) | **Merged** —
reliability work incorporated in 0.9.0 (cherry-picks `f905838`, `9e9879e`,
`d14707e`); `--fallback-engines` excluded; re-check before future merges | |
n4s5ti/searxngr | Nothing to merge — stale May 2026 snapshot, 0 commits ahead |
| noahbenjamin1994/searxngr | Nothing to merge — earlier work already in
upstream `main` |

## External Dependencies

### Core Runtime Dependencies

- **`httpx`**: Async HTTP client for SearXNG communication
- **`rich`**: Terminal formatting and rich text display
- **`prompt-toolkit`**: Interactive console features and command history
- **`beautifulsoup4`**: HTML parsing for engine extraction
- **`html2text`**: HTML to markdown conversion for content previews
- **`babel`**: Date localization and formatting
- **`python-dateutil`**: Robust date parsing
- **`xdg-base-dirs`**: Cross-platform configuration directory management
- **`pyperclip`**: Clipboard integration for URLs

### Development Dependencies

- **`pytest`**: Testing framework with extensive mocking support
- **`ruff`**: Linting and formatting (flake8-equivalent rule set, 120 character
  line limit)
- **`hatchling`**: Build backend for package distribution
- **`uv`**: Package manager and tool installer

### Dependency Relationships

```mermaid
graph TB
    A[searxngr] --> B[httpx]
    A --> C[rich]
    A --> D[prompt-toolkit]
    A --> E[beautifulsoup4]
    A --> F[html2text]
    A --> G[babel]
    A --> H[python-dateutil]
    A --> I[xdg-base-dirs]
    A --> J[pyperclip]
    
    C --> K[rich.console]
    C --> L[rich.table]
    C --> M[rich.panel]
    
    D --> N[prompt_toolkit]
    D --> O[prompt_toolkit.history]
    
    style A fill:#e1f5fe
```

## Error Handling

### Custom Exception Hierarchy

The client uses a custom exception hierarchy for testable error handling:

- **`SearXNGError`**: Base exception for all SearXNG-related errors
- **`SearXNGConnectionError`**: Raised when connection to SearXNG instance fails
- **`SearXNGTimeoutError`**: Raised when request times out
- **`SearXNGHTTPError`**: Raised for HTTP error responses (4xx, 5xx)
- **`SearXNGJSONError`**: Raised when JSON response cannot be decoded
- **`SearXNGEngineError`**: Raised for search-engine failures

Exceptions are caught in `cli.py` and displayed to the user with appropriate
error messages.

### HTTP Error Management

- **JSON Decode Errors**: Graceful handling via `SearXNGJSONError`
- **Connection Failures**: Timeout and network error handling via
  `SearXNGConnectionError`
- **SSL Issues**: Configurable certificate verification
- **Engine Failures**: Reporting of unresponsive search engines

### User Experience Error Handling

- **Configuration Errors**: Clear error messages with setup guidance
- **First-time Setup**: Interactive wizard for initial configuration
- **Debug Mode**: Verbose error output for troubleshooting
- **Graceful Degradation**: Continued operation with missing data

### Error Recovery Flow

```mermaid
flowchart TD
    A[Operation] --> B{Error Occurred?}
    B -->|No| C[Continue Processing]
    B -->|Yes| D[Error Classification]
    
    D --> E[Network Error]
    D --> F[Configuration Error]
    D --> G[Data Error]
    
    E --> H[Retry Logic]
    F --> I[Setup Guidance]
    G --> J[Skip Component]
    
    H --> K{Retry Successful?}
    K -->|Yes| C
    K -->|No| L[Report & Continue]
    
    I --> M[Exit with Help]
    J --> C
    L --> C
    
    style F fill:#ffcdd2
    style M fill:#ffcdd2
```

## Interactive Features

### Console Engine Management

The application supports dynamic engine management during interactive sessions:

- **Engine Switching**: Add/remove engines with `e +engine` or `e -engine`
- **Category Management**: Switch between search categories
- **History Navigation**: Arrow key navigation through search history
- **URL Handlers**: Configurable primary and secondary URL handlers

### Interactive Console Architecture

```mermaid
graph TB
    A[InteractiveConsole] --> B[prompt_toolkit Integration]
    A --> C[Rich Console]
    A --> D[History Management]
    
    B --> E[Command Parsing]
    B --> F[Auto-completion]
    B --> G[Key Bindings]
    
    C --> H[Rich Formatting]
    C --> I[Color Schemes]
    C --> J[Tables & Panels]
    
    D --> K[Search History]
    D --> L[Navigation Commands]
    D --> M[Session Persistence]
    
    style A fill:#e1f5fe
```

### Browser Integration

- **Primary URL Handler**: System default browser
- **Secondary URL Handler**: Alternative browser or tools
- **Platform-specific Defaults**: Different defaults per operating system
- **Custom Commands**: Support for custom URL opening commands

______________________________________________________________________

## Architecture Summary

The searxngr architecture demonstrates a well-structured CLI application with:

- **Clear separation of concerns** across presentation, business logic, and data
  layers
- **Robust configuration management** following XDG standards
- **Extensible search engine management** with dynamic discovery
- **Rich terminal interface** with interactive features
- **Comprehensive error handling** with bounded retries for reliable operation
- **Modular design** enabling easy testing and maintenance

This architecture provides a solid foundation for both current functionality and
future enhancements while maintaining simplicity for end users.

> **Note on reliability claims**: searxngr needs a reachable SearXNG server with
> JSON output enabled and working search engines; it cannot guarantee results
> during outages or upstream blocks. There are no background monitors, automatic
> server restarts, or hidden public-instance fallbacks — see the fork-heritage
> section above.
