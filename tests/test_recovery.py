"""Deterministic fault injection: retries without live search."""

import io

import httpx
import pytest

from searxngr.cli import create_parser
from searxngr.client import (
    SearXNGClient,
    SearXNGConnectionError,
    SearXNGEngineError,
    SearXNGHTTPError,
    SearXNGJSONError,
    SearXNGTimeoutError,
)
from searxngr.config import SearxngrConfig

RESULTS = [{"url": "https://example.com/result", "title": "Recovered"}]


@pytest.fixture(autouse=True)
def no_wait(monkeypatch):
    monkeypatch.setattr("searxngr.client.time.sleep", lambda seconds: None)


@pytest.fixture
def client_factory():
    clients = []

    def make(responses, **options):
        requests = []
        responses = iter(responses)

        def handler(request):
            requests.append(request)
            response = next(responses)  # An extra request is a test failure.
            if isinstance(response, Exception):
                raise response
            if isinstance(response, int):
                return httpx.Response(response)
            return httpx.Response(200, json=response)

        client = SearXNGClient("https://searxng.example.com", **options)
        client.client.close()
        client.client = httpx.Client(transport=httpx.MockTransport(handler))
        clients.append(client)
        return client, requests

    yield make
    for client in clients:
        client.client.close()


@pytest.fixture
def error_console_proxy(monkeypatch):
    """Capture client diagnostics through a console that always emits ANSI.

    The client module builds its own stderr console at import time; rich
    strips escape codes for non-terminals, so the test forces a terminal to
    observe the styling a TTY user actually sees.
    """
    from rich.console import Console

    import searxngr.client as client_module

    buffer = io.StringIO()
    forced = Console(file=buffer, stderr=True, force_terminal=True, color_system="truecolor")
    monkeypatch.setattr(client_module, "error_console", forced)
    return buffer


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize(
    "fault",
    [
        500,
        502,
        503,
        504,
        httpx.ConnectError("connection refused"),
        httpx.ReadTimeout("slow response"),
        httpx.RemoteProtocolError("disconnected"),
    ],
)
def test_transient_failure_recovers(client_factory, fault, method, capsys):
    client, requests = client_factory([fault, {"results": RESULTS}])
    assert client.search("C++ & C#", http_method=method) == RESULTS
    assert len(requests) == 2
    assert requests[0].url == requests[1].url
    assert requests[0].content == requests[1].content
    output = capsys.readouterr()
    assert output.out == ""
    assert "retry 1/2" in output.err


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429])
def test_permanent_http_errors_are_not_retried(client_factory, status):
    client, requests = client_factory([status])
    with pytest.raises(SearXNGHTTPError):
        client.search("query")
    assert len(requests) == 1


@pytest.mark.parametrize(
    "fault,error",
    [
        (503, SearXNGHTTPError),
        (httpx.ConnectError("offline"), SearXNGConnectionError),
        (httpx.ReadTimeout("timeout"), SearXNGTimeoutError),
    ],
)
def test_retries_are_bounded(client_factory, fault, error):
    client, requests = client_factory([fault] * 3)
    with pytest.raises(error):
        client.search("query")
    assert len(requests) == 3


def test_retries_can_be_disabled(client_factory):
    client, requests = client_factory([503], retries=0)
    with pytest.raises(SearXNGHTTPError):
        client.search("query")
    assert len(requests) == 1


def test_genuine_empty_search_returns_empty_list(client_factory):
    client, requests = client_factory([{"results": []}])
    assert client.search("no matches") == []
    assert len(requests) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"results": ["not an object"]},
        {"results": [], "unresponsive_engines": "wrong type"},
        {"results": [], "unresponsive_engines": [["incomplete"]]},
        {"results": [], "unresponsive_engines": [[{}, []]]},
    ],
)
def test_invalid_schema_does_not_crash_or_retry(client_factory, payload):
    client, requests = client_factory([payload])
    with pytest.raises(SearXNGJSONError):
        client.search("query")
    assert len(requests) == 1


def test_engine_failure_diagnostic_is_red_on_stderr(client_factory, error_console_proxy, no_wait):
    """Regression (aeded1f): engine diagnostics keep 0.8.2's red styling.

    v0.8.2 rendered `Engine: <name> [red]<error>[/red]`; the fork's stderr
    re-route accidentally disabled rich markup, leaving the error plain white.
    The diagnostic must go to stderr (JSON purity) AND keep the red error
    text a terminal user sees.
    """
    failures = [["google cse", "Suspended: too many requests"]]
    client, _ = client_factory([{"results": [], "unresponsive_engines": failures}])

    with pytest.raises(SearXNGEngineError, match="search engines failed"):
        client.search("query")

    rendered = error_console_proxy.getvalue()
    # Red ANSI wraps the error text, not the engine name (0.8.2 rendering).
    assert "Engine: google cse \x1b[31mSuspended: too many requests\x1b[0m" in rendered
    # Markup is parsed, not printed literally.
    assert "[red]" not in rendered


def test_engine_failure_diagnostic_is_plain_when_not_a_terminal(client_factory, capsys):
    """Same diagnostic through real (non-terminal) consoles: no ANSI codes."""
    failures = [["google cse", "Suspended: too many requests"]]
    client, _ = client_factory([{"results": [], "unresponsive_engines": failures}])

    with pytest.raises(SearXNGEngineError, match="search engines failed"):
        client.search("query")

    captured = capsys.readouterr()
    assert "Engine: google cse Suspended: too many requests" in captured.err
    assert "\x1b[" not in captured.err
    assert captured.out == ""


def test_preferences_header_is_preserved(client_factory):
    client, requests = client_factory([{"results": []}])
    headers = {"Accept": "text/html"}
    client.get("/preferences", headers)
    assert requests[0].headers["Accept"] == "text/html"
    assert headers == {"Accept": "text/html"}


def test_config_and_cli_preserve_retry_settings(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text("[searxngr]\nretries = 1\n")
    cfg = SearxngrConfig(config_path=str(tmp_path))
    parser = create_parser(cfg)
    defaults = parser.parse_args([])
    assert defaults.retries == 1
    assert parser.parse_args(["--retries", "0"]).retries == 0


@pytest.mark.parametrize("retries", [-1, 6, 1.5])
def test_invalid_retry_limits_are_rejected(retries):
    with pytest.raises(ValueError):
        SearXNGClient("https://searxng.example.com", retries=retries)
