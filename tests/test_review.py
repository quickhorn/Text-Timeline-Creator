"""
Tests for the user review module.

Uses unittest.mock.patch to simulate user input (input() calls)
without actually prompting in the terminal.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from src.models import ChatAnalysisResult, ChatMessage, FileInfo, Message
from src.review import (
    review_analyses,
    _detect_date,
    _prompt_confirm_date,
    _prompt_enter_date,
    _prompt_speaker_names,
)


class TestDetectDate:
    """Tests for _detect_date (two-stage date detection)."""

    def test_uses_claude_timestamp_first(self):
        """Should parse Claude's extracted timestamp before trying fallback."""
        result = ChatAnalysisResult(
            success=True,
            messages=[
                ChatMessage(speaker="right", text="Hey", timestamp="Mar 15, 2024"),
                ChatMessage(speaker="left", text="Hi"),
            ],
        )
        date = _detect_date(result)
        assert date is not None
        assert date.month == 3
        assert date.day == 15

    def test_skips_null_timestamps(self):
        """Should skip messages with no timestamp and use the first valid one."""
        result = ChatAnalysisResult(
            success=True,
            messages=[
                ChatMessage(speaker="right", text="Hey", timestamp=None),
                ChatMessage(speaker="left", text="Hi", timestamp="Jun 1, 2024"),
            ],
        )
        date = _detect_date(result)
        assert date is not None
        assert date.month == 6

    def test_falls_back_to_date_parser(self):
        """When no Claude timestamps exist, should use extract_best_date on text."""
        result = ChatAnalysisResult(
            success=True,
            messages=[
                ChatMessage(speaker="right", text="See you on Mar 15"),
                ChatMessage(speaker="left", text="Sounds good"),
            ],
        )
        date = _detect_date(result)
        assert date is not None
        assert date.month == 3
        assert date.day == 15

    def test_returns_none_when_no_date_found(self):
        """Should return None when neither timestamps nor text contain dates."""
        result = ChatAnalysisResult(
            success=True,
            messages=[
                ChatMessage(speaker="right", text="Hello"),
                ChatMessage(speaker="left", text="Hi"),
            ],
        )
        date = _detect_date(result)
        assert date is None

    def test_empty_messages_returns_none(self):
        """Should handle results with no messages gracefully."""
        result = ChatAnalysisResult(success=True, messages=[])
        date = _detect_date(result)
        assert date is None


class TestPromptSpeakerNames:
    """Tests for _prompt_speaker_names (speaker naming with memory)."""

    def test_prompts_for_new_speakers(self):
        """First screenshot: should prompt in sorted order (left, then right)."""
        result = ChatAnalysisResult(
            success=True,
            messages=[
                ChatMessage(speaker="right", text="Hey"),
                ChatMessage(speaker="left", text="Hi"),
            ],
        )
        # sorted order: left first, then right
        with patch('builtins.input', side_effect=['Mike', 'Jenna']):
            names = _prompt_speaker_names(result, {})

        assert names["left"] == "Mike"
        assert names["right"] == "Jenna"

    def test_defaults_when_enter_pressed(self):
        """Pressing Enter should use default names."""
        result = ChatAnalysisResult(
            success=True,
            messages=[ChatMessage(speaker="right", text="Hey")],
        )
        with patch('builtins.input', return_value=''):
            names = _prompt_speaker_names(result, {})

        assert names["right"] == "Speaker Right"

    def test_remembers_names_across_screenshots(self):
        """Existing names should be shown and confirmed with Enter."""
        result = ChatAnalysisResult(
            success=True,
            messages=[
                ChatMessage(speaker="right", text="Hey"),
                ChatMessage(speaker="left", text="Hi"),
            ],
        )
        existing = {"right": "Jenna", "left": "Mike"}

        # Press Enter to confirm existing names
        with patch('builtins.input', return_value=''):
            names = _prompt_speaker_names(result, existing)

        assert names["right"] == "Jenna"
        assert names["left"] == "Mike"

    def test_rename_existing_speakers(self):
        """Typing 'r' should allow renaming existing speakers."""
        result = ChatAnalysisResult(
            success=True,
            messages=[
                ChatMessage(speaker="right", text="Hey"),
                ChatMessage(speaker="left", text="Hi"),
            ],
        )
        existing = {"right": "Jenna", "left": "Mike"}

        # 'r' to rename, then new names (sorted order: left, then right)
        with patch('builtins.input', side_effect=['r', 'Tom', 'Sarah']):
            names = _prompt_speaker_names(result, existing)

        assert names["left"] == "Tom"
        assert names["right"] == "Sarah"

    def test_empty_messages_returns_current_names(self):
        """No speakers in screenshot should return existing names unchanged."""
        result = ChatAnalysisResult(success=True, messages=[])
        existing = {"right": "Jenna"}

        names = _prompt_speaker_names(result, existing)
        assert names == existing


