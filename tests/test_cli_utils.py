import pytest
from unittest.mock import patch, MagicMock
import subprocess

from searxngr.cli import open_url


class TestOpenUrl:
    """Test open_url function"""

    @patch("searxngr.cli.subprocess.run")
    @patch("searxngr.cli.console")
    def test_open_url_success(self, mock_console, mock_run):
        """Test open_url succeeds with valid handler and URL"""
        mock_run.return_value = MagicMock()
        result = open_url("https://example.com", "open")
        assert result is True
        mock_run.assert_called_once()

    @patch("searxngr.cli.subprocess.run")
    @patch("searxngr.cli.console")
    def test_open_url_file_not_found(self, mock_console, mock_run):
        """Test open_url handles FileNotFoundError"""
        mock_run.side_effect = FileNotFoundError("Command not found")
        result = open_url("https://example.com", "nonexistent_cmd")
        assert result is False
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "Warning" in call_args
        assert "not found" in call_args.lower()

    @patch("searxngr.cli.subprocess.run")
    @patch("searxngr.cli.console")
    def test_open_url_called_process_error(self, mock_console, mock_run):
        """Test open_url handles CalledProcessError"""
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")
        result = open_url("https://example.com", "open")
        assert result is False
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "Error" in call_args

    @patch("searxngr.cli.shlex.split")
    @patch("searxngr.cli.subprocess.run")
    @patch("searxngr.cli.console")
    def test_open_url_command_constructed_correctly(
        self, mock_console, mock_run, mock_split
    ):
        """Test open_url constructs command correctly"""
        mock_split.return_value = ["open"]
        mock_run.return_value = MagicMock()
        open_url("https://example.com", "open")
        mock_split.assert_called_once_with("open")
        mock_run.assert_called_once()
        called_command = mock_run.call_args[0][0]
        assert called_command == ["open", "https://example.com"]
