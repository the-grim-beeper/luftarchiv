from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.collections import router as collections_router
from app.api.export import router as export_router
from app.api.import_ import router as import_router
from app.api.knowledge import router as knowledge_router
from app.api.records import router as records_router
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


@app.get("/api/health")
async def health():
    return {"status": "ok"}
