"""
User Review Module

CLI interface for reviewing auto-detected dates and confirming or correcting them.
The paralegal sees each extracted message, its auto-detected date, and can confirm,
override, or skip.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import dateparser

from src.date_parser import extract_best_date
from src.models import ExtractionResult, FileInfo, Message

logger = logging.getLogger(__name__)

TEXT_PREVIEW_LENGTH = 200


def review_extractions(
    results: Dict[str, ExtractionResult],
    file_list: List[FileInfo],
) -> List[Message]:
    """
    Interactive review of extracted text and auto-detected dates.

    For each successfully extracted file:
    - Shows a preview of the extracted text
    - Shows the auto-detected date (if any) with the matched text
    - Lets the user confirm, override, or skip

    Args:
        results: Dictionary mapping filename to ExtractionResult
        file_list: List of FileInfo objects for resolving full file paths
                   (used to embed source images in the DOCX export)

    Returns:
        List of Message objects with confirmed dates
    """
    # Build filename -> full path lookup for embedding images
    path_lookup = {fi.filename: fi.full_path for fi in file_list}

    successful = {k: v for k, v in results.items() if v.success}

    if not successful:
        logger.warning("No successful extractions to review.")
        return []

    messages = []
    total = len(successful)

    print("\n" + "=" * 70)
    print("DATE REVIEW")
    print("For each message, confirm the auto-detected date or enter a new one.")
    print("=" * 70)

    for index, (filename, result) in enumerate(successful.items(), start=1):
        print(f"\n--- Message {index}/{total} ---")
        print(f"File: {filename}")

        # Show text preview
        text_preview = result.text[:TEXT_PREVIEW_LENGTH]
        if len(result.text) > TEXT_PREVIEW_LENGTH:
            text_preview += "..."
        print(f'Text: "{text_preview}"')

        # Try auto-detection
        auto_date = extract_best_date(result.text)

        if auto_date:
            print(f"Auto-detected date: {auto_date.strftime('%Y-%m-%d %I:%M %p')}")
            confirmed_date = _prompt_confirm_date(auto_date)
        else:
            print("No date detected.")
            confirmed_date = _prompt_enter_date()

        messages.append(Message(
            text=result.text,
            date=confirmed_date,
            source_file=filename,
            source_path=path_lookup.get(filename),
        ))

        if confirmed_date:
            print(f"  -> Confirmed: {confirmed_date.strftime('%Y-%m-%d %I:%M %p')}")
        else:
            print("  -> Undated (will appear at end of timeline)")

    dated = sum(1 for m in messages if m.date is not None)
    undated = len(messages) - dated

    print(f"\n{'=' * 70}")
    print(f"Review complete: {dated} message(s) dated, {undated} undated")
    print(f"{'=' * 70}")

    return messages


def _prompt_confirm_date(auto_date: datetime) -> Optional[datetime]:
    """
    Prompt user to confirm or override an auto-detected date.
    Loops on invalid input until the user provides a valid date,
    confirms with Enter, or explicitly skips with 's'.

    Returns:
        Confirmed datetime, or None if skipped
    """
    while True:
        response = input(
            "[Enter] to confirm, type a date to override, or 's' to skip: "
        ).strip()

        if response == '':
            return auto_date
        if response.lower() == 's':
            return None

        parsed = dateparser.parse(response, settings={'PREFER_DATES_FROM': 'past'})
        if parsed:
            return parsed

        print(f"  Could not parse '{response}'. Try again (e.g., '3/15/2024').")


def _prompt_enter_date() -> Optional[datetime]:
    """
    Prompt user to enter a date when none was auto-detected.
    Loops on invalid input until the user provides a valid date
    or explicitly skips with 's'.

    Returns:
        Parsed datetime, or None if skipped
    """
    while True:
        response = input("Enter a date (or 's' to skip): ").strip()

        if response.lower() == 's':
            return None

        if response == '':
            print("  Please enter a date or 's' to skip.")
            continue

        parsed = dateparser.parse(response, settings={'PREFER_DATES_FROM': 'past'})
        if parsed:
            return parsed

        print(f"  Could not parse '{response}'. Try again (e.g., '3/15/2024').")
