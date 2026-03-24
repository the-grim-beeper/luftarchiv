"""
Geocoding API for crash site locations.

Uses Claude to batch-geocode WWII location names to coordinates.
Results are cached in the geocoded_locations table.
"""

import json
import uuid

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.services.llm_config import load_config

router = APIRouter(prefix="/api/geocode", tags=["geocode"])


@router.get("/locations")
async def get_geocoded_locations(session: AsyncSession = Depends(get_session)):
    """Return all geocoded locations with their coordinates and record counts."""
    result = await session.execute(text("""
        SELECT g.location_text, g.latitude, g.longitude, g.resolved_name, g.country, g.record_count
        FROM archive_data.geocoded_locations g
        WHERE g.latitude IS NOT NULL
        ORDER BY g.record_count DESC
    """))
    rows = result.fetchall()
    return {
        "locations": [
            {
                "location": r[0],
                "lat": r[1],
                "lng": r[2],
                "resolved_name": r[3],
                "country": r[4],
                "record_count": r[5],
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.get("/stats")
async def geocode_stats(session: AsyncSession = Depends(get_session)):
    """Stats on geocoding progress."""
    total_locations = (await session.execute(text(
        "SELECT count(DISTINCT location) FROM archive_data.records WHERE location IS NOT NULL AND location != '' AND location != 'Unbekannt'"
    ))).scalar()
    geocoded = (await session.execute(text(
        "SELECT count(*) FROM archive_data.geocoded_locations WHERE latitude IS NOT NULL"
    ))).scalar()
    total_records_with_location = (await session.execute(text(
        "SELECT count(*) FROM archive_data.records WHERE location IS NOT NULL AND location != '' AND location != 'Unbekannt'"
    ))).scalar()

    return {
        "unique_locations": total_locations,
        "geocoded": geocoded,
        "records_with_location": total_records_with_location,
    }


@router.post("/run")
async def run_geocoding(
    batch_size: int = 100,
    session: AsyncSession = Depends(get_session),
):
    """Geocode the top N un-geocoded locations using Claude."""
    config = load_config()
    if not config.api_key:
        raise HTTPException(status_code=400, detail="No API key configured")

    # Get top locations by frequency that haven't been geocoded yet
    result = await session.execute(text("""
        SELECT r.location, count(*) as cnt
        FROM archive_data.records r
        WHERE r.location IS NOT NULL
          AND r.location != ''
          AND r.location != 'Unbekannt'
          AND r.location != 'Nicht gemeldet'
          AND r.location NOT IN (SELECT location_text FROM archive_data.geocoded_locations)
        GROUP BY r.location
        ORDER BY cnt DESC
        LIMIT :batch_size
    """), {"batch_size": batch_size})
    locations = [(r[0], r[1]) for r in result.fetchall()]

    if not locations:
        return {"status": "done", "message": "All locations already geocoded", "geocoded": 0}

    # Build prompt for Claude
    location_list = "\n".join(f"- {loc} ({cnt} records)" for loc, cnt in locations)

    client = anthropic.AsyncAnthropic(api_key=config.api_key)
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": f"""These are location names from WWII German Luftwaffe loss reports (1941-1945).
They refer to crash sites, airfields, and military locations primarily on the Eastern Front, Mediterranean, and Western Europe.

Geocode each location to approximate latitude/longitude coordinates. Many are:
- Russian/Ukrainian cities and villages (Eastern Front)
- Tunisian/Sicilian/Italian locations (Mediterranean theater)
- French/Belgian/Dutch locations (Western Front)
- German airfields

Return a JSON array. For locations you cannot identify, use null for lat/lng.

Locations:
{location_list}

Return ONLY this JSON format, no other text:
[
  {{"location": "original text", "lat": 52.5, "lng": 13.4, "resolved_name": "Berlin, Germany", "country": "Germany"}},
  ...
]"""
        }],
    )

    # Parse response
    raw = message.content[0].text.strip()
    # Extract JSON array
    import re
    json_match = re.search(r'\[[\s\S]*\]', raw)
    if not json_match:
        raise HTTPException(status_code=500, detail="Claude did not return valid JSON")

    try:
        geocoded = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse geocoding response")

    # Store results
    location_counts = dict(locations)
    inserted = 0
    for item in geocoded:
        loc = item.get("location", "")
        if not loc:
            continue

        cnt = location_counts.get(loc, 0)
        await session.execute(text("""
            INSERT INTO archive_data.geocoded_locations (location_text, latitude, longitude, resolved_name, country, record_count)
            VALUES (:loc, :lat, :lng, :name, :country, :cnt)
            ON CONFLICT (location_text) DO UPDATE SET
                latitude = :lat, longitude = :lng, resolved_name = :name, country = :country, record_count = :cnt
        """), {
            "loc": loc,
            "lat": item.get("lat"),
            "lng": item.get("lng"),
            "name": item.get("resolved_name"),
            "country": item.get("country"),
            "cnt": cnt,
        })
        inserted += 1

    await session.commit()

    return {
        "status": "ok",
        "geocoded": inserted,
        "remaining": max(0, len(locations) - inserted),
    }
