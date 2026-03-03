"""
Chat Analyzer Module

Sends messaging screenshots to Claude Vision API and gets back structured
conversation data with speaker identification and message text.

Replaces the Azure OCR path (text_extractor.py) for chat screenshots.
"""

import base64
import json
import logging
import time
from pathlib import Path
from typing import Dict, List

import anthropic

from src.models import ChatAnalysisResult, ChatMessage, FileInfo

logger = logging.getLogger(__name__)

# Retry settings (same pattern as text_extractor.py)
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 2
BACKOFF_MULTIPLIER = 2

# Delay between API calls to avoid rate limits
BETWEEN_FILE_DELAY = 1.5

# Claude model for vision analysis
MODEL = "claude-sonnet-4-5-20250929"

# Map file extensions to MIME types accepted by the Claude Vision API
MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# System prompt that tells Claude how to analyze chat screenshots
SYSTEM_PROMPT = """You are a chat screenshot analyzer. You extract structured conversation data from messaging app screenshots.

Rules:
- Extract every message bubble as a separate entry
- Label each message as "left" or "right" based on which side of the screen the bubble appears
- In most messaging apps, RIGHT bubbles are sent by the phone owner, LEFT bubbles are received
- Extract the exact text content of each message — do not paraphrase or correct spelling
- If a timestamp is visible near a message or group of messages, include it as-is
- Ignore UI chrome: status bar, signal strength, battery, navigation buttons, keyboard
- Ignore read receipts ("Read 3:42 PM") and delivery indicators
- Order messages from top to bottom as they appear on screen (chronological within the screenshot)

Return ONLY valid JSON in this exact format, with no other text:
{
    "messages": [
        {"speaker": "left", "text": "message text here", "timestamp": "visible timestamp or null"},
        {"speaker": "right", "text": "message text here", "timestamp": null}
    ]
}"""


