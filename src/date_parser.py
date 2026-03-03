"""
Date Parser Module

Extracts dates and times from OCR-extracted text using the dateparser library.
Handles absolute dates ("Mar 15, 2024"), relative dates ("Yesterday"),
and time-only values ("10:42 AM").

When multiple dates are found, extract_best_date ranks them by specificity:
a full "Mon, Feb 23 at 6:20 PM" beats a bare "12:34" from a phone status bar.
"""

import logging
import re
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


MONTH_NAMES = {
    'jan', 'feb', 'mar', 'apr', 'may', 'jun',
    'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
    'january', 'february', 'march', 'april',
    'june', 'july', 'august', 'september',
    'october', 'november', 'december',
}

DAY_OF_WEEK_NAMES = {
    'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
    'monday', 'tuesday', 'wednesday', 'thursday',
    'friday', 'saturday', 'sunday',
}

# Matches a 4-digit year (1900-2099)
_YEAR_PATTERN = re.compile(r'\b(19|20)\d{2}\b')

# Matches a bare time like "12:34" or "6:20 PM" — used to detect time-only matches
_TIME_ONLY_PATTERN = re.compile(
    r'^\d{1,2}:\d{2}(\s*[AaPp][Mm])?$'
)


def _score_date_match(match: DateMatch) -> int:
    """
    Score a date match by how specific the original text is.

    Higher scores mean more date information was present in the original text.
    A bare time like "12:34" scores 1; a full "Mon, Feb 23 at 6:20 PM" scores 6+.
    """
    text = match.original_text.strip().lower()
    score = 1  # base score for any valid match

    # Year present (e.g., "2024") — strongest signal
    if _YEAR_PATTERN.search(text):
        score += 4

    # Month name present (e.g., "Feb", "March")
    words = re.findall(r'[a-z]+', text)
    if any(w in MONTH_NAMES for w in words):
        score += 3

    # Day-of-week present (e.g., "Mon", "Tuesday")
    if any(w in DAY_OF_WEEK_NAMES for w in words):
        score += 2

    # Relative date words (e.g., "Yesterday", "Today")
    if any(w in RELATIVE_DATE_WORDS for w in words):
        score += 2

    return score


def extract_best_date(text: str) -> Optional[datetime]:
    """
    Extract the single most likely date/time from text.

    Ranks all matches by specificity — a full date beats a bare time.
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

    best = max(matches, key=_score_date_match)
    logger.debug(
        f"Best date: '{best.original_text}' (score={_score_date_match(best)}) "
        f"-> {best.parsed_date}"
    )
    return best.parsed_date