class TestPromptConfirmDate:
    """Tests for _prompt_confirm_date (auto-detected date exists)."""

    def test_enter_confirms_auto_date(self):
        """Pressing Enter (empty input) should return the auto-detected date."""
        auto_date = datetime(2024, 3, 15, 10, 42)
        with patch('builtins.input', return_value=''):
            result = _prompt_confirm_date(auto_date)
        assert result == auto_date

    def test_s_skips(self):
        """Typing 's' should return None (skip)."""
        auto_date = datetime(2024, 3, 15)
        with patch('builtins.input', return_value='s'):
            result = _prompt_confirm_date(auto_date)
        assert result is None

    def test_valid_date_overrides(self):
        """Typing a valid date should override the auto-detected one."""
        auto_date = datetime(2024, 3, 15)
        with patch('builtins.input', return_value='6/1/2024'):
            result = _prompt_confirm_date(auto_date)
        assert result is not None
        assert result.month == 6
        assert result.day == 1

    def test_invalid_then_valid_retries(self):
        """Invalid input should re-prompt, then accept valid input."""
        auto_date = datetime(2024, 3, 15)
        with patch('builtins.input', side_effect=['not a date', '6/1/2024']):
            result = _prompt_confirm_date(auto_date)
        assert result.month == 6

    def test_invalid_then_enter_confirms(self):
        """Invalid input then Enter should confirm the auto-detected date."""
        auto_date = datetime(2024, 3, 15)
        with patch('builtins.input', side_effect=['garbage', '']):
            result = _prompt_confirm_date(auto_date)
        assert result == auto_date


class TestPromptEnterDate:
    """Tests for _prompt_enter_date (no auto-detected date)."""

    def test_valid_date_returns_datetime(self):
        """Typing a valid date should return a parsed datetime."""
        with patch('builtins.input', return_value='3/15/2024'):
            result = _prompt_enter_date()
        assert result is not None
        assert result.month == 3

    def test_s_skips(self):
        """Typing 's' should return None."""
        with patch('builtins.input', return_value='s'):
            result = _prompt_enter_date()
        assert result is None

    def test_empty_then_valid_retries(self):
        """Empty input should re-prompt, not skip."""
        with patch('builtins.input', side_effect=['', '3/15/2024']):
            result = _prompt_enter_date()
        assert result is not None
        assert result.month == 3

    def test_invalid_then_skip_retries(self):
        """Invalid input should re-prompt, then 's' should skip."""
        with patch('builtins.input', side_effect=['not a date', 's']):
            result = _prompt_enter_date()
        assert result is None


