from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.collections import router as collections_router

app = FastAPI(title="Luftarchiv", description="OCR Archive Search Tool for Luftwaffe Research")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(collections_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
