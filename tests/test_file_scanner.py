"""
Tests for the file scanner module.
"""

from pathlib import Path
import pytest
from src.file_scanner import scan_message_directory, SUPPORTED_FORMATS
from src.models import FileInfo


# Path to test fixtures
TEST_MESSAGES_DIR = Path(__file__).parent.parent / 'data' / 'test_messages'


class TestScanMessageDirectory:
    """Tests for scan_message_directory function."""

    def test_finds_all_supported_files(self):
        """Should find 9 supported files across all subdirectories."""
        files = scan_message_directory(str(TEST_MESSAGES_DIR))
        assert len(files) == 9

    def test_returns_file_info_objects(self):
        """Should return FileInfo dataclass instances, not dicts."""
        files = scan_message_directory(str(TEST_MESSAGES_DIR))
        for file in files:
            assert isinstance(file, FileInfo)

    def test_filters_out_unsupported_formats(self):
        """Should not include .txt files (not_a_message.txt)."""
        files = scan_message_directory(str(TEST_MESSAGES_DIR))
        extensions = [f.extension for f in files]
        assert '.txt' not in extensions

    def test_all_extensions_are_supported(self):
        """Every returned file should have a supported extension."""
        files = scan_message_directory(str(TEST_MESSAGES_DIR))
        for file in files:
            assert file.extension in SUPPORTED_FORMATS

    def test_scans_subdirectories_recursively(self):
        """Should find files in nested subdirectories."""
        files = scan_message_directory(str(TEST_MESSAGES_DIR))
        # Files exist in more-messages/, more-messages/even-more-messages/, more-messages-2/
        filepaths = [str(f.filepath) for f in files]
        has_nested = any('more-messages' in fp for fp in filepaths)
        assert has_nested

    def test_raises_error_for_missing_directory(self):
        """Should raise FileNotFoundError for a directory that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            scan_message_directory("/nonexistent/path/to/nowhere")

    def test_raises_error_for_file_path(self):
        """Should raise NotADirectoryError when given a file instead of directory."""
        file_path = TEST_MESSAGES_DIR / 'not_a_message.txt'
        with pytest.raises(NotADirectoryError):
            scan_message_directory(str(file_path))

    def test_filenames_are_correct(self):
        """Filenames should not include directory components."""
        files = scan_message_directory(str(TEST_MESSAGES_DIR))
        for file in files:
            assert '/' not in file.filename
            assert '\\' not in file.filename