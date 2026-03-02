"""
Text Extraction Module

Handles extracting text from images and PDFs using Azure Document Intelligence.
"""

import os
from pathlib import Path
from typing import Dict, List
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import time

from src.models import FileInfo, ExtractionResult

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

        print(f"✅ Connected to Azure Document Intelligence")

    def extract_text_from_file(self, file_path: Path) -> ExtractionResult:
        """
        Extract text from a file (image or PDF) using Azure Document Intelligence.

        Args:
            file_path: Path to the file to extract text from

        Returns:
            ExtractionResult with success status, extracted text, page count, and any error
        """
        try:
            print(f"  Processing: {file_path}...", end=' ')

            with open(file_path, 'rb') as file:
                #Send to Azure for analysis
                #We use a "prebuilt-read" module which is optimized for text extraction
                poller = self.client.begin_analyze_document(
                    "prebuilt-read",
                    document=file
                )

                analysis_result = poller.result()

            full_text = analysis_result.content
            page_count = len(analysis_result.pages)

            print(f"✅ ({page_count} page(s), {len(full_text)} characters)")
            return ExtractionResult(
                success=True,
                text=full_text,
                page_count=page_count
            )
        except FileNotFoundError:
            error_msg = f"File not found: {file_path}"
            print(f"x {error_msg}")
            return ExtractionResult(success=False, error=error_msg)

        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            print(f"x {error_msg}")
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

        print(f"\nExtracting text from {total_files} file(s):")
        print("-" * 70)

        for index, file_info in enumerate(file_list, start=1):
            print(f"[{index}/{total_files}] ", end='')

            #Extract text from this file
            extraction_result = self.extract_text_from_file(file_info.full_path)

            #store result with filename as key
            results[file_info.filename] = extraction_result

            #small delay to avoid hitting API rate limits
            if index < total_files:
                time.sleep(0.7)

        successful = sum(1 for r in results.values() if r.success)
        failed = total_files - successful

        print("-" * 70)
        print(f"Extraction complete: {successful} successful, {failed} failed")
        print()

        return results

def main():
    """
    Test function for text extraction
    """
    from dotenv import load_dotenv
    from src.file_scanner import scan_message_directory

    # load environment variables
    load_dotenv()

    endpoint = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
    key = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')

    if not endpoint or not key:
        print("Error: Azure credentials not found in .env file")
        return

    #create extractor
    extractor = TextExtractor(endpoint, key)

    #scan for files
    messages_dir = Path(__file__).parent.parent / 'data' / 'test_image_messages'
    files = scan_message_directory(str(messages_dir))

    if not files:
        print("No files found to process")
        return

    #extract text
    results = extractor.extract_text_from_files(files)

    #display sample of extracted text
    print()
    print("Extracted text:")
    print("=" * 70)
    for filename, result in results.items():
        if result.success:
            text = result.text.replace('\n', ' ')
            print(f"\n{filename}:")
            print(f" {text}")
            print(f" (Total: {len(result.text)} characters)")

if __name__ == "__main__":
    main()