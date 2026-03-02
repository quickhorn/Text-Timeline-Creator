# Production Roadmap: Text Timeline Creator for Law Firms

## Context

The Text Timeline Creator is a Python pipeline that processes message screenshots/PDFs via Azure OCR to build chronological timelines. The user wants to productize this for family law firms, where clients upload documents to SharePoint Online. The current codebase (~380 lines across 3 files) has the first two pipeline stages working (scan + extract) but has bugs, no package structure, no tests, and two pipeline stages still unbuilt. Now — while the codebase is small — is the ideal time to refactor before building more on a shaky foundation.

## Architecture Target

```
SharePoint Online / Local Dir
         |
   [File Source Abstraction]
         |
   [Text Extraction]  ←─  Azure Doc Intelligence (images/PDFs)
         |                 Azure Speech Services (audio files)
   [Date Extraction + User Review]
         |
   [Timeline Builder]
         |
   [DOCX Export]
```

---

## Phase 1: Refactor & Stabilize (Foundation)

**Why first:** The codebase has bugs that will compound as we add features. Fixing ~380 lines now is cheap. Fixing 2,000 lines later is painful.

### 1a. Fix existing bugs
- `src/file_scanner.py:50` — orphaned `print` (bare `print` without parens, does nothing)
- `src/file_scanner.py:19,56` — `any` → `Any` (lowercase `any` is the builtin function, not a type hint)
- `src/file_scanner.py:33,38` — `filesFound`/`pathFile` → `files_found`/`path_file` (Python convention is snake_case)
- `src/text_extractor.py:135` — missing space `values()if` → `values() if`
- `src/text_extractor.py:149` — `from file_scanner` → `from src.file_scanner` (broken when run as module)
- `src/text_extractor.py:181` — `filename = filename` (no-op, remove)
- `src/file_scanner.py:75` — stray `print(f"FileInfo: ")` cluttering display output

