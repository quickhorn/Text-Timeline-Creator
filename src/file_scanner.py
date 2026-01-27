"""
File Scanner Module

This module scans a directory for message files (images and PDFs)
and returns a list of files to process.

"""

from pathlib import Path
from typing import List, Dict
import os


# Constants: Values that don't change
SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.heic']
SUPPORTED_DOCUMENT_FORMATS = ['.pdf']
SUPPORTED_FORMATS = SUPPORTED_IMAGE_FORMATS + SUPPORTED_DOCUMENT_FORMATS

def scan_message_directory(directory_path: str) -> List[Dict[str, any]]:
    """
    Scan a directory for message files (images and PDFs)
    and return a list of files to process.
    """

    directory = Path(directory_path)

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")

    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory_path}")

    filesFound = []

    for file_path, dirs, files in directory.walk():
        #print(f"file_path: {file_path}. directories: {dirs}. files: {files}")
        for file in files:
            pathFile = Path(file)
            if pathFile.name.startswith('.'):
                continue

            extension = pathFile.suffix.lower()

            if extension in SUPPORTED_FORMATS:
                file_info = {
                    'filepath': file_path,
                    'filename': pathFile.name,
                    'extension': extension
                }
                print
                filesFound.append(file_info)
        

    return filesFound

def display_files_found(files: List[Dict[str, any]]) -> None:
    """
    Display the files found in a formatted way.

    Args:
        files (List[Dict[str, any]]): List of files found from scan_message_directory

    """
    print("Files found:")
    if not files:
        print("No message files found.")
        return

    print(f"Found {len(files)} message files:")
    print()
    print(f"{'#':<5} {'Filename':<40} {'Filepath':<80}")
    print("-" * 70)

    for index, file_info in enumerate(files, start=1):
        print(f"FileInfo: ")
        print(f"{index:<5} {file_info['filename']:<40} "
            f"{file_info['filepath']}")
    
    print()

def main():
    """
    Test function - run this module directly to test it.
    """
    messages_dir = Path(__file__).parent.parent / 'data' / 'test_messages'
    
    print(f"Scanning directory: {messages_dir}")
    print(f"Supported formats: {SUPPORTED_FORMATS}")
    print()
    
    try:
        files = scan_message_directory(str(messages_dir))
        display_files_found(files)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print()
        print(f"Please create the directory and add some message files:")
        print(f" mkdir -p {messages_dir}")
        return
    
    print("Scan complete!")

if __name__ == "__main__":
    main()
