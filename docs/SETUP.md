# Setup (local/dev)

This project uses a mixture of system-level tools (poppler, qpdf) and Python packages. Follow these steps to prepare a dev environment.

## System packages (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y poppler-utils qpdf build-essential
```

## Python packages

Create a venv and install Python deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Notes
- `pdftoppm` is provided by `poppler-utils` and is used by `scripts/rasterize_pdfs.py`.
- `qpdf` is used by `scripts/validate_pdfs.py` for robust PDF checks.
- `paddleocr` requires additional model downloads on first run and may need GPU support for performance.
