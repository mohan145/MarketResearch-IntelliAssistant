import pytest
from unittest.mock import Mock, patch

from src.backend.pipeline.scraper import (
    fetch_url,
    extract_content,
    scrape_urls,
    FetchResult,
    ExtractedContent,
    ContentTooShortError,
)


class TestFetchUrl:
    """Test URL fetching with retry logic."""

    @patch("src.backend.pipeline.scraper.httpx.Client.get")
    def test_successful_fetch(self, mock_get):
        """Test successful URL fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>content</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_url("https://example.com")

        assert result.is_success()
        assert result.status_code == 200
        assert result.html == "<html>content</html>"
        assert result.error is None

    @patch("src.backend.pipeline.scraper.httpx.Client.get")
    def test_fetch_timeout(self, mock_get):
        """Test fetch timeout returns error without raising."""
        import httpx

        mock_get.side_effect = httpx.TimeoutException("Timeout")

        result = fetch_url("https://example.com", timeout=5)

        assert not result.is_success()
        assert result.status_code == 0
        assert "Timeout" in result.error

    @patch("src.backend.pipeline.scraper.httpx.Client.get")
    def test_fetch_404(self, mock_get):
        """Test 404 response."""
        import httpx

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=Mock(), response=mock_response
        )
        mock_get.return_value = mock_response

        result = fetch_url("https://example.com/missing")

        assert not result.is_success()
        assert result.status_code == 404
        assert "404" in result.error


class TestExtractContent:
    """Test content extraction with trafilatura."""

    def test_extract_successful(self, sample_html):
        """Test successful extraction returns clean text."""
        result = extract_content(sample_html, "https://example.com")

        assert isinstance(result, ExtractedContent)
        assert result.url == "https://example.com"
        assert result.word_count >= 50
        assert "AI" in result.text or "market" in result.text.lower()

    def test_extract_too_short(self):
        """Test extraction fails for very short content."""
        short_html = "<html><body>Hello world</body></html>"

        with pytest.raises(ContentTooShortError):
            extract_content(short_html, "https://example.com")

    def test_extract_empty_html(self):
        """Test extraction fails for empty/whitespace-only HTML."""
        empty_html = "<html><body></body></html>"

        with pytest.raises(ContentTooShortError):
            extract_content(empty_html, "https://example.com")

    def test_extract_metadata(self, sample_html):
        """Test that metadata is extracted."""
        result = extract_content(sample_html, "https://example.com")

        assert result.title is not None or result.author is not None
        assert result.word_count > 0


class TestScrapeUrls:
    """Test scraping multiple URLs."""

    @patch("src.backend.pipeline.scraper.fetch_url")
    @patch("src.backend.pipeline.scraper.extract_content")
    def test_scrape_multiple_urls(self, mock_extract, mock_fetch):
        """Test scraping returns results for each URL."""
        # Setup mocks
        mock_fetch.return_value = FetchResult(
            url="https://example.com",
            status_code=200,
            html="<html>content</html>",
            error=None,
            fetched_at=__import__("datetime").datetime.utcnow(),
        )

        mock_extract.return_value = ExtractedContent(
            url="https://example.com",
            title="Test Article",
            author="Test Author",
            publish_date="2024-06-13",
            text="This is test content " * 20,  # 80 words
            word_count=80,
        )

        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
        ]

        results = scrape_urls(urls)

        assert len(results) == 3
        assert all(r.is_success() for r in results)
        assert all(r.extracted_content.word_count == 80 for r in results)

    @patch("src.backend.pipeline.scraper.fetch_url")
    def test_scrape_with_fetch_error(self, mock_fetch):
        """Test scraping handles fetch errors gracefully."""
        mock_fetch.return_value = FetchResult(
            url="https://example.com",
            status_code=404,
            html=None,
            error="HTTP 404",
            fetched_at=__import__("datetime").datetime.utcnow(),
        )

        results = scrape_urls(["https://example.com/missing"])

        assert len(results) == 1
        assert not results[0].is_success()
        assert "404" in results[0].error

    @patch("src.backend.pipeline.scraper.fetch_url")
    @patch("src.backend.pipeline.scraper.extract_content")
    def test_scrape_with_extraction_error(self, mock_extract, mock_fetch):
        """Test scraping handles extraction errors gracefully."""
        mock_fetch.return_value = FetchResult(
            url="https://example.com",
            status_code=200,
            html="<html>Short</html>",
            error=None,
            fetched_at=__import__("datetime").datetime.utcnow(),
        )

        mock_extract.side_effect = ContentTooShortError("Too short")

        results = scrape_urls(["https://example.com"])

        assert len(results) == 1
        assert not results[0].is_success()
        assert "Too short" in results[0].error

    @patch("src.backend.pipeline.scraper.fetch_url")
    @patch("src.backend.pipeline.scraper.extract_content")
    def test_scrape_mixed_results(self, mock_extract, mock_fetch):
        """Test scraping with mix of successful and failed URLs."""

        def fetch_side_effect(url):
            if "success" in url:
                return FetchResult(
                    url=url,
                    status_code=200,
                    html="<html>content</html>",
                    error=None,
                    fetched_at=__import__("datetime").datetime.utcnow(),
                )
            else:
                return FetchResult(
                    url=url,
                    status_code=404,
                    html=None,
                    error="HTTP 404",
                    fetched_at=__import__("datetime").datetime.utcnow(),
                )

        def extract_side_effect(html, url):
            return ExtractedContent(
                url=url,
                title="Test",
                author=None,
                publish_date=None,
                text="Valid content " * 20,
                word_count=40,
            )

        mock_fetch.side_effect = fetch_side_effect
        mock_extract.side_effect = extract_side_effect

        urls = [
            "https://example.com/success1",
            "https://example.com/fail",
            "https://example.com/success2",
        ]

        results = scrape_urls(urls)

        assert len(results) == 3
        assert results[0].is_success()
        assert not results[1].is_success()
        assert results[2].is_success()