### 1b. Package structure
- Add `src/__init__.py`
- Add `pyproject.toml` for proper Python packaging
- Remove `pathlib` from requirements.txt (it's a stdlib module)
- Delete duplicate `src/venv/` directory (keep only root `/venv/`)

### 1c. Data models
- Create `src/models.py` with dataclasses:
  - `FileInfo` — replaces the untyped dicts (`filepath`, `filename`, `extension`)
  - `ExtractionResult` — replaces the result dicts (`success`, `text`, `page_count`, `error`)
- Update `file_scanner.py` and `text_extractor.py` to use these models

### 1d. Logging
- Replace all `print()` calls with Python `logging` module
- Keep console output via a StreamHandler, but now with levels (INFO, ERROR, DEBUG)
- This prepares us for file logging and structured output later

### 1e. Testing
- Add `pytest` to requirements.txt
- Create `tests/` directory with:
  - `test_file_scanner.py` — test scanning, filtering, recursive walks
  - `test_models.py` — test dataclass creation/validation
- Use existing `data/test_messages/` fixtures

### 1f. Security
- Rotate the Azure Document Intelligence key (it was committed to git history)
- Add `.env.example` with placeholder values (document what's needed without exposing secrets)

**Deliverable:** Same functionality, zero bugs, proper structure, tests passing.

---

## Phase 2: Complete the Core Pipeline (MVP)

**Why second:** This is the product. Without timeline + export, there's nothing to sell.

### 2a. Date extraction from OCR text
- Create `src/date_parser.py`
- Use regex patterns to find common date/time formats in extracted text (screenshot timestamps like "10:42 AM", "Mar 15, 2024", etc.)
- Return parsed dates or `None` if no date found

### 2b. User review step
- Create `src/review.py` — CLI-based review interface
- For each extracted message: show the text, show the auto-detected date (if any)
- If no date detected: prompt user to enter one
- If date detected: let user confirm or override
- Store confirmed date with each message

### 2c. Timeline builder
- Create `src/timeline_builder.py`
- Add `Message` dataclass to `models.py` (text, date, source_file, sender info if available)
- Add `Timeline` dataclass to `models.py` (sorted list of Messages)
- Sort messages chronologically by confirmed date

### 2d. DOCX export
- Create `src/docx_exporter.py`
- Use `python-docx` (already in requirements) to generate formatted document
- Include: date/time, message text, source filename for reference
- Output to `output/` directory

**Deliverable:** End-to-end pipeline: scan → extract → review dates → build timeline → export DOCX.

---

## Phase 3: Audio Transcription

**Why third:** Extends the pipeline to handle voice messages (audio files), which the user identified as a need.

### 3a. Azure Speech Services integration
- Create `src/audio_transcriber.py`
- Add `azure-cognitiveservices-speech` to requirements.txt
- Add Speech Services credentials to `.env`
- Implement transcription for `.mp3`, `.m4a`, `.wav` files

### 3b. Update file scanner
- Add audio formats to `SUPPORTED_FORMATS` in `file_scanner.py`
- Categorize files by type (image/document vs audio) so the right extractor is called

### 3c. Update main pipeline
- Route audio files to `audio_transcriber` instead of `text_extractor`
- Merge results into the same review → timeline → export flow

**Deliverable:** Full pipeline handles images, PDFs, and audio files.

---

## Phase 4: SharePoint Online Integration

**Why fourth:** This is the deployment mechanism, not the core product. The pipeline needs to work first, then we connect it to where the law firm's files live.

### 4a. File source abstraction
- Create `src/file_sources/` package:
  - `base.py` — abstract `FileSource` class (interface: `list_files()`, `read_file() → BytesIO`)
  - `local.py` — wraps current `file_scanner.py` logic, reads files from disk
  - `sharepoint.py` — reads files from SharePoint Online
- Refactor `text_extractor.py` to accept `BinaryIO` streams instead of file paths (enables in-memory processing from any source)

### 4b. SharePoint connector
- Add `msal` and `office365-rest-python-client` to requirements.txt
- Implement Service Principal authentication (client credentials flow, no user interaction)
- Read files into `BytesIO` in-memory (no temp files — important for sensitive legal documents)
- Add SharePoint credentials to `.env` (tenant_id, client_id, client_secret, site_url)

### 4c. Source selection via CLI
- Extend `argparse` in `main.py`:
  - `python -m src.main ./local/path` — local directory (existing behavior)
  - `python -m src.main --sharepoint "/sites/ClientDocs/Shared Documents/CaseName"` — SharePoint path
- Start with polling (check SharePoint on-demand when run); event-driven later if volume warrants it

**Deliverable:** Pipeline reads from local directories or SharePoint Online, streaming files in-memory.

---

## Phase 5: Production Hardening

### 5a. Retry logic
- Add `tenacity` library for retry with exponential backoff on Azure API calls
- Handle transient failures (network timeouts, rate limits)

### 5b. Configuration
- Move all settings to a config file or environment variables
- Azure model names, rate-limit delays, output format preferences

### 5c. CI/CD
- GitHub Actions workflow: lint, test, type-check on push
- Add `ruff` for linting, `mypy` for type checking

---

## Critical Files to Modify/Create

| File | Action | Phase |
|------|--------|-------|
| `src/file_scanner.py` | Fix bugs, snake_case, use models | 1 |
| `src/text_extractor.py` | Fix bugs, use models, accept BinaryIO | 1, 4 |
| `src/main.py` | Update for new models, extend argparse | 1, 4 |
| `src/models.py` | **Create** — FileInfo, ExtractionResult, Message, Timeline | 1, 2 |
| `src/__init__.py` | **Create** — empty, enables package imports | 1 |
| `pyproject.toml` | **Create** — modern Python packaging | 1 |
| `tests/test_file_scanner.py` | **Create** — pytest tests | 1 |
| `.env.example` | **Create** — document required env vars | 1 |
| `src/date_parser.py` | **Create** — extract dates from OCR text | 2 |
| `src/review.py` | **Create** — CLI review interface | 2 |
| `src/timeline_builder.py` | **Create** — sort messages, build timeline | 2 |
| `src/docx_exporter.py` | **Create** — generate DOCX output | 2 |
| `src/audio_transcriber.py` | **Create** — Azure Speech Services | 3 |
| `src/file_sources/base.py` | **Create** — FileSource abstraction | 4 |
| `src/file_sources/local.py` | **Create** — local directory adapter | 4 |
| `src/file_sources/sharepoint.py` | **Create** — SharePoint Online adapter | 4 |
| `requirements.txt` | Update each phase | 1-5 |

## Verification

After each phase, verify by:
- **Phase 1:** `pytest tests/` passes. `python -m src.main` runs against `data/test_image_messages/` with no errors. No bugs in code.
- **Phase 2:** Full pipeline produces a `.docx` file in `output/` from test images with correctly ordered messages.
- **Phase 3:** Pipeline processes a test audio file and includes transcription in timeline output.
- **Phase 4:** Pipeline reads files from a SharePoint test site and produces the same output as local files.
- **Phase 5:** CI/CD pipeline runs on push, retry logic handles simulated failures.
