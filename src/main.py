"""
Text Message Timeline Generator

Main application file that processes message files and creates a timeline.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from src.file_scanner import scan_message_directory, display_files_found

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
    
    # TODO: Process files and create timeline
    print("Processing files...")
    # ... rest of processing logic
    
if __name__ == "__main__":
    main()
