from unittest.mock import patch, MagicMock

from searxngr.searxngr import SearXNGClient, SAFE_SEARCH_OPTIONS


class TestSearXNGClient:
    """Test SearXNG client functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.base_url = "https://example.com"
        self.client = SearXNGClient(url=self.base_url)

    def test_client_initialization(self):
        """Test client initialization with default parameters"""
        assert self.client.url == self.base_url
        assert self.client.username is None
        assert self.client.password is None
        assert self.client.verify_ssl is True
        assert self.client.timeout == 30
        assert "User-Agent" in self.client.default_headers

    def test_client_initialization_with_auth(self):
        """Test client initialization with authentication"""
        client = SearXNGClient(
            url=self.base_url, username="testuser", password="testpass"
        )

        assert client.username == "testuser"
        assert client.password == "testpass"

    @patch("searxngr.searxngr.httpx.Client")
    def test_get_request(self, mock_httpx_client):
        """Test GET request functionality"""
        # Mock the HTTP client and response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.return_value.get.return_value = mock_response

        client = SearXNGClient(url=self.base_url)
        response = client.get("/test")

        # Verify the request was made correctly
        mock_httpx_client.return_value.get.assert_called_once_with(
            f"{self.base_url}/test",
            headers=client.default_headers,
            follow_redirects=True,
        )
        assert response == mock_response

    @patch("searxngr.searxngr.httpx.Client")
    def test_post_request(self, mock_httpx_client):
        """Test POST request functionality"""
        # Mock the HTTP client and response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.return_value.post.return_value = mock_response

        client = SearXNGClient(url=self.base_url)
        data = {"key": "value"}
        response = client.post("/test", data=data)

        # Verify the request was made correctly
        mock_httpx_client.return_value.post.assert_called_once_with(
            f"{self.base_url}/test",
            data=data,
            headers=client.default_headers,
            follow_redirects=True,
        )
        assert response == mock_response

    @patch("searxngr.searxngr.httpx.Client")
    def test_search_get_method(self, mock_httpx_client):
        """Test search functionality with GET method"""
        # Mock the HTTP client and response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com/test",
                    "content": "Test content",
                    "engine": "testengine",
                }
            ]
        }
        mock_httpx_client.return_value.get.return_value = mock_response

        client = SearXNGClient(url=self.base_url)
        results = client.search(
            query="test query",
            categories=["general"],
            engines=["testengine"],
            safe_search="moderate",
            http_method="GET",
        )

        # Verify the results
        assert len(results) == 1
        assert results[0]["title"] == "Test Result"

        # Verify the URL was constructed correctly
        call_args = mock_httpx_client.return_value.get.call_args
        assert "test query" in call_args[0][0]
        assert "general" in call_args[0][0]
        assert "testengine" in call_args[0][0]
        assert str(SAFE_SEARCH_OPTIONS["moderate"]) in call_args[0][0]

    @patch("searxngr.searxngr.httpx.Client")
    def test_search_post_method(self, mock_httpx_client):
        """Test search functionality with POST method"""
        # Mock the HTTP client and response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com/test",
                    "content": "Test content",
                    "engine": "testengine",
                }
            ]
        }
        mock_httpx_client.return_value.post.return_value = mock_response

        client = SearXNGClient(url=self.base_url)
        results = client.search(
            query="test query",
            categories=["general"],
            engines=["testengine"],
            safe_search="strict",
            http_method="POST",
        )

        # Verify the results
        assert len(results) == 1
        assert results[0]["title"] == "Test Result"

        # Verify the body was constructed correctly
        call_args = mock_httpx_client.return_value.post.call_args
        body = call_args[1]["data"]
        assert body["q"] == "test query"
        assert body["categories"] == "general"
        assert body["engines"] == "testengine"
        assert body["safesearch"] == SAFE_SEARCH_OPTIONS["strict"]

    @patch("searxngr.searxngr.httpx.Client")
    def test_search_with_site_filter(self, mock_httpx_client):
        """Test search functionality with site filter"""
        # Mock the HTTP client and response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_httpx_client.return_value.get.return_value = mock_response

        client = SearXNGClient(url=self.base_url)
        client.search(query="test query", site="example.com", http_method="GET")

        # Verify the site filter was applied
        call_args = mock_httpx_client.return_value.get.call_args
        assert "site:example.com test query" in call_args[0][0]

    @patch("searxngr.searxngr.httpx.Client")
    def test_search_with_time_range(self, mock_httpx_client):
        """Test search functionality with time range filter"""
        # Mock the HTTP client and response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_httpx_client.return_value.get.return_value = mock_response

        client = SearXNGClient(url=self.base_url)
        client.search(query="test query", time_range="week", http_method="GET")

        # Verify the time range was applied
        call_args = mock_httpx_client.return_value.get.call_args
        assert "time_range=week" in call_args[0][0]

    @patch("searxngr.searxngr.httpx.Client")
    def test_empty_results_handling(self, mock_httpx_client):
        """Test handling of empty search results"""
        # Mock the HTTP client and response with empty results
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_httpx_client.return_value.get.return_value = mock_response

        client = SearXNGClient(url=self.base_url)
        results = client.search(query="test query")

        # Verify empty results are handled correctly
        assert results == []

    @patch("searxngr.searxngr.httpx.Client")
    def test_unresponsive_engines_handling(self, mock_httpx_client):
        """Test handling of unresponsive engines"""
        # Mock the HTTP client and response with unresponsive engines
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [],
            "unresponsive_engines": [["engine1", "timeout"], ["engine2", "error"]],
        }
        mock_httpx_client.return_value.get.return_value = mock_response

        client = SearXNGClient(url=self.base_url)
        results = client.search(query="test query")

        # Verify results are returned despite unresponsive engines
        assert results == []
