"""
Data Models

Dataclasses that define the structured data types used throughout the pipeline.
"""

from dataclasses import dataclass
from pathlib import Path


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