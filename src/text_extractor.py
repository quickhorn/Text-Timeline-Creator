"""
Text Extraction Module

Handles extracting text from images and PDFs using Azure Document Intelligence.
"""

import os
from pathlib import Path
from typing import Dict, Optional
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import time

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
        
    def extract_text_from_file(self, file_path: Path) -> Dict[str, any]:
        """
        Extract text from a file (image or PDF) using Azure Document Intelligence.
        
        Args:
            file_path: Path to the file to extract text from
            
        Returns:
            Dictionary containing extracted text and metadata
            {
                'success': bool,
                'text': str (full extracted text),
                'page_count': int,
                'error': str (if success is False)
            }
        """
        result = {
            'success': False,
            'text': '',
            'page_count': 0,
            'error': ''
        }
        
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

            result['success'] = True
            result['text'] = full_text
            result['page_count'] = page_count

            print(f"✅ ({page_count} page(s), {len(full_text)} characters)")
            print(f"Result {result['text']}")
        except FileNotFoundError:
            error_msg = f"File not found: {file_path}"
            result['error'] = error_msg
            print(f"x {error_msg}")
    
        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            result['error'] = error_msg
            print(f"x {error_msg}")
            
        return result

    def extract_text_from_files(self, file_list: list) -> Dict[str, Dict]:
        """
        Extract text from multiple files.
        
        Args:
            file_list: List of file dictionaries from file_scanner
            
        Returns:
            Dictionary mapping filepath to extraction results:
            {
                '/path/to/file.jpg': {
                    'success': True,
                    'text': '...',
                    'page_count': 1,
                    'error': None
                },
                ...
            }
        """
        results = {}
        total_files = len(file_list)

        print(f"\nExtracting text from {total_files} file(s):")
        print("-" * 70)

        for index, file_info in enumerate(file_list, start=1):
            print(f"File Info {file_info}")
            file_path = file_info['filepath']
            file_name = file_info['filename']

            print(f"[{index}/{total_files}] ", end='')

            #Extract text from this file
            extraction_result = self.extract_text_from_file(Path.joinpath(file_path, file_name))

            #store result with filepath as key
            results[str(file_name)] = extraction_result

            #small delay to avoid hitting API rate limits
            if index < total_files:
                time.sleep(0.7)
        
        print(f"Results: {results}")
        successful = sum(1 for r in results.values()if r['success'])
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
    from file_scanner import scan_message_directory

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
        if result['success']:
            filename = filename
            text = result['text'].replace('\n', ' ')
            print(f"\n{filename}:")
            print(f" {text}")
            print(f" (Total: {len(result['text'])} characters)")

if __name__ == "__main__":
    main()