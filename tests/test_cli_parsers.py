import pytest
from unittest.mock import patch, MagicMock
import argparse

from searxngr.cli import parse_pre_args, create_parser, main
from searxngr.config import SearxngrConfig


class TestCLIParsers:
    """Test CLI parser functions"""

    def test_parse_pre_args_empty(self):
        """Test parse_pre_args with no arguments"""
        with patch("sys.argv", ["searxngr"]):
            result = parse_pre_args()
            assert isinstance(result, argparse.Namespace)
            assert result.searxng_url is None
            assert result.version is False
            assert result.config is False
            assert result.list_categories is False
            assert result.list_engines is False
            assert result.help is False

    def test_parse_pre_args_with_url(self):
        """Test parse_pre_args with --searxng-url"""
        with patch("sys.argv", ["searxngr", "--searxng-url", "https://searxng.example.com"]):
            result = parse_pre_args()
            assert result.searxng_url == "https://searxng.example.com"

    def test_parse_pre_args_with_version(self):
        """Test parse_pre_args with --version"""
        with patch("sys.argv", ["searxngr", "--version"]):
            result = parse_pre_args()
            assert result.version is True

    def test_parse_pre_args_with_config(self):
        """Test parse_pre_args with --config"""
        with patch("sys.argv", ["searxngr", "--config"]):
            result = parse_pre_args()
            assert result.config is True

    def test_parse_pre_args_with_list_categories(self):
        """Test parse_pre_args with --list-categories"""
        with patch("sys.argv", ["searxngr", "--list-categories"]):
            result = parse_pre_args()
            assert result.list_categories is True

    def test_parse_pre_args_with_list_engines(self):
        """Test parse_pre_args with --list-engines"""
        with patch("sys.argv", ["searxngr", "--list-engines"]):
            result = parse_pre_args()
            assert result.list_engines is True


