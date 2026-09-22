"""Deterministic fault injection: retries and engine recovery without live search."""

from urllib.parse import parse_qs

import httpx
import pytest

from searxngr.client import (
    SearXNGClient,
    SearXNGConnectionError,
    SearXNGEngineError,
    SearXNGHTTPError,
    SearXNGJSONError,
    SearXNGTimeoutError,
)
from searxngr.config import SearxngrConfig
from searxngr.cli import create_parser

RESULTS = [{"url": "https://example.com/result", "title": "Recovered"}]
BLOCKED = {"results": [], "unresponsive_engines": [["primary", "CAPTCHA"]]}


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

        client = SearXNGClient("https://example.com", **options)
        client.client.close()
        client.client = httpx.Client(transport=httpx.MockTransport(handler))
        clients.append(client)
        return client, requests

    yield make
    for client in clients:
        client.client.close()


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
def test_permanent_http_errors_are_not_retried_or_bypassed(client_factory, status):
    client, requests = client_factory([status], fallback_engines=["backup"])
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
    client, requests = client_factory([fault] * 3, fallback_engines=["backup"])
    with pytest.raises(error):
        client.search("query")
    assert len(requests) == 3


def test_retries_can_be_disabled(client_factory):
    client, requests = client_factory([503], retries=0)
    with pytest.raises(SearXNGHTTPError):
        client.search("query")
    assert len(requests) == 1


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_backup_preserves_query_filters_and_server(client_factory, method, capsys):
    client, requests = client_factory(
        [BLOCKED, {"results": RESULTS}], fallback_engines=["backup one", "backup two"]
    )
    assert (
        client.search(
            "C++ & C#",
            site="example.org",
            language="en",
            safe_search="strict",
            time_range="week",
            http_method=method,
        )
        == RESULTS
    )
    assert len(requests) == 2
    first, second = requests
    if method == "GET":
        original, fallback = dict(first.url.params), dict(second.url.params)
    else:
        original = {k: v[0] for k, v in parse_qs(first.content.decode()).items()}
        fallback = {k: v[0] for k, v in parse_qs(second.content.decode()).items()}
    assert fallback.pop("engines") == "backup one,backup two"
    assert original == fallback
    assert fallback["q"] == "site:example.org C++ & C#"
    assert first.url.host == second.url.host == "example.com"
    assert "backup engines" in capsys.readouterr().err


@pytest.mark.parametrize(
    "options",
    [
        {"engines": ["chosen"]},
        {"categories": ["news"]},
        {"categories": ["general"]},
        {"pageno": 2},
        {"query": "!google query"},
    ],
)
def test_backup_never_overrides_explicit_selection(client_factory, options):
    client, requests = client_factory([BLOCKED], fallback_engines=["backup"])
    with pytest.raises(SearXNGEngineError):
        client.search(**{"query": "query", **options})
    assert len(requests) == 1


def test_success_and_genuine_empty_search_do_not_trigger_backup(client_factory):
    client, requests = client_factory(
        [
            {"results": RESULTS, "unresponsive_engines": [["other", "timeout"]]},
            {"results": []},
        ],
        fallback_engines=["backup"],
    )
    assert client.search("query") == RESULTS
    assert client.search("no matches") == []
    assert len(requests) == 2


@pytest.mark.parametrize("backup_response", [BLOCKED, {"results": []}])
def test_all_engines_failing_is_not_silently_successful(
    client_factory, backup_response
):
    client, requests = client_factory(
        [BLOCKED, backup_response], fallback_engines=["backup"]
    )
    with pytest.raises(SearXNGEngineError):
        client.search("query")
    assert len(requests) == 2


def test_backup_selection_persists_for_pagination_but_not_new_search(client_factory):
    client, requests = client_factory(
        [BLOCKED] + [{"results": RESULTS}] * 3, fallback_engines=["backup"]
    )
    client.search("query", pageno=1)
    client.search("query", pageno=2)
    client.search("query", pageno=1)
    assert requests[2].url.params["engines"] == "backup"
    assert requests[2].url.params["pageno"] == "2"
    assert "engines" not in requests[3].url.params


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
    client, requests = client_factory([payload], fallback_engines=["backup"])
    with pytest.raises(SearXNGJSONError):
        client.search("query")
    assert len(requests) == 1


def test_preferences_header_is_preserved(client_factory):
    client, requests = client_factory([{"results": []}])
    headers = {"Accept": "text/html"}
    client.get("/preferences", headers)
    assert requests[0].headers["Accept"] == "text/html"
    assert headers == {"Accept": "text/html"}


def test_config_and_cli_preserve_engine_names(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "[searxngr]\nretries = 1\nfallback_engines = google cse, mwmbl\n"
    )
    cfg = SearxngrConfig(config_path=str(tmp_path))
    parser = create_parser(cfg)
    defaults = parser.parse_args([])
    assert defaults.retries == 1
    assert defaults.fallback_engines == ["google cse", "mwmbl"]
    assert parser.parse_args(["--fallback-engines", ""]).fallback_engines == []
    assert parser.parse_args(["--retries", "0"]).retries == 0


@pytest.mark.parametrize("retries", [-1, 6, 1.5])
def test_invalid_retry_limits_are_rejected(retries):
    with pytest.raises(ValueError):
        SearXNGClient("https://example.com", retries=retries)
