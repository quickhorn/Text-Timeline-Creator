"""
Text Message Timeline Generator

Main application file that processes message files and creates a timeline.
"""

import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from src.file_scanner import scan_message_directory, display_files_found
from src.text_extractor import TextExtractor

def main():
    """
    Main application entry point
    """

    print("=" * 70)
    print("Text Message Timeline Generator")
    print("=" * 70)
    print()

    load_dotenv()

    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    if not endpoint or not key:
        print("ERROR: Azure credentials not found!")
        print("Please check your .env file contains:")
        print("  AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=...")
        print("  AZURE_DOCUMENT_INTELLIGENCE_KEY=...")
        return

    print("✅ Azure credentials loaded successfully!")
    print()

    #TODO: Let's make this configurable as quickly as possible
    messages_dir = Path(__file__).parent/ 'data' / 'messages'

    print(f"Looking for message files in: {messages_dir}")
    print()
    
    try:
        # Scan for message files
        message_files = scan_message_directory(messages_dir)
        display_files_found(message_files)

    except Exception as e:
        print(f"Error scanning for message files: {e}")
        return
    
    if not message_files:
        print("No message files found!")
        print("Please ensure you have message files in the 'data/messages' directory.")
        return
    
    # Extract text from the message files using Azure OCR
    extractor = TextExtractor(endpoint, key)
    results = extractor.extract_text_from_files(message_files)

    # Report results
    successful = sum(1 for r in results.values() if r['success'])
    failed = len(results) - successful

    if successful == 0:
        print("No text was successfully extracted from any files.")
        return

    print(f"Extracted text from {successful} file(s) ({failed} failed)")
    print()

    # TODO: Build timeline from extracted text
    # TODO: Export timeline to DOCX

if __name__ == "__main__":
    main()
