from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# Aircraft type normalization: map raw OCR values to canonical names
AIRCRAFT_NORMALIZE_SQL = """
    CASE
        WHEN aircraft_type IN ('F', 'P', 'H', '#', '') THEN NULL
        WHEN length(aircraft_type) <= 2 AND aircraft_type ~ '^[0-9]+$' THEN NULL
        WHEN upper(aircraft_type) LIKE '%109%' THEN
            CASE
                WHEN aircraft_type ~* 'G6|G-6' THEN 'Bf 109 G-6'
                WHEN aircraft_type ~* 'G4|G-4' THEN 'Bf 109 G-4'
                WHEN aircraft_type ~* 'G2|G-2' THEN 'Bf 109 G-2'
                WHEN aircraft_type ~* 'G1|G-1' THEN 'Bf 109 G-1'
                WHEN aircraft_type ~* 'F4|F-4' THEN 'Bf 109 F-4'
                WHEN aircraft_type ~* 'F2|F-2' THEN 'Bf 109 F-2'
                WHEN aircraft_type ~* 'F1|F-1' THEN 'Bf 109 F-1'
                WHEN aircraft_type ~* 'E7|E-7' THEN 'Bf 109 E-7'
                WHEN aircraft_type ~* 'E[^0-9]|E$' THEN 'Bf 109 E'
                WHEN aircraft_type ~* 'F[0-9]' THEN 'Bf 109 F'
                ELSE 'Bf 109 (var.)'
            END
        WHEN upper(aircraft_type) LIKE '%190%' AND length(aircraft_type) > 2 THEN
            CASE
                WHEN aircraft_type ~* 'A5|A-5' THEN 'Fw 190 A-5'
                WHEN aircraft_type ~* 'A4|A-4' THEN 'Fw 190 A-4'
                WHEN aircraft_type ~* 'A3|A-3' THEN 'Fw 190 A-3'
                WHEN aircraft_type ~* 'A2|A-2' THEN 'Fw 190 A-2'
                WHEN aircraft_type ~* 'A6|A-6' THEN 'Fw 190 A-6'
                WHEN aircraft_type ~* 'F[0-9]' THEN 'Fw 190 F'
                ELSE 'Fw 190'
            END
        WHEN upper(aircraft_type) LIKE '%JU%88%' OR aircraft_type LIKE 'Ju 88%' THEN
            CASE
                WHEN aircraft_type ~* 'A4|A-4' THEN 'Ju 88 A-4'
                WHEN aircraft_type ~* 'A14|A-14' THEN 'Ju 88 A-14'
                WHEN aircraft_type ~* 'A5|A-5' THEN 'Ju 88 A-5'
                WHEN aircraft_type ~* 'D1|D-1' THEN 'Ju 88 D-1'
                WHEN aircraft_type ~* 'C6|C-6' THEN 'Ju 88 C-6'
                WHEN aircraft_type ~* 'G6|G-6' THEN 'Ju 88 G-6'
                ELSE 'Ju 88'
            END
        WHEN upper(aircraft_type) LIKE '%JU%87%' OR aircraft_type LIKE 'Ju 87%' THEN 'Ju 87'
        WHEN upper(aircraft_type) LIKE '%JU%52%' OR aircraft_type LIKE 'Ju 52%' THEN 'Ju 52'
        WHEN upper(aircraft_type) LIKE '%HE%111%' OR aircraft_type LIKE 'He 111%' THEN 'He 111'
        WHEN upper(aircraft_type) LIKE '%BF%110%' OR aircraft_type LIKE 'Bf 110%' THEN 'Bf 110'
        WHEN upper(aircraft_type) LIKE '%DO%217%' OR aircraft_type LIKE 'Do 217%' THEN 'Do 217'
        WHEN upper(aircraft_type) LIKE '%DO%17%' OR aircraft_type LIKE 'Do 17%' THEN 'Do 17'
        WHEN upper(aircraft_type) LIKE '%ME%262%' THEN 'Me 262'
        WHEN upper(aircraft_type) LIKE '%ME%210%' THEN 'Me 210'
        WHEN upper(aircraft_type) LIKE '%ME%410%' THEN 'Me 410'
        WHEN upper(aircraft_type) LIKE '%FW%200%' OR aircraft_type LIKE 'FW 200%' THEN 'Fw 200'
        WHEN upper(aircraft_type) LIKE '%HE%177%' THEN 'He 177'
        WHEN upper(aircraft_type) LIKE '%HS%126%' OR aircraft_type LIKE 'Hs 126%' THEN 'Hs 126'
        WHEN upper(aircraft_type) LIKE '%HS%129%' THEN 'Hs 129'
        WHEN aircraft_type ~* '^Fl\\.Fl\\.' THEN NULL
        ELSE aircraft_type
    END
"""