class TestReviewAnalyses:
    """Tests for review_analyses (the main review loop)."""

    def test_empty_results_returns_empty(self):
        """No successful analyses should return an empty list."""
        results = {}
        with patch('builtins.input'):
            messages = review_analyses(results, [])
        assert messages == []

    def test_all_failed_returns_empty(self):
        """Only failed analyses should return an empty list."""
        results = {
            'a.jpg': ChatAnalysisResult(success=False, error="fail"),
        }
        with patch('builtins.input'):
            messages = review_analyses(results, [])
        assert messages == []

    def test_produces_message_per_chat_message(self):
        """Each ChatMessage should become a separate Message in the output."""
        file_list = [
            FileInfo(filepath=Path("/imgs"), filename="a.png", extension=".png"),
        ]
        results = {
            'a.png': ChatAnalysisResult(
                success=True,
                messages=[
                    ChatMessage(speaker="right", text="Hey", timestamp="Mar 15, 2024"),
                    ChatMessage(speaker="left", text="Hi"),
                    ChatMessage(speaker="right", text="How are you?"),
                ],
            ),
        }

        # Confirm date (Enter), name speakers (sorted: left=Mike, right=Jenna)
        with patch('builtins.input', side_effect=['', 'Mike', 'Jenna']):
            messages = review_analyses(results, file_list)

        assert len(messages) == 3
        assert all(isinstance(m, Message) for m in messages)
        assert messages[0].text == "Hey"
        assert messages[0].speaker == "Jenna"    # right speaker
        assert messages[1].text == "Hi"
        assert messages[1].speaker == "Mike"     # left speaker
        assert messages[2].text == "How are you?"
        assert messages[2].speaker == "Jenna"    # right speaker

    def test_all_messages_share_same_date_and_source(self):
        """All messages from one screenshot should share date and source."""
        file_list = [
            FileInfo(filepath=Path("/imgs"), filename="chat.jpg", extension=".jpg"),
        ]
        results = {
            'chat.jpg': ChatAnalysisResult(
                success=True,
                messages=[
                    ChatMessage(speaker="right", text="A", timestamp="Jun 1, 2024"),
                    ChatMessage(speaker="left", text="B"),
                ],
            ),
        }

        # sorted order: left=Bob, right=Alice
        with patch('builtins.input', side_effect=['', 'Bob', 'Alice']):
            messages = review_analyses(results, file_list)

        assert messages[0].date == messages[1].date
        assert messages[0].source_file == "chat.jpg"
        assert messages[1].source_file == "chat.jpg"
        assert messages[0].source_path == Path("/imgs/chat.jpg")

    def test_speaker_names_carry_across_screenshots(self):
        """Speaker names from first screenshot should be remembered for second."""
        file_list = [
            FileInfo(filepath=Path("/imgs"), filename="a.png", extension=".png"),
            FileInfo(filepath=Path("/imgs"), filename="b.png", extension=".png"),
        ]
        results = {
            'a.png': ChatAnalysisResult(
                success=True,
                messages=[
                    ChatMessage(speaker="right", text="First", timestamp="Mar 1, 2024"),
                ],
            ),
            'b.png': ChatAnalysisResult(
                success=True,
                messages=[
                    ChatMessage(speaker="right", text="Second", timestamp="Mar 2, 2024"),
                ],
            ),
        }

        # First screenshot: confirm date, name speaker "Jenna"
        # Second screenshot: confirm date, confirm existing name (Enter)
        with patch('builtins.input', side_effect=['', 'Jenna', '', '']):
            messages = review_analyses(results, file_list)

        assert len(messages) == 2
        assert messages[0].speaker == "Jenna"
        assert messages[1].speaker == "Jenna"

    def test_skip_date_produces_undated_messages(self):
        """Skipping date should produce Messages with date=None."""
        results = {
            'a.png': ChatAnalysisResult(
                success=True,
                messages=[
                    ChatMessage(speaker="right", text="Hello"),
                ],
            ),
        }

        # 's' to skip date, name speaker
        with patch('builtins.input', side_effect=['s', 'Jenna']):
            messages = review_analyses(results, [])

        assert len(messages) == 1
        assert messages[0].date is None
