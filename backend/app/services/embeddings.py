"""
Embedding service for Luftarchiv.

Provides:
- generate_record_summary()  — template-based NL summary of a Record
- generate_embedding(text)   — 1024-dim vector via fastembed BAAI/bge-large-en-v1.5
"""

import asyncio
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.record import Record

MODEL_NAME = "BAAI/bge-large-en-v1.5"
EMBEDDING_DIM = 1024


@lru_cache(maxsize=1)
def _get_model():
    """Load (and cache) the fastembed TextEmbedding model."""
    from fastembed import TextEmbedding  # type: ignore

    return TextEmbedding(model_name=MODEL_NAME)


def generate_record_summary(record: "Record") -> str:
    """
    Build a natural-language summary string from a Record's fields.
    Used as the text input to the embedding model.
    """
    parts: list[str] = []

    if record.date:
        parts.append(f"Date: {record.date}.")
    if record.unit_designation:
        parts.append(f"Unit: {record.unit_designation}.")
    if record.aircraft_type:
        parts.append(f"Aircraft: {record.aircraft_type}.")
    if record.werknummer:
        parts.append(f"Werknummer: {record.werknummer}.")
    if record.incident_type:
        parts.append(f"Incident: {record.incident_type}.")
    if record.incident_description:
        parts.append(f"Description: {record.incident_description}.")
    if record.damage_percentage:
        parts.append(f"Damage: {record.damage_percentage}%.")
    if record.location:
        parts.append(f"Location: {record.location}.")

    # Append personnel info
    if hasattr(record, "personnel") and record.personnel:
        personnel_parts: list[str] = []
        for p in record.personnel:
            name_parts = []
            if p.rank_abbreviation:
                name_parts.append(p.rank_abbreviation)
            if p.surname:
                name_parts.append(p.surname)
            if p.first_name:
                name_parts.append(p.first_name)
            name_str = " ".join(name_parts)
            if p.fate:
                name_str += f" ({p.fate})"
            if name_str.strip():
                personnel_parts.append(name_str)
        if personnel_parts:
            parts.append("Personnel: " + "; ".join(personnel_parts) + ".")

    if record.raw_text_original:
        # Truncate raw text to avoid overly long summaries
        raw = record.raw_text_original[:500].replace("\n", " ")
        parts.append(f"Raw text: {raw}")

    return " ".join(parts) if parts else "No data."


async def generate_embedding(text: str) -> list[float]:
    """
    Generate a 1024-dimensional embedding for *text* using fastembed.
    Runs the CPU-bound model inference in a thread pool so it does not
    block the asyncio event loop.
    """
    loop = asyncio.get_running_loop()

    def _embed(t: str) -> list[float]:
        model = _get_model()
        vectors = list(model.embed([t]))
        return vectors[0].tolist()

    return await loop.run_in_executor(None, _embed, text)
