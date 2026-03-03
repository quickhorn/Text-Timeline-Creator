# Production Roadmap: Text Timeline Creator for Law Firms

## Context

The Text Timeline Creator is a Python pipeline that processes message screenshots/PDFs into chronological timelines for family law firms. Phases 1 (Refactor & Stabilize) and 2 (Core Pipeline MVP) are complete — the pipeline scans files, extracts text via Azure OCR, reviews dates with the user, builds a timeline, and exports to DOCX. 66 tests pass.

**The problem:** Azure OCR returns flat text with no speaker identification or message boundaries. A screenshot with 6 messages from 2 people comes back as one blob. We lose who said what.

**The solution:** Replace Azure OCR with Claude Vision API, which understands chat UI layout and returns structured `Speaker: message` pairs directly.

## Architecture Target

```
SharePoint Online / Local Dir
         |
   [File Scanner]
         |
   [Chat Analyzer]  <--  Claude Vision API (screenshots -> structured messages)
         |                Azure Speech Services (audio -> transcription, future)
   [Date Confirmation + User Review]
         |
   [Timeline Builder]
         |
   [DOCX Export]
```

---

## Phase 1: Refactor & Stabilize -- COMPLETE

Fixed bugs, added package structure (pyproject.toml, src/__init__.py), created data models
(FileInfo, ExtractionResult, DateMatch), replaced print() with logging, added pytest with
test_file_scanner.py and test_models.py.

## Phase 2: Complete the Core Pipeline (MVP) -- COMPLETE

Created date_parser.py (with specificity-based scoring), review.py (interactive CLI),
timeline_builder.py (chronological sorting), docx_exporter.py (Word export with embedded images).
Added retry with exponential backoff to text_extractor.py. Fixed SSL error handling (OSError catch).
66 tests passing.

---

## Phase 3: Claude Vision Chat Analyzer

**Why next:** This is the biggest value upgrade. Going from "blob of text" to "structured conversation with speakers" transforms the product from a novelty into something a paralegal can actually use. A timeline that shows who said what is fundamentally more useful than one that just dumps OCR text.

### The Shift

Currently: `1 screenshot -> 1 flat text blob -> 1 Message`
After:     `1 screenshot -> N structured chat messages with speakers -> N Messages`

This ripples through every module downstream of extraction.

### 3a. New module: `src/chat_analyzer.py`

Create a `ChatAnalyzer` class that sends images to the Claude Vision API and gets back structured conversation data.

**How it works:**
1. Read the image file, base64-encode it
2. Send to Claude (Sonnet 4.5) with a carefully crafted prompt asking for JSON output
3. Parse the JSON response into Pydantic-validated dataclasses
4. Return a list of `ChatMessage` objects

**Key design decisions:**
- Use the `anthropic` Python SDK directly (no `instructor` wrapper -- we learn more by handling JSON ourselves)
- Use Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) for the best cost/quality balance (~$0.005/image)
- The prompt should ask Claude to:
  - Identify left-speaker vs right-speaker messages
  - Extract the exact text of each message
  - Extract any visible timestamps
  - Ignore UI chrome (status bar, signal strength, battery, navigation buttons)
  - Identify system messages separately ("Today", "Read 3:42 PM", etc.)
- Return structured JSON that we validate with Pydantic

**New file structure:**
```python
# src/chat_analyzer.py

class ChatAnalyzer:
    def __init__(self, api_key: str):
        """Initialize with Anthropic API key."""

    def analyze_screenshot(self, file_path: Path) -> ChatAnalysisResult:
        """Send a single screenshot to Claude Vision, get structured messages back."""

    def analyze_files(self, file_list: List[FileInfo]) -> Dict[str, ChatAnalysisResult]:
        """Process multiple files, with delay between API calls."""
```

### 3b. Update data models in `src/models.py`

**New dataclasses:**
- `ChatMessage` -- a single message extracted from a screenshot
  - `speaker: str` -- "left" or "right" (which side of the screen)
  - `text: str` -- the message content
  - `timestamp: Optional[str]` -- visible timestamp if any (raw string from Claude)
