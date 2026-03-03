"""
Timeline Builder Module

Sorts reviewed messages into chronological order.
"""

import logging
from typing import List

from src.models import Message, Timeline

logger = logging.getLogger(__name__)


def build_timeline(messages: List[Message]) -> Timeline:
    """
    Build a chronological timeline from reviewed messages.

    Dated messages are sorted earliest-first. Undated messages (date=None)
    are placed at the end of the timeline.

    Args:
        messages: List of Message objects (some may have date=None)

    Returns:
        Timeline with dated messages sorted chronologically, undated at end
    """
    dated = [m for m in messages if m.date is not None]
    undated = [m for m in messages if m.date is None]

    sorted_dated = sorted(dated, key=lambda m: m.date)
    sorted_messages = sorted_dated + undated

    logger.info(f"Built timeline with {len(sorted_messages)} message(s) "
                f"({len(dated)} dated, {len(undated)} undated)")
    if sorted_dated:
        first = sorted_dated[0].date.strftime('%Y-%m-%d')
        last = sorted_dated[-1].date.strftime('%Y-%m-%d')
        logger.info(f"Date range: {first} to {last}")

    return Timeline(messages=sorted_messages)
