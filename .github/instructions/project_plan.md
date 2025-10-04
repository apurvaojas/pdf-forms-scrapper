# PDF Forms Scraper — Project Plan

## Overview

Goal: Build a repeatable pipeline that scrapes PDFs, prepares labeled training data, fine-tunes LayoutLMv1 to extract structured fields from forms, and iterates as new PDFs are added.

High-level stages:
1. PDF scraping (done)
2. Data preparation for LayoutLMv1
3. Annotation (Label Studio)
4. Convert annotations → LayoutLMv1 format
5. Train LayoutLMv1
6. Test & validate
7. Iterate with new PDFs

---

## 1) PDF scraping

Status: Done

Artifacts:
- Raw PDFs in `downloads/`
- `pdf_metadata.db` tracking metadata

Acceptance criteria:
- All scraped PDFs are stored in `downloads/`.
- Metadata DB contains source, filename, timestamp, and fetch status.

Notes:
- Keep download logs and original URLs in `pdf_metadata.db` for provenance.

---

## 2) Data preparation (for LayoutLMv1)

Sub-steps, tools, and acceptance criteria:

### 2.1 Data cleaning — delete or quarantine corrupted PDFs
- What: Validate each PDF, move unreadable/corrupt files to `downloads/quarantine/` (or delete if preferred).
- Tools: Python with PyPDF2 or pdfminer.six (quick open/read), `qpdf --check` for robust checks.
- Acceptance: Script `scripts/validate_pdfs.py` exits 0 and produces `reports/validation_report.csv` listing OK vs corrupted files; corrupted files moved to `downloads/quarantine/`.

### 2.2 Rasterize all PDFs
- What: Convert each PDF page to an image (PNG/JPEG) at a consistent DPI (recommended 300 DPI).
- Tools: `pdftoppm` (poppler) or Python `pdf2image` (with poppler). Organize outputs as:
  - `data/images/<pdf_id>/page_000.png`, `page_001.png`, ...
- Acceptance: Every non-quarantined PDF has corresponding image pages in `data/images/<pdf_id>/`. Log rasterization errors to `logs/rasterize.log`.

### 2.3 Run PaddleOCR to create dataset compatible with Label Studio
- What: Run OCR on each page image to produce word-level tokens with bounding boxes and text. Export OCR outputs into an importable JSONL for Label Studio containing:
  - image URL/path
  - OCR tokens: text + bounding box (x0,y0,x1,y1)
  - optional line/grouping info
- Tools: PaddleOCR (Python), or alternatives like Tesseract if needed.
- Output layout suggestion: `data/ocr/<pdf_id>/page_000.json` and a combined `data/labelstudio_import.jsonl` where each line corresponds to one image with OCR payload.
- Acceptance: Label Studio can import the JSONL and display each token & bounding box aligned with the image.

### 2.4 Pre-check / small sanity visualizer (optional but recommended)
- What: For a subset, overlay OCR boxes on images and save `debug/overlays/<pdf_id>/page_000.png`.
- Acceptance: Visual checks confirm boxes align with text.

---

## 3) Annotate and label data using Label Studio
- What: Create a Label Studio project with an interface for box + text annotation mapped to the schema you need (key-value extraction, checkboxes, etc.). Import `data/labelstudio_import.jsonl`.
- Config suggestion: Use Image tasks with preloaded OCR tokens as helper data, or text+blocks UI so annotators can click words/boxes to assign labels.
- Acceptance: Completed Label Studio project with N annotated documents, consistent labeling guidelines, and exportable annotations.

Tips:
- Create a short annotation guide with examples and edge cases.
- Use inter-annotator agreement checks on a small subset.

---

## 4) Export annotated data from Label Studio
- What: Export annotations as JSONL (Label Studio standard), ensure it contains:
  - image/file references
  - labeled regions with bounding boxes
  - label names and mapping to fields
  - mapping to OCR tokens (if you used token-selection mode)
- Acceptance: Exported file(s) placed in `data/labelstudio_exports/` and validated for expected keys.

---

## 5) Convert exported data to LayoutLMv1 format
- Goal: Produce training samples for LayoutLMv1: tokens, normalized bounding boxes, and token-level labels.
- Steps:
  - Use OCR output (from step 2.3) to obtain tokens and bounding boxes.
  - For each exported annotation, map labeled regions to the OCR tokens by intersection-over-union or containment (token bbox center inside label bbox).
  - Normalize bounding boxes to [0, 1000] coordinate space (LayoutLMv1 convention) or to [0,1] depending on your training code.
  - Produce per-page JSON with:
    - words: ["The", "quick", "brown", ...]
    - bboxes: [[x0,y0,x1,y1], ...] normalized
    - labels: ["O", "B-Field", "I-Field", ...] (BIO scheme per token)
    - image/file path and metadata
- Output: `data/layoutlm_v1/train/`, `data/layoutlm_v1/val/`, `data/layoutlm_v1/test/` — each with JSON lines or per-sample JSON files.
- Acceptance: A script `scripts/convert_labelstudio_to_layoutlm.py` that takes Label Studio exports and OCR JSONs and emits LayoutLMv1 training files; verified on a sample.

Edge cases:
- Tokens that overlap multiple labels — apply deterministic rules (largest overlap or token center).
- Missing OCR tokens for annotated text — record and optionally mark tokens as unknown; log for manual review.

---

## 6) Train the model (LayoutLMv1)
- What: Fine-tune LayoutLMv1 (Hugging Face / PyTorch) on the prepared dataset.
- Requirements:
  - Training script `train_layoutlm.py` supporting configs for model checkpoint, batch size, lr, epochs, logging, and saving checkpoints.
  - Use transformers + datasets or custom dataloader that reads your JSON format.
