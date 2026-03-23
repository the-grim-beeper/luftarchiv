from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.collections import router as collections_router
from app.api.export import router as export_router
from app.api.import_ import router as import_router
from app.api.knowledge import router as knowledge_router
from app.api.records import router as records_router
from app.api.analytics import router as analytics_router
from app.api.search import router as search_router

app = FastAPI(title="Luftarchiv", description="OCR Archive Search Tool for Luftwaffe Research")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(collections_router)
app.include_router(import_router)
app.include_router(knowledge_router)
app.include_router(search_router)
app.include_router(records_router)
app.include_router(export_router)
app.include_router(analytics_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve frontend static files in production (when built into ./static)
_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.is_dir():
    # Serve index.html for all non-API routes (SPA client-side routing)
    from fastapi.responses import FileResponse

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file_path = _static_dir / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_static_dir / "index.html")

    app.mount("/assets", StaticFiles(directory=str(_static_dir / "assets")), name="static")
