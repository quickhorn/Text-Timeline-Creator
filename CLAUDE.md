# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Text Message Timeline Generator — a Python pipeline that scans directories for message screenshots and PDFs, extracts text via Azure Document Intelligence OCR, and (planned) assembles them into a chronological timeline. The project is in early development; file scanning and text extraction work, but timeline assembly and export are not yet implemented.

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate   # Linux/WSL
pip install -r requirements.txt

# Run the application (must run from project root)
python -m src.main
```

Individual modules have `if __name__ == "__main__":` test harnesses:
```bash
python src/file_scanner.py    # tests scanning against data/test_messages/
python src/text_extractor.py  # tests OCR against data/test_image_messages/
```

No test framework is configured yet.

## Architecture

The pipeline flows: **scan files → extract text → (TODO) build timeline → (TODO) export**

- `src/main.py` — Entry point. Loads Azure credentials from `.env`, calls file scanner, will orchestrate the full pipeline.
- `src/file_scanner.py` — `scan_message_directory()` walks a directory tree and returns a list of dicts (`filepath`, `filename`, `extension`) for supported formats. Supported: `.jpg`, `.jpeg`, `.png`, `.heic`, `.pdf`.
- `src/text_extractor.py` — `TextExtractor` class wraps the Azure Document Intelligence `DocumentAnalysisClient` using the `prebuilt-read` model. Processes files sequentially with a 0.7s delay between API calls for rate limiting.

## Key Details

- **Python 3.12**, uses `venv` (both `./venv` and `./src/venv` exist)
- **Azure Document Intelligence** credentials required in `.env` (`AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`, `AZURE_DOCUMENT_INTELLIGENCE_KEY`)
- Message input directory is currently hardcoded to `src/data/messages/` (relative to `main.py`'s `__file__`); there's a TODO to make it configurable
- `data/` contains test fixtures (`test_messages/`, `test_image_messages/`)
- `output/` is for generated `.docx` files (gitignored); `python-docx` is in requirements but not yet used
