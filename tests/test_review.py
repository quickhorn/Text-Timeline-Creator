"""
Tests for the user review module.

Uses unittest.mock.patch to simulate user input (input() calls)
without actually prompting in the terminal.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from src.models import ExtractionResult, FileInfo, Message
from src.review import review_extractions, _prompt_confirm_date, _prompt_enter_date


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


class TestReviewExtractions:
    """Tests for review_extractions (the main review loop)."""

    def test_empty_results_returns_empty(self):
        """No successful extractions should return an empty list."""
        results = {}
        with patch('builtins.input'):
            messages = review_extractions(results, [])
        assert messages == []

    def test_all_failed_returns_empty(self):
        """Only failed extractions should return an empty list."""
        results = {
            'a.jpg': ExtractionResult(success=False, error="fail"),
        }
        with patch('builtins.input'):
            messages = review_extractions(results, [])
        assert messages == []

    def test_confirm_auto_detected_date(self):
        """Confirming (Enter) should produce a Message with a date."""
        file_list = [
            FileInfo(filepath=Path("/imgs"), filename="a.jpg", extension=".jpg"),
        ]
        results = {
            'a.jpg': ExtractionResult(
                success=True,
                text="Message from Mar 15, 2024",
                page_count=1
            ),
        }
        with patch('builtins.input', return_value=''):
            messages = review_extractions(results, file_list)
        assert len(messages) == 1
        assert isinstance(messages[0], Message)
        assert messages[0].date is not None
        assert messages[0].source_file == 'a.jpg'
        assert messages[0].source_path == Path("/imgs/a.jpg")

    def test_skip_produces_undated_message(self):
        """Skipping should produce a Message with date=None."""
        results = {
            'a.jpg': ExtractionResult(
                success=True,
                text="Message from Mar 15, 2024",
                page_count=1
            ),
        }
        with patch('builtins.input', return_value='s'):
            messages = review_extractions(results, [])
        assert len(messages) == 1
        assert messages[0].date is None

    def test_multiple_files_all_confirmed(self):
        """Multiple files confirmed should produce that many Messages."""
        results = {
            'a.jpg': ExtractionResult(success=True, text="Mar 1, 2024", page_count=1),
            'b.jpg': ExtractionResult(success=True, text="Mar 2, 2024", page_count=1),
        }
        with patch('builtins.input', return_value=''):
            messages = review_extractions(results, [])
        assert len(messages) == 2

    def test_source_path_populated_from_file_list(self):
        """source_path should be set when file_list is provided."""
        file_list = [
            FileInfo(filepath=Path("/data"), filename="img.png", extension=".png"),
        ]
        results = {
            'img.png': ExtractionResult(success=True, text="Mar 1, 2024", page_count=1),
        }
        with patch('builtins.input', return_value=''):
            messages = review_extractions(results, file_list)
        assert messages[0].source_path == Path("/data/img.png")
