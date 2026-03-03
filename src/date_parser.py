"""
Date Parser Module

Extracts dates and times from OCR-extracted text using the dateparser library.
Handles absolute dates ("Mar 15, 2024"), relative dates ("Yesterday"),
and time-only values ("10:42 AM").
"""

import logging
from datetime import datetime
from typing import List, Optional

from dateparser.search import search_dates

from src.models import DateMatch

logger = logging.getLogger(__name__)

# Prefer past dates since we're processing message history, not future events.
# "Monday" should resolve to last Monday, not next Monday.
DATEPARSER_SETTINGS = {
    'PREFER_DATES_FROM': 'past',
}

# dateparser aggressively matches common words as dates (e.g., "no" -> November).
# We filter matches: they must contain a digit OR be a known relative date word.
RELATIVE_DATE_WORDS = {
    'yesterday', 'today', 'tomorrow',
    'monday', 'tuesday', 'wednesday', 'thursday',
    'friday', 'saturday', 'sunday',
}


def extract_dates(text: str) -> List[DateMatch]:
    """
    Find all dates and times in a block of text.

    Uses dateparser's search_dates to scan OCR text for date/time patterns,
    including natural language like "Yesterday" and "Monday".

    Args:
        text: Raw OCR-extracted text to search for dates

    Returns:
        List of DateMatch objects, each containing the original text
        and parsed datetime
    """
    if not text or not text.strip():
        return []

    results = search_dates(text, settings=DATEPARSER_SETTINGS)

    if not results:
        return []

    matches = []
    for original_text, parsed_date in results:
        if not _is_valid_date_match(original_text):
            logger.debug(f"Filtered false positive: '{original_text}'")
            continue
        matches.append(DateMatch(
            original_text=original_text,
            parsed_date=parsed_date
        ))
        logger.debug(f"Found date: '{original_text}' -> {parsed_date}")

    return matches


def _is_valid_date_match(original_text: str) -> bool:
    """
    Filter out false positives from dateparser.

    dateparser can match common English words as dates (e.g., "no" -> November,
    "are" -> some date). A valid match must contain at least one digit
    (like "10:42 AM" or "3/15/2024") or be a recognized relative date word
    (like "Yesterday" or "Monday").
    """
    text = original_text.strip().lower()
    if any(c.isdigit() for c in text):
        return True
    # Check if any word in the matched text is a relative date word.
    # search_dates can return "Yesterday at noon" as a single match.
    words = text.split()
    if any(word in RELATIVE_DATE_WORDS for word in words):
        return True
    return False


def extract_best_date(text: str) -> Optional[datetime]:
    """
    Extract the single most likely date/time from text.

    Convenience wrapper around extract_dates that returns just the first match.
    Returns None if no date is found.

    Args:
        text: Raw OCR-extracted text to search for dates

    Returns:
        The parsed datetime of the best match, or None
    """
    matches = extract_dates(text)
    if not matches:
        logger.debug("No dates found in text")
        return None
    return matches[0].parsed_date
