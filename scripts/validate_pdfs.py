#!/usr/bin/env python3
"""Validate PDFs in a directory and move corrupted ones to downloads/quarantine.

Produces: reports/validation_report.csv with columns: filename, status, message

Checks:
- Quick qpdf --check if qpdf available
- Try opening with PyPDF2

Usage:
    python scripts/validate_pdfs.py --input-dir downloads --quarantine-dir downloads/quarantine --report reports/validation_report.csv
"""
import argparse
import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path

from typing import Optional, Tuple

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None


def qpdf_check(pdf_path: Path) -> Tuple[Optional[bool], str]:
    try:
        res = subprocess.run(["qpdf", "--check", str(pdf_path)], capture_output=True, text=True)
        if res.returncode == 0:
            return True, "qpdf ok"
        else:
            return False, res.stderr.strip() or res.stdout.strip()
    except FileNotFoundError:
        return None, "qpdf-not-available"


def pypdf_check(pdf_path: Path) -> Tuple[Optional[bool], str]:
    if PdfReader is None:
        return None, "PyPDF2-not-installed"
    try:
        with open(pdf_path, "rb") as f:
            PdfReader(f)
        return True, "PyPDF2 ok"
    except Exception as e:
        return False, str(e)


def ensure_dir(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="downloads", help="Directory containing PDFs")
    parser.add_argument("--quarantine-dir", default="downloads/quarantine", help="Where to move corrupted PDFs")
    parser.add_argument("--report", default="reports/validation_report.csv", help="CSV report path")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    quarantine_dir = Path(args.quarantine_dir)
    report_path = Path(args.report)

    ensure_dir(report_path)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted([p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"])

    rows = []
    for p in pdf_files:
        status = "ok"
        message = ""

        qpdf_res = qpdf_check(p)
        if qpdf_res[0] is True:
            status = "ok"
            message = qpdf_res[1]
        elif qpdf_res[0] is False:
            status = "corrupt"
            message = f"qpdf: {qpdf_res[1]}"
        else:
            # qpdf not available; fall back to PyPDF2
            pypdf_res = pypdf_check(p)
            if pypdf_res[0] is True:
                status = "ok"
                message = pypdf_res[1]
            elif pypdf_res[0] is False:
                status = "corrupt"
                message = f"PyPDF2: {pypdf_res[1]}"
            else:
                status = "warning"
                message = "No qpdf or PyPDF2 available to validate"

        if status == "corrupt":
            dest = quarantine_dir / p.name
            shutil.move(str(p), str(dest))
            message += f"; moved to {dest}"

        rows.append((p.name, status, message))
        print(p.name, status, message)

    # write report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "status", "message"])
        for r in rows:
            writer.writerow(r)

    if any(r[1] == "corrupt" for r in rows):
        print("One or more corrupted PDFs were moved to quarantine.")
        sys.exit(2)
    else:
        print("All PDFs validated OK or no validator available.")
        sys.exit(0)


if __name__ == "__main__":
    main()
