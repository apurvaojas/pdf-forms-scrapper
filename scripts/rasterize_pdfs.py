#!/usr/bin/env python3
"""Rasterize PDFs to PNGs at a target DPI.

Outputs images into: data/images/<pdf_stem>/page_000.png

Usage:
    python scripts/rasterize_pdfs.py --input-dir downloads --output-dir data/images --dpi 300
"""
import argparse
import subprocess
from pathlib import Path


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def rasterize_with_pdftoppm(pdf_path: Path, out_dir: Path, dpi: int):
    ensure_dir(out_dir)
    prefix = out_dir / "page"
    cmd = ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(prefix)]
    subprocess.run(cmd, check=True)
    # pdftoppm will create files like page-1.png, page-2.png
    # rename to page_000.png style
    files = sorted(out_dir.glob("page-*.png"))
    for i, f in enumerate(files):
        new = out_dir / f"page_{i:03d}.png"
        f.rename(new)


def rasterize(pdf_path: Path, out_root: Path, dpi: int):
    out_dir = out_root / pdf_path.stem
    # skip if already rasterized
    if out_dir.exists() and any(out_dir.glob('*.png')):
        print(f"Skipping {pdf_path.name}: images already exist in {out_dir}")
        return

    try:
        rasterize_with_pdftoppm(pdf_path, out_dir, dpi)
    except FileNotFoundError:
        raise RuntimeError("pdftoppm not found. Please install poppler-utils or use pdf2image fallback")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="downloads")
    parser.add_argument("--output-dir", default="data/images")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N PDFs (pilot mode)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    out_root = Path(args.output_dir)
    ensure_dir(out_root)

    pdf_files = sorted([p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"])
    if args.limit:
        pdf_files = pdf_files[: args.limit]

    for p in pdf_files:
        print("Rasterizing", p)
        # ensure logs dir exists
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        try:
            rasterize(p, out_root, args.dpi)
            with open(log_dir / "rasterize.log", "a") as lf:
                lf.write(f"OK,{p.name}\n")
        except Exception as e:
            print("Failed to rasterize", p, e)
            with open(log_dir / "rasterize.log", "a") as lf:
                lf.write(f"ERROR,{p.name},{e}\n")


if __name__ == "__main__":
    main()
