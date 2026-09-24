from unittest.mock import MagicMock, patch

import pytest

from searxngr.constants import (
    SAFE_SEARCH_OPTIONS,
    SEARXNG_CATEGORIES,
    TIME_RANGE_OPTIONS,
    parse_engine_command,
    validate_engines,
    validate_result_url,
    validate_url_handler,
    validate_url_syntax,
)


class TestConstants:
    """Test constants module functionality"""

    def test_parse_engine_command_plain(self):
        """Test parsing plain engine names"""
        to_add, to_remove, replacement_list, has_modifiers = parse_engine_command("google duckduckgo")
        assert to_add == []
        assert to_remove == []
        assert replacement_list == ["google", "duckduckgo"]
        assert has_modifiers is False

    def test_parse_engine_command_with_add(self):
        """Test parsing engines with + prefix"""
        to_add, to_remove, replacement_list, has_modifiers = parse_engine_command("+google +bing")
        assert to_add == ["google", "bing"]
        assert to_remove == []
        assert replacement_list == []
        assert has_modifiers is True

    def test_parse_engine_command_with_remove(self):
        """Test parsing engines with - prefix"""
        to_add, to_remove, replacement_list, has_modifiers = parse_engine_command("-google -bing")
        assert to_add == []
        assert to_remove == ["google", "bing"]
        assert replacement_list == []
        assert has_modifiers is True

    def test_parse_engine_command_mixed(self):
        """Test parsing engines with mixed modifiers"""
        to_add, to_remove, replacement_list, has_modifiers = parse_engine_command("google +bing -duckduckgo")
        assert to_add == ["bing"]
        assert to_remove == ["duckduckgo"]
        assert replacement_list == ["google"]
        assert has_modifiers is True

    def test_parse_engine_command_comma_separated(self):
        """Test parsing comma-separated engine names"""
        to_add, to_remove, replacement_list, has_modifiers = parse_engine_command("google, duckduckgo, brave")
        assert to_add == []
        assert to_remove == []
        assert replacement_list == ["google", "duckduckgo", "brave"]
        assert has_modifiers is False

    def test_validate_url_handler_valid(self):
        """Test validate_url_handler with valid command"""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/open"
            result = validate_url_handler("open")
            assert result is True

    def test_validate_url_handler_invalid(self):
        """Test validate_url_handler with invalid command"""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            result = validate_url_handler("nonexistent_command_12345")
            assert result is False

    def test_validate_url_handler_with_args(self):
        """Test validate_url_handler with command and arguments"""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/xdg-open"
            result = validate_url_handler("xdg-open https://example.com")
            assert result is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://searxng.example.com",
            "http://127.0.0.1:8080",
            "https://searxng.home.lan/search",
            "HTTPS://EXAMPLE.COM",
        ],
    )
    def test_validate_url_syntax_accepts_valid(self, url):
        """Instance URLs with http(s) scheme and a hostname are valid"""
        assert validate_url_syntax(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https:/searxng.home.lan",  # missing slash: host lands in path
            "notaurl",
            "ftp://example.com",
            "file:///etc/passwd",
            "//example.com",
            "/search",
            "",
        ],
    )
    def test_validate_url_syntax_rejects_invalid(self, url):
        """Typos, wrong schemes, and scheme-less URLs are rejected"""
        assert validate_url_syntax(url) is False

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com",
            "http://example.com/a?b=c&d=e",
            "HTTPS://EXAMPLE.COM/path",
        ],
    )
    def test_validate_result_url_accepts_http_https(self, url):
        """Result URLs from remote engines: http(s) are openable"""
        assert validate_result_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",  # local scheme handler
            "smb://server/share",  # network share handler
            "magnet:?xt=urn:btih:xyz",  # external app handler
            "ftp://example.com/file",
            "javascript:alert(1)",
            "--some-flag",  # argv-flag-shaped
            "-o Pen」tra missing",  # argv-flag-shaped with non-ascii
            "",
        ],
    )
    def test_validate_result_url_rejects_non_http(self, url):
        """Non-http(s) schemes and flag-shaped strings are refused"""
        assert validate_result_url(url) is False

    def test_validate_engines_success(self):
        """Test validate_engines with valid engines"""
        mock_client = MagicMock()
        mock_client.engines.return_value = [
            {"name": "google"},
            {"name": "duckduckgo"},
            {"name": "brave"},
        ]

        valid, invalid = validate_engines(["google", "duckduckgo", "invalid_engine"], mock_client)

        assert valid == ["google", "duckduckgo"]
        assert invalid == ["invalid_engine"]

    def test_validate_engines_all_invalid(self):
        """Test validate_engines with all invalid engines"""
        mock_client = MagicMock()
        mock_client.engines.return_value = [
            {"name": "google"},
            {"name": "duckduckgo"},
        ]

        valid, invalid = validate_engines(["invalid1", "invalid2"], mock_client)

        assert valid == []
        assert invalid == ["invalid1", "invalid2"]

    def test_safe_search_options(self):
        """Test SAFE_SEARCH_OPTIONS values"""
        assert SAFE_SEARCH_OPTIONS["none"] == "0"
        assert SAFE_SEARCH_OPTIONS["moderate"] == "1"
        assert SAFE_SEARCH_OPTIONS["strict"] == "2"

    def test_time_range_options(self):
        """Test TIME_RANGE_OPTIONS values"""
        assert "day" in TIME_RANGE_OPTIONS
        assert "week" in TIME_RANGE_OPTIONS
        assert "month" in TIME_RANGE_OPTIONS
        assert "year" in TIME_RANGE_OPTIONS

    def test_searxng_categories(self):
        """Test SEARXNG_CATEGORIES values"""
        assert "general" in SEARXNG_CATEGORIES
        assert "news" in SEARXNG_CATEGORIES
        assert "images" in SEARXNG_CATEGORIES
        assert "videos" in SEARXNG_CATEGORIES
        assert "science" in SEARXNG_CATEGORIES
