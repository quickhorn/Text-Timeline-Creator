"""
File Scanner Module

This module scans a directory for message files (images and PDFs)
and returns a list of files to process.

"""

import logging
from pathlib import Path
from typing import List
from src.models import FileInfo

logger = logging.getLogger(__name__)

# Constants: Values that don't change
SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.heic']
SUPPORTED_DOCUMENT_FORMATS = ['.pdf']
SUPPORTED_FORMATS = SUPPORTED_IMAGE_FORMATS + SUPPORTED_DOCUMENT_FORMATS

def scan_message_directory(directory_path: str) -> List[FileInfo]:
    """
    Scan a directory for message files (images and PDFs)
    and return a list of files to process.
    """

    directory = Path(directory_path)

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")

    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory_path}")

    files_found = []

    for file_path, dirs, files in directory.walk():
        for file in files:
            path_file = Path(file)
            if path_file.name.startswith('.'):
                continue

            extension = path_file.suffix.lower()

            if extension in SUPPORTED_FORMATS:
                files_found.append(FileInfo(
                    filepath=file_path,
                    filename=path_file.name,
                    extension=extension
                ))

    logger.debug(f"Found {len(files_found)} supported files in {directory_path}")
    return files_found

def display_files_found(files: List[FileInfo]) -> None:
    """
    Display the files found in a formatted way.

    Args:
        files: List of FileInfo objects from scan_message_directory

    """
    if not files:
        logger.info("No message files found.")
        return

    logger.info(f"Found {len(files)} message files:")

    header = f"{'#':<5} {'Filename':<40} {'Filepath':<80}"
    logger.info(header)
    logger.info("-" * 70)

    for index, file_info in enumerate(files, start=1):
        logger.info(f"{index:<5} {file_info.filename:<40} "
            f"{file_info.filepath}")

def main():
    """
    Test function - run this module directly to test it.
    """
    logging.basicConfig(level=logging.DEBUG)

    messages_dir = Path(__file__).parent.parent / 'data' / 'test_messages'

    logger.info(f"Scanning directory: {messages_dir}")
    logger.info(f"Supported formats: {SUPPORTED_FORMATS}")

    try:
        files = scan_message_directory(str(messages_dir))
        display_files_found(files)
    except FileNotFoundError as e:
        logger.error(f"{e}")
        logger.error(f"Please create the directory and add some message files:")
        logger.error(f" mkdir -p {messages_dir}")
        return

    logger.info("Scan complete!")

if __name__ == "__main__":
    main()