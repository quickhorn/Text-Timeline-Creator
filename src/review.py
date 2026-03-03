"""
User Review Module

CLI interface for reviewing Claude Vision analysis results.
The paralegal sees structured messages with speaker labels, confirms dates,
and names the speakers for the timeline.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import dateparser

from src.date_parser import extract_best_date
from src.models import ChatAnalysisResult, FileInfo, Message

logger = logging.getLogger(__name__)


def review_analyses(
    results: Dict[str, ChatAnalysisResult],
    file_list: List[FileInfo],
) -> List[Message]:
    """
    Interactive review of Claude Vision analysis results.

    For each successfully analyzed screenshot:
    - Shows the structured messages with speaker labels
    - Detects a date (from Claude's timestamps or fallback date parser)
    - Lets the user confirm, override, or skip the date
    - Asks the user to name the speakers (remembered across screenshots)

    Args:
        results: Dictionary mapping filename to ChatAnalysisResult
        file_list: List of FileInfo objects for resolving full file paths

    Returns:
        List of Message objects with confirmed dates and speaker names
    """
    path_lookup = {fi.filename: fi.full_path for fi in file_list}

    successful = {k: v for k, v in results.items() if v.success}

    if not successful:
        logger.warning("No successful analyses to review.")
        return []

    messages = []
    total = len(successful)

    # Remember speaker names across screenshots
    speaker_names: Dict[str, str] = {}

    print("\n" + "=" * 70)
    print("REVIEW")
    print("Review messages, confirm dates, and name the speakers.")
    print("=" * 70)

    for index, (filename, result) in enumerate(successful.items(), start=1):
        print(f"\n--- Screenshot {index}/{total}: {filename} ---")
        print(f"Found {len(result.messages)} message(s):\n")

        for msg in result.messages:
            label = msg.speaker.capitalize()
            print(f"  [{label}] {msg.text}")

        # Detect date: try Claude's timestamps first, then fallback
        auto_date = _detect_date(result)

        if auto_date:
            print(f"\nDate detected: {auto_date.strftime('%Y-%m-%d %I:%M %p')}")
            confirmed_date = _prompt_confirm_date(auto_date)
        else:
            print("\nNo date detected.")
            confirmed_date = _prompt_enter_date()

        if confirmed_date:
            print(f"  -> Confirmed: {confirmed_date.strftime('%Y-%m-%d %I:%M %p')}")
        else:
            print("  -> Undated (will appear at end of timeline)")

        # Name the speakers
        speaker_names = _prompt_speaker_names(result, speaker_names)

        # Convert each ChatMessage into a Message for the timeline
        source_path = path_lookup.get(filename)
        for msg in result.messages:
            messages.append(Message(
                text=msg.text,
                source_file=filename,
                date=confirmed_date,
                source_path=source_path,
                speaker=speaker_names.get(msg.speaker),
            ))

    dated = sum(1 for m in messages if m.date is not None)
    undated = len(messages) - dated

    print(f"\n{'=' * 70}")
    print(f"Review complete: {dated} message(s) dated, {undated} undated")
    print(f"{'=' * 70}")

    return messages


def _detect_date(result: ChatAnalysisResult) -> Optional[datetime]:
    """
    Try to find a date from the analysis result.

    Strategy:
    1. Look for Claude-extracted timestamps on individual messages
    2. Fall back to extract_best_date() on the concatenated message text

    Returns:
        Parsed datetime, or None if no date found
    """
    # Try Claude's timestamps first (pick the first non-null one)
    for msg in result.messages:
        if msg.timestamp:
            parsed = dateparser.parse(
                msg.timestamp, settings={'PREFER_DATES_FROM': 'past'}
            )
            if parsed:
                logger.debug(f"Date from Claude timestamp: '{msg.timestamp}' -> {parsed}")
                return parsed

    # Fallback: run our date parser on the concatenated text
    all_text = "\n".join(msg.text for msg in result.messages)
    fallback = extract_best_date(all_text)
    if fallback:
        logger.debug(f"Date from fallback parser: {fallback}")
    return fallback


def _prompt_speaker_names(
    result: ChatAnalysisResult,
    current_names: Dict[str, str],
) -> Dict[str, str]:
    """
    Ask the user to name the speakers found in this screenshot.
    Remembers names from previous screenshots — only prompts for new speakers
    or lets the user re-confirm existing names.

    Args:
        result: The ChatAnalysisResult with messages
        current_names: Speaker names from previous screenshots

    Returns:
        Updated speaker name mapping (e.g., {"right": "Jenna", "left": "Mike"})
    """
    # Find unique speakers in this screenshot
    speakers_in_screenshot = sorted({msg.speaker for msg in result.messages})

    if not speakers_in_screenshot:
        return current_names

    # Check if all speakers already have names
    unnamed = [s for s in speakers_in_screenshot if s not in current_names]

    if not unnamed and current_names:
        # All speakers already named — show current names and let user confirm
        print("\nSpeakers:")
        for speaker in speakers_in_screenshot:
            label = speaker.capitalize()
            print(f"  {label} = {current_names[speaker]}")

        response = input("[Enter] to keep, or 'r' to rename: ").strip()
        if response.lower() != 'r':
            return current_names
        # Fall through to renaming
        unnamed = speakers_in_screenshot

    # Prompt for names
    print("\nName the speakers (Right is usually the phone owner):")
    updated = dict(current_names)

    for speaker in speakers_in_screenshot:
        label = speaker.capitalize()
        default = current_names.get(speaker, f"Speaker {label}")
        name = input(f"  {label} speaker name [Enter for '{default}']: ").strip()
        updated[speaker] = name if name else default

    return updated


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