# Fate normalization
FATE_NORMALIZE_SQL = """
    CASE
        WHEN lower(fate_english) LIKE '%killed%' OR lower(fate_english) LIKE '%dead%'
             OR lower(fate_english) = 'tot' THEN 'Killed'
        WHEN lower(fate_english) LIKE '%wound%' OR lower(fate_english) LIKE '%injur%' THEN 'Wounded'
        WHEN lower(fate_english) LIKE '%miss%' THEN 'Missing'
        WHEN lower(fate_english) LIKE '%captured%' OR lower(fate_english) LIKE '%prisoner%'
             OR lower(fate_english) LIKE '%gefangen%' OR lower(fate_english) LIKE '%pow%' THEN 'Captured/POW'
        WHEN lower(fate_english) LIKE '%uninjur%' OR lower(fate_english) LIKE '%unhurt%'
             OR lower(fate_english) LIKE '%safe%' THEN 'Uninjured'
        WHEN lower(fate_english) LIKE '%bail%' OR lower(fate_english) LIKE '%parachut%' THEN 'Bailed out'
        WHEN fate_english IS NULL OR fate_english = '' THEN NULL
        ELSE 'Other'
    END
"""


@router.get("/overview")
async def overview(session: AsyncSession = Depends(get_session)):
    total_records = (await session.execute(text(
        "SELECT count(*) FROM archive_data.records"
    ))).scalar() or 0
    total_personnel = (await session.execute(text(
        "SELECT count(*) FROM archive_data.personnel"
    ))).scalar() or 0

    # Losses by normalized aircraft type (excluding junk values)
    by_aircraft = await session.execute(text(f"""
        SELECT normalized, sum(cnt) as total FROM (
            SELECT {AIRCRAFT_NORMALIZE_SQL} as normalized, count(*) as cnt
            FROM archive_data.records
            WHERE aircraft_type IS NOT NULL
            GROUP BY aircraft_type
        ) sub
        WHERE normalized IS NOT NULL
        GROUP BY normalized
        ORDER BY total DESC
        LIMIT 15
    """))

    # Losses by incident type (top 12)
    by_incident = await session.execute(text("""
        SELECT incident_type, count(*) as cnt
        FROM archive_data.records
        WHERE incident_type IS NOT NULL AND incident_type != ''
        GROUP BY incident_type
        ORDER BY cnt DESC
        LIMIT 12
    """))

    # Losses by month (filter out clearly wrong dates)
    by_month = await session.execute(text("""
        SELECT to_char(date, 'YYYY-MM') as month, count(*) as cnt
        FROM archive_data.records
        WHERE date IS NOT NULL AND date >= '1939-09-01' AND date <= '1945-05-08'
        GROUP BY month
        ORDER BY month
    """))

    # Personnel fates (normalized)
    by_fate = await session.execute(text(f"""
        SELECT normalized, sum(cnt) as total FROM (
            SELECT {FATE_NORMALIZE_SQL} as normalized, count(*) as cnt
            FROM archive_data.personnel
            GROUP BY fate_english
        ) sub
        WHERE normalized IS NOT NULL
        GROUP BY normalized
        ORDER BY total DESC
    """))

    return {
        "total_records": total_records,
        "total_personnel": total_personnel,
        "by_aircraft": [{"name": r[0], "count": r[1]} for r in by_aircraft],
        "by_incident": [{"name": r[0], "count": r[1]} for r in by_incident],
        "by_month": [{"month": r[0], "count": r[1]} for r in by_month],
        "by_fate": [{"name": r[0], "count": r[1]} for r in by_fate],
    }