class ChatAnalyzer:
    """
    Analyzes chat screenshots using Claude Vision API.

    Sends images to Claude and gets back structured conversation data
    with speaker positions (left/right) and message text.
    """

    def __init__(self, api_key: str):
        """
        Initialize with an Anthropic API key.

        Args:
            api_key: Anthropic API key for Claude Vision access
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        logger.info("Initialized ChatAnalyzer with Claude Vision")

    def analyze_screenshot(self, file_path: Path) -> ChatAnalysisResult:
        """
        Send a single screenshot to Claude Vision and get structured messages back.

        Retries up to MAX_RETRIES times with exponential backoff on transient
        failures (connection errors, rate limits). Does NOT retry on file-not-found
        or unsupported file types.

        Args:
            file_path: Path to the screenshot image file

        Returns:
            ChatAnalysisResult with structured messages or error info
        """
        logger.info(f"Analyzing: {file_path}")

        # Validate file exists
        if not file_path.exists():
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            return ChatAnalysisResult(success=False, error=error_msg)

        # Validate file type
        ext = file_path.suffix.lower()
        mime_type = MIME_TYPES.get(ext)
        if not mime_type:
            error_msg = (
                f"Unsupported image format '{ext}' for {file_path.name}. "
                f"Supported: {', '.join(sorted(MIME_TYPES.keys()))}"
            )
            logger.error(error_msg)
            return ChatAnalysisResult(success=False, error=error_msg)

        # Read and base64-encode the image
        image_data = base64.standard_b64encode(file_path.read_bytes()).decode("utf-8")

        # Send to Claude with retry logic
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.client.messages.create(
                    model=MODEL,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": mime_type,
                                        "data": image_data,
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": "Extract all messages from this chat screenshot.",
                                },
                            ],
                        }
                    ],
                )

                raw_text = response.content[0].text
                return self._parse_response(raw_text, file_path.name)

            except anthropic.APIConnectionError as e:
                # Network-level failure — retry
                delay = INITIAL_RETRY_DELAY * (BACKOFF_MULTIPLIER ** attempt)
                if attempt < MAX_RETRIES:
                    logger.warning(
                        f"Attempt {attempt + 1}/{MAX_RETRIES + 1} failed for "
                        f"{file_path.name}: {e}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    error_msg = f"Failed after {MAX_RETRIES + 1} attempts: {e}"
                    logger.error(error_msg)
                    return ChatAnalysisResult(success=False, error=error_msg)

            except anthropic.RateLimitError as e:
                # Rate limited — retry with backoff
                delay = INITIAL_RETRY_DELAY * (BACKOFF_MULTIPLIER ** attempt)
                if attempt < MAX_RETRIES:
                    logger.warning(
                        f"Rate limited on {file_path.name}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    error_msg = f"Rate limited after {MAX_RETRIES + 1} attempts: {e}"
                    logger.error(error_msg)
                    return ChatAnalysisResult(success=False, error=error_msg)

            except anthropic.APIStatusError as e:
                # Server error (5xx) — retry; client error (4xx) — don't
                if e.status_code >= 500:
                    delay = INITIAL_RETRY_DELAY * (BACKOFF_MULTIPLIER ** attempt)
                    if attempt < MAX_RETRIES:
                        logger.warning(
                            f"Server error ({e.status_code}) on {file_path.name}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        error_msg = f"Server error after {MAX_RETRIES + 1} attempts: {e}"
                        logger.error(error_msg)
                        return ChatAnalysisResult(success=False, error=error_msg)
                else:
                    # 4xx — bad request, auth failure, etc. Don't retry.
                    error_msg = f"API error ({e.status_code}): {e.message}"
                    logger.error(error_msg)
                    return ChatAnalysisResult(success=False, error=error_msg)

            except Exception as e:
                # Unknown error — don't retry
                error_msg = f"Unexpected error analyzing {file_path.name}: {e}"
                logger.error(error_msg)
                return ChatAnalysisResult(success=False, error=error_msg)

    def analyze_files(
        self, file_list: List[FileInfo]
    ) -> Dict[str, ChatAnalysisResult]:
        """
        Analyze multiple screenshot files.

        Args:
            file_list: List of FileInfo objects from file_scanner

        Returns:
            Dictionary mapping filename to ChatAnalysisResult
        """
        results = {}
        total = len(file_list)

        logger.info(f"Analyzing {total} screenshot(s) with Claude Vision:")
        logger.info("-" * 70)

        for index, file_info in enumerate(file_list, start=1):
            logger.info(f"[{index}/{total}] {file_info.filename}")

            result = self.analyze_screenshot(file_info.full_path)
            results[file_info.filename] = result

            if result.success:
                logger.info(f"  Found {len(result.messages)} message(s)")
            else:
                logger.error(f"  Failed: {result.error}")

            # Delay between files to avoid rate limits
            if index < total:
                time.sleep(BETWEEN_FILE_DELAY)

        successful = sum(1 for r in results.values() if r.success)
        failed = total - successful

        logger.info("-" * 70)
        logger.info(f"Analysis complete: {successful} successful, {failed} failed")

        return results

    def _parse_response(
        self, raw_text: str, filename: str
    ) -> ChatAnalysisResult:
        """
        Parse Claude's JSON response into ChatMessage objects.

        Args:
            raw_text: The raw text from Claude's response
            filename: Source filename (for logging)

        Returns:
            ChatAnalysisResult with parsed messages or error
        """
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON from Claude for {filename}: {e}"
            logger.error(error_msg)
            return ChatAnalysisResult(
                success=False, raw_response=raw_text, error=error_msg
            )

        if "messages" not in data:
            error_msg = f"Missing 'messages' key in Claude response for {filename}"
            logger.error(error_msg)
            return ChatAnalysisResult(
                success=False, raw_response=raw_text, error=error_msg
            )

        messages = []
        for item in data["messages"]:
            speaker = item.get("speaker", "unknown")
            text = item.get("text", "")
            timestamp = item.get("timestamp")

            if not text.strip():
                continue

            messages.append(
                ChatMessage(speaker=speaker, text=text, timestamp=timestamp)
            )

        logger.info(
            f"Parsed {len(messages)} message(s) from {filename}"
        )

        return ChatAnalysisResult(
            success=True, messages=messages, raw_response=raw_text
        )
