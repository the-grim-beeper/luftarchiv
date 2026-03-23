from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Record, Personnel

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(session: AsyncSession = Depends(get_session)):
    total_records = (await session.execute(select(func.count(Record.id)))).scalar() or 0
    total_personnel = (await session.execute(select(func.count(Personnel.id)))).scalar() or 0

    # Losses by aircraft type
    by_aircraft = await session.execute(
        select(Record.aircraft_type, func.count(Record.id))
        .where(Record.aircraft_type.isnot(None))
        .group_by(Record.aircraft_type)
        .order_by(func.count(Record.id).desc())
        .limit(15)
    )

    # Losses by incident type
    by_incident = await session.execute(
        select(Record.incident_type, func.count(Record.id))
        .where(Record.incident_type.isnot(None))
        .group_by(Record.incident_type)
        .order_by(func.count(Record.id).desc())
        .limit(10)
    )

    # Losses by month
    by_month = await session.execute(
        select(
            func.to_char(Record.date, "YYYY-MM").label("month"),
            func.count(Record.id),
        )
        .where(Record.date.isnot(None))
        .group_by("month")
        .order_by("month")
    )

    # Personnel fates
    by_fate = await session.execute(
        select(Personnel.fate_english, func.count(Personnel.id))
        .where(Personnel.fate_english.isnot(None))
        .group_by(Personnel.fate_english)
        .order_by(func.count(Personnel.id).desc())
    )

    return {
        "total_records": total_records,
        "total_personnel": total_personnel,
        "by_aircraft": [{"name": r[0], "count": r[1]} for r in by_aircraft],
        "by_incident": [{"name": r[0], "count": r[1]} for r in by_incident],
        "by_month": [{"month": r[0], "count": r[1]} for r in by_month],
        "by_fate": [{"name": r[0], "count": r[1]} for r in by_fate],
    }
