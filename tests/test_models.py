"""
Tests for data models.
"""

from datetime import datetime
from pathlib import Path
from src.models import FileInfo, ExtractionResult, DateMatch, Message, Timeline


class TestFileInfo:
    """Tests for the FileInfo dataclass."""

    def test_creates_with_required_fields(self):
        info = FileInfo(
            filepath=Path("/some/dir"),
            filename="photo.jpg",
            extension=".jpg"
        )
        assert info.filepath == Path("/some/dir")
        assert info.filename == "photo.jpg"
        assert info.extension == ".jpg"

    def test_full_path_combines_filepath_and_filename(self):
        info = FileInfo(
            filepath=Path("/messages/folder"),
            filename="image.png",
            extension=".png"
        )
        assert info.full_path == Path("/messages/folder/image.png")


class TestExtractionResult:
    """Tests for the ExtractionResult dataclass."""

    def test_successful_result(self):
        result = ExtractionResult(
            success=True,
            text="Hello world",
            page_count=1
        )
        assert result.success is True
        assert result.text == "Hello world"
        assert result.page_count == 1
        assert result.error == ''

    def test_failed_result(self):
        result = ExtractionResult(
            success=False,
            error="File not found"
        )
        assert result.success is False
        assert result.text == ''
        assert result.page_count == 0
        assert result.error == "File not found"

    def test_success_is_required(self):
        """ExtractionResult must be created with an explicit success value."""
        try:
            ExtractionResult()
            assert False, "Should have raised TypeError"
        except TypeError:
            pass


class TestDateMatch:
    """Tests for the DateMatch dataclass."""

    def test_creates_with_required_fields(self):
        match = DateMatch(
            original_text="Mar 15, 2024",
            parsed_date=datetime(2024, 3, 15)
        )
        assert match.original_text == "Mar 15, 2024"
        assert match.parsed_date == datetime(2024, 3, 15)

    def test_both_fields_are_required(self):
        """DateMatch needs both original_text and parsed_date."""
        try:
            DateMatch()
            assert False, "Should have raised TypeError"
        except TypeError:
            pass


class TestMessage:
    """Tests for the Message dataclass."""

    def test_creates_with_date(self):
        msg = Message(
            text="Hello",
            source_file="img.jpg",
            date=datetime(2024, 3, 15)
        )
        assert msg.text == "Hello"
        assert msg.source_file == "img.jpg"
        assert msg.date == datetime(2024, 3, 15)

    def test_date_defaults_to_none(self):
        """Messages can be created without a date (undated/skipped)."""
        msg = Message(text="Hello", source_file="img.jpg")
        assert msg.date is None

    def test_text_and_source_file_are_required(self):
        try:
            Message()
            assert False, "Should have raised TypeError"
        except TypeError:
            pass


class TestTimeline:
    """Tests for the Timeline dataclass."""

    def test_creates_with_message_list(self):
        msgs = [
            Message(text="A", source_file="a.jpg", date=datetime(2024, 1, 1)),
            Message(text="B", source_file="b.jpg", date=datetime(2024, 1, 2)),
        ]
        timeline = Timeline(messages=msgs)
        assert len(timeline.messages) == 2

    def test_messages_is_required(self):
        try:
            Timeline()
            assert False, "Should have raised TypeError"
        except TypeError:
            pass