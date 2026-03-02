"""
Text Message Timeline Generator

Main application file that processes message files and creates a timeline.
"""

import os
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv
from src.file_scanner import scan_message_directory, display_files_found
from src.text_extractor import TextExtractor

# Configure logging for the entire application
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def main():
    """
    Main application entry point
    """

    logger.info("=" * 70)
    logger.info("Text Message Timeline Generator")
    logger.info("=" * 70)

    load_dotenv()

    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    if not endpoint or not key:
        logger.error("Azure credentials not found!")
        logger.error("Please check your .env file contains:")
        logger.error("  AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=...")
        logger.error("  AZURE_DOCUMENT_INTELLIGENCE_KEY=...")
        return

    logger.info("Azure credentials loaded successfully!")

    parser = argparse.ArgumentParser(description="Text Message Timeline Generator")
    parser.add_argument(
        "directory",
        nargs="?",
        default=Path("data/messages"),
        type=Path,
        help="Path to the directory containing message files (default: data/messages)"
    )
    args = parser.parse_args()

    messages_dir = args.directory

    logger.info(f"Looking for message files in: {messages_dir}")

    try:
        # Scan for message files
        message_files = scan_message_directory(messages_dir)
        display_files_found(message_files)

    except Exception as e:
        logger.error(f"Error scanning for message files: {e}")
        return

    if not message_files:
        logger.warning("No message files found!")
        logger.warning(f"Please ensure you have message files in: {messages_dir}")
        return

    # Extract text from the message files using Azure OCR
    extractor = TextExtractor(endpoint, key)
    results = extractor.extract_text_from_files(message_files)

    # Report results
    successful = sum(1 for r in results.values() if r.success)
    failed = len(results) - successful

    if successful == 0:
        logger.warning("No text was successfully extracted from any files.")
        return

    logger.info(f"Extracted text from {successful} file(s) ({failed} failed)")

    # TODO: Build timeline from extracted text
    # TODO: Export timeline to DOCX

if __name__ == "__main__":
    main()
