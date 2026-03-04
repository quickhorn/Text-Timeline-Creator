"""
Text Message Timeline Generator

Main application file that processes message screenshots into a
speaker-attributed chronological timeline.
"""

import os
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv
from src.file_scanner import scan_message_directory, display_files_found
from src.chat_analyzer import ChatAnalyzer
from src.review import review_analyses
from src.timeline_builder import build_timeline
from src.docx_exporter import export_timeline

# Configure logging for the entire application
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def main():
    """
    Main application entry point.

    Pipeline: scan files -> analyze with Claude Vision -> review -> build timeline -> export DOCX
    """

    logger.info("=" * 70)
    logger.info("Text Message Timeline Generator")
    logger.info("=" * 70)

    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        logger.error("Anthropic API key not found!")
        logger.error("Please check your .env file contains:")
        logger.error("  ANTHROPIC_API_KEY=your-key-here")
        return

    logger.info("Anthropic API key loaded successfully!")

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

    # Analyze screenshots with Claude Vision
    analyzer = ChatAnalyzer(api_key)
    results = analyzer.analyze_files(message_files)

    # Report results
    successful = sum(1 for r in results.values() if r.success)
    failed = len(results) - successful

    if successful == 0:
        logger.warning("No screenshots were successfully analyzed.")
        return

    logger.info(f"Analyzed {successful} screenshot(s) ({failed} failed)")

    # Review messages, dates, and speaker names with user
    messages = review_analyses(results, message_files)

    if not messages:
        logger.warning("No messages to build a timeline from.")
        return

    # Build chronological timeline
    timeline = build_timeline(messages)

    # Export to DOCX
    output_dir = Path("output")
    output_path = export_timeline(timeline, output_dir)
    logger.info(f"Done! Timeline saved to: {output_path}")

if __name__ == "__main__":
    main()
