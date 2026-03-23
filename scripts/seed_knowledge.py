#!/usr/bin/env python3
"""
Seed script: creates the default admin user and loads glossary-seed.csv
into the glossary table as "verified" entries (trust_level=2).

Usage (from repo root):
    cd backend
    source .venv/bin/activate
    python ../scripts/seed_knowledge.py
"""

import asyncio
import csv
import sys
import uuid
from pathlib import Path

# Allow running from repo root or from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models import Glossary, User

ADMIN_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")
# Look for seed CSV in multiple locations (repo root or Docker container)
_candidates = [
    Path(__file__).resolve().parents[1] / "docs" / "glossary-seed.csv",
    Path("/app/seed/glossary-seed.csv"),
]
SEED_CSV = next((p for p in _candidates if p.exists()), _candidates[0])


async def ensure_admin(session: AsyncSession) -> None:
    result = await session.execute(select(User).where(User.id == ADMIN_UUID))
    user = result.scalar_one_or_none()
    if not user:
        admin = User(id=ADMIN_UUID, username="admin", role="admin")
        session.add(admin)
        await session.flush()
        print("Created default admin user.")
    else:
        print("Admin user already exists — skipping.")


async def load_glossary(session: AsyncSession) -> None:
    if not SEED_CSV.exists():
        print(f"ERROR: Seed CSV not found at {SEED_CSV}", file=sys.stderr)
        sys.exit(1)

    from datetime import datetime, timezone

    rows_added = 0
    with SEED_CSV.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            term = row["term"].strip()
            # Skip if already present
            result = await session.execute(
                select(Glossary).where(Glossary.term == term)
            )
            if result.scalar_one_or_none():
                print(f"  Skipping duplicate: {term}")
                continue

            entry = Glossary(
                term=term,
                definition=row["definition"].strip() or None,
                category=row["category"].strip() or None,
                language="de",
                trust_level="verified",
                source="glossary-seed.csv",
                proposed_by=ADMIN_UUID,
                verified_by=ADMIN_UUID,
                verified_at=datetime.now(timezone.utc),
            )
            session.add(entry)
            rows_added += 1

    await session.flush()
    print(f"Added {rows_added} glossary entries.")


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as session:
        async with session.begin():
            await ensure_admin(session)
            await load_glossary(session)

    await engine.dispose()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
