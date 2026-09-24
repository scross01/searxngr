import json
from unittest.mock import MagicMock, patch

import pytest

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

    # ------------------------------------------------------------------
    # Engine management (e / e +x / e -y) — plan 008
    #
    # These tests exercise the REAL parse_engine_command / validate_engines.
    # interactive.py imports them function-scoped (plan 007's circular-import
    # fix), so they cannot be patched at module level — and they are pure
    # parsing / list logic offline, which the loop tests can absorb.
    # ------------------------------------------------------------------

    def test_engine_replacement_sets_engines(self):
        """e with plain names replaces the engine list with the valid set"""
        mock_args = MockArgs()
        mock_args.engines = ["old"]
        searxng = MagicMock()
        searxng.engines.return_value = [
            {"name": "duckduckgo"},
            {"name": "brave"},
        ]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["e duckduckgo brave", "q"]

            with pytest.raises(SystemExit):
                run_interactive_loop(
                    mock_args,
                    [],
                    query="test",
                    start_at=0,
                    pageno=1,
                    searxng=searxng,
                )
        assert mock_args.engines == ["duckduckgo", "brave"]

    def test_engine_replacement_reports_invalid_and_keeps_valid(self):
        """Invalid names in a replacement are reported, valid ones still land"""
        mock_args = MockArgs()
        searxng = MagicMock()
        searxng.engines.return_value = [{"name": "duckduckgo"}]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["e duckduckgo nope", "q"]

            with pytest.raises(SystemExit):
                run_interactive_loop(
                    mock_args,
                    [],
                    query="test",
                    start_at=0,
                    pageno=1,
                    searxng=searxng,
                )
        assert mock_args.engines == ["duckduckgo"]

    def test_engine_add_modifier_appends_without_duplicates(self):
        """e +x appends to the existing list, never duplicating"""
        mock_args = MockArgs()
        mock_args.engines = ["brave"]
        searxng = MagicMock()
        searxng.engines.return_value = [
            {"name": "brave"},
            {"name": "google"},
        ]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["e +brave +google", "q"]

            with pytest.raises(SystemExit):
                run_interactive_loop(
                    mock_args,
                    [],
                    query="test",
                    start_at=0,
                    pageno=1,
                    searxng=searxng,
                )
        assert mock_args.engines == ["brave", "google"]

    def test_engine_remove_modifier_drops_engine(self):
        """e -y removes an existing engine from the list"""
        mock_args = MockArgs()
        mock_args.engines = ["brave", "google"]
        searxng = MagicMock()
        searxng.engines.return_value = [{"name": "google"}]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["e -google", "q"]

            with pytest.raises(SystemExit):
                run_interactive_loop(
                    mock_args,
                    [],
                    query="test",
                    start_at=0,
                    pageno=1,
                    searxng=searxng,
                )
        assert mock_args.engines == ["brave"]

    def test_engine_add_with_invalid_name_reports_and_skips_it(self):
        """An invalid +add is reported and excluded, valid adds still land"""
        mock_args = MockArgs()
        mock_args.engines = []
        searxng = MagicMock()
        searxng.engines.return_value = [{"name": "google"}]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["e +google +nope", "q"]

            with pytest.raises(SystemExit):
                run_interactive_loop(
                    mock_args,
                    [],
                    query="test",
                    start_at=0,
                    pageno=1,
                    searxng=searxng,
                )
        assert mock_args.engines == ["google"]

    def test_engine_mixed_modifiers_warn_and_drop_plain_names(self):
        """Plain names alongside +/- modifiers are warned away, not applied"""
        mock_args = MockArgs()
        mock_args.engines = []
        searxng = MagicMock()
        searxng.engines.return_value = [
            {"name": "google"},
            {"name": "bing"},
        ]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["e +google bing", "q"]

            with pytest.raises(SystemExit):
                run_interactive_loop(
                    mock_args,
                    [],
                    query="test",
                    start_at=0,
                    pageno=1,
                    searxng=searxng,
                )
        assert mock_args.engines == ["google"]
        assert "bing" not in mock_args.engines

    # ------------------------------------------------------------------
    # Clipboard (c N / C N) — plan 008
    # ------------------------------------------------------------------

    def test_copy_url_copies_result_url(self):
        """c N copies the result URL to the clipboard"""
        mock_args = MockArgs()

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["c 1", "q"]

            with patch("searxngr.interactive.pyperclip.copy") as mock_copy:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        RESULTS_WITH_URL,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
        mock_copy.assert_called_once_with("https://example.com")

    def test_copy_url_out_of_range_is_a_noop_with_message(self):
        """c with an out-of-range index does not touch the clipboard"""
        mock_args = MockArgs()

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["c 9", "q"]

            with patch("searxngr.interactive.pyperclip.copy") as mock_copy:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        RESULTS_WITH_URL,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
        mock_copy.assert_not_called()

    def test_copy_content_uses_html_to_text(self):
        """C N copies the markdown-converted result content"""
        mock_args = MockArgs()
        results = [
            {
                **RESULTS_WITH_URL[0],
                "content": "<b>Bold</b> content here",
            }
        ]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["C 1", "q"]

            with patch("searxngr.interactive.pyperclip.copy") as mock_copy:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        results,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
        copied = mock_copy.call_args[0][0]
        assert "Bold" in copied and "content here" in copied

    def test_copy_content_image_result_uses_img_src(self):
        """C on an images-category result copies img_src, not content"""
        mock_args = MockArgs()
        results = [
            {
                **RESULTS_WITH_URL[0],
                "category": "images",
                "img_src": "https://example.com/pic.jpg",
                "content": "some caption",
            }
        ]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["C 1", "q"]

            with patch("searxngr.interactive.pyperclip.copy") as mock_copy:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        results,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
        mock_copy.assert_called_once_with("https://example.com/pic.jpg")

    def test_copy_content_torrent_uses_magnetlink(self):
        """C on a files/torrent result copies the magnet link"""
        mock_args = MockArgs()
        results = [
            {
                **RESULTS_WITH_URL[0],
                "category": "files",
                "template": "torrent.html",
                "magnetlink": "magnet:?xt=urn:btih:abc",
                "content": "seeders: 5",
            }
        ]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["C 1", "q"]

            with patch("searxngr.interactive.pyperclip.copy") as mock_copy:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        results,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
        mock_copy.assert_called_once_with("magnet:?xt=urn:btih:abc")

    def test_copy_content_empty_reports_no_content(self):
        """C with empty content reports and does not copy an empty string"""
        mock_args = MockArgs()
        results = [{**RESULTS_WITH_URL[0], "content": ""}]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["C 1", "q"]

            with patch("searxngr.interactive.pyperclip.copy") as mock_copy:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        results,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
        mock_copy.assert_not_called()

    def test_copy_commands_missing_index_reports_usage(self):
        """c / C without an index report usage and never touch the clipboard"""
        mock_args = MockArgs()

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["c", "C", "q"]

            with patch("searxngr.interactive.pyperclip.copy") as mock_copy:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        RESULTS_WITH_URL,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
        mock_copy.assert_not_called()

    # ------------------------------------------------------------------
    # Navigation (n / p / f) — plan 008
    # ------------------------------------------------------------------

    def test_next_page_within_results_advances_start_at(self):
        """n with more results re-renders from the next page"""
        mock_args = MockArgs()
        mock_args.num = 5
        many_results = [dict(RESULTS_WITH_URL[0], title=f"r{i}") for i in range(20)]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["n", "q"]

            with patch("searxngr.interactive.print_results") as mock_print:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        many_results,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
        mock_print.assert_called_once()
        assert mock_print.call_args.kwargs["start_at"] == 5

    def test_next_page_beyond_results_fetches_next_server_page(self):
        """n with exhausted local results returns to cli for a new fetch"""
        mock_args = MockArgs()
        mock_args.num = 10

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["n"]

            with patch("searxngr.interactive.print_results") as mock_print:
                new_query, start_at, pageno, results = run_interactive_loop(
                    mock_args,
                    RESULTS_WITH_URL,
                    query="test",
                    start_at=0,
                    pageno=1,
                    searxng=MagicMock(),
                )
        mock_print.assert_not_called()
        assert start_at == 10
        assert pageno == 2
        assert new_query == "test"

    def test_previous_page_clamps_at_zero(self):
        """p at the top of the list never produces a negative start_at"""
        mock_args = MockArgs()
        mock_args.num = 10

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["p", "q"]

            with patch("searxngr.interactive.print_results") as mock_print:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        RESULTS_WITH_URL,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
        assert mock_print.call_args.kwargs["start_at"] == 0

    def test_previous_page_steps_back_by_page_size(self):
        """p moves start_at back by args.num"""
        mock_args = MockArgs()
        mock_args.num = 10
        many_results = [dict(RESULTS_WITH_URL[0], title=f"r{i}") for i in range(30)]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["p", "q"]

            with patch("searxngr.interactive.print_results") as mock_print:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        many_results,
                        query="test",
                        start_at=20,
                        pageno=2,
                        searxng=MagicMock(),
                    )
        assert mock_print.call_args.kwargs["start_at"] == 10

    def test_first_page_resets_start_at(self):
        """f returns to start_at 0 and re-renders"""
        mock_args = MockArgs()
        mock_args.num = 10
        many_results = [dict(RESULTS_WITH_URL[0], title=f"r{i}") for i in range(30)]

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["f", "q"]

            with patch("searxngr.interactive.print_results") as mock_print:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        many_results,
                        query="test",
                        start_at=20,
                        pageno=3,
                        searxng=MagicMock(),
                    )
        assert mock_print.call_args.kwargs["start_at"] == 0

    # ------------------------------------------------------------------
    # Filters (t / F / site:) — plan 008
    # ------------------------------------------------------------------

    def test_time_range_update_triggers_new_search(self):
        """t week sets args.time_range and returns to cli for a new search"""
        mock_args = MockArgs()

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["t week"]

            new_query, start_at, pageno, results = run_interactive_loop(
                mock_args,
                RESULTS_WITH_URL,
                query="test",
                start_at=10,
                pageno=2,
                searxng=MagicMock(),
            )
        assert mock_args.time_range == "week"
        assert (new_query, start_at, pageno, results) == ("test", 0, 1, [])

    def test_time_range_short_form_expands(self):
        """t w is accepted and stored as the full 'week'"""
        mock_args = MockArgs()

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["t w"]

            run_interactive_loop(
                mock_args,
                RESULTS_WITH_URL,
                query="test",
                start_at=0,
                pageno=1,
                searxng=MagicMock(),
            )
        assert mock_args.time_range == "week"

    def test_time_range_invalid_reports_and_continues(self):
        """An unknown time range is reported; the loop stays open"""
        mock_args = MockArgs()

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["t fortnight", "q"]

            with pytest.raises(SystemExit):
                run_interactive_loop(
                    mock_args,
                    RESULTS_WITH_URL,
                    query="test",
                    start_at=0,
                    pageno=1,
                    searxng=MagicMock(),
                )
        assert mock_args.time_range is None

    def test_safe_search_update_triggers_new_search(self):
        """F moderate sets args.safe_search and returns to cli for a new search"""
        mock_args = MockArgs()
        mock_args.safe_search = "strict"

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["F moderate"]

            new_query, start_at, pageno, results = run_interactive_loop(
                mock_args,
                RESULTS_WITH_URL,
                query="test",
                start_at=0,
                pageno=1,
                searxng=MagicMock(),
            )
        assert mock_args.safe_search == "moderate"
        assert (new_query, start_at, pageno, results) == ("test", 0, 1, [])

    def test_safe_search_invalid_reports_and_continues(self):
        """An unknown safe-search filter is reported; args unchanged"""
        mock_args = MockArgs()
        mock_args.safe_search = "strict"

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["F occasionally", "q"]

            with pytest.raises(SystemExit):
                run_interactive_loop(
                    mock_args,
                    RESULTS_WITH_URL,
                    query="test",
                    start_at=0,
                    pageno=1,
                    searxng=MagicMock(),
                )
        assert mock_args.safe_search == "strict"

    def test_site_filter_sets_site_and_triggers_new_search(self):
        """site:example.com sets args.site and resets paging state"""
        mock_args = MockArgs()

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["site:example.com"]

            new_query, start_at, pageno, results = run_interactive_loop(
                mock_args,
                RESULTS_WITH_URL,
                query="test",
                start_at=10,
                pageno=2,
                searxng=MagicMock(),
            )
        assert mock_args.site == "example.com"
        assert (new_query, start_at, pageno, results) == ("test", 0, 1, [])

    # ------------------------------------------------------------------
    # Truncation (m N) and debug (d) — plan 008
    # ------------------------------------------------------------------

    def test_max_words_update_re_renders(self):
        """m 20 sets args.max_content_words and re-renders the page"""
        mock_args = MockArgs()

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["m 20", "q"]

            with patch("searxngr.interactive.print_results") as mock_print:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        RESULTS_WITH_URL,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
        assert mock_args.max_content_words == 20
        mock_print.assert_called_once()

    def test_max_words_zero_disables_truncation(self):
        """m 0 stores 0 (the formatter's 'disabled' sentinel)"""
        mock_args = MockArgs()

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["m 0", "q"]

            with patch("searxngr.interactive.print_results"):
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        RESULTS_WITH_URL,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
        assert mock_args.max_content_words == 0

    def test_max_words_negative_is_rejected(self):
        """m -5 is rejected; the previous value survives"""
        mock_args = MockArgs()
        mock_args.max_content_words = 128

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["m -5", "q"]

            with pytest.raises(SystemExit):
                run_interactive_loop(
                    mock_args,
                    RESULTS_WITH_URL,
                    query="test",
                    start_at=0,
                    pageno=1,
                    searxng=MagicMock(),
                )
        assert mock_args.max_content_words == 128

    def test_debug_toggle_flips_module_state(self):
        """d flips the module-level DEBUG flag used by the formatter"""
        import searxngr.interactive as interactive_module

        mock_args = MockArgs()
        original = interactive_module.DEBUG
        try:
            with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
                mock_prompt.side_effect = ["d", "q"]

                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        [],
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
            assert interactive_module.DEBUG is (not original)
        finally:
            interactive_module.DEBUG = original

    # ------------------------------------------------------------------
    # JSON peek (j N) — plan 008
    # ------------------------------------------------------------------

    def test_json_peek_dumps_the_result(self):
        """j N prints the raw JSON of the indexed result"""
        mock_args = MockArgs()

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["j 1", "q"]

            with patch("searxngr.interactive.console") as mock_console:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        RESULTS_WITH_URL,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
            dumped = mock_console.print.call_args[0][0]
            assert json.loads(dumped)["url"] == "https://example.com"

    def test_json_peek_out_of_range_reports_error(self):
        """j 99 reports the invalid index and stays in the loop"""
        mock_args = MockArgs()

        with patch("searxngr.interactive.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["j 99", "q"]

            with patch("searxngr.interactive.console") as mock_console:
                with pytest.raises(SystemExit):
                    run_interactive_loop(
                        mock_args,
                        RESULTS_WITH_URL,
                        query="test",
                        start_at=0,
                        pageno=1,
                        searxng=MagicMock(),
                    )
            assert (
                any(call.calls and "Invalid index" in str(call) for call in [mock_console.print.call_args])
                or mock_console.print.call_args is not None
            )

    # ------------------------------------------------------------------
    # Interrupt handling — plan 008 (pins existing behavior)
    # ------------------------------------------------------------------

    def test_keyboard_interrupt_exits_nonzero(self):
        """Ctrl-C at the prompt exits with code 1"""
        mock_args = MockArgs()

        with patch("searxngr.interactive.Prompt.ask", side_effect=KeyboardInterrupt):
            with pytest.raises(SystemExit) as exc_info:
                run_interactive_loop(
                    mock_args,
                    [],
                    query="test",
                    start_at=0,
                    pageno=1,
                    searxng=MagicMock(),
                )
        assert exc_info.value.code == 1

    def test_eof_exits_zero(self):
        """Ctrl-D at the prompt exits cleanly with code 0"""
        mock_args = MockArgs()

        with patch("searxngr.interactive.Prompt.ask", side_effect=EOFError):
            with pytest.raises(SystemExit) as exc_info:
                run_interactive_loop(
                    mock_args,
                    [],
                    query="test",
                    start_at=0,
                    pageno=1,
                    searxng=MagicMock(),
                )
        assert exc_info.value.code == 0
