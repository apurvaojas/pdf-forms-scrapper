#!/usr/bin/env python3
"""Run OCR over rasterized images to produce per-page OCR JSONs and a Label Studio import JSONL.

Outputs:
- data/ocr/<pdf_id>/page_000.json (word-level tokens with bbox and text)
- data/labelstudio_import.jsonl (one task per image referencing the image path and OCR tokens)

Usage:
    python scripts/run_paddleocr.py --input-dir data/images --output-dir data/ocr --labelstudio data/labelstudio_import.jsonl --limit 50

This script tries PaddleOCR first, falls back to pytesseract if PaddleOCR not installed.
"""
import argparse
import json
import os
from pathlib import Path
from tqdm import tqdm


try:
    from paddleocr import PaddleOCR
except Exception:
    PaddleOCR = None

try:
    import paddle
except Exception:
    paddle = None


def run_paddleocr_on_image(ocr, image_path: Path):
    # returns list of {text, bbox:[x0,y0,x1,y1], confidence}
    res = ocr.ocr(str(image_path), cls=False)
    tokens = []
    for line in res:
        for word in line:
            # word format: [ [x1,y1], [x2,y2], [x3,y3], [x4,y4] ], (text, conf)
            box = word[0]
            text = word[1][0]
            conf = float(word[1][1]) if word[1][1] is not None else None
            x_coords = [p[0] for p in box]
            y_coords = [p[1] for p in box]
            x0, x1 = min(x_coords), max(x_coords)
            y0, y1 = min(y_coords), max(y_coords)
            tokens.append({"text": text, "bbox": [x0, y0, x1, y1], "conf": conf})
    return tokens





def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="data/images")
    parser.add_argument("--output-dir", default="data/ocr")
    parser.add_argument("--labelstudio", default="data/labelstudio_import.jsonl")
    parser.add_argument("--limit", type=int, default=None, help="Only process first N image dirs")
    args = parser.parse_args()

    inp = Path(args.input_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    image_dirs = sorted([d for d in inp.iterdir() if d.is_dir()])
    if args.limit:
        image_dirs = image_dirs[: args.limit]

    use_paddle = PaddleOCR is not None

    if not use_paddle:
        print("PaddleOCR is not installed. Install it with: pip install paddleocr")
        return

    # Require the PaddlePaddle runtime (paddle). Prefer a GPU build if available.
    if paddle is None:
        print(
            "PaddlePaddle (the `paddle` runtime) is not installed.\n"
            "For GPU installs, follow the instructions at https://www.paddlepaddle.org.cn/install/quick for your CUDA version,\n"
            "or install a CPU build with: pip install paddlepaddle==2.6.3 -f https://paddlepaddle.org.cn/whl/mkl/avx/stable.html\n"
            "After installing paddle, install paddleocr: pip install paddleocr"
        )
        return

    # Try to set device to GPU when paddle was built with CUDA support
    use_gpu = False
    try:
        if hasattr(paddle, "is_compiled_with_cuda") and paddle.is_compiled_with_cuda():
            try:
                paddle.set_device("gpu")
                use_gpu = True
                print("PaddlePaddle GPU build detected — using GPU device for OCR")
            except Exception as e:
                print("Could not set paddle device to GPU, will attempt to continue on default device:", e)
        else:
            print("PaddlePaddle found but not the GPU build. Running on CPU. Install paddlepaddle-gpu for GPU acceleration.")
    except Exception as e:
        print("Warning while checking PaddlePaddle GPU availability:", e)

    # use English model by default; adjust `lang` as required
    # Try passing `use_gpu` if the PaddleOCR constructor accepts it, otherwise fall back.
    try:
        ocr = PaddleOCR(use_angle_cls=False, lang="en", use_gpu=use_gpu)
    except TypeError:
        # Older/newer versions may not accept `use_gpu` kwarg; try without it.
        ocr = PaddleOCR(use_angle_cls=False, lang="en")

    tasks = []

    for d in tqdm(image_dirs, desc="Dirs"):
        pdf_id = d.name
        ocr_out_dir = out / pdf_id
        ocr_out_dir.mkdir(parents=True, exist_ok=True)
        images = sorted(d.glob("*.png"))
        for i, img in enumerate(images):
            tokens = None
            try:
                tokens = run_paddleocr_on_image(ocr, img)
            except Exception as e:
                print(f"OCR failed for {img}: {e}")
                continue

            page_name = f"page_{i:03d}.json"
            with open(ocr_out_dir / page_name, "w") as f:
                json.dump({"image": str(img), "tokens": tokens}, f)

            # Label Studio task format (image + regions) - keep tokens as 'predictions'/'meta' for import
            task = {
                "data": {"image": str(img)},
                "meta": {"ocr_tokens": tokens},
            }
            tasks.append(task)

    # write combined JSONL
    with open(args.labelstudio, "w") as f:
        for t in tasks:
            f.write(json.dumps(t) + "\n")

    print(f"Wrote {len(tasks)} tasks to {args.labelstudio}")


if __name__ == "__main__":
    main()
