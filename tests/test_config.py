import configparser
import os
import tempfile
from unittest.mock import patch, mock_open, MagicMock

from searxngr.searxngr import SearxngrConfig


class TestSearxngrConfig:
    """Test configuration management functionality"""

    def test_config_initialization_defaults(self):
        """Test configuration initialization with default values"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock config file
            config_content = """
[searxngr]
searxng_url = https://example.com
result_count = 10
safe_search = moderate
expand = false
"""

            with patch("builtins.open", mock_open(read_data=config_content)):
                with patch("os.path.exists", return_value=True):
                    config = SearxngrConfig(config_path=temp_dir)

                    # Verify default values
                    assert config.searxng_url == "https://example.com"
                    assert config.result_count == 10
                    assert config.safe_search == "moderate"
                    assert config.expand is False

    def test_config_loading(self):
        """Test configuration loading from a file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock config file
            config_content = """
[searxngr]
searxng_url = https://test.com
result_count = 20
safe_search = strict
expand = true
engines = google duckduckgo
categories = news general
"""

            with patch("builtins.open", mock_open(read_data=config_content)):
                with patch("os.path.exists", return_value=True):
                    config = SearxngrConfig(config_path=temp_dir)

                    # Verify loaded values
                    assert config.searxng_url == "https://test.com"
                    assert config.result_count == 20
                    assert config.safe_search == "strict"
                    assert config.expand is True
                    assert config.engines == ["google", "duckduckgo"]
                    assert config.categories == ["news", "general"]

    def test_category_validation(self):
        """Test category validation functionality"""
        # Test valid categories
        valid_categories = [
            "general",
            "news",
            "videos",
            "images",
            "music",
            "map",
            "science",
            "it",
            "files",
            "social+media",
        ]
        for category in valid_categories:
            assert SearxngrConfig.validate_category(None, category) is True

        # Test invalid category
        assert SearxngrConfig.validate_category(None, "invalid_category") is False

    def test_config_helper_methods(self):
        """Test configuration helper methods"""
        parser = configparser.ConfigParser()
        parser["searxngr"] = {
            "test_string": "value",
            "test_int": "42",
            "test_float": "3.14",
            "test_bool": "true",
            "test_list": "item1 item2 item3",
            "test_list2": "item1  item2   item3",
            "test_list_csv": "item1, item2, item3",
            "test_list_csv2": "item1,  item2,   item3",
            "test_list_empty": "",
            "test_list_one_item": "item1",
        }

        config = SearxngrConfig()

        # Test string helper
        result = config.get_config_str(parser, "test_string", "default")
        assert result == "value"

        # Test int helper
        result = config.get_config_int(parser, "test_int", 10)
        assert result == 42

        # Test float helper
        result = config.get_config_float(parser, "test_float", 1.0)
        assert result == 3.14

        # Test bool helper
        result = config.get_config_bool(parser, "test_bool", False)
        assert result is True

        # Test list helper
        result = config.get_config_list(parser, "test_list", None)
        assert result == ["item1", "item2", "item3"]

        result = config.get_config_list(parser, "test_list2", None)
        assert result == ["item1", "item2", "item3"]

        result = config.get_config_list(parser, "test_list_csv", None)
        assert result == ["item1", "item2", "item3"]

        result = config.get_config_list(parser, "test_list_csv2", None)
        assert result == ["item1", "item2", "item3"]

        result = config.get_config_list(parser, "test_list_empty", None)
        assert result is None

        result = config.get_config_list(parser, "test_list_one_item", None)
        assert result == ["item1"]

        # Test default values
        result = config.get_config_str(parser, "nonexistent", "default")
        assert result == "default"

        result = config.get_config_int(parser, "nonexistent", 10)
        assert result == 10

        result = config.get_config_float(parser, "nonexistent", 1.0)
        assert result == 1.0

        result = config.get_config_bool(parser, "nonexistent", False)
        assert result is False

        result = config.get_config_list(parser, "nonexistent", None)
        assert result is None