- `ChatAnalysisResult` -- result of analyzing one screenshot
  - `success: bool`
  - `messages: List[ChatMessage]` -- the structured messages found
  - `raw_response: str` -- Claude's raw JSON (for debugging)
  - `error: str` -- error message if failed

**Updated dataclass:**
- `Message` -- add `speaker: Optional[str] = None` field
  - This preserves backward compatibility: old-style flat text Messages have speaker=None
  - New Claude-extracted Messages have speaker="left" or "right" (user can rename during review)

### 3c. Update `src/review.py` for structured messages

The review step changes significantly:

**Before (flat text):**
```
--- Message 1/2 ---
File: IMG_6019.PNG
Text: "12:34 254 Do you remember if they owe us..."
Auto-detected date: 2025-02-23 06:20 PM
[Enter] to confirm, type a date to override, or 's' to skip:
```

**After (structured messages):**
```
--- Screenshot 1/2: IMG_6019.PNG ---
Found 4 messages:

  [Right] Do you remember if they owe us this time?
  [Left]  I don't think so
  [Left]  Lemme know when you're headed back
  [Right] Will do

Date detected: Mon, Feb 23 at 6:20 PM
[Enter] to confirm date, type to override, 's' to skip:

Speaker names — Right is the phone owner. Left is the other person.
  Right speaker name [Enter for "Speaker 1"]:
  Left speaker name [Enter for "Speaker 2"]:
```

**Key changes:**
- Show all messages from a screenshot grouped together with speaker labels
- Ask user to name the speakers once per screenshot (or once globally)
- Date review stays similar but uses Claude's extracted timestamp if available
- Each `ChatMessage` becomes a separate `Message` in the output list

### 3d. Update `src/main.py` pipeline

- Load `ANTHROPIC_API_KEY` from `.env` (instead of or alongside Azure credentials)
- Replace `TextExtractor` calls with `ChatAnalyzer` calls
- Pass `ChatAnalysisResult` objects to the updated `review_extractions()`
- Keep Azure credentials optional (for future PDF/fallback use)

### 3e. Update `src/docx_exporter.py` for speaker labels

**Before:**
```
February 23, 2025  06:20 PM
Source: IMG_6019.PNG
[embedded image]

12:34 254 Do you remember if they owe us othestime...
```

**After:**
```
February 23, 2025  06:20 PM
Source: IMG_6019.PNG
[embedded image]

Jenna:  Do you remember if they owe us this time?
Mike:   I don't think so
Mike:   Lemme know when you're headed back
Jenna:  Will do
```

**Changes:**
- Format each message with speaker label prefix
- Handle the case where a Message has speaker=None (legacy/fallback)
- Bold the speaker names for readability

### 3f. Update `src/date_parser.py` role

The date parser becomes a **fallback/validator** rather than the primary date source:
- Claude extracts timestamps directly from the screenshot (it can read "Mon, Feb 23 at 6:20 PM" in context)
- `date_parser.py` is used to parse Claude's timestamp strings into datetime objects
- If Claude doesn't find a timestamp, fall back to running `extract_best_date()` on the concatenated message text
- Keep all existing tests -- they still validate the fallback path

### 3g. Update dependencies

**`pyproject.toml`:**
- Add `anthropic` SDK to dependencies
- Azure dependencies become optional (move to `[project.optional-dependencies]`)

**`.env.example`:**
- Add `ANTHROPIC_API_KEY=your-key-here`
- Keep Azure keys documented but mark as optional

### 3h. Testing

- `tests/test_chat_analyzer.py` -- mock the Anthropic API, test JSON parsing, error handling
- Update `tests/test_review.py` -- test the new structured message review flow
- Update `tests/test_docx_exporter.py` -- test speaker labels in output
- Keep all `test_date_parser.py` tests (fallback path)

### 3i. Handle `text_extractor.py`

