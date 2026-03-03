"""
Tests for the date parser module.
"""

from datetime import datetime
from src.date_parser import extract_dates, extract_best_date, _is_valid_date_match
from src.models import DateMatch


class TestExtractDates:
    """Tests for extract_dates function."""

    def test_finds_absolute_date(self):
        """Should find a standard date like 'Mar 15, 2024'."""
        matches = extract_dates("Messages from Mar 15, 2024")
        assert len(matches) >= 1
        assert any(m.parsed_date.year == 2024 and m.parsed_date.month == 3
                    for m in matches)

    def test_finds_date_with_time(self):
        """Should find date+time like '3/15/2024 10:42 AM'."""
        matches = extract_dates("Sent on 3/15/2024 10:42 AM")
        assert len(matches) >= 1
        assert any(m.parsed_date.month == 3 and m.parsed_date.day == 15
                    for m in matches)

    def test_finds_relative_date_yesterday(self):
        """Should find 'Yesterday' and resolve it to a datetime."""
        matches = extract_dates("Yesterday at noon")
        assert len(matches) >= 1
        # Yesterday should be a real datetime, not None
        assert isinstance(matches[0].parsed_date, datetime)

    def test_finds_time_only(self):
        """Should find a standalone time like '10:42 AM'."""
        matches = extract_dates("Message received 10:42 AM")
        assert len(matches) >= 1
        assert any(m.parsed_date.hour == 10 and m.parsed_date.minute == 42
                    for m in matches)

    def test_returns_empty_for_no_dates(self):
        """Plain text with no dates should return an empty list."""
        matches = extract_dates("Just some random text here")
        assert matches == []

    def test_returns_empty_for_empty_string(self):
        matches = extract_dates("")
        assert matches == []

    def test_returns_empty_for_whitespace(self):
        matches = extract_dates("   ")
        assert matches == []

    def test_returns_date_match_objects(self):
        """Results should be DateMatch dataclass instances."""
        matches = extract_dates("Mar 15, 2024")
        assert len(matches) >= 1
        assert isinstance(matches[0], DateMatch)

    def test_filters_false_positive_no(self):
        """The word 'no' should not be matched as November."""
        matches = extract_dates("I have no idea what you mean")
        assert matches == []

    def test_filters_false_positive_common_words(self):
        """Common English words should not produce date matches."""
        matches = extract_dates("How are you doing today")
        # 'today' is in RELATIVE_DATE_WORDS so it may match, but 'are' should not
        for m in matches:
            assert m.original_text.strip().lower() != "are"


class TestExtractBestDate:
    """Tests for extract_best_date convenience function."""

    def test_returns_datetime_for_valid_date(self):
        result = extract_best_date("Mar 15, 2024")
        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_returns_none_for_no_dates(self):
        result = extract_best_date("No dates in this text")
        assert result is None

    def test_returns_none_for_empty_string(self):
        result = extract_best_date("")
        assert result is None


class TestIsValidDateMatch:
    """Tests for the _is_valid_date_match filter function."""

    def test_accepts_text_with_digits(self):
        assert _is_valid_date_match("3/15/2024") is True
        assert _is_valid_date_match("10:42 AM") is True

    def test_accepts_relative_date_words(self):
        assert _is_valid_date_match("yesterday") is True
        assert _is_valid_date_match("Yesterday") is True
        assert _is_valid_date_match("Monday") is True
        assert _is_valid_date_match("today") is True

    def test_rejects_common_words(self):
        assert _is_valid_date_match("no") is False
        assert _is_valid_date_match("are") is False
        assert _is_valid_date_match("the") is False

    def test_rejects_empty_string(self):
        assert _is_valid_date_match("") is False
