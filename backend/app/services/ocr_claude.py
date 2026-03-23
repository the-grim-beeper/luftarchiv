"""Claude extraction service — Stage 2 of the OCR pipeline.

Sends a scanned Luftwaffe loss report page (image + raw OCR text + glossary
context) to Claude Sonnet and returns structured JSON records.
"""

import base64
import json
import re
from pathlib import Path

import anthropic

from app.config import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MODEL = "claude-sonnet-4-20250514"
_MAX_TOKENS = 4096

_SYSTEM_PROMPT = """You are an expert at reading and interpreting German Luftwaffe loss reports (Verlustmeldungen) from World War II.

Your task is to extract structured records from scanned pages of these documents. Each page typically contains multiple entries recording aircraft losses, damage, and personnel casualties.

Return your response as a single JSON object with this exact structure:
{
  "records": [
    {
      "entry_number": <int or null>,
      "date": "<YYYY-MM-DD or null>",
      "unit_designation": "<string as written in document or null>",
      "aircraft_type": "<string as written in document or null>",
      "werknummer": "<string or null>",
      "incident_type": "<string in original German or null>",
      "incident_description": "<English description of what happened or null>",
      "damage_percentage": <int 0-100 or null>,
      "location": "<string or null>",
      "personnel": [
        {
          "rank_abbreviation": "<abbreviated rank as written or null>",
          "rank_full": "<full rank name in German or null>",
          "surname": "<string or null>",
          "first_name": "<string or null>",
          "fate": "<string in original German or null>",
          "fate_english": "<English translation of fate or null>"
        }
      ],
      "new_abbreviations": [
        {
          "term": "<abbreviation string>",
          "suggested_definition": "<your best guess at the definition>",
          "category": "<one of: rank, unit, aircraft, incident, location, other>"
        }
      ]
    }
  ]
}

Rules:
- Preserve original German spelling in: incident_type, fate, unit_designation, rank_full
- Provide English translations in: fate_english, incident_description
- Use null for fields that are unreadable or not present in the source
- Convert German date formats (e.g. 15.3.43 or 15.3.1943) to ISO 8601 (1943-03-15)
- Two-digit years should be interpreted as 1940s (e.g. 43 → 1943)
- Flag any abbreviations not found in the provided glossary in the new_abbreviations array
- Return only the JSON object — no markdown, no commentary
"""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def build_extraction_prompt(raw_ocr_text: str, glossary_context: dict) -> str:
    """Build the user-facing prompt combining OCR text and glossary.

    Args:
        raw_ocr_text: The raw text extracted by Kraken OCR.
        glossary_context: Mapping of German terms/abbreviations to their
            English definitions, used to guide extraction.

    Returns:
        A fully-formed prompt string ready to send to Claude.
    """
    glossary_lines = "\n".join(
        f"  {term}: {definition}"
        for term, definition in sorted(glossary_context.items())
    )
    glossary_section = (
        f"Known abbreviations and terms from the glossary:\n{glossary_lines}"
        if glossary_lines
        else "No glossary entries provided."
    )

    return (
        f"Please extract all loss report records from the following page.\n\n"
        f"--- GLOSSARY CONTEXT ---\n"
        f"{glossary_section}\n\n"
        f"--- RAW OCR TEXT ---\n"
        f"{raw_ocr_text}\n\n"
        f"Use both the image and the OCR text above to produce structured JSON records. "
        f"The image is the authoritative source; the OCR text is a helpful (but potentially "
        f"imperfect) transcription. Flag any abbreviations not present in the glossary."
    )


# ---------------------------------------------------------------------------
# Internal API call
# ---------------------------------------------------------------------------


async def _call_claude(image_path: str | Path, prompt: str) -> dict:
    """Call Claude Sonnet with the page image and extraction prompt.

    Args:
        image_path: Path to the image file to analyse.
        prompt: The user-facing extraction prompt (from build_extraction_prompt).

    Returns:
        Parsed JSON dict as returned by Claude.

    Raises:
        ValueError: If the response cannot be parsed as valid JSON.
    """
    image_path = Path(image_path)

    # Determine media type from extension
    suffix = image_path.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(suffix, "image/jpeg")

    # Encode image as base64
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    from app.services.llm_config import load_config
    config = load_config()
    api_key = config.api_key or settings.anthropic_api_key
    model = config.effective_model if config.provider == "claude" else _MODEL

    client = anthropic.AsyncAnthropic(api_key=api_key)

    message = await client.messages.create(
        model=model,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    raw_text = message.content[0].text

    # Extract JSON from response — handle text before/after code blocks
    stripped = raw_text.strip()

    # Try to find JSON in a code block anywhere in the response
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
    if code_block:
        stripped = code_block.group(1).strip()
    else:
        # Try to find raw JSON object
        json_match = re.search(r'\{[\s\S]*\}', stripped)
        if json_match:
            stripped = json_match.group(0)

    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Claude returned non-JSON response: {raw_text[:500]!r}"
        ) from exc


# ---------------------------------------------------------------------------
# Public orchestration function
# ---------------------------------------------------------------------------


async def extract_records_from_page(
    image_path: str | Path,
    raw_ocr_text: str,
    glossary_context: dict,
) -> list[dict]:
    """Extract structured loss-report records from a single scanned page.

    Orchestrates prompt construction, Claude API call, and result unpacking.

    Args:
        image_path: Path to the page image file.
        raw_ocr_text: Raw OCR text for the page (from Stage 1 / Kraken).
        glossary_context: Mapping of known German abbreviations to definitions.

    Returns:
        List of structured record dicts as parsed from Claude's JSON response.
    """
    prompt = build_extraction_prompt(raw_ocr_text, glossary_context)
    response = await _call_claude(image_path, prompt)
    return response.get("records", [])
