"""
Data Models

Dataclasses that define the structured data types used throughout the pipeline.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class FileInfo:
    """Represents a file found by the scanner."""
    filepath: Path
    filename: str
    extension: str

    @property
    def full_path(self) -> Path:
        """Returns the complete path including filename."""
        return self.filepath / self.filename


@dataclass
class ExtractionResult:
    """Represents the result of extracting text from a single file."""
    success: bool
    text: str = ''
    page_count: int = 0
    error: str = ''


@dataclass
class DateMatch:
    """Represents a date/time found in extracted text."""
    original_text: str
    parsed_date: datetime


@dataclass
class Message:
    """A single message with confirmed date, ready for timeline placement.
    Date is None for skipped/undated messages (placed at end of timeline).
    source_path is the full disk path for embedding images in the DOCX."""
    text: str
    source_file: str
    date: Optional[datetime] = None
    source_path: Optional[Path] = None


@dataclass
class Timeline:
    """A chronologically sorted collection of messages."""
    messages: list['Message']