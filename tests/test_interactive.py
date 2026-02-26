import pytest
from unittest.mock import MagicMock, patch

from searxngr.interactive import run_interactive_loop


class MockArgs:
    """Mock args object for testing"""

    def __init__(self):
        self.url_handler = "open"
        self.secondary_url_handler = None
        self.num = 10
        self.expand = False
        self.safe_search = "strict"
        self.time_range = None
        self.engines = None
        self.categories = None
        self.language = None
        self.site = None
        self.http_method = "GET"
        self.timeout = 30
        self.no_verify_ssl = False
        self.searxng_url = "https://example.com"


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
        mock_args.searxng_url = "https://example.com"
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
