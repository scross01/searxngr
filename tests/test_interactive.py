import pytest
from unittest.mock import MagicMock, patch

from searxngr.interactive import run_interactive_loop


RESULTS_WITH_URL = [
    {
        "title": "Test Result",
        "url": "https://example.com",
        "content": "Test content",
        "engine": "testengine",
        "category": "general",
        "engines": ["testengine"],
    }
]


class MockArgs:
    """Mock args object for testing"""

    def __init__(self):
        self.url_handler = "open"
        self.secondary_url_handler = None
        self.num = 10
        self.expand = False
        self.max_content_words = 128
        self.safe_search = "strict"
        self.time_range = None
        self.engines = None
        self.categories = None
        self.language = None
        self.site = None
        self.http_method = "GET"
        self.timeout = 30
        self.no_verify_ssl = False
        self.searxng_url = "https://searxng.example.com"


class TestInteractive:
    """Test interactive module functionality"""

    def test_run_interactive_loop_quit(self):
        """Test that quit command exits the loop"""
        mock_args = MockArgs()
        mock_results = []

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.return_value = "q"

            with pytest.raises(SystemExit) as exc_info:
                run_interactive_loop(
                    mock_args,
                    mock_results,
                    query="test query",
                    start_at=0,
                    pageno=1,
                    searxng=MagicMock(),
                )
            assert exc_info.value.code == 0

    def test_run_interactive_loop_help(self):
        """Test that help command displays help"""
        mock_args = MockArgs()
        mock_results = []

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["?", "q"]

            with patch("searxngr.interactive.console") as mock_console:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        mock_results,
                        query="test query",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
                mock_console.print.assert_called()

    def test_run_interactive_loop_new_search(self):
        """Test that entering a new query returns new search params"""
        mock_args = MockArgs()
        mock_results = []

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.return_value = "new search query"

            new_query, start_at, pageno, results = run_interactive_loop(
                mock_args,
                mock_results,
                query="old query",
                start_at=0,
                pageno=1,
                searxng=MagicMock(),
            )

            assert new_query == "new search query"
            assert start_at == 0
            assert pageno == 1

    def test_run_interactive_loop_toggle_expand(self):
        """Test that x command toggles expand"""
        mock_args = MockArgs()
        mock_args.expand = False
        mock_results = [
            {
                "title": "Test Result",
                "url": "https://example.com",
                "content": "Test content",
                "engine": "testengine",
                "category": "general",
                "engines": ["testengine"],
            }
        ]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["x", "q"]

            with patch("searxngr.interactive.print_results"):
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        mock_results,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
                assert mock_args.expand is True

    def test_run_interactive_loop_show_settings(self):
        """Test that s command shows settings"""
        mock_args = MockArgs()
        mock_args.searxng_url = "https://searxng.example.com"
        mock_results = []

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["s", "q"]

            with patch("searxngr.interactive.console") as mock_console:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        mock_results,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
                mock_console.print.assert_called()

    def test_run_interactive_loop_invalid_command(self):
        """Test that invalid command triggers new search"""
        mock_args = MockArgs()
        mock_results = []

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.return_value = "invalid_command_xyz"

            new_query, start_at, pageno, results = run_interactive_loop(
                mock_args,
                mock_results,
                query="test",
                start_at=0,
                pageno=1,
                searxng=MagicMock(),
            )

            assert new_query == "invalid_command_xyz"

    def test_open_index_routes_through_cli_open_url(self):
        """The primary-handler open (index command) must go through
        cli.open_url — the plan-007 dedup contract"""
        mock_args = MockArgs()

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["1", "q"]

            with patch("searxngr.cli.open_url") as mock_open:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        RESULTS_WITH_URL,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
            mock_open.assert_called_once_with("https://example.com", "open")

    def test_open_secondary_routes_through_cli_open_url(self):
        """The secondary handler (o command) resolves the handler locally and
        routes through cli.open_url"""
        mock_args = MockArgs()
        mock_args.secondary_url_handler = "firefox"

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["o 1", "q"]

            with patch("searxngr.cli.open_url") as mock_open:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        RESULTS_WITH_URL,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
            mock_open.assert_called_once_with("https://example.com", "firefox")

    def test_open_secondary_falls_back_to_primary_handler(self):
        """o command with no secondary_url_handler configured uses the
        primary handler"""
        mock_args = MockArgs()
        assert mock_args.secondary_url_handler is None

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["o 1", "q"]

            with patch("searxngr.cli.open_url") as mock_open:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        RESULTS_WITH_URL,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
            mock_open.assert_called_once_with("https://example.com", "open")

    def test_open_refused_url_does_not_spawn(self):
        """A non-http(s) result URL is refused by open_url's allowlist; the
        refusal path must be the shared one (open_url returns False)."""
        mock_args = MockArgs()
        results = [{**RESULTS_WITH_URL[0], "url": "file:///etc/passwd"}]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["1", "q"]

            with patch("searxngr.cli.open_url", return_value=False) as mock_open:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        results,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
            mock_open.assert_called_once_with("file:///etc/passwd", "open")
