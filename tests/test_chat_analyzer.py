"""
Tests for the chat analyzer module.

Uses unittest.mock to simulate Anthropic API responses
without making real API calls.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import anthropic

from src.chat_analyzer import ChatAnalyzer
from src.models import ChatAnalysisResult, ChatMessage, FileInfo


def _make_mock_response(json_data: dict) -> MagicMock:
    """Helper: create a mock Anthropic response with the given JSON as text content."""
    mock_response = MagicMock()
    mock_content_block = MagicMock()
    mock_content_block.text = json.dumps(json_data)
    mock_response.content = [mock_content_block]
    return mock_response


class TestParseResponse:
    """Tests for _parse_response (JSON parsing from Claude's output)."""

    def setup_method(self):
        """Create analyzer with a dummy key (no real API calls)."""
        with patch.object(anthropic, 'Anthropic'):
            self.analyzer = ChatAnalyzer(api_key="test-key")

    def test_valid_json_with_messages(self):
        """Valid JSON with messages should return success with ChatMessage objects."""
        raw = json.dumps({
            "messages": [
                {"speaker": "right", "text": "Hey there", "timestamp": "10:42 AM"},
                {"speaker": "left", "text": "Hi!", "timestamp": None},
            ]
        })
        result = self.analyzer._parse_response(raw, "test.png")

        assert result.success is True
        assert len(result.messages) == 2
        assert result.messages[0].speaker == "right"
        assert result.messages[0].text == "Hey there"
        assert result.messages[0].timestamp == "10:42 AM"
        assert result.messages[1].speaker == "left"
        assert result.messages[1].text == "Hi!"
        assert result.messages[1].timestamp is None

    def test_invalid_json_returns_error(self):
        """Non-JSON text should return a failed result with raw response preserved."""
        result = self.analyzer._parse_response("not valid json {{{", "test.png")

        assert result.success is False
        assert "Invalid JSON" in result.error
        assert result.raw_response == "not valid json {{{"

    def test_missing_messages_key_returns_error(self):
        """JSON without 'messages' key should return a failed result."""
        raw = json.dumps({"data": []})
        result = self.analyzer._parse_response(raw, "test.png")

        assert result.success is False
        assert "Missing 'messages' key" in result.error

    def test_empty_text_messages_are_skipped(self):
        """Messages with blank text should be filtered out."""
        raw = json.dumps({
            "messages": [
                {"speaker": "right", "text": "Real message"},
                {"speaker": "left", "text": "   "},
                {"speaker": "left", "text": ""},
            ]
        })
        result = self.analyzer._parse_response(raw, "test.png")

        assert result.success is True
        assert len(result.messages) == 1
        assert result.messages[0].text == "Real message"

    def test_missing_fields_get_defaults(self):
        """Messages missing optional fields should get safe defaults."""
        raw = json.dumps({
            "messages": [
                {"text": "No speaker field"},
            ]
        })
        result = self.analyzer._parse_response(raw, "test.png")

        assert result.success is True
        assert len(result.messages) == 1
        assert result.messages[0].speaker == "unknown"
        assert result.messages[0].timestamp is None

    def test_raw_response_preserved_on_success(self):
        """The raw JSON string should be stored for debugging."""
        raw = json.dumps({"messages": [{"speaker": "left", "text": "Hi"}]})
        result = self.analyzer._parse_response(raw, "test.png")

        assert result.raw_response == raw


class TestAnalyzeScreenshot:
    """Tests for analyze_screenshot (file handling + API interaction)."""

    def setup_method(self):
        """Create analyzer with mocked Anthropic client."""
        with patch.object(anthropic, 'Anthropic') as mock_cls:
            self.mock_client = MagicMock()
            mock_cls.return_value = self.mock_client
            self.analyzer = ChatAnalyzer(api_key="test-key")

    def test_file_not_found(self):
        """Non-existent file should return error without calling API."""
        result = self.analyzer.analyze_screenshot(Path("/nonexistent/fake.png"))

        assert result.success is False
        assert "File not found" in result.error
        self.mock_client.messages.create.assert_not_called()

    def test_unsupported_format(self, tmp_path):
        """Unsupported file type should return error without calling API."""
        heic_file = tmp_path / "photo.heic"
        heic_file.write_bytes(b"fake heic data")

        result = self.analyzer.analyze_screenshot(heic_file)

        assert result.success is False
        assert "Unsupported image format" in result.error
        assert ".heic" in result.error
        self.mock_client.messages.create.assert_not_called()

    def test_successful_analysis(self, tmp_path):
        """Valid image file with good API response should return parsed messages."""
        img_file = tmp_path / "chat.png"
        img_file.write_bytes(b"fake png data")

        mock_response = _make_mock_response({
            "messages": [
                {"speaker": "right", "text": "Hello", "timestamp": "3:00 PM"},
                {"speaker": "left", "text": "Hi there", "timestamp": None},
            ]
        })
        self.mock_client.messages.create.return_value = mock_response

        result = self.analyzer.analyze_screenshot(img_file)

        assert result.success is True
        assert len(result.messages) == 2
        assert result.messages[0].speaker == "right"
        assert result.messages[0].text == "Hello"
        assert result.messages[1].speaker == "left"
        self.mock_client.messages.create.assert_called_once()

    def test_retries_on_connection_error(self, tmp_path):
        """APIConnectionError should trigger retry, then succeed."""
        img_file = tmp_path / "chat.jpg"
        img_file.write_bytes(b"fake jpg data")

        good_response = _make_mock_response({
            "messages": [{"speaker": "left", "text": "Works now"}]
        })
        self.mock_client.messages.create.side_effect = [
            anthropic.APIConnectionError(request=MagicMock()),
            good_response,
        ]

        with patch('src.chat_analyzer.time.sleep'):
            result = self.analyzer.analyze_screenshot(img_file)

        assert result.success is True
        assert len(result.messages) == 1
        assert self.mock_client.messages.create.call_count == 2

    def test_no_retry_on_4xx_error(self, tmp_path):
        """4xx client errors should NOT retry — fail immediately."""
        img_file = tmp_path / "chat.png"
        img_file.write_bytes(b"fake png data")

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": {"message": "Bad request"}}
        self.mock_client.messages.create.side_effect = anthropic.BadRequestError(
            message="Bad request",
            response=mock_response,
            body={"error": {"message": "Bad request"}},
        )

        result = self.analyzer.analyze_screenshot(img_file)

        assert result.success is False
        assert "400" in result.error
        self.mock_client.messages.create.assert_called_once()

    def test_retries_on_5xx_error(self, tmp_path):
        """5xx server errors should trigger retry."""
        img_file = tmp_path / "chat.png"
        img_file.write_bytes(b"fake png data")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Internal server error"}}

        good_response = _make_mock_response({
            "messages": [{"speaker": "right", "text": "Recovered"}]
        })
        self.mock_client.messages.create.side_effect = [
            anthropic.InternalServerError(
                message="Internal server error",
                response=mock_response,
                body={"error": {"message": "Internal server error"}},
            ),
            good_response,
        ]

        with patch('src.chat_analyzer.time.sleep'):
            result = self.analyzer.analyze_screenshot(img_file)

        assert result.success is True
        assert self.mock_client.messages.create.call_count == 2

    def test_retries_on_rate_limit(self, tmp_path):
        """RateLimitError should trigger retry with backoff."""
        img_file = tmp_path / "chat.png"
        img_file.write_bytes(b"fake png data")

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limited"}}

        good_response = _make_mock_response({
            "messages": [{"speaker": "left", "text": "After rate limit"}]
        })
        self.mock_client.messages.create.side_effect = [
            anthropic.RateLimitError(
                message="Rate limited",
                response=mock_response,
                body={"error": {"message": "Rate limited"}},
            ),
            good_response,
        ]

        with patch('src.chat_analyzer.time.sleep'):
            result = self.analyzer.analyze_screenshot(img_file)

        assert result.success is True
        assert self.mock_client.messages.create.call_count == 2

    def test_exhausted_retries_returns_error(self, tmp_path):
        """If all retry attempts fail, should return an error result."""
        img_file = tmp_path / "chat.png"
        img_file.write_bytes(b"fake png data")

        self.mock_client.messages.create.side_effect = anthropic.APIConnectionError(
            request=MagicMock()
        )

        with patch('src.chat_analyzer.time.sleep'):
            result = self.analyzer.analyze_screenshot(img_file)

        assert result.success is False
        assert "Failed after" in result.error
        # MAX_RETRIES + 1 attempts total
        assert self.mock_client.messages.create.call_count == 4


class TestAnalyzeFiles:
    """Tests for analyze_files (batch processing)."""

    def setup_method(self):
        with patch.object(anthropic, 'Anthropic') as mock_cls:
            self.mock_client = MagicMock()
            mock_cls.return_value = self.mock_client
            self.analyzer = ChatAnalyzer(api_key="test-key")

    def test_processes_multiple_files(self, tmp_path):
        """Should return a result for each file in the list."""
        # Create two fake image files
        img1 = tmp_path / "a.png"
        img2 = tmp_path / "b.jpg"
        img1.write_bytes(b"fake")
        img2.write_bytes(b"fake")

        file_list = [
            FileInfo(filepath=tmp_path, filename="a.png", extension=".png"),
            FileInfo(filepath=tmp_path, filename="b.jpg", extension=".jpg"),
        ]

        mock_response = _make_mock_response({
            "messages": [{"speaker": "left", "text": "Hi"}]
        })
        self.mock_client.messages.create.return_value = mock_response

        with patch('src.chat_analyzer.time.sleep'):
            results = self.analyzer.analyze_files(file_list)

        assert len(results) == 2
        assert "a.png" in results
        assert "b.jpg" in results
        assert results["a.png"].success is True
        assert results["b.jpg"].success is True

    def test_empty_file_list(self):
        """Empty file list should return empty dict without API calls."""
        with patch('src.chat_analyzer.time.sleep'):
            results = self.analyzer.analyze_files([])

        assert results == {}
        self.mock_client.messages.create.assert_not_called()
