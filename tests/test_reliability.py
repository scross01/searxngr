"""Regression tests for search reliability; no live network needed."""

import json
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from searxngr import cli
from searxngr.client import SearXNGClient, SearXNGError, SearXNGJSONError


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Do not depend on the developer's config or installed browser handlers."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = tmp_path / "searxngr"
    config_dir.mkdir()
    (config_dir / "config.ini").write_text(
        "[searxngr]\nsearxng_url = https://example.com\nurl_handler =\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_query_and_filters_roundtrip(method):
    query = "C++ & C# 日本語 %20 &engines=evil #fragment\nnext"
    categories = ["social+media"]
    with patch("searxngr.client.httpx.Client") as http:
        getattr(http.return_value, method.lower()).return_value.json.return_value = {"results": []}
        client = SearXNGClient("https://example.com/")
        client.search(
            query,
            categories=categories,
            safe_search="strict",
            language="ja",
            time_range="week",
            pageno=2,
            http_method=method,
        )
        call = getattr(http.return_value, method.lower()).call_args
        if method == "GET":
            params = {k: v[0] for k, v in parse_qs(urlsplit(call.args[0]).query).items()}
        else:
            params = call.kwargs["data"]
        assert params == {
            "q": query,
            "format": "json",
            "categories": "social media",
            "safesearch": "2",
            "language": "ja",
            "time_range": "week",
            "pageno": "2",
        }
        assert categories == ["social+media"]
        assert call.args[0].startswith("https://example.com/search")


@pytest.mark.parametrize("payload", [None, [], {"error": "broken"}, {"results": "wrong"}])
def test_invalid_response_is_an_error(payload):
    with patch("searxngr.client.httpx.Client") as http:
        http.return_value.get.return_value.json.return_value = payload
        with pytest.raises(SearXNGJSONError):
            SearXNGClient("https://example.com").search("query")


def test_partial_engine_failure_keeps_results_and_stdout_clean(capsys):
    with patch("searxngr.client.httpx.Client") as http:
        results = [{"title": "Working", "url": "https://example.com"}]
        http.return_value.get.return_value.json.return_value = {
            "results": results,
            "unresponsive_engines": [["google", "CAPTCHA"]],
        }
        assert SearXNGClient("https://example.com").search("query") == results
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "CAPTCHA" in captured.err


def test_transport_failure_is_a_client_error():
    with patch("searxngr.client.httpx.Client") as http:
        http.return_value.get.side_effect = httpx.RemoteProtocolError("server disconnected")
        with pytest.raises(SearXNGError, match="server disconnected"):
            SearXNGClient("https://example.com").search("query")


def run_cli(arguments, pages):
    """Return the mocked client after a successful noninteractive invocation."""
    with (
        patch("sys.argv", ["searxngr", *arguments, "query"]),
        patch("searxngr.cli.SearXNGClient") as client,
        patch("searxngr.cli.print_results"),
        patch("searxngr.cli.run_interactive_loop") as interactive,
        patch("sys.stdin.isatty", return_value=False),
    ):
        client.return_value.search.side_effect = pages
        with pytest.raises(SystemExit) as exit_info:
            cli.main()
        assert exit_info.value.code == 0
        interactive.assert_not_called()
        return client.return_value


def test_json_fetches_only_one_page(capsys):
    results = [{"url": "https://example.com"}]
    client = run_cli(["--json"], [results])
    assert client.search.call_count == 1
    assert json.loads(capsys.readouterr().out) == results


def test_exact_page_size_does_not_fetch_again():
    results = [{"url": f"https://example.com/{i}"} for i in range(10)]
    assert run_cli(["--np"], [results]).search.call_count == 1


def test_repeated_page_stops_pagination():
    results = [{"url": "https://example.com"}]
    assert run_cli(["--np"], [results, results]).search.call_count == 2


def test_successful_page_survives_later_failure():
    assert run_cli(["--np"], [[{"url": "https://example.com"}], SearXNGError("timeout")]).search.call_count == 2


def test_pagination_is_bounded():
    pages = [[{"url": f"https://example.com/{i}"}] for i in range(11)]
    assert run_cli(["--np", "-n", "1000"], pages).search.call_count == 10


def _tty_run_cli(arguments, pages, stdout_tty: bool):
    """Run the CLI with stdin as a TTY and stdout as configured.

    The patched run_interactive_loop raises SystemExit, so a call through it
    is distinguishable from an exit at the non-interactive gate.
    """
    with (
        patch("sys.argv", ["searxngr", *arguments, "query"]),
        patch("searxngr.cli.SearXNGClient") as client,
        patch("searxngr.cli.print_results"),
        patch("searxngr.cli.run_interactive_loop") as interactive,
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout.isatty", return_value=stdout_tty),
    ):
        interactive.side_effect = SystemExit(0)
        client.return_value.search.side_effect = pages
        with pytest.raises(SystemExit) as exit_info:
            cli.main()
        return exit_info.value.code, interactive


def _full_page():
    """A full display page, so main does not auto-fetch a second one."""
    return [{"url": f"https://example.com/{i}"} for i in range(10)]


def test_interactive_mode_engages_on_tty_stdin_and_stdout():
    code, interactive = _tty_run_cli([], [_full_page()], stdout_tty=True)
    assert code == 0
    interactive.assert_called()


def test_redirected_stdout_disables_interactive_mode():
    """Regression: stdout redirected to a file/pipe must skip the prompt even
    when stdin is a TTY — an unanswerable prompt would block forever."""
    code, interactive = _tty_run_cli([], [_full_page()], stdout_tty=False)
    assert code == 0
    interactive.assert_not_called()


def test_failed_search_exits_nonzero_without_corrupting_json(capsys):
    with (
        patch("sys.argv", ["searxngr", "--json", "query"]),
        patch("searxngr.cli.SearXNGClient") as client,
    ):
        client.return_value.search.side_effect = SearXNGError("upstreams unavailable")
        with pytest.raises(SystemExit) as exit_info:
            cli.main()
        assert exit_info.value.code == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "upstreams unavailable" in captured.err
