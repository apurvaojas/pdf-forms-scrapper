# PDF Forms Scrapper (MVP)

This small project searches the web for PDF application forms, downloads them in parallel, deduplicates by SHA256, and stores metadata in a local SQLite database (`pdf_metadata.db`).

Quickstart
1. create a virtualenv and install requirements

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the CLI

```bash
python -m src.cli "site:.gov application form"
```

Files
- `src/searcher.py` - uses `duckduckgo-search` to find PDF links
- `src/downloader.py` - async downloads, SHA256 dedup, saves to `downloads/`
- `src/metadata.py` - sqlite metadata storage and helpers
- `src/cli.py` - ties the pieces together

Notes
- This is an MVP. For production: add robust retry/backoff, rate-limiting, per-domain concurrency limits, object storage support, and tests against a reproducible fixture.