class TestCreateParser:
    """Test create_parser function"""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config object"""
        config = MagicMock()
        config.searxng_url = "https://searxng.example.com"
        config.categories = ["general"]
        config.debug = False
        config.engines = ["google"]
        config.expand = False
        config.http_method = "GET"
        config.http_timeout = 10.0
        config.language = "en"
        config.no_verify_ssl = False
        config.no_color = False
        config.no_user_agent = False
        config.result_count = 10
        config.safe_search = "moderate"
        config.url_handler = "open"
        config.secondary_url_handler = None
        return config

    def test_create_parser_returns_argparse(self, mock_config):
        """Test create_parser returns an ArgumentParser"""
        result = create_parser(mock_config)
        assert isinstance(result, argparse.ArgumentParser)

    def test_create_parser_has_query_positional(self, mock_config):
        """Test parser has query positional argument"""
        parser = create_parser(mock_config)
        args = parser.parse_args(["test query"])
        assert args.query == ["test query"]

    def test_create_parser_has_query_option(self, mock_config):
        """Test parser has -q/--query option"""
        parser = create_parser(mock_config)
        args = parser.parse_args(["-q", "test query"])
        assert args.query_opt == "test query"

    def test_create_parser_has_searxng_url(self, mock_config):
        """Test parser has --searxng-url with default from config"""
        parser = create_parser(mock_config)
        args = parser.parse_args([])
        assert args.searxng_url == "https://searxng.example.com"

    def test_create_parser_has_categories(self, mock_config):
        """Test parser has -c/--categories with default from config"""
        parser = create_parser(mock_config)
        args = parser.parse_args([])
        assert args.categories == ["general"]

    def test_create_parser_has_num(self, mock_config):
        """Test parser has -n/--num with default from config"""
        parser = create_parser(mock_config)
        args = parser.parse_args([])
        assert args.num == 10

    def test_create_parser_has_safe_search(self, mock_config):
        """Test parser has --safe-search with default from config"""
        parser = create_parser(mock_config)
        args = parser.parse_args([])
        assert args.safe_search == "moderate"

    def test_create_parser_has_first(self, mock_config):
        """Test parser has -j/--first flag"""
        parser = create_parser(mock_config)
        args = parser.parse_args(["--first"])
        assert args.first is True

    def test_create_parser_has_lucky(self, mock_config):
        """Test parser has --lucky flag"""
        parser = create_parser(mock_config)
        args = parser.parse_args(["--lucky"])
        assert args.lucky is True

    def test_create_parser_has_json(self, mock_config):
        """Test parser has --json flag"""
        parser = create_parser(mock_config)
        args = parser.parse_args(["--json"])
        assert args.json is True

    def test_create_parser_has_http_method(self, mock_config):
        """Test parser has --http-method with choices"""
        parser = create_parser(mock_config)
        args = parser.parse_args(["--http-method", "POST"])
        assert args.http_method == "POST"

    def test_create_parser_invalid_http_method(self, mock_config):
        """Test parser rejects invalid --http-method"""
        parser = create_parser(mock_config)
        with pytest.raises(SystemExit):
            parser.parse_args(["--http-method", "INVALID"])


class TestMainValidation:
    """main()-level validation exits: URL syntax and category names."""

    @staticmethod
    def _mock_config(categories=None):
        """Config mock with plain values so main()'s validation logic runs."""
        return MagicMock(
            searxng_url=None,
            safe_search=None,
            categories=categories,
            time_range=None,
            url_handler=None,
            secondary_url_handler=None,
            debug=False,
            retries=2,
            num=10,
            result_count=10,
        )

    @pytest.mark.parametrize(
        "url",
        [
            "https:/searxng.home.lan",  # missing slash: host lands in path
            "notaurl",
            "ftp://example.com",
        ],
    )
    def test_main_rejects_invalid_url_syntax(self, url, tmp_path, capsys):
        """A syntactically invalid instance URL fails at startup with a
        specific message, before any search is attempted."""
        with (
            patch("sys.argv", ["searxngr", "--searxng-url", url, "-q", "test"]),
            patch("searxngr.cli.SearxngrConfig") as mock_cfg,
        ):
            mock_cfg.return_value = self._mock_config()
            with pytest.raises(SystemExit) as exit_info:
                main()
            assert exit_info.value.code == 1
        assert "Invalid SearXNG instance URL" in capsys.readouterr().out

    def test_main_accepts_valid_url_syntax(self, tmp_path):
        """A syntactically valid URL passes startup validation and proceeds
        to search (client is constructed; search is mocked)."""
        with (
            patch(
                "sys.argv",
                ["searxngr", "--searxng-url", "https://searxng.example.com", "--np", "-q", "test"],
            ),
            patch("searxngr.cli.SearxngrConfig") as mock_cfg,
            patch("searxngr.cli.SearXNGClient") as mock_client,
            patch("searxngr.cli.print_results"),
        ):
            mock_cfg.return_value = self._mock_config()
            mock_client.return_value.search.return_value = [{"url": f"https://example.com/{i}"} for i in range(10)]
            with pytest.raises(SystemExit) as exit_info:
                main()
            assert exit_info.value.code == 0

    def test_main_rejects_invalid_category(self, capsys):
        """Pin the invalid-category failure mode: loud exit with the
        supported-categories message (validate_category prints, main exits 1)."""
        with (
            patch(
                "sys.argv",
                [
                    "searxngr",
                    "--searxng-url",
                    "https://searxng.example.com",
                    "-c",
                    "genral",
                    "-q",
                    "test",
                ],
            ),
            patch("searxngr.cli.SearxngrConfig") as mock_cfg,
        ):
            mock_cfg.return_value = self._mock_config(categories=["genral"])
            # Use the real category validation (classmethod bound to the class);
            # a MagicMock method would be truthy and skip the check.
            mock_cfg.return_value.validate_category.side_effect = SearxngrConfig.validate_category
            with patch("searxngr.cli.SearXNGClient"):
                with pytest.raises(SystemExit) as exit_info:
                    main()
            assert exit_info.value.code == 1
        assert "Invalid category 'genral'" in capsys.readouterr().out
