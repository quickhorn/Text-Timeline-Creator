"""
Tests for data models.
"""

from pathlib import Path
from src.models import FileInfo, ExtractionResult


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