"""
Ollama-based extraction service.

Uses Ollama's vision models (llama3.2-vision, llava, etc.) to extract
structured records from scanned document images. Same interface as
ocr_claude.py but runs locally — free, private, no API key needed.
"""

import base64
import json
import re
from pathlib import Path

import httpx

from app.services.llm_config import load_config
from app.services.ocr_claude import EXTRACTION_SYSTEM_PROMPT, build_extraction_prompt


async def _call_ollama(image_path: str, prompt: str) -> dict:
    """Call Ollama API with image and prompt. Returns parsed JSON."""
    config = load_config()

    image_data = Path(image_path).read_bytes()
    base64_image = base64.b64encode(image_data).decode("utf-8")

    payload = {
        "model": config.effective_model,
        "messages": [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": prompt,
                "images": [base64_image],
            },
        ],
        "stream": False,
        "options": {"temperature": 0.1},
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{config.ollama_url}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        result = response.json()

    raw_text = result.get("message", {}).get("content", "")

    # Extract JSON from response
    stripped = raw_text.strip()
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
    if code_block:
        stripped = code_block.group(1).strip()
    else:
        json_match = re.search(r"\{[\s\S]*\}", stripped)
        if json_match:
            stripped = json_match.group(0)

    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Ollama returned non-JSON response: {raw_text[:500]!r}"
        ) from exc


async def extract_records_from_page(
    image_path: str,
    raw_ocr_text: str,
    glossary_context: dict[str, str],
) -> list[dict]:
    """Extract structured records from a single page using Ollama."""
    prompt = build_extraction_prompt(raw_ocr_text, glossary_context)
    result = await _call_ollama(image_path, prompt)
    return result.get("records", [])