- Keep the file but don't import it in `main.py` by default
- It serves as a fallback for non-screenshot files (plain PDFs, scanned documents)
- Future: could be invoked when ChatAnalyzer detects "this isn't a chat screenshot"

**Deliverable:** Pipeline produces DOCX timelines with speaker-attributed messages. `Jenna: Do you remember...` instead of a flat text dump.

**Verification:**
- `pytest tests/` passes (all existing + new tests)
- `timeline data/messages` processes screenshots via Claude Vision
- Output DOCX shows speaker-labeled messages in chronological order
- Existing date scoring and review flows still work as fallback

---

## Phase 4: Audio Transcription

**Why next:** Extends the pipeline to handle voice messages (audio files).

### 4a. Azure Speech Services integration
- Create `src/audio_transcriber.py`
- Add `azure-cognitiveservices-speech` to pyproject.toml
- Implement transcription for `.mp3`, `.m4a`, `.wav` files

### 4b. Update file scanner
- Add audio formats to `SUPPORTED_FORMATS`
- Categorize files by type (image vs audio) for routing

### 4c. Update main pipeline
- Route audio files to `audio_transcriber` instead of `chat_analyzer`
- Merge results into the same review -> timeline -> export flow

**Deliverable:** Full pipeline handles images, PDFs, and audio files.

---

## Phase 5: SharePoint Online Integration

**Why next:** Deployment mechanism for law firms. Pipeline needs to work first.

### 5a. File source abstraction
- Create `src/file_sources/` package (base, local, sharepoint)
- Refactor to accept `BinaryIO` streams instead of file paths

### 5b. SharePoint connector
- `msal` + `office365-rest-python-client` for Service Principal auth
- Stream files in-memory (no temp files -- sensitive legal documents)

### 5c. Source selection via CLI
- `timeline ./local/path` (existing)
- `timeline --sharepoint "/sites/ClientDocs/..."` (new)

**Deliverable:** Pipeline reads from local directories or SharePoint Online.

---

## Phase 6: Production Hardening

### 6a. Configuration
- Centralized config (env vars, config file)
- Model selection, rate limits, output preferences

### 6b. CI/CD
- GitHub Actions: lint, test, type-check on push
- `ruff` for linting, `mypy` for type checking

---

## Critical Files to Modify/Create

| File | Action | Phase |
|------|--------|-------|
| `src/chat_analyzer.py` | **Create** -- Claude Vision integration | 3 |
| `src/models.py` | Add ChatMessage, ChatAnalysisResult, speaker field on Message | 3 |
| `src/review.py` | Rewrite for structured message review | 3 |
| `src/docx_exporter.py` | Add speaker labels to output | 3 |
| `src/main.py` | Swap TextExtractor for ChatAnalyzer | 3 |
| `src/date_parser.py` | Keep as fallback, no major changes | 3 |
| `pyproject.toml` | Add `anthropic`, make Azure optional | 3 |
| `.env.example` | Add `ANTHROPIC_API_KEY` | 3 |
| `tests/test_chat_analyzer.py` | **Create** -- mock API tests | 3 |
| `tests/test_review.py` | Update for structured messages | 3 |
| `tests/test_docx_exporter.py` | Update for speaker labels | 3 |
| `src/audio_transcriber.py` | **Create** -- Azure Speech Services | 4 |
| `src/file_sources/base.py` | **Create** -- FileSource abstraction | 5 |
| `src/file_sources/local.py` | **Create** -- local directory adapter | 5 |
| `src/file_sources/sharepoint.py` | **Create** -- SharePoint Online adapter | 5 |

## Verification

- **Phase 3:** `pytest tests/` passes. `timeline data/messages` produces a DOCX with speaker-labeled messages via Claude Vision. Review step shows structured messages with speaker names.
- **Phase 4:** Pipeline processes audio files and includes transcriptions in timeline.
- **Phase 5:** Pipeline reads from SharePoint and produces identical output to local files.
- **Phase 6:** CI/CD runs on push, config is externalized.
