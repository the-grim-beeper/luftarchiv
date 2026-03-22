import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.services.export import export_records_to_csv

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/{collection_id}/csv")
async def export_collection_csv(
    collection_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    try:
        csv_data, filename = await export_records_to_csv(collection_id, session)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    def _iter_csv():
        yield csv_data

    return StreamingResponse(
        _iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
