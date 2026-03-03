"""
Text Extraction Module

Handles extracting text from images and PDFs using Azure Document Intelligence.
Includes retry with exponential backoff for transient API failures.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.ai.formrecognizer import DocumentAnalysisClient
import time

from src.models import FileInfo, ExtractionResult

logger = logging.getLogger(__name__)

# Retry settings for transient Azure API failures
MAX_RETRIES = 3          # Total attempts = MAX_RETRIES + 1
INITIAL_RETRY_DELAY = 2  # Seconds before first retry
BACKOFF_MULTIPLIER = 2   # Each retry waits 2x longer

# Delay between processing files (seconds) — be gentle on the rate limit
BETWEEN_FILE_DELAY = 1.5


class TextExtractor:
    """
    Handles text extraction from images and PDFs using Azure Document Intelligence.
    """

    def __init__(self, endpoint: str, key: str):
        """
        Initialize the text extractor with Azure credentials.

        Args:
            endpoint: Azure Document Intelligence endpoint
            key: Azure Document Intelligence key
        """
        self.endpoint = endpoint
        self.key = key

        credential = AzureKeyCredential(self.key)
        self.client = DocumentAnalysisClient(
            endpoint=self.endpoint,
            credential=credential
        )

        logger.info("Connected to Azure Document Intelligence")

    def extract_text_from_file(self, file_path: Path) -> ExtractionResult:
        """
        Extract text from a file (image or PDF) using Azure Document Intelligence.

        Retries up to MAX_RETRIES times with exponential backoff on transient
        failures (connection errors, rate limits). Does NOT retry on file-not-found.

        Args:
            file_path: Path to the file to extract text from

        Returns:
            ExtractionResult with success status, extracted text, page count, and any error
        """
        logger.info(f"Processing: {file_path}")

        for attempt in range(MAX_RETRIES + 1):
            try:
                with open(file_path, 'rb') as file:
                    poller = self.client.begin_analyze_document(
                        "prebuilt-read",
                        document=file
                    )
                    analysis_result = poller.result()

                full_text = analysis_result.content
                page_count = len(analysis_result.pages)

                logger.info(f"Success: {page_count} page(s), {len(full_text)} characters")
                return ExtractionResult(
                    success=True,
                    text=full_text,
                    page_count=page_count
                )

            except FileNotFoundError:
                # Not transient — don't retry
                error_msg = f"File not found: {file_path}"
                logger.error(error_msg)
                return ExtractionResult(success=False, error=error_msg)

            except (OSError, HttpResponseError) as e:
                delay = INITIAL_RETRY_DELAY * (BACKOFF_MULTIPLIER ** attempt)
                if attempt < MAX_RETRIES:
                    logger.warning(
                        f"Attempt {attempt + 1}/{MAX_RETRIES + 1} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    error_msg = (
                        f"Failed after {MAX_RETRIES + 1} attempts: {e}"
                    )
                    logger.error(error_msg)
                    return ExtractionResult(success=False, error=error_msg)

            except Exception as e:
                # Unknown error — don't retry
                error_msg = f"Error processing file: {str(e)}"
                logger.error(error_msg)
                return ExtractionResult(success=False, error=error_msg)

    def extract_text_from_files(self, file_list: List[FileInfo]) -> Dict[str, ExtractionResult]:
        """
        Extract text from multiple files.

        Args:
            file_list: List of FileInfo objects from file_scanner

        Returns:
            Dictionary mapping filename to ExtractionResult
        """
        results = {}
        total_files = len(file_list)

        logger.info(f"Extracting text from {total_files} file(s):")
        logger.info("-" * 70)

        for index, file_info in enumerate(file_list, start=1):
            logger.info(f"[{index}/{total_files}] {file_info.filename}")

            #Extract text from this file
            extraction_result = self.extract_text_from_file(file_info.full_path)

            #store result with filename as key
            results[file_info.filename] = extraction_result

            # Delay between files to avoid hitting API rate limits
            if index < total_files:
                time.sleep(BETWEEN_FILE_DELAY)

        successful = sum(1 for r in results.values() if r.success)
        failed = total_files - successful

        logger.info("-" * 70)
        logger.info(f"Extraction complete: {successful} successful, {failed} failed")

        return results

def main():
    """
    Test function for text extraction
    """
    logging.basicConfig(level=logging.INFO)

    from dotenv import load_dotenv
    from src.file_scanner import scan_message_directory

    # load environment variables
    load_dotenv()

    endpoint = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
    key = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')

    if not endpoint or not key:
        logger.error("Azure credentials not found in .env file")
        return

    #create extractor
    extractor = TextExtractor(endpoint, key)

    #scan for files
    messages_dir = Path(__file__).parent.parent / 'data' / 'test_image_messages'
    files = scan_message_directory(str(messages_dir))

    if not files:
        logger.warning("No files found to process")
        return

    #extract text
    results = extractor.extract_text_from_files(files)

    #display sample of extracted text
    logger.info("Extracted text:")
    logger.info("=" * 70)
    for filename, result in results.items():
        if result.success:
            text = result.text.replace('\n', ' ')
            logger.info(f"\n{filename}:")
            logger.info(f" {text}")
            logger.info(f" (Total: {len(result.text)} characters)")

if __name__ == "__main__":
    main()