- Recommended compute:
  - GPU with ≥12GB VRAM for reasonable batch sizes. If multiple GPUs, use distributed training.
- Acceptance:
  - Training runs end-to-end and saves checkpoints to `models/layoutlm/checkpoint-*`.
  - Training and validation loss curves recorded (TensorBoard logs in `logs/tensorboard/`).

Suggested metrics:
- Token-level F1 for each label.
- Field-level F1 (group tokens into fields, evaluate exact match).

---

## 7) Test / Validation step
- What:
  - Evaluate on held-out test set.
  - Run inference on a set of unseen PDF pages, convert model outputs back to structured fields, and compare to ground-truth.
- Acceptance:
  - Precision, recall, F1 per-field reported in `reports/eval_<timestamp>.json`.
  - Qualitative report with sample predictions + images in `reports/samples/` for manual inspection.
- Smoke tests:
  - Ensure model inference script `infer_layoutlm.py` accepts a PDF or image directory and outputs JSON with extracted fields.

---

## 8) Iterate with new PDFs scraped from web
- Pipeline automation:
  - Create a driver script `pipeline/run_full_pipeline.py` that accepts new PDF(s) and runs: validation → rasterize → OCR → create Label Studio task → (optionally) auto-label suggestions → annotate → export → convert → train incrementally.
- Acceptance:
  - New data can be added and the pipeline rerun with minimal manual steps; incremental training strategy (continue training from last checkpoint) supported.
- Versioning:
  - Keep dataset versions and model checkpoints linked to the PDF set used.
  - Maintain evaluation baselines to compare improvements.

---

## File & folder layout suggestions
- data/
  - images/<pdf_id>/page_000.png
  - ocr/<pdf_id>/page_000.json
  - labelstudio_import.jsonl
  - labelstudio_exports/
  - layoutlm_v1/{train,val,test}/
- downloads/ (raw PDFs)
- downloads/quarantine/ (corrupt)
- scripts/
  - validate_pdfs.py
  - rasterize_pdfs.py
  - run_paddleocr.py
  - make_labelstudio_import.py
  - convert_labelstudio_to_layoutlm.py
  - train_layoutlm.py
  - infer_layoutlm.py
  - pipeline/run_full_pipeline.py
- logs/
- models/
  - layoutlm/
- reports/
- README.md (update with pipeline run instructions)

---

## Tools / Libraries
- PDF handling: poppler (`pdftoppm`), pdf2image, PyPDF2, qpdf
- OCR: PaddleOCR (recommended), Tesseract as fallback
- Annotation: Label Studio
- Model: Hugging Face Transformers (LayoutLMv1), PyTorch
- Utilities: pandas, tqdm, pillow, shapely (for bbox intersection), numpy

---

## "Contract" for key scripts
- validate_pdfs.py
  - Input: `downloads/` path
  - Output: `reports/validation_report.csv`, moves invalid files
  - Error modes: unreadable file, missing permissions
- rasterize_pdfs.py
  - Input: PDFs list
  - Output: images in `data/images/`
  - Error modes: pdftoppm missing, conversion failures
- run_paddleocr.py
  - Input: image dir
  - Output: OCR JSONS
  - Error modes: OCR model not found, memory issues
- convert_labelstudio_to_layoutlm.py
  - Input: Label Studio export + OCR JSONs
  - Output: LayoutLMv1 JSONL files
  - Success: sample validated with expected token counts
- train_layoutlm.py
  - Input: train/val data, hyperparams
  - Output: model checkpoints and logs
  - Error modes: out-of-memory, missing data

---

## Edge cases & risks
- Corrupt or scanned PDFs with poor image quality → OCR errors. Mitigation: add image preprocessing (denoise, binarize) and low-confidence logging.
- Multi-column / complex layouts → token grouping may be ambiguous. Mitigation: use line/paragraph grouping heuristics from OCR and manual review.
- Large PDFs (many pages) causing memory issues → process and batch by page.
- Inconsistent annotation schema → enforce a labeling guideline and validate exports.

---

## Quick next steps (concrete)
1. Add/confirm validation script `scripts/validate_pdfs.py`. (todo assigned)
2. Add rasterization script `scripts/rasterize_pdfs.py` and run on `downloads/`.
3. Run PaddleOCR on rasterized images and create `data/labelstudio_import.jsonl`.
4. Configure Label Studio project and do a small pilot of 50 pages to iterate on annotation guidelines.
5. Convert pilot exports to LayoutLMv1 format and run a quick fine-tune to validate training pipeline.

---

## Useful commands examples
- Validate PDFs with qpdf:
```bash
qpdf --check downloads/your.pdf
```

- Rasterize using pdftoppm:
```bash
pdftoppm -png -r 300 downloads/your.pdf data/images/your_pdf_page
```

- Run PaddleOCR (Python example pattern):
```bash
python scripts/run_paddleocr.py --input_dir data/images --output_dir data/ocr
```

---

## Completion / Acceptance Criteria (project-level)
- A reproducible pipeline that:
  - Cleans and rasterizes new PDFs.
  - Produces OCR tokens and Label Studio import files.
  - Supports annotation and converts exports to LayoutLMv1 format.
  - Fine-tunes LayoutLMv1 and runs evaluation producing metric reports.
- Scripts and small README show how to run each step.
- Pipeline can process new scraped PDFs with minimal manual effort.

---

If you want, I can:
- Generate the template scripts (validate, rasterize, OCR runner, converter) and add them to `scripts/`.
- Create a minimal README with runnable examples and sample Label Studio config.
- Implement the Label Studio → LayoutLMv1 converter for a small sample and run a quick smoke test on a few PDFs you point to.

Which of these would you like me to implement next?
