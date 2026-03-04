"""
Tests for the chat analyzer module.

Uses unittest.mock to simulate Anthropic API responses
without making real API calls. Tests mock the tool_use response
format that Claude returns when forced via tool_choice.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import anthropic

from src.chat_analyzer import ChatAnalyzer
from src.models import ChatAnalysisResult, ChatMessage, FileInfo


def _make_mock_response(data: dict) -> MagicMock:
    """Helper: create a mock Anthropic response with a tool_use content block.

    The real API returns a tool_use block where block.input is already
    a parsed Python dict — no JSON string involved.
    """
    mock_response = MagicMock()
    mock_tool_block = MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.input = data
    mock_response.content = [mock_tool_block]
    return mock_response


def _make_text_only_response() -> MagicMock:
    """Helper: create a mock response with only a text block (no tool_use)."""
    mock_response = MagicMock()
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "I can see a chat screenshot."
    mock_response.content = [mock_text_block]
    return mock_response


class TestParseToolResult:
    """Tests for _parse_tool_result (converting tool_use dict to ChatMessages)."""

    def setup_method(self):
        """Create analyzer with a dummy key (no real API calls)."""
        with patch.object(anthropic, 'Anthropic'):
            self.analyzer = ChatAnalyzer(api_key="test-key")

    def test_valid_data_with_messages(self):
        """Valid dict with messages should return success with ChatMessage objects."""
        data = {
            "messages": [
                {"speaker": "right", "text": "Hey there", "timestamp": "10:42 AM"},
                {"speaker": "left", "text": "Hi!", "timestamp": None},
            ]
        }
        result = self.analyzer._parse_tool_result(data, "test.png")

        assert result.success is True
        assert len(result.messages) == 2
        assert result.messages[0].speaker == "right"
        assert result.messages[0].text == "Hey there"
        assert result.messages[0].timestamp == "10:42 AM"
        assert result.messages[1].speaker == "left"
        assert result.messages[1].text == "Hi!"
        assert result.messages[1].timestamp is None

    def test_messages_as_json_string_gets_parsed(self):
        """If messages is a JSON string instead of a list, it should be parsed."""
        data = {
            "messages": '[{"speaker": "left", "text": "Hello"}, {"speaker": "right", "text": "Hi back"}]'
        }
        result = self.analyzer._parse_tool_result(data, "test.png")

        assert result.success is True
        assert len(result.messages) == 2
        assert result.messages[0].speaker == "left"
        assert result.messages[0].text == "Hello"
        assert result.messages[1].speaker == "right"
        assert result.messages[1].text == "Hi back"

    def test_messages_as_unparseable_string_returns_raw_text(self):
        """If messages is a non-JSON string, return it as a single message."""
        data = {"messages": "Some raw text Claude returned"}
        result = self.analyzer._parse_tool_result(data, "test.png")

        assert result.success is True
        assert len(result.messages) == 1
        assert result.messages[0].text == "Some raw text Claude returned"
        assert result.messages[0].speaker == "unknown"

    def test_missing_messages_key_returns_error(self):
        """Dict without 'messages' key should return a failed result."""
        data = {"data": []}
        result = self.analyzer._parse_tool_result(data, "test.png")

        assert result.success is False
        assert "Missing 'messages' key" in result.error

    def test_empty_text_messages_are_skipped(self):
        """Messages with blank text should be filtered out."""
        data = {
            "messages": [
                {"speaker": "right", "text": "Real message"},
                {"speaker": "left", "text": "   "},
                {"speaker": "left", "text": ""},
            ]
        }
        result = self.analyzer._parse_tool_result(data, "test.png")

        assert result.success is True
        assert len(result.messages) == 1
        assert result.messages[0].text == "Real message"

    def test_string_items_salvaged_as_messages(self):
        """Bare strings in messages array should be salvaged with speaker='unknown'."""
        data = {
            "messages": [
                {"speaker": "right", "text": "Real message"},
                "stray string item",
                {"speaker": "left", "text": "Another real one"},
            ]
        }
        result = self.analyzer._parse_tool_result(data, "test.png")

        assert result.success is True
        assert len(result.messages) == 3
        assert result.messages[0].text == "Real message"
        assert result.messages[1].text == "stray string item"
        assert result.messages[1].speaker == "unknown"
        assert result.messages[2].text == "Another real one"

    def test_non_string_non_dict_items_are_skipped(self):
        """Non-string, non-dict items (ints, etc.) should be silently skipped."""
        data = {
            "messages": [
                {"speaker": "right", "text": "Real message"},
                42,
                None,
            ]
        }
        result = self.analyzer._parse_tool_result(data, "test.png")

        assert result.success is True
        assert len(result.messages) == 1
        assert result.messages[0].text == "Real message"

    def test_missing_fields_get_defaults(self):
        """Messages missing optional fields should get safe defaults."""
        data = {
            "messages": [
                {"text": "No speaker field"},
            ]
        }
        result = self.analyzer._parse_tool_result(data, "test.png")

        assert result.success is True
        assert len(result.messages) == 1
        assert result.messages[0].speaker == "unknown"
        assert result.messages[0].timestamp is None

    def test_raw_response_preserved_on_success(self):
        """The raw JSON string should be stored for debugging."""
        data = {"messages": [{"speaker": "left", "text": "Hi"}]}
        result = self.analyzer._parse_tool_result(data, "test.png")

        assert result.raw_response  # Non-empty string
        assert "Hi" in result.raw_response


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

    def test_no_tool_use_block_returns_error(self, tmp_path):
        """If response has no tool_use block, should return error."""
        img_file = tmp_path / "chat.png"
        img_file.write_bytes(b"fake png data")

        self.mock_client.messages.create.return_value = _make_text_only_response()

        result = self.analyzer.analyze_screenshot(img_file)

        assert result.success is False
        assert "No tool_use block" in result.error

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
