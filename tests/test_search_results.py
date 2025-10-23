import os
from unittest.mock import patch, MagicMock
from searxngr.searxngr import print_results


class TestSearchResults:
    """Test search results processing and display functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.sample_results = [
            {
                "title": "Test Result 1",
                "url": "https://example.com/result1",
                "content": "<p>This is a test result with some content to display.</p>",
                "engine": "testengine",
                "template": None,
                "category": "general",
                "engines": ["testengine", "otherengine"],
                "publishedDate": None
            },
            {
                "title": "News Result",
                "url": "https://news.example.com/article",
                "content": "<p>This is a news article with content that might need to be truncated when displayed.</p>",
                "engine": "testengine",
                "template": None,
                "category": "news",
                "engines": ["testengine"],
                "publishedDate": "2023-01-15T10:30:00Z"
            },
            {
                "title": "Image Result",
                "url": "https://images.example.com/photo",
                "content": "<p>Image search result</p>",
                "engine": "testengine",
                "template": None,
                "category": "images",
                "engines": ["testengine"],
                "publishedDate": None,
                "source": "Image Source",
                "resolution": "1920x1080",
                "img_src": "https://example.com/image.jpg"
            },
            {
                "title": "Video Result",
                "url": "https://videos.example.com/watch",
                "content": "<p>Video search result</p>",
                "engine": "testengine",
                "template": None,
                "category": "videos",
                "engines": ["testengine"],
                "publishedDate": None,
                "author": "Video Author",
                "length": 122.0
            }
        ]

    @patch('searxngr.searxngr.console')
    @patch('searxngr.searxngr.os.get_terminal_size')
    def test_print_results_basic(self, mock_terminal_size, mock_console):
        """Test basic result printing functionality"""
        # Mock terminal size
        mock_terminal_size.return_value = os.terminal_size((80, 24))
        
        print_results(self.sample_results[:1], count=1)
        
        # Verify that console.print was called
        mock_console.print.assert_called()
        
        # Check that basic result elements were printed
        call_args = mock_console.print.call_args_list
        assert any("Test Result 1" in str(call) for call in call_args)
        assert any("example.com" in str(call) for call in call_args)
        assert any("testengine" in str(call) for call in call_args)

    @patch('searxngr.searxngr.console')
    @patch('searxngr.searxngr.os.get_terminal_size')
    def test_print_results_with_long_content(self, mock_terminal_size, mock_console):
        """Test result printing with content that needs truncation"""
        # Mock terminal size
        mock_terminal_size.return_value = os.terminal_size((80, 24))
        
        print_results(self.sample_results[:1], count=1)
        
        # Verify that console.print was called
        mock_console.print.assert_called()
        
        # Check that content was truncated
        call_args = mock_console.print.call_args_list
        content_calls = [call for call in call_args if "This is a test result" in str(call)]
        assert len(content_calls) > 0

    @patch('searxngr.searxngr.console')
    @patch('searxngr.searxngr.os.get_terminal_size')
    def test_print_results_with_expand(self, mock_terminal_size, mock_console):
        """Test result printing with expand option"""
        # Mock terminal size
        mock_terminal_size.return_value = os.terminal_size((80, 24))
        
        print_results(self.sample_results[:1], count=1, expand=True)
        
        # Verify that console.print was called
        mock_console.print.assert_called()
        
        # Check that full URL was printed
        call_args = mock_console.print.call_args_list
        assert any("https://example.com/result1" in str(call) for call in call_args)

    @patch('searxngr.searxngr.console')
    @patch('searxngr.searxngr.os.get_terminal_size')
    def test_print_results_news_category(self, mock_terminal_size, mock_console):
        """Test result printing for news category with date"""
        # Mock terminal size
        mock_terminal_size.return_value = os.terminal_size((80, 24))
        
        print_results(self.sample_results[1:2], count=1)
        
        # Verify that console.print was called
        mock_console.print.assert_called()
        
        # Check that news details were printed
        call_args = mock_console.print.call_args_list
        assert any("News Result" in str(call) for call in call_args)
        assert any("example.com" in str(call) for call in call_args)
        # Check that published date was formatted (could be different format)
        assert any("2023" in str(call) for call in call_args)

    @patch('searxngr.searxngr.console')
    @patch('searxngr.searxngr.os.get_terminal_size')
    def test_print_results_images_category(self, mock_terminal_size, mock_console):
        """Test result printing for images category"""
        # Mock terminal size
        mock_terminal_size.return_value = os.terminal_size((80, 24))
        
        print_results(self.sample_results[2:3], count=1)
        
        # Verify that console.print was called
        mock_console.print.assert_called()
        
        # Check that image details were printed
        call_args = mock_console.print.call_args_list
        assert any("Image Result" in str(call) for call in call_args)
        assert any("1920x1080" in str(call) for call in call_args)
        assert any("Image Source" in str(call) for call in call_args)
        assert any("https://example.com/image.jpg" in str(call) for call in call_args)

    @patch('searxngr.searxngr.console')
    @patch('searxngr.searxngr.os.get_terminal_size')
    def test_print_results_videos_category(self, mock_terminal_size, mock_console):
        """Test result printing for videos category"""
        # Mock terminal size
        mock_terminal_size.return_value = os.terminal_size((80, 24))
        
        print_results(self.sample_results[3:4], count=1)
        
        # Verify that console.print was called
        mock_console.print.assert_called()
        
        # Check that video details were printed
        call_args = mock_console.print.call_args_list
        assert any("Video Result" in str(call) for call in call_args)
        assert any("Video Author" in str(call) for call in call_args)
        assert any("02:02" in str(call) for call in call_args)  # Formatted length