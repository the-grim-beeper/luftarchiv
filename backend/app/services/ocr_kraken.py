"""Kraken OCR service wrapper.

Stage 1 of the two-stage OCR pipeline: local text extraction via Kraken.
Stage 2 (Claude) handles intelligent structured extraction from the raw text.

NOTE: Kraken is not listed as a hard dependency because of its heavy footprint.
      If Kraken is not installed the service returns empty results so the rest
      of the pipeline can continue operating (e.g. during development/testing).

NOTE: Kraken's internal API is version-dependent.  The calls inside
      ``_run_kraken`` represent the most common surface area as of Kraken 4.x
      but may need adaptation if a different version is installed.
"""

import asyncio
from pathlib import Path


async def kraken_ocr_page(image_path: Path | str) -> dict:
    """Run Kraken OCR on a single page image.

    Offloads the CPU-bound Kraken work to a thread-pool executor so the
    async event loop is never blocked.

    Args:
        image_path: Path to the image file to process.

    Returns:
        dict with keys:
        - raw_text: str — full page text (lines joined by newline)
        - segmentation: list of {text: str, bbox: {x, y, w, h}} — line-level
          results with bounding-box coordinates in pixels
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run_kraken, Path(image_path))


def _run_kraken(image_path: Path) -> dict:
    """Synchronous Kraken OCR — runs in a thread-pool executor."""
    try:
        from kraken.lib.models import load_any
        from kraken.blla import segment
        from kraken.rpred import rpred
        from PIL import Image
    except ImportError:
        # Kraken (or Pillow) is not installed.
        # Return an empty but structurally valid result so the rest of the
        # system continues to function without Kraken present.
        return {"raw_text": "", "segmentation": []}

    im = Image.open(image_path)

    # Load the default English model bundled with Kraken.
    # Pass an explicit model path or name if a custom model is needed.
    model = load_any("en_best.mlmodel")

    # Baseline segmentation (Kraken 4.x BLLA segmenter).
    baseline_seg = segment(im)

    # Recognise text line by line.
    pred_it = rpred(model, im, baseline_seg)

    lines: list[dict] = []
    full_text_parts: list[str] = []

    for record in pred_it:
        line_text = record.prediction

        # Best-effort bounding-box extraction.
        # ``record.cuts`` contains the character-level cut points; we derive a
        # line bounding box from the extremes.  The attribute name and structure
        # differ across Kraken versions so we fall back to zeros on any error.
        try:
            cuts = record.cuts
            if cuts:
                xs = [p[0] for p in cuts]
                ys = [p[1] for p in cuts]
                x_min, x_max = int(min(xs)), int(max(xs))
                y_min = int(min(ys))
                bbox = {
                    "x": x_min,
                    "y": y_min,
                    "w": x_max - x_min if len(cuts) > 1 else 0,
                    "h": 30,  # Kraken does not expose a reliable line height here
                }
            else:
                bbox = {"x": 0, "y": 0, "w": 0, "h": 0}
        except (AttributeError, TypeError):
            bbox = {"x": 0, "y": 0, "w": 0, "h": 0}

        lines.append({"text": line_text, "bbox": bbox})
        full_text_parts.append(line_text)

    return {
        "raw_text": "\n".join(full_text_parts),
        "segmentation": lines,
    }
