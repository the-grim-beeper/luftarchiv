# Luftarchiv Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an open-source OCR archive search tool that extracts structured data from scanned Luftwaffe loss reports and makes them searchable via direct, semantic, and AI-powered queries.

**Architecture:** Two-schema PostgreSQL (archive_data + archive_knowledge) with pgvector for semantic search. Two-stage OCR pipeline: Kraken for local text extraction, Claude Sonnet for intelligent structured extraction. FastAPI backend, React/Vite/TailwindCSS frontend with document-first UI.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy async, PostgreSQL 16 + pgvector, Kraken OCR, Anthropic Claude API, fastembed, React 19, TypeScript, Vite, TailwindCSS v4, OpenSeadragon, TanStack Table, Recharts

**Spec:** `docs/superpowers/specs/2026-03-22-luftarchiv-design.md`

---

## Phase 1: Foundation

### Task 1: Project Scaffolding & Infrastructure

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create docker-compose.yml with PostgreSQL + pgvector**

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: luftarchiv
      POSTGRES_USER: luftarchiv
      POSTGRES_PASSWORD: luftarchiv_dev
    ports:
      - "5435:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./backend/db-init:/docker-entrypoint-initdb.d

volumes:
  pgdata:
```

- [ ] **Step 2: Create db-init script for schemas**

Create `backend/db-init/01-schemas.sql`:
```sql
CREATE SCHEMA IF NOT EXISTS archive_data;
CREATE SCHEMA IF NOT EXISTS archive_knowledge;
CREATE EXTENSION IF NOT EXISTS vector;
```

- [ ] **Step 3: Create .env.example and .gitignore**

`.env.example`:
```
DATABASE_URL=postgresql+asyncpg://luftarchiv:luftarchiv_dev@localhost:5435/luftarchiv
ANTHROPIC_API_KEY=sk-ant-your-key-here
IMAGE_STORAGE_PATH=./data/images
```

`.gitignore`:
```
__pycache__/
*.pyc
.env
.venv/
node_modules/
dist/
data/
*.egg-info/
.pytest_cache/
```

- [ ] **Step 4: Create backend/pyproject.toml**

```toml
[project]
name = "luftarchiv"
version = "0.1.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 5: Create backend/requirements.txt**

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
sqlalchemy[asyncio]>=2.0.36
asyncpg>=0.30.0
alembic>=1.14.0
pgvector>=0.3.6
anthropic>=0.42.0
fastembed>=0.4.0
kraken>=5.2.0
Pillow>=11.0.0
pydantic>=2.10.0
pydantic-settings>=2.6.0
python-multipart>=0.0.18
pytest>=8.3.0
pytest-asyncio>=0.24.0
httpx>=0.28.0
```

- [ ] **Step 6: Create backend/app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://luftarchiv:luftarchiv_dev@localhost:5435/luftarchiv"
    anthropic_api_key: str = ""
    image_storage_path: str = "./data/images"

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 7: Create backend/app/__init__.py and backend/tests/__init__.py**

Both empty files.

- [ ] **Step 8: Create backend/tests/conftest.py with async test DB fixture**

```python
import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base, get_session
from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://luftarchiv:luftarchiv_dev@localhost:5435/luftarchiv_test"

engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_session() -> AsyncGenerator[AsyncSession]:
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session
```

- [ ] **Step 9: Start Docker and create test database**

```bash
cd ~/projects/luftarchiv
docker compose up -d
# Wait for DB to be ready, then create test DB
docker compose exec db psql -U luftarchiv -c "CREATE DATABASE luftarchiv_test;"
docker compose exec db psql -U luftarchiv -d luftarchiv_test -c "CREATE SCHEMA IF NOT EXISTS archive_data; CREATE SCHEMA IF NOT EXISTS archive_knowledge; CREATE EXTENSION IF NOT EXISTS vector;"
```

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat: project scaffolding with Docker, config, and test infrastructure"
```

---

### Task 2: Database Models — archive_data Schema

**Files:**
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/database.py`
- Create: `backend/app/db/models/__init__.py`
- Create: `backend/app/db/models/user.py`
- Create: `backend/app/db/models/collection.py`
- Create: `backend/app/db/models/page.py`
- Create: `backend/app/db/models/record.py`
- Create: `backend/app/db/models/personnel.py`
- Create: `backend/app/db/models/correction.py`
- Create: `backend/app/db/models/pipeline_job.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Create database.py with engine and session**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
```

- [ ] **Step 2: Create user.py model**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "archive_data"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="contributor")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 3: Create collection.py model**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Collection(Base):
    __tablename__ = "collections"
    __table_args__ = {"schema": "archive_data"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    document_type: Mapped[str | None] = mapped_column(String)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    pages = relationship("Page", back_populates="collection", cascade="all, delete-orphan")
```

- [ ] **Step 4: Create page.py model**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = {"schema": "archive_data"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("archive_data.collections.id"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[str] = mapped_column(String, nullable=False)
    ocr_status: Mapped[str] = mapped_column(String, default="pending")
    ocr_confidence: Mapped[float | None] = mapped_column(Float)
    raw_ocr_text: Mapped[str | None] = mapped_column(Text)
    segmentation_data: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    collection = relationship("Collection", back_populates="pages")
    records = relationship("Record", back_populates="page", cascade="all, delete-orphan")
```

- [ ] **Step 5: Create record.py model**

```python
import uuid
from datetime import date, datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Record(Base):
    __tablename__ = "records"
    __table_args__ = {"schema": "archive_data"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("archive_data.pages.id"), nullable=False
    )
    page_id_end: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("archive_data.pages.id")
    )
    entry_number: Mapped[int | None] = mapped_column(Integer)
    date: Mapped[date | None] = mapped_column(Date)
    unit_designation: Mapped[str | None] = mapped_column(String)
    aircraft_type: Mapped[str | None] = mapped_column(String)
    werknummer: Mapped[str | None] = mapped_column(String)
    incident_type: Mapped[str | None] = mapped_column(String)
    incident_description: Mapped[str | None] = mapped_column(Text)
    damage_percentage: Mapped[int | None] = mapped_column(Integer)
    location: Mapped[str | None] = mapped_column(String)
    raw_text_original: Mapped[str | None] = mapped_column(Text)
    bounding_boxes: Mapped[dict | None] = mapped_column(JSON)
    search_embedding = mapped_column(Vector(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    page = relationship("Page", back_populates="records", foreign_keys=[page_id])
    personnel = relationship("Personnel", back_populates="record", cascade="all, delete-orphan")
    corrections = relationship("RecordCorrection", back_populates="record", cascade="all, delete-orphan")
```

- [ ] **Step 6: Create personnel.py model**

```python
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Personnel(Base):
    __tablename__ = "personnel"
    __table_args__ = {"schema": "archive_data"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("archive_data.records.id"), nullable=False
    )
    rank_abbreviation: Mapped[str | None] = mapped_column(String)
    rank_full: Mapped[str | None] = mapped_column(String)
    surname: Mapped[str | None] = mapped_column(String)
    first_name: Mapped[str | None] = mapped_column(String)
    fate: Mapped[str | None] = mapped_column(String)
    fate_english: Mapped[str | None] = mapped_column(String)

    record = relationship("Record", back_populates="personnel")
```

- [ ] **Step 7: Create correction.py model**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class RecordCorrection(Base):
    __tablename__ = "record_corrections"
    __table_args__ = {"schema": "archive_data"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("archive_data.records.id"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String, nullable=False)
    original_value: Mapped[str | None] = mapped_column(Text)
    corrected_value: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("archive_data.users.id"), nullable=False
    )
    corrected_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    record = relationship("Record", back_populates="corrections")
```

- [ ] **Step 8: Create pipeline_job.py model**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class PipelineJob(Base):
    __tablename__ = "pipeline_jobs"
    __table_args__ = {"schema": "archive_data"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("archive_data.collections.id"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String, nullable=False)  # kraken / claude / embedding
    status: Mapped[str] = mapped_column(String, default="pending")  # pending / running / completed / failed
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    processed_pages: Mapped[int] = mapped_column(Integer, default=0)
    last_processed_page_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
```

- [ ] **Step 9: Create models/__init__.py importing all models**

```python
from app.db.models.collection import Collection
from app.db.models.correction import RecordCorrection
from app.db.models.page import Page
from app.db.models.personnel import Personnel
from app.db.models.pipeline_job import PipelineJob
from app.db.models.record import Record
from app.db.models.user import User

__all__ = [
    "Collection",
    "Page",
    "Personnel",
    "PipelineJob",
    "Record",
    "RecordCorrection",
    "User",
]
```

- [ ] **Step 10: Write test that models can be created and queried**

`backend/tests/test_models.py`:
```python
import uuid

from app.db.models import Collection, Page, Personnel, Record, User


async def test_create_user(db_session):
    user = User(username="testadmin", role="admin")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    assert user.username == "testadmin"
    assert user.role == "admin"
    assert user.id is not None


async def test_create_collection_with_pages(db_session):
    collection = Collection(name="RL 2-III/1190", source_reference="RL_2_III_1190", status="pending")
    db_session.add(collection)
    await db_session.commit()
    await db_session.refresh(collection)

    page = Page(collection_id=collection.id, page_number=1, image_path="/data/images/page_001.jpg")
    db_session.add(page)
    await db_session.commit()
    await db_session.refresh(page)

    assert page.collection_id == collection.id
    assert page.ocr_status == "pending"


async def test_create_record_with_personnel(db_session):
    collection = Collection(name="Test", status="pending")
    db_session.add(collection)
    await db_session.commit()

    page = Page(collection_id=collection.id, page_number=1, image_path="/test.jpg")
    db_session.add(page)
    await db_session.commit()

    record = Record(
        page_id=page.id,
        entry_number=1,
        unit_designation="II./JG 54",
        aircraft_type="Bf 109 G-4",
        incident_type="Bruchlandung",
        damage_percentage=40,
    )
    db_session.add(record)
    await db_session.commit()

    person = Personnel(
        record_id=record.id,
        rank_abbreviation="Uffz.",
        surname="Schmidt",
        first_name="Werner",
        fate="unverletzt",
        fate_english="uninjured",
    )
    db_session.add(person)
    await db_session.commit()

    await db_session.refresh(record)
    assert len(record.personnel) == 1
    assert record.personnel[0].surname == "Schmidt"
```

- [ ] **Step 11: Run tests**

```bash
cd ~/projects/luftarchiv/backend
python -m pytest tests/test_models.py -v
```
Expected: 3 tests PASS

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "feat: archive_data schema models with tests"
```

---

### Task 3: Database Models — archive_knowledge Schema

**Files:**
- Create: `backend/app/db/models/glossary.py`
- Create: `backend/app/db/models/document_schema.py`
- Create: `backend/app/db/models/unit_designation.py`
- Create: `backend/app/db/models/aircraft_type.py`
- Create: `backend/app/db/models/knowledge_review.py`
- Modify: `backend/app/db/models/__init__.py`
- Create: `backend/tests/test_knowledge_models.py`

- [ ] **Step 1: Create glossary.py model**

```python
import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Glossary(Base):
    __tablename__ = "glossary"
    __table_args__ = {"schema": "archive_knowledge"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    term: Mapped[str] = mapped_column(String, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)  # rank/unit_type/incident_type/aircraft/location/other
    language: Mapped[str] = mapped_column(String, default="de")
    trust_level: Mapped[str] = mapped_column(String, default="ai_suggested")  # verified/proposed/ai_suggested
    source: Mapped[str | None] = mapped_column(String)
    proposed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("archive_data.users.id"))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("archive_data.users.id"))
    verified_at: Mapped[datetime | None] = mapped_column()
    embedding = mapped_column(Vector(1024), nullable=True)
```

- [ ] **Step 2: Create unit_designation.py model**

```python
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class UnitDesignation(Base):
    __tablename__ = "unit_designations"
    __table_args__ = {"schema": "archive_knowledge"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    abbreviation: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    unit_type: Mapped[str | None] = mapped_column(String)
    parent_unit_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("archive_knowledge.unit_designations.id"))
    active_from: Mapped[date | None] = mapped_column(Date)
    active_to: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    trust_level: Mapped[str] = mapped_column(String, default="ai_suggested")
```

- [ ] **Step 3: Create aircraft_type.py model**

```python
import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AircraftType(Base):
    __tablename__ = "aircraft_types"
    __table_args__ = {"schema": "archive_knowledge"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    designation: Mapped[str] = mapped_column(String, nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String)
    common_name: Mapped[str | None] = mapped_column(String)
    variants: Mapped[dict | None] = mapped_column(JSON)
    trust_level: Mapped[str] = mapped_column(String, default="ai_suggested")
```

- [ ] **Step 4: Create document_schema.py model**

```python
import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class DocumentSchema(Base):
    __tablename__ = "document_schemas"
    __table_args__ = {"schema": "archive_knowledge"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_type: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    column_definitions: Mapped[dict | None] = mapped_column(JSON)
    example_collection_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # No cross-schema FK
    trust_level: Mapped[str] = mapped_column(String, default="ai_suggested")
```

- [ ] **Step 5: Create knowledge_review.py model**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class KnowledgeReview(Base):
    __tablename__ = "knowledge_reviews"
    __table_args__ = {"schema": "archive_knowledge"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # propose/approve/reject/demote
    old_trust_level: Mapped[str | None] = mapped_column(String)
    new_trust_level: Mapped[str] = mapped_column(String, nullable=False)
    reviewer: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("archive_data.users.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 6: Update models/__init__.py with knowledge models**

Add to the existing imports:
```python
from app.db.models.aircraft_type import AircraftType
from app.db.models.document_schema import DocumentSchema
from app.db.models.glossary import Glossary
from app.db.models.knowledge_review import KnowledgeReview
from app.db.models.unit_designation import UnitDesignation
```

And update `__all__`.

- [ ] **Step 7: Write knowledge model tests**

`backend/tests/test_knowledge_models.py`:
```python
from app.db.models import AircraftType, Glossary, UnitDesignation, User


async def test_create_glossary_entry(db_session):
    user = User(username="admin", role="admin")
    db_session.add(user)
    await db_session.commit()

    entry = Glossary(
        term="Bruchlandung",
        definition="Crash landing",
        category="incident_type",
        trust_level="verified",
        proposed_by=user.id,
        verified_by=user.id,
    )
    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)
    assert entry.term == "Bruchlandung"
    assert entry.trust_level == "verified"


async def test_create_unit_with_parent(db_session):
    parent = UnitDesignation(abbreviation="JG 54", full_name="Jagdgeschwader 54", unit_type="Geschwader")
    db_session.add(parent)
    await db_session.commit()

    child = UnitDesignation(
        abbreviation="II./JG 54",
        full_name="II. Gruppe, Jagdgeschwader 54",
        unit_type="Gruppe",
        parent_unit_id=parent.id,
    )
    db_session.add(child)
    await db_session.commit()
    assert child.parent_unit_id == parent.id


async def test_create_aircraft_type(db_session):
    aircraft = AircraftType(
        designation="Bf 109 G-4",
        manufacturer="Messerschmitt",
        common_name="Me 109",
        variants={"G-4/R3": "Reconnaissance variant", "G-4/Trop": "Tropical variant"},
        trust_level="verified",
    )
    db_session.add(aircraft)
    await db_session.commit()
    assert aircraft.variants["G-4/Trop"] == "Tropical variant"
```

- [ ] **Step 8: Run tests**

```bash
cd ~/projects/luftarchiv/backend
python -m pytest tests/ -v
```
Expected: All tests PASS (6 total: 3 from task 2 + 3 new)

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: archive_knowledge schema models with tests"
```

---

### Task 4: Alembic Setup & Initial Migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/` (auto-generated migration)

- [ ] **Step 1: Initialize alembic**

```bash
cd ~/projects/luftarchiv/backend
python -m alembic init alembic
```

- [ ] **Step 2: Edit alembic.ini — set sqlalchemy.url to empty (will use env.py)**

In `alembic.ini`, set:
```ini
sqlalchemy.url =
```

- [ ] **Step 3: Edit alembic/env.py for async + both schemas**

Replace `alembic/env.py` with:
```python
import asyncio
import sys
from pathlib import Path

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.db.database import Base
from app.db.models import *  # noqa: F401, F403 — force model registration

target_metadata = Base.metadata


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name in ("archive_data", "archive_knowledge")
    return True


def run_migrations_offline():
    context.configure(
        url=settings.database_url.replace("+asyncpg", ""),
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        include_name=include_name,
        version_table_schema="archive_data",
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        version_table_schema="archive_data",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: Generate initial migration**

```bash
cd ~/projects/luftarchiv/backend
python -m alembic revision --autogenerate -m "initial schema"
```

- [ ] **Step 5: Run migration**

```bash
python -m alembic upgrade head
```

- [ ] **Step 6: Verify tables exist**

```bash
docker compose exec db psql -U luftarchiv -d luftarchiv -c "\dt archive_data.*"
docker compose exec db psql -U luftarchiv -d luftarchiv -c "\dt archive_knowledge.*"
```
Expected: All tables from both schemas listed

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: alembic setup with initial migration for both schemas"
```

---

### Task 5: FastAPI App Shell & Collections CRUD API

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/collection.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/collections.py`
- Create: `backend/tests/test_api_collections.py`

- [ ] **Step 1: Create Pydantic schemas for collections**

`backend/app/schemas/collection.py`:
```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class CollectionCreate(BaseModel):
    name: str
    source_reference: str | None = None
    description: str | None = None
    document_type: str | None = None


class CollectionResponse(BaseModel):
    id: uuid.UUID
    name: str
    source_reference: str | None
    description: str | None
    document_type: str | None
    page_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CollectionList(BaseModel):
    collections: list[CollectionResponse]
    total: int
```

- [ ] **Step 2: Create collections API router**

`backend/app/api/collections.py`:
```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Collection
from app.schemas.collection import CollectionCreate, CollectionList, CollectionResponse

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.get("", response_model=CollectionList)
async def list_collections(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Collection).order_by(Collection.created_at.desc()))
    collections = result.scalars().all()
    return CollectionList(collections=collections, total=len(collections))


@router.post("", response_model=CollectionResponse, status_code=201)
async def create_collection(data: CollectionCreate, session: AsyncSession = Depends(get_session)):
    collection = Collection(**data.model_dump())
    session.add(collection)
    await session.commit()
    await session.refresh(collection)
    return collection


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(collection_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    await session.delete(collection)
    await session.commit()
```

- [ ] **Step 3: Create main.py**

```python
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
```

- [ ] **Step 4: Write API tests**

`backend/tests/test_api_collections.py`:
```python
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_create_and_list_collections(client):
    resp = await client.post("/api/collections", json={
        "name": "RL 2-III/1190",
        "source_reference": "RL_2_III_1190",
        "description": "Luftwaffe loss reports",
        "document_type": "loss_report",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "RL 2-III/1190"
    assert data["status"] == "pending"
    collection_id = data["id"]

    resp = await client.get("/api/collections")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    resp = await client.get(f"/api/collections/{collection_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "RL 2-III/1190"


async def test_delete_collection(client):
    resp = await client.post("/api/collections", json={"name": "To delete"})
    collection_id = resp.json()["id"]

    resp = await client.delete(f"/api/collections/{collection_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/collections/{collection_id}")
    assert resp.status_code == 404
```

- [ ] **Step 5: Run tests**

```bash
cd ~/projects/luftarchiv/backend
python -m pytest tests/ -v
```
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: FastAPI shell with collections CRUD API and tests"
```

---

### Task 6: Collection Import Service (Scan Folder → Pages)

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/import_service.py`
- Create: `backend/app/api/import_.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_import_service.py`

- [ ] **Step 1: Write failing test for import service**

`backend/tests/test_import_service.py`:
```python
import os
import tempfile
from pathlib import Path

from PIL import Image

from app.db.models import Collection
from app.services.import_service import import_scan_folder


def create_test_images(folder: Path, count: int = 3):
    """Create dummy JPEG images for testing."""
    for i in range(1, count + 1):
        img = Image.new("RGB", (100, 100), color="white")
        img.save(folder / f"test_{i:04d}.jpg")


async def test_import_scan_folder(db_session):
    with tempfile.TemporaryDirectory() as tmpdir:
        folder = Path(tmpdir)
        create_test_images(folder, count=3)

        collection = await import_scan_folder(
            session=db_session,
            folder_path=folder,
            name="Test Collection",
            source_reference="TEST_001",
        )

        assert collection.name == "Test Collection"
        assert collection.page_count == 3
        assert collection.status == "pending"

        await db_session.refresh(collection)
        assert len(collection.pages) == 3
        assert collection.pages[0].page_number == 1
        assert collection.pages[2].page_number == 3
        assert collection.pages[0].ocr_status == "pending"


async def test_import_skips_non_images(db_session):
    with tempfile.TemporaryDirectory() as tmpdir:
        folder = Path(tmpdir)
        create_test_images(folder, count=1)
        (folder / "readme.txt").write_text("not an image")

        collection = await import_scan_folder(
            session=db_session,
            folder_path=folder,
            name="Mixed files",
        )
        assert collection.page_count == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_import_service.py -v
```
Expected: FAIL — `import_service` does not exist

- [ ] **Step 3: Implement import_service.py**

```python
import shutil
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Collection, Page

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


async def import_scan_folder(
    session: AsyncSession,
    folder_path: Path,
    name: str,
    source_reference: str | None = None,
    description: str | None = None,
    document_type: str | None = None,
) -> Collection:
    """Import a folder of scanned images as a new collection."""
    image_files = sorted(
        f for f in folder_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    collection = Collection(
        name=name,
        source_reference=source_reference,
        description=description,
        document_type=document_type,
        page_count=len(image_files),
        status="pending",
    )
    session.add(collection)
    await session.flush()

    storage_dir = Path(settings.image_storage_path) / str(collection.id)
    storage_dir.mkdir(parents=True, exist_ok=True)

    for i, image_file in enumerate(image_files, start=1):
        dest = storage_dir / image_file.name
        shutil.copy2(image_file, dest)

        page = Page(
            collection_id=collection.id,
            page_number=i,
            image_path=str(dest),
            ocr_status="pending",
        )
        session.add(page)

    await session.commit()
    await session.refresh(collection)
    return collection
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_import_service.py -v
```
Expected: 2 tests PASS

- [ ] **Step 5: Add import API endpoint**

`backend/app/api/import_.py`:
```python
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.schemas.collection import CollectionResponse
from app.services.import_service import import_scan_folder

router = APIRouter(prefix="/api/import", tags=["import"])


class ImportRequest(BaseModel):
    folder_path: str
    name: str
    source_reference: str | None = None
    description: str | None = None
    document_type: str | None = None


@router.post("", response_model=CollectionResponse, status_code=201)
async def import_folder(data: ImportRequest, session: AsyncSession = Depends(get_session)):
    folder = Path(data.folder_path)
    if not folder.is_dir():
        raise HTTPException(status_code=400, detail=f"Folder not found: {data.folder_path}")

    collection = await import_scan_folder(
        session=session,
        folder_path=folder,
        name=data.name,
        source_reference=data.source_reference,
        description=data.description,
        document_type=data.document_type,
    )
    return collection
```

- [ ] **Step 6: Register router in main.py**

Add to `main.py`:
```python
from app.api.import_ import router as import_router
app.include_router(import_router)
```

- [ ] **Step 7: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: scan folder import service with image copying and page creation"
```

---

## Phase 2: OCR Pipeline

### Task 7: Kraken OCR Service

**Files:**
- Create: `backend/app/services/ocr_kraken.py`
- Create: `backend/tests/test_ocr_kraken.py`

- [ ] **Step 1: Write failing test for Kraken service**

`backend/tests/test_ocr_kraken.py`:
```python
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.services.ocr_kraken import kraken_ocr_page


def create_test_image_with_text(path: Path):
    """Create a simple image with text for OCR testing."""
    img = Image.new("RGB", (800, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "Test document text 12345", fill="black")
    img.save(path)


async def test_kraken_ocr_returns_text_and_segmentation():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "test.jpg"
        create_test_image_with_text(img_path)

        result = await kraken_ocr_page(img_path)

        assert "raw_text" in result
        assert "segmentation" in result
        assert isinstance(result["raw_text"], str)
        assert isinstance(result["segmentation"], list)
        # Segmentation entries should have text and bbox
        if result["segmentation"]:
            seg = result["segmentation"][0]
            assert "text" in seg
            assert "bbox" in seg
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_ocr_kraken.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement ocr_kraken.py**

```python
import asyncio
from pathlib import Path

from kraken.lib.models import load_any
from kraken.blla import segment
from kraken.rpred import rpred
from PIL import Image


# Default model — Kraken ships with a general-purpose model
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = load_any("en_best.mlmodel")  # Kraken's bundled best model
    return _model


def _run_kraken(image_path: Path) -> dict:
    """Synchronous Kraken OCR — runs in thread pool."""
    im = Image.open(image_path)
    model = _get_model()

    # Segment the page
    baseline_seg = segment(im)

    # Recognize text
    pred_it = rpred(model, im, baseline_seg)

    lines = []
    full_text_parts = []
    for record in pred_it:
        line_text = record.prediction
        # Extract bounding box from the baseline segmentation
        bbox = {
            "x": int(record.cuts[0][0]) if record.cuts else 0,
            "y": int(record.cuts[0][1]) if record.cuts else 0,
            "w": int(record.cuts[-1][0] - record.cuts[0][0]) if len(record.cuts) > 1 else 0,
            "h": 30,  # Approximate line height
        }
        lines.append({"text": line_text, "bbox": bbox})
        full_text_parts.append(line_text)

    return {
        "raw_text": "\n".join(full_text_parts),
        "segmentation": lines,
    }


async def kraken_ocr_page(image_path: Path) -> dict:
    """Run Kraken OCR on a single page image. Returns raw_text and segmentation."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_kraken, image_path)
```

Note: The Kraken API may need adjustment based on the installed version. The key contract is: input an image path, output `{raw_text: str, segmentation: [{text, bbox}]}`. If Kraken's API differs at install time, adapt the wrapper — the interface stays the same.

- [ ] **Step 4: Run test**

```bash
python -m pytest tests/test_ocr_kraken.py -v
```
Expected: PASS (may need Kraken model download on first run)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: Kraken OCR service with text extraction and segmentation"
```

---

### Task 8: Claude Extraction Service

**Files:**
- Create: `backend/app/services/ocr_claude.py`
- Create: `backend/tests/test_ocr_claude.py`

- [ ] **Step 1: Write test with a mock Claude response**

`backend/tests/test_ocr_claude.py`:
```python
import json
from unittest.mock import AsyncMock, patch

from app.services.ocr_claude import extract_records_from_page, build_extraction_prompt


def test_build_extraction_prompt():
    prompt = build_extraction_prompt(
        raw_ocr_text="1. 15.3.43 II./JG 54 Bf 109 G-4 Bruchlandung 40%",
        glossary_context={"Bruchlandung": "crash landing", "Uffz.": "Unteroffizier"},
    )
    assert "Bruchlandung" in prompt
    assert "crash landing" in prompt
    assert "JSON" in prompt


MOCK_CLAUDE_RESPONSE = {
    "records": [
        {
            "entry_number": 1,
            "date": "1943-03-15",
            "unit_designation": "II./JG 54",
            "aircraft_type": "Bf 109 G-4",
            "werknummer": "19241",
            "incident_type": "Bruchlandung",
            "incident_description": "Crash landing due to engine failure",
            "damage_percentage": 40,
            "location": "Krasnogvardeisk",
            "personnel": [
                {
                    "rank_abbreviation": "Uffz.",
                    "rank_full": "Unteroffizier",
                    "surname": "Schmidt",
                    "first_name": "Werner",
                    "fate": "unverletzt",
                    "fate_english": "uninjured",
                }
            ],
            "new_abbreviations": [],
        }
    ]
}


@patch("app.services.ocr_claude._call_claude")
async def test_extract_records_from_page(mock_call):
    mock_call.return_value = MOCK_CLAUDE_RESPONSE

    records = await extract_records_from_page(
        image_path="/test/image.jpg",
        raw_ocr_text="1. 15.3.43 II./JG 54 Bf 109 G-4 Bruchlandung 40%",
        glossary_context={},
    )

    assert len(records) == 1
    assert records[0]["unit_designation"] == "II./JG 54"
    assert records[0]["personnel"][0]["surname"] == "Schmidt"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_ocr_claude.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement ocr_claude.py**

```python
import base64
import json
from pathlib import Path

import anthropic

from app.config import settings

EXTRACTION_SYSTEM_PROMPT = """You are an expert at reading German Luftwaffe loss reports (Flugzeugunfälle und Verluste) from World War II. You extract structured data from scanned document images.

You receive:
1. A scanned image of a page from a loss report
2. Raw OCR text from Kraken (may have errors)
3. A glossary of known abbreviations

Extract every record (row/entry) on the page as structured JSON. Each record represents one aircraft incident.

Output format:
{
  "records": [
    {
      "entry_number": int or null,
      "date": "YYYY-MM-DD" or null,
      "unit_designation": "string as written",
      "aircraft_type": "string as written",
      "werknummer": "string" or null,
      "incident_type": "string in original German",
      "incident_description": "string" or null,
      "damage_percentage": int or null,
      "location": "string" or null,
      "personnel": [
        {
          "rank_abbreviation": "string",
          "rank_full": "string or null",
          "surname": "string",
          "first_name": "string or null",
          "fate": "string in original German",
          "fate_english": "string"
        }
      ],
      "new_abbreviations": [
        {"term": "string", "suggested_definition": "string", "category": "string"}
      ]
    }
  ]
}

Rules:
- Preserve original German text in incident_type, fate, unit_designation fields
- Provide English translations in fate_english and incident_description
- If a field is unreadable, use null
- Flag any abbreviation you encounter that is NOT in the provided glossary as new_abbreviations
- One record per incident. Multiple personnel per record if multiple crew listed.
- Dates: convert German date format (e.g., "15.3.43") to ISO format ("1943-03-15")"""


def build_extraction_prompt(raw_ocr_text: str, glossary_context: dict[str, str]) -> str:
    glossary_str = "\n".join(f"- {term}: {defn}" for term, defn in glossary_context.items())
    if not glossary_str:
        glossary_str = "(no glossary entries yet)"

    return f"""Extract all records from this loss report page.

Known abbreviations:
{glossary_str}

Raw OCR text (may contain errors — use the image as the primary source):
{raw_ocr_text}

Return the structured JSON as specified."""


async def _call_claude(image_path: str, prompt: str) -> dict:
    """Call Claude API with image and prompt. Returns parsed JSON."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Read and encode image
    image_data = Path(image_path).read_bytes()
    base64_image = base64.b64encode(image_data).decode("utf-8")

    # Determine media type
    suffix = Path(image_path).suffix.lower()
    media_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".tif": "image/tiff", ".tiff": "image/tiff"}.get(suffix, "image/jpeg")

    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": base64_image}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    # Parse JSON from response
    response_text = message.content[0].text
    # Handle case where Claude wraps JSON in markdown code block
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    return json.loads(response_text)


async def extract_records_from_page(
    image_path: str,
    raw_ocr_text: str,
    glossary_context: dict[str, str],
) -> list[dict]:
    """Extract structured records from a single page using Claude."""
    prompt = build_extraction_prompt(raw_ocr_text, glossary_context)
    result = await _call_claude(image_path, prompt)
    return result.get("records", [])
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_ocr_claude.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: Claude extraction service with structured JSON output"
```

---

### Task 9: Extraction Pipeline Orchestrator

**Files:**
- Create: `backend/app/services/extraction.py`
- Modify: `backend/app/api/collections.py` (add trigger endpoint)
- Create: `backend/tests/test_extraction.py`

- [ ] **Step 1: Write test for pipeline orchestrator**

`backend/tests/test_extraction.py`:
```python
from unittest.mock import AsyncMock, patch

from app.db.models import Collection, Page, PipelineJob
from app.services.extraction import run_kraken_stage, run_claude_stage


@patch("app.services.extraction.kraken_ocr_page")
async def test_run_kraken_stage(mock_kraken, db_session):
    mock_kraken.return_value = {
        "raw_text": "Test OCR output",
        "segmentation": [{"text": "Test OCR output", "bbox": {"x": 0, "y": 0, "w": 100, "h": 30}}],
    }

    collection = Collection(name="Test", status="pending", page_count=1)
    db_session.add(collection)
    await db_session.commit()

    page = Page(collection_id=collection.id, page_number=1, image_path="/test.jpg", ocr_status="pending")
    db_session.add(page)
    await db_session.commit()

    job = PipelineJob(collection_id=collection.id, stage="kraken", total_pages=1)
    db_session.add(job)
    await db_session.commit()

    await run_kraken_stage(db_session, collection.id, job.id)

    await db_session.refresh(page)
    assert page.raw_ocr_text == "Test OCR output"
    assert page.ocr_status == "extracted"
    assert page.segmentation_data is not None

    await db_session.refresh(job)
    assert job.status == "completed"
    assert job.processed_pages == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_extraction.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement extraction.py**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Glossary, Page, PipelineJob, Record, Personnel
from app.services.ocr_kraken import kraken_ocr_page
from app.services.ocr_claude import extract_records_from_page


async def _get_glossary_context(session: AsyncSession) -> dict[str, str]:
    """Load verified and proposed glossary entries as context for Claude."""
    result = await session.execute(
        select(Glossary).where(Glossary.trust_level.in_(["verified", "proposed"]))
    )
    entries = result.scalars().all()
    return {e.term: e.definition for e in entries}


async def run_kraken_stage(session: AsyncSession, collection_id: uuid.UUID, job_id: uuid.UUID):
    """Run Kraken OCR on all pending pages in a collection."""
    job = await session.get(PipelineJob, job_id)
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    await session.commit()

    result = await session.execute(
        select(Page)
        .where(Page.collection_id == collection_id, Page.ocr_status == "pending")
        .order_by(Page.page_number)
    )
    pages = result.scalars().all()

    for page in pages:
        try:
            ocr_result = await kraken_ocr_page(page.image_path)
            page.raw_ocr_text = ocr_result["raw_text"]
            page.segmentation_data = ocr_result["segmentation"]
            page.ocr_status = "extracted"
            job.processed_pages += 1
            job.last_processed_page_id = page.id
            await session.commit()
        except Exception as e:
            job.status = "failed"
            job.error_message = f"Failed on page {page.page_number}: {str(e)}"
            await session.commit()
            return

    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)
    await session.commit()


async def run_claude_stage(session: AsyncSession, collection_id: uuid.UUID, job_id: uuid.UUID):
    """Run Claude extraction on all pages with Kraken text."""
    job = await session.get(PipelineJob, job_id)
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    await session.commit()

    glossary_context = await _get_glossary_context(session)

    result = await session.execute(
        select(Page)
        .where(Page.collection_id == collection_id, Page.ocr_status == "extracted")
        .order_by(Page.page_number)
    )
    pages = result.scalars().all()

    for page in pages:
        try:
            records_data = await extract_records_from_page(
                image_path=page.image_path,
                raw_ocr_text=page.raw_ocr_text or "",
                glossary_context=glossary_context,
            )

            for rec_data in records_data:
                personnel_data = rec_data.pop("personnel", [])
                new_abbrevs = rec_data.pop("new_abbreviations", [])

                record = Record(page_id=page.id, **{k: v for k, v in rec_data.items() if k in Record.__table__.columns.keys()})
                session.add(record)
                await session.flush()

                for p in personnel_data:
                    person = Personnel(record_id=record.id, **p)
                    session.add(person)

                # Auto-suggest new abbreviations
                for abbrev in new_abbrevs:
                    existing = await session.execute(
                        select(Glossary).where(Glossary.term == abbrev["term"])
                    )
                    if not existing.scalar_one_or_none():
                        glossary_entry = Glossary(
                            term=abbrev["term"],
                            definition=abbrev.get("suggested_definition", ""),
                            category=abbrev.get("category", "other"),
                            trust_level="ai_suggested",
                            source=f"Auto-detected from page {page.page_number}",
                        )
                        session.add(glossary_entry)

            job.processed_pages += 1
            job.last_processed_page_id = page.id
            await session.commit()
        except Exception as e:
            job.status = "failed"
            job.error_message = f"Failed on page {page.page_number}: {str(e)}"
            await session.commit()
            return

    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)
    await session.commit()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_extraction.py -v
```
Expected: PASS

- [ ] **Step 5: Add pipeline trigger endpoint to collections API**

Add to `backend/app/api/collections.py`:
```python
from app.db.models import PipelineJob, Page
from app.services.extraction import run_kraken_stage, run_claude_stage
from fastapi import BackgroundTasks


@router.post("/{collection_id}/extract")
async def start_extraction(
    collection_id: uuid.UUID,
    stage: str = "kraken",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_session),
):
    collection = await session.get(Collection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Count pages for the job
    result = await session.execute(select(func.count(Page.id)).where(Page.collection_id == collection_id))
    page_count = result.scalar()

    job = PipelineJob(collection_id=collection_id, stage=stage, total_pages=page_count)
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Run in background
    if stage == "kraken":
        background_tasks.add_task(run_kraken_stage, session, collection_id, job.id)
    elif stage == "claude":
        background_tasks.add_task(run_claude_stage, session, collection_id, job.id)

    return {"job_id": str(job.id), "stage": stage, "status": "started"}
```

- [ ] **Step 6: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: extraction pipeline orchestrator with Kraken and Claude stages"
```

---

## Phase 3: Knowledge Base & Search

### Task 10: Knowledge CRUD API

**Files:**
- Create: `backend/app/schemas/knowledge.py`
- Create: `backend/app/api/knowledge.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_api_knowledge.py`

- [ ] **Step 1: Create Pydantic schemas for knowledge entities**

`backend/app/schemas/knowledge.py`:
```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class GlossaryCreate(BaseModel):
    term: str
    definition: str
    category: str
    language: str = "de"
    trust_level: str = "proposed"
    source: str | None = None


class GlossaryResponse(BaseModel):
    id: uuid.UUID
    term: str
    definition: str
    category: str
    language: str
    trust_level: str
    source: str | None
    proposed_by: uuid.UUID | None
    verified_by: uuid.UUID | None
    verified_at: datetime | None

    model_config = {"from_attributes": True}


class GlossaryList(BaseModel):
    entries: list[GlossaryResponse]
    total: int


class ReviewAction(BaseModel):
    action: str  # approve / reject / demote
    reason: str | None = None


class UnitDesignationCreate(BaseModel):
    abbreviation: str
    full_name: str
    unit_type: str | None = None
    parent_unit_id: uuid.UUID | None = None
    notes: str | None = None
    trust_level: str = "proposed"


class UnitDesignationResponse(BaseModel):
    id: uuid.UUID
    abbreviation: str
    full_name: str
    unit_type: str | None
    parent_unit_id: uuid.UUID | None
    trust_level: str

    model_config = {"from_attributes": True}


class AircraftTypeCreate(BaseModel):
    designation: str
    manufacturer: str | None = None
    common_name: str | None = None
    variants: dict | None = None
    trust_level: str = "proposed"


class AircraftTypeResponse(BaseModel):
    id: uuid.UUID
    designation: str
    manufacturer: str | None
    common_name: str | None
    variants: dict | None
    trust_level: str

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create knowledge API router**

`backend/app/api/knowledge.py`:
```python
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Glossary, UnitDesignation, AircraftType, KnowledgeReview
from app.schemas.knowledge import (
    GlossaryCreate, GlossaryList, GlossaryResponse, ReviewAction,
    UnitDesignationCreate, UnitDesignationResponse,
    AircraftTypeCreate, AircraftTypeResponse,
)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


# --- Glossary ---

@router.get("/glossary", response_model=GlossaryList)
async def list_glossary(
    trust_level: str | None = None,
    category: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    query = select(Glossary)
    if trust_level:
        query = query.where(Glossary.trust_level == trust_level)
    if category:
        query = query.where(Glossary.category == category)
    result = await session.execute(query.order_by(Glossary.term))
    entries = result.scalars().all()
    return GlossaryList(entries=entries, total=len(entries))


@router.post("/glossary", response_model=GlossaryResponse, status_code=201)
async def create_glossary_entry(data: GlossaryCreate, session: AsyncSession = Depends(get_session)):
    entry = Glossary(**data.model_dump())
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


@router.post("/glossary/{entry_id}/review", response_model=GlossaryResponse)
async def review_glossary_entry(
    entry_id: uuid.UUID,
    review: ReviewAction,
    session: AsyncSession = Depends(get_session),
):
    entry = await session.get(Glossary, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Glossary entry not found")

    old_level = entry.trust_level
    new_level = {"approve": "verified", "reject": "ai_suggested", "demote": "proposed"}.get(review.action)
    if not new_level:
        raise HTTPException(status_code=400, detail=f"Invalid action: {review.action}")

    entry.trust_level = new_level
    if review.action == "approve":
        entry.verified_at = datetime.now(timezone.utc)

    # Audit trail
    kr = KnowledgeReview(
        entity_type="glossary",
        entity_id=entry_id,
        action=review.action,
        old_trust_level=old_level,
        new_trust_level=new_level,
        reviewer=uuid.UUID("00000000-0000-0000-0000-000000000001"),  # Default admin in V1
        reason=review.reason,
    )
    session.add(kr)
    await session.commit()
    await session.refresh(entry)
    return entry


# --- Unit Designations ---

@router.get("/units", response_model=list[UnitDesignationResponse])
async def list_units(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(UnitDesignation).order_by(UnitDesignation.abbreviation))
    return result.scalars().all()


@router.post("/units", response_model=UnitDesignationResponse, status_code=201)
async def create_unit(data: UnitDesignationCreate, session: AsyncSession = Depends(get_session)):
    unit = UnitDesignation(**data.model_dump())
    session.add(unit)
    await session.commit()
    await session.refresh(unit)
    return unit


# --- Aircraft Types ---

@router.get("/aircraft", response_model=list[AircraftTypeResponse])
async def list_aircraft(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(AircraftType).order_by(AircraftType.designation))
    return result.scalars().all()


@router.post("/aircraft", response_model=AircraftTypeResponse, status_code=201)
async def create_aircraft(data: AircraftTypeCreate, session: AsyncSession = Depends(get_session)):
    aircraft = AircraftType(**data.model_dump())
    session.add(aircraft)
    await session.commit()
    await session.refresh(aircraft)
    return aircraft
```

- [ ] **Step 3: Register router in main.py**

```python
from app.api.knowledge import router as knowledge_router
app.include_router(knowledge_router)
```

- [ ] **Step 4: Write API tests**

`backend/tests/test_api_knowledge.py`:
```python
async def test_glossary_crud(client):
    resp = await client.post("/api/knowledge/glossary", json={
        "term": "Bruchlandung",
        "definition": "Crash landing",
        "category": "incident_type",
    })
    assert resp.status_code == 201
    entry_id = resp.json()["id"]
    assert resp.json()["trust_level"] == "proposed"

    resp = await client.get("/api/knowledge/glossary")
    assert resp.json()["total"] == 1

    resp = await client.get("/api/knowledge/glossary?category=incident_type")
    assert resp.json()["total"] == 1

    # Approve
    resp = await client.post(f"/api/knowledge/glossary/{entry_id}/review", json={
        "action": "approve",
        "reason": "Confirmed by domain expert",
    })
    assert resp.json()["trust_level"] == "verified"
    assert resp.json()["verified_at"] is not None


async def test_unit_designations_crud(client):
    resp = await client.post("/api/knowledge/units", json={
        "abbreviation": "JG 54",
        "full_name": "Jagdgeschwader 54",
        "unit_type": "Geschwader",
    })
    assert resp.status_code == 201

    resp = await client.get("/api/knowledge/units")
    assert len(resp.json()) == 1


async def test_aircraft_types_crud(client):
    resp = await client.post("/api/knowledge/aircraft", json={
        "designation": "Bf 109 G-4",
        "manufacturer": "Messerschmitt",
    })
    assert resp.status_code == 201

    resp = await client.get("/api/knowledge/aircraft")
    assert len(resp.json()) == 1
```

- [ ] **Step 5: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: knowledge base CRUD API with review workflow and audit trail"
```

---

### Task 11: Seed Knowledge Data

**Files:**
- Create: `docs/glossary-seed.csv`
- Create: `scripts/seed_knowledge.py`

- [ ] **Step 1: Create glossary-seed.csv with common Luftwaffe abbreviations**

`docs/glossary-seed.csv`:
```csv
term,definition,category
Bruchlandung,Crash landing,incident_type
Notlandung,Emergency landing,incident_type
Luftkampf,Aerial combat,incident_type
Feindberührung,Enemy contact,incident_type
Motorschaden,Engine damage,incident_type
Fahrwerkschaden,Landing gear damage,incident_type
Bodenunfall,Ground accident,incident_type
Startunfall,Take-off accident,incident_type
Landeunfall,Landing accident,incident_type
Flakbeschuss,Anti-aircraft fire,incident_type
gefallen,Killed in action,fate
verwundet,Wounded,fate
vermisst,Missing,fate
unverletzt,Uninjured,fate
tot,Dead,fate
in Gefangenschaft,Captured / POW,fate
Obst.,Oberst (Colonel),rank
Obstlt.,Oberstleutnant (Lieutenant Colonel),rank
Maj.,Major,rank
Hptm.,Hauptmann (Captain),rank
Oblt.,Oberleutnant (First Lieutenant),rank
Lt.,Leutnant (Second Lieutenant),rank
Ofw.,Oberfeldwebel (Master Sergeant),rank
Fw.,Feldwebel (Sergeant),rank
Uffz.,Unteroffizier (Corporal),rank
Ogefr.,Obergefreiter (Senior Private),rank
Gefr.,Gefreiter (Private First Class),rank
Fl.Fl.,Flugfeld (Airfield),location
JG,Jagdgeschwader (Fighter Wing),unit_type
KG,Kampfgeschwader (Bomber Wing),unit_type
StG,Sturzkampfgeschwader (Dive Bomber Wing),unit_type
ZG,Zerstörergeschwader (Destroyer Wing),unit_type
NJG,Nachtjagdgeschwader (Night Fighter Wing),unit_type
SG,Schlachtgeschwader (Ground Attack Wing),unit_type
TG,Transportgeschwader (Transport Wing),unit_type
Aufkl.Gr.,Aufklärungsgruppe (Reconnaissance Group),unit_type
Bf 109,Messerschmitt Bf 109 single-engine fighter,aircraft
Bf 110,Messerschmitt Bf 110 twin-engine heavy fighter,aircraft
Fw 190,Focke-Wulf Fw 190 single-engine fighter,aircraft
Ju 87,Junkers Ju 87 Stuka dive bomber,aircraft
Ju 88,Junkers Ju 88 medium bomber/night fighter,aircraft
He 111,Heinkel He 111 medium bomber,aircraft
Do 217,Dornier Do 217 bomber,aircraft
Me 262,Messerschmitt Me 262 jet fighter,aircraft
Me 410,Messerschmitt Me 410 heavy fighter,aircraft
Ju 52,Junkers Ju 52 transport aircraft,aircraft
```

- [ ] **Step 2: Create seed script**

`scripts/seed_knowledge.py`:
```python
"""Seed the knowledge base with common Luftwaffe abbreviations."""
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select
from app.db.database import SessionLocal
from app.db.models import Glossary, User


async def seed():
    async with SessionLocal() as session:
        # Create default admin user if not exists
        result = await session.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(username="admin", role="admin")
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            print(f"Created admin user: {admin.id}")

        # Load glossary seed
        csv_path = Path(__file__).parent.parent / "docs" / "glossary-seed.csv"
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                existing = await session.execute(
                    select(Glossary).where(Glossary.term == row["term"])
                )
                if existing.scalar_one_or_none():
                    continue

                entry = Glossary(
                    term=row["term"],
                    definition=row["definition"],
                    category=row["category"],
                    trust_level="verified",
                    source="Initial seed data",
                    proposed_by=admin.id,
                    verified_by=admin.id,
                )
                session.add(entry)
                count += 1

            await session.commit()
            print(f"Seeded {count} glossary entries")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 3: Run seed script**

```bash
cd ~/projects/luftarchiv
python scripts/seed_knowledge.py
```
Expected: "Created admin user: ...", "Seeded ~45 glossary entries"

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: seed knowledge base with common Luftwaffe abbreviations"
```

---

### Task 12: Embedding Service

**Files:**
- Create: `backend/app/services/embeddings.py`
- Create: `backend/tests/test_embeddings.py`

- [ ] **Step 1: Write failing test**

`backend/tests/test_embeddings.py`:
```python
from app.services.embeddings import generate_record_summary, generate_embedding


def test_generate_record_summary():
    summary = generate_record_summary(
        date="1943-03-15",
        aircraft_type="Bf 109 G-4",
        werknummer="19241",
        unit_designation="II./JG 54",
        incident_type="Bruchlandung",
        damage_percentage=40,
        location="Krasnogvardeisk",
        personnel=[{"rank_full": "Unteroffizier", "surname": "Schmidt", "fate_english": "uninjured"}],
        glossary={"Bruchlandung": "crash landing"},
    )
    assert "1943-03-15" in summary
    assert "crash landing" in summary
    assert "Schmidt" in summary


async def test_generate_embedding():
    text = "A Bf 109 crash landed at an airfield"
    embedding = await generate_embedding(text)
    assert len(embedding) == 1024
    assert isinstance(embedding[0], float)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_embeddings.py -v
```

- [ ] **Step 3: Implement embeddings.py**

```python
import asyncio
from functools import lru_cache

from fastembed import TextEmbedding


@lru_cache(maxsize=1)
def _get_model():
    return TextEmbedding("BAAI/bge-large-en-v1.5")


def generate_record_summary(
    date: str | None = None,
    aircraft_type: str | None = None,
    werknummer: str | None = None,
    unit_designation: str | None = None,
    incident_type: str | None = None,
    damage_percentage: int | None = None,
    location: str | None = None,
    personnel: list[dict] | None = None,
    glossary: dict[str, str] | None = None,
) -> str:
    """Generate a natural language summary of a record for embedding."""
    glossary = glossary or {}

    # Resolve incident type if in glossary
    incident_desc = glossary.get(incident_type, incident_type) if incident_type else "unknown incident"

    parts = []
    if date:
        parts.append(f"On {date}")
    if aircraft_type:
        parts.append(f"a {aircraft_type}")
        if werknummer:
            parts.append(f"(WNr {werknummer})")
    if unit_designation:
        parts.append(f"from {unit_designation}")
    parts.append(f"experienced {incident_desc}")
    if location:
        parts.append(f"at {location}")

    summary = " ".join(parts) + "."

    if damage_percentage is not None:
        summary += f" {damage_percentage}% damage."

    if personnel:
        people_parts = []
        for p in personnel:
            rank = p.get("rank_full", "")
            name = p.get("surname", "unknown")
            fate = p.get("fate_english", "unknown fate")
            people_parts.append(f"{rank} {name} — {fate}".strip())
        summary += " Personnel: " + "; ".join(people_parts) + "."

    return summary


async def generate_embedding(text: str) -> list[float]:
    """Generate a 1024-dim embedding for the given text."""
    loop = asyncio.get_event_loop()

    def _embed():
        model = _get_model()
        embeddings = list(model.embed([text]))
        return embeddings[0].tolist()

    return await loop.run_in_executor(None, _embed)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_embeddings.py -v
```
Expected: PASS (first run may download the model)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: embedding service with fastembed and record summary generation"
```

---

### Task 13: Search Service & API

**Files:**
- Create: `backend/app/services/search.py`
- Create: `backend/app/schemas/search.py`
- Create: `backend/app/api/search.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_search.py`

- [ ] **Step 1: Create search schemas**

`backend/app/schemas/search.py`:
```python
import uuid
from datetime import date

from pydantic import BaseModel


class SearchFilters(BaseModel):
    query: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    unit: str | None = None
    aircraft_type: str | None = None
    incident_type: str | None = None
    personnel_name: str | None = None
    mode: str = "direct"  # direct / semantic / analytical


class PersonnelResult(BaseModel):
    rank_abbreviation: str | None
    rank_full: str | None
    surname: str | None
    first_name: str | None
    fate: str | None
    fate_english: str | None

    model_config = {"from_attributes": True}


class RecordResult(BaseModel):
    id: uuid.UUID
    page_id: uuid.UUID
    entry_number: int | None
    date: date | None
    unit_designation: str | None
    aircraft_type: str | None
    werknummer: str | None
    incident_type: str | None
    incident_description: str | None
    damage_percentage: int | None
    location: str | None
    personnel: list[PersonnelResult]

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    results: list[RecordResult]
    total: int
    mode: str
    ai_summary: str | None = None
```

- [ ] **Step 2: Implement search service**

`backend/app/services/search.py`:
```python
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Record, Personnel
from app.schemas.search import SearchFilters
from app.services.embeddings import generate_embedding


async def direct_search(session: AsyncSession, filters: SearchFilters) -> list[Record]:
    """SQL-based direct search with field filters."""
    query = select(Record).options(selectinload(Record.personnel))
    conditions = []

    if filters.date_from:
        conditions.append(Record.date >= filters.date_from)
    if filters.date_to:
        conditions.append(Record.date <= filters.date_to)
    if filters.unit:
        conditions.append(Record.unit_designation.ilike(f"%{filters.unit}%"))
    if filters.aircraft_type:
        conditions.append(Record.aircraft_type.ilike(f"%{filters.aircraft_type}%"))
    if filters.incident_type:
        conditions.append(Record.incident_type.ilike(f"%{filters.incident_type}%"))
    if filters.query:
        # Full-text search across multiple fields
        q = f"%{filters.query}%"
        conditions.append(or_(
            Record.unit_designation.ilike(q),
            Record.aircraft_type.ilike(q),
            Record.incident_type.ilike(q),
            Record.location.ilike(q),
            Record.raw_text_original.ilike(q),
        ))
    if filters.personnel_name:
        query = query.join(Record.personnel)
        name = f"%{filters.personnel_name}%"
        conditions.append(or_(
            Personnel.surname.ilike(name),
            Personnel.first_name.ilike(name),
        ))

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(Record.date, Record.entry_number).limit(200)
    result = await session.execute(query)
    return result.scalars().unique().all()


async def semantic_search(session: AsyncSession, query_text: str, limit: int = 50) -> list[Record]:
    """Vector similarity search using pgvector."""
    query_embedding = await generate_embedding(query_text)

    result = await session.execute(
        select(Record)
        .options(selectinload(Record.personnel))
        .where(Record.search_embedding.isnot(None))
        .order_by(Record.search_embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    return result.scalars().unique().all()
```

- [ ] **Step 3: Create search API**

`backend/app/api/search.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.schemas.search import SearchFilters, SearchResponse, RecordResult
from app.services.search import direct_search, semantic_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(filters: SearchFilters, session: AsyncSession = Depends(get_session)):
    if filters.mode == "semantic" and filters.query:
        records = await semantic_search(session, filters.query)
    else:
        records = await direct_search(session, filters)

    return SearchResponse(
        results=[RecordResult.model_validate(r) for r in records],
        total=len(records),
        mode=filters.mode,
    )
```

- [ ] **Step 4: Register router in main.py**

```python
from app.api.search import router as search_router
app.include_router(search_router)
```

- [ ] **Step 5: Write search tests**

`backend/tests/test_search.py`:
```python
from datetime import date

from app.db.models import Collection, Page, Record, Personnel
from app.services.search import direct_search
from app.schemas.search import SearchFilters


async def _create_test_records(db_session):
    collection = Collection(name="Test", status="complete", page_count=1)
    db_session.add(collection)
    await db_session.commit()

    page = Page(collection_id=collection.id, page_number=1, image_path="/test.jpg")
    db_session.add(page)
    await db_session.commit()

    r1 = Record(
        page_id=page.id, entry_number=1, date=date(1943, 3, 15),
        unit_designation="II./JG 54", aircraft_type="Bf 109 G-4",
        incident_type="Bruchlandung", damage_percentage=40,
    )
    r2 = Record(
        page_id=page.id, entry_number=2, date=date(1943, 4, 1),
        unit_designation="I./KG 55", aircraft_type="Ju 88 A-4",
        incident_type="Luftkampf", damage_percentage=100,
    )
    db_session.add_all([r1, r2])
    await db_session.commit()

    p1 = Personnel(record_id=r1.id, surname="Schmidt", fate="unverletzt", fate_english="uninjured")
    p2 = Personnel(record_id=r2.id, surname="Müller", fate="gefallen", fate_english="killed")
    db_session.add_all([p1, p2])
    await db_session.commit()
    return r1, r2


async def test_direct_search_by_unit(db_session):
    r1, r2 = await _create_test_records(db_session)
    results = await direct_search(db_session, SearchFilters(unit="JG 54"))
    assert len(results) == 1
    assert results[0].unit_designation == "II./JG 54"


async def test_direct_search_by_date_range(db_session):
    await _create_test_records(db_session)
    results = await direct_search(db_session, SearchFilters(
        date_from=date(1943, 3, 1), date_to=date(1943, 3, 31)
    ))
    assert len(results) == 1


async def test_direct_search_by_personnel_name(db_session):
    await _create_test_records(db_session)
    results = await direct_search(db_session, SearchFilters(personnel_name="Müller"))
    assert len(results) == 1
    assert results[0].personnel[0].surname == "Müller"


async def test_direct_search_by_query(db_session):
    await _create_test_records(db_session)
    results = await direct_search(db_session, SearchFilters(query="Bf 109"))
    assert len(results) == 1
```

- [ ] **Step 6: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: search service with direct and semantic search, plus API"
```

---

### Task 14: Export Service

**Files:**
- Create: `backend/app/services/export.py`
- Create: `backend/app/api/export.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_export.py`

- [ ] **Step 1: Write failing test**

`backend/tests/test_export.py`:
```python
import csv
import io
from datetime import date

from app.db.models import Collection, Page, Record, Personnel
from app.services.export import export_records_to_csv


async def test_export_to_csv(db_session):
    collection = Collection(name="Test", status="complete", page_count=1)
    db_session.add(collection)
    await db_session.commit()

    page = Page(collection_id=collection.id, page_number=1, image_path="/test.jpg")
    db_session.add(page)
    await db_session.commit()

    record = Record(
        page_id=page.id, entry_number=1, date=date(1943, 3, 15),
        unit_designation="II./JG 54", aircraft_type="Bf 109 G-4",
        incident_type="Bruchlandung", damage_percentage=40,
    )
    db_session.add(record)
    await db_session.commit()

    p = Personnel(record_id=record.id, rank_abbreviation="Uffz.", surname="Schmidt", fate_english="uninjured")
    db_session.add(p)
    await db_session.commit()

    csv_content = await export_records_to_csv(db_session, collection.id)

    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["unit_designation"] == "II./JG 54"
    assert rows[0]["personnel_1_surname"] == "Schmidt"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_export.py -v
```

- [ ] **Step 3: Implement export service**

`backend/app/services/export.py`:
```python
import csv
import io
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Record


async def export_records_to_csv(session: AsyncSession, collection_id: uuid.UUID) -> str:
    """Export all records in a collection to CSV format."""
    result = await session.execute(
        select(Record)
        .join(Record.page)
        .where(Record.page.has(collection_id=collection_id))
        .options(selectinload(Record.personnel))
        .order_by(Record.date, Record.entry_number)
    )
    records = result.scalars().unique().all()

    # Determine max personnel per record for column headers
    max_personnel = max((len(r.personnel) for r in records), default=0)

    output = io.StringIO()
    base_fields = [
        "entry_number", "date", "unit_designation", "aircraft_type",
        "werknummer", "incident_type", "incident_description",
        "damage_percentage", "location",
    ]
    personnel_fields = []
    for i in range(1, max_personnel + 1):
        personnel_fields.extend([
            f"personnel_{i}_rank", f"personnel_{i}_surname",
            f"personnel_{i}_first_name", f"personnel_{i}_fate",
        ])

    writer = csv.DictWriter(output, fieldnames=base_fields + personnel_fields)
    writer.writeheader()

    for record in records:
        row = {f: getattr(record, f, None) for f in base_fields}
        if row["date"]:
            row["date"] = str(row["date"])
        for i, person in enumerate(record.personnel, start=1):
            row[f"personnel_{i}_rank"] = person.rank_abbreviation
            row[f"personnel_{i}_surname"] = person.surname
            row[f"personnel_{i}_first_name"] = person.first_name
            row[f"personnel_{i}_fate"] = person.fate_english
        writer.writerow(row)

    return output.getvalue()
```

- [ ] **Step 4: Create export API endpoint**

`backend/app/api/export.py`:
```python
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.services.export import export_records_to_csv

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/{collection_id}/csv")
async def export_csv(collection_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    csv_content = await export_records_to_csv(session, collection_id)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=luftarchiv_{collection_id}.csv"},
    )
```

Register in main.py:
```python
from app.api.export import router as export_router
app.include_router(export_router)
```

- [ ] **Step 5: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: CSV export service for collection records"
```

---

## Phase 4: Frontend

### Task 15: Frontend Scaffolding

**Files:**
- Create: `frontend/` (Vite + React + TS project)
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/App.tsx`
- Create: `frontend/tailwind.config.ts` (or CSS import for v4)

- [ ] **Step 1: Scaffold Vite project**

```bash
cd ~/projects/luftarchiv
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss @tailwindcss/vite
npm install react-router-dom @tanstack/react-table recharts openseadragon
```

- [ ] **Step 2: Configure TailwindCSS v4**

Update `frontend/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 3001, proxy: { '/api': 'http://localhost:8000' } },
})
```

Replace `frontend/src/index.css`:
```css
@import "tailwindcss";

@theme {
  --color-ivory: #FDFAF5;
  --color-parchment: #F5F0E8;
  --color-slate-ink: #1E293B;
  --color-archive-amber: #92400E;
  --color-archive-amber-light: #D97706;
  --color-trust-verified: #059669;
  --color-trust-proposed: #D97706;
  --color-trust-ai: #6366F1;
  --font-heading: 'Playfair Display', Georgia, serif;
  --font-body: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
```

- [ ] **Step 3: Create API client**

`frontend/src/api/client.ts`:
```typescript
const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  // Collections
  listCollections: () => request<any>('/collections'),
  getCollection: (id: string) => request<any>(`/collections/${id}`),
  importFolder: (data: any) => request<any>('/import', { method: 'POST', body: JSON.stringify(data) }),
  startExtraction: (id: string, stage: string) =>
    request<any>(`/collections/${id}/extract?stage=${stage}`, { method: 'POST' }),

  // Search
  search: (filters: any) => request<any>('/search', { method: 'POST', body: JSON.stringify(filters) }),

  // Knowledge
  listGlossary: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return request<any>(`/knowledge/glossary${qs}`);
  },
  reviewGlossary: (id: string, action: any) =>
    request<any>(`/knowledge/glossary/${id}/review`, { method: 'POST', body: JSON.stringify(action) }),

  // Export
  exportCsv: (collectionId: string) => `${BASE_URL}/export/${collectionId}/csv`,
};
```

- [ ] **Step 4: Set up App.tsx with routing**

`frontend/src/App.tsx`:
```tsx
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Collections from './pages/Collections';
import DocumentViewer from './pages/DocumentViewer';
import Search from './pages/Search';
import Knowledge from './pages/Knowledge';
import Analytics from './pages/Analytics';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-ivory">
        <nav className="border-b border-parchment bg-white/80 backdrop-blur-sm sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-6 flex items-center h-14 gap-8">
            <h1 className="font-heading text-xl font-bold text-slate-ink tracking-tight">
              Luftarchiv
            </h1>
            <div className="flex gap-6 text-sm font-body">
              {[
                ['/', 'Collections'],
                ['/search', 'Search'],
                ['/knowledge', 'Knowledge'],
                ['/analytics', 'Analytics'],
              ].map(([path, label]) => (
                <NavLink
                  key={path}
                  to={path}
                  className={({ isActive }) =>
                    `py-1 border-b-2 transition-colors ${
                      isActive
                        ? 'border-archive-amber text-archive-amber'
                        : 'border-transparent text-slate-ink/60 hover:text-slate-ink'
                    }`
                  }
                >
                  {label}
                </NavLink>
              ))}
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<Collections />} />
            <Route path="/viewer/:collectionId" element={<DocumentViewer />} />
            <Route path="/viewer/:collectionId/:pageNumber" element={<DocumentViewer />} />
            <Route path="/search" element={<Search />} />
            <Route path="/knowledge" element={<Knowledge />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
```

- [ ] **Step 5: Create placeholder pages**

Create each of these with a minimal placeholder:

`frontend/src/pages/Collections.tsx`:
```tsx
export default function Collections() {
  return <div className="font-heading text-2xl text-slate-ink">Collections</div>;
}
```

Same pattern for `DocumentViewer.tsx`, `Search.tsx`, `Knowledge.tsx`, `Analytics.tsx`.

- [ ] **Step 6: Verify dev server runs**

```bash
cd ~/projects/luftarchiv/frontend
npm run dev
```
Open http://localhost:3001 — should see "Luftarchiv" nav with routing working.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: frontend scaffolding with Vite, TailwindCSS v4, routing, and API client"
```

---

### Task 16: Collections Page

**Files:**
- Modify: `frontend/src/pages/Collections.tsx`

- [ ] **Step 1: Implement Collections page with cards**

`frontend/src/pages/Collections.tsx`:
```tsx
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';

interface Collection {
  id: string;
  name: string;
  source_reference: string | null;
  description: string | null;
  document_type: string | null;
  page_count: number;
  status: string;
  created_at: string;
}

export default function Collections() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listCollections().then((data: any) => {
      setCollections(data.collections);
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="text-slate-ink/50 font-body">Loading...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h2 className="font-heading text-3xl text-slate-ink">Collections</h2>
      </div>

      {collections.length === 0 ? (
        <div className="text-center py-16 text-slate-ink/40 font-body">
          <p className="text-lg">No collections yet.</p>
          <p className="text-sm mt-2">Import a folder of scanned documents to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {collections.map((c) => (
            <Link
              key={c.id}
              to={`/viewer/${c.id}`}
              className="block bg-white rounded-lg border border-parchment p-6 hover:shadow-md transition-shadow"
            >
              <h3 className="font-heading text-lg text-slate-ink font-semibold">{c.name}</h3>
              {c.source_reference && (
                <p className="text-sm text-slate-ink/50 font-mono mt-1">{c.source_reference}</p>
              )}
              {c.description && (
                <p className="text-sm text-slate-ink/70 mt-2 font-body">{c.description}</p>
              )}
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-parchment">
                <span className="text-sm text-slate-ink/50 font-body">{c.page_count} pages</span>
                <span
                  className={`text-xs font-body px-2 py-0.5 rounded-full ${
                    c.status === 'complete'
                      ? 'bg-trust-verified/10 text-trust-verified'
                      : c.status === 'processing'
                      ? 'bg-trust-proposed/10 text-trust-proposed'
                      : 'bg-slate-ink/5 text-slate-ink/50'
                  }`}
                >
                  {c.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser**

Start backend + frontend. If no collections exist yet, should show the empty state.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: Collections page with card grid and status indicators"
```

---

### Task 17: Document Viewer Page

**Files:**
- Modify: `frontend/src/pages/DocumentViewer.tsx`
- Create: `frontend/src/components/ScanViewer.tsx`
- Create: `frontend/src/components/RecordCard.tsx`
- Create: `frontend/src/components/KnowledgePanel.tsx`

This is the most complex UI component. The implementation should be built incrementally — start with a working split-pane layout, then add image zoom, record highlighting, and the knowledge panel.

- [ ] **Step 1: Create ScanViewer component**

`frontend/src/components/ScanViewer.tsx`:
```tsx
import { useEffect, useRef } from 'react';
import OpenSeadragon from 'openseadragon';

interface ScanViewerProps {
  imagePath: string;
  highlightRegions?: Array<{ x: number; y: number; w: number; h: number }>;
}

export default function ScanViewer({ imagePath, highlightRegions }: ScanViewerProps) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const osdRef = useRef<OpenSeadragon.Viewer | null>(null);

  useEffect(() => {
    if (!viewerRef.current) return;

    osdRef.current = OpenSeadragon({
      element: viewerRef.current,
      tileSources: {
        type: 'image',
        url: `/api/pages/image?path=${encodeURIComponent(imagePath)}`,
      },
      showNavigationControl: true,
      navigationControlAnchor: OpenSeadragon.ControlAnchor.TOP_LEFT,
      minZoomLevel: 0.5,
      maxZoomLevel: 5,
      visibilityRatio: 0.8,
    });

    return () => {
      osdRef.current?.destroy();
    };
  }, [imagePath]);

  return (
    <div ref={viewerRef} className="w-full h-full bg-parchment/50 rounded" />
  );
}
```

- [ ] **Step 2: Create RecordCard component**

`frontend/src/components/RecordCard.tsx`:
```tsx
interface Personnel {
  rank_abbreviation: string | null;
  surname: string | null;
  first_name: string | null;
  fate_english: string | null;
}

interface RecordCardProps {
  record: {
    entry_number: number | null;
    date: string | null;
    unit_designation: string | null;
    aircraft_type: string | null;
    werknummer: string | null;
    incident_type: string | null;
    damage_percentage: number | null;
    personnel: Personnel[];
  };
  isSelected: boolean;
  onClick: () => void;
}

export default function RecordCard({ record, isSelected, onClick }: RecordCardProps) {
  return (
    <div
      onClick={onClick}
      className={`p-4 rounded border cursor-pointer transition-colors ${
        isSelected
          ? 'border-archive-amber bg-archive-amber/5'
          : 'border-parchment bg-white hover:border-archive-amber/30'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-xs text-slate-ink/40">#{record.entry_number}</span>
        <span className="text-sm text-slate-ink/70 font-body">{record.date}</span>
      </div>
      <div className="space-y-1">
        {record.unit_designation && (
          <p className="text-sm font-semibold text-slate-ink font-body">{record.unit_designation}</p>
        )}
        <div className="flex items-center gap-2 text-sm text-slate-ink/70 font-body">
          {record.aircraft_type && <span>{record.aircraft_type}</span>}
          {record.werknummer && <span className="font-mono text-xs">WNr {record.werknummer}</span>}
        </div>
        {record.incident_type && (
          <p className="text-sm text-slate-ink/60 italic font-body">{record.incident_type}</p>
        )}
        {record.damage_percentage != null && (
          <div className="flex items-center gap-2">
            <div className="h-1.5 flex-1 bg-parchment rounded overflow-hidden">
              <div
                className="h-full bg-archive-amber rounded"
                style={{ width: `${record.damage_percentage}%` }}
              />
            </div>
            <span className="text-xs text-slate-ink/50 font-mono">{record.damage_percentage}%</span>
          </div>
        )}
      </div>
      {record.personnel.length > 0 && (
        <div className="mt-3 pt-2 border-t border-parchment space-y-1">
          {record.personnel.map((p, i) => (
            <div key={i} className="flex items-center justify-between text-xs font-body">
              <span className="text-slate-ink/80">
                {p.rank_abbreviation} {p.surname}{p.first_name ? `, ${p.first_name}` : ''}
              </span>
              <span
                className={`px-1.5 py-0.5 rounded ${
                  p.fate_english === 'killed'
                    ? 'bg-red-50 text-red-700'
                    : p.fate_english === 'wounded'
                    ? 'bg-amber-50 text-amber-700'
                    : p.fate_english === 'missing'
                    ? 'bg-purple-50 text-purple-700'
                    : 'bg-green-50 text-green-700'
                }`}
              >
                {p.fate_english}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create KnowledgePanel component**

`frontend/src/components/KnowledgePanel.tsx`:
```tsx
import { useEffect, useState } from 'react';
import { api } from '../api/client';

interface GlossaryEntry {
  id: string;
  term: string;
  definition: string;
  trust_level: string;
}

export default function KnowledgePanel({ terms }: { terms: string[] }) {
  const [entries, setEntries] = useState<GlossaryEntry[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    api.listGlossary().then((data: any) => {
      const relevant = data.entries.filter((e: GlossaryEntry) =>
        terms.some((t) => e.term.toLowerCase() === t.toLowerCase())
      );
      setEntries(relevant);
    });
  }, [terms]);

  if (entries.length === 0) return null;

  const trustBadge = (level: string) => {
    const styles: Record<string, string> = {
      verified: 'text-trust-verified',
      proposed: 'text-trust-proposed',
      ai_suggested: 'text-trust-ai',
    };
    const labels: Record<string, string> = {
      verified: 'Verified',
      proposed: 'Proposed',
      ai_suggested: 'AI',
    };
    return <span className={`text-xs ${styles[level]}`}>{labels[level]}</span>;
  };

  return (
    <div className="border-t border-parchment bg-white/50">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2 flex items-center justify-between text-sm text-slate-ink/60 hover:text-slate-ink font-body"
      >
        <span>Knowledge ({entries.length} terms)</span>
        <span>{expanded ? 'Hide' : 'Show'}</span>
      </button>
      {expanded && (
        <div className="px-4 pb-3 grid grid-cols-2 gap-2">
          {entries.map((e) => (
            <div key={e.id} className="flex items-center gap-2 text-sm font-body">
              <span className="font-mono text-slate-ink/70">{e.term}</span>
              <span className="text-slate-ink/40">→</span>
              <span className="text-slate-ink/80">{e.definition}</span>
              {trustBadge(e.trust_level)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Implement DocumentViewer page**

`frontend/src/pages/DocumentViewer.tsx`:
```tsx
import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import ScanViewer from '../components/ScanViewer';
import RecordCard from '../components/RecordCard';
import KnowledgePanel from '../components/KnowledgePanel';

export default function DocumentViewer() {
  const { collectionId, pageNumber } = useParams();
  const [collection, setCollection] = useState<any>(null);
  const [pages, setPages] = useState<any[]>([]);
  const [currentPage, setCurrentPage] = useState<any>(null);
  const [records, setRecords] = useState<any[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<string | null>(null);
  const pageNum = parseInt(pageNumber || '1');

  useEffect(() => {
    if (!collectionId) return;
    api.getCollection(collectionId).then(setCollection);
    // Fetch pages list and current page records
    // These endpoints will need to be added to the backend
    fetch(`/api/collections/${collectionId}/pages`).then(r => r.json()).then(setPages);
  }, [collectionId]);

  useEffect(() => {
    if (!collectionId) return;
    fetch(`/api/collections/${collectionId}/pages/${pageNum}/records`)
      .then(r => r.json())
      .then(data => {
        setCurrentPage(data.page);
        setRecords(data.records);
      });
  }, [collectionId, pageNum]);

  // Extract unique terms from records for knowledge panel
  const terms = [...new Set(records.flatMap((r: any) => [
    r.incident_type, r.unit_designation,
    ...r.personnel.map((p: any) => p.rank_abbreviation),
  ].filter(Boolean)))];

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <Link to="/" className="text-sm text-slate-ink/50 hover:text-slate-ink font-body">
            ← Collections
          </Link>
          <h2 className="font-heading text-xl text-slate-ink">{collection?.name}</h2>
        </div>
        <div className="flex items-center gap-2 font-body text-sm">
          <Link
            to={`/viewer/${collectionId}/${Math.max(1, pageNum - 1)}`}
            className="px-2 py-1 rounded border border-parchment hover:bg-parchment"
          >
            ←
          </Link>
          <span className="text-slate-ink/60">
            Page {pageNum} of {collection?.page_count || '?'}
          </span>
          <Link
            to={`/viewer/${collectionId}/${pageNum + 1}`}
            className="px-2 py-1 rounded border border-parchment hover:bg-parchment"
          >
            →
          </Link>
          <a
            href={api.exportCsv(collectionId || '')}
            className="ml-4 px-3 py-1 rounded bg-archive-amber text-white text-sm hover:bg-archive-amber/90"
          >
            Export CSV
          </a>
        </div>
      </div>

      {/* Split pane */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Left: Scan viewer */}
        <div className="flex-1 rounded-lg overflow-hidden border border-parchment">
          {currentPage?.image_path ? (
            <ScanViewer imagePath={currentPage.image_path} />
          ) : (
            <div className="flex items-center justify-center h-full text-slate-ink/30 font-body">
              No image loaded
            </div>
          )}
        </div>

        {/* Right: Records */}
        <div className="w-96 flex flex-col min-h-0">
          <h3 className="font-heading text-sm text-slate-ink/60 mb-3">
            Extracted Records ({records.length})
          </h3>
          <div className="flex-1 overflow-y-auto space-y-3 pr-1">
            {records.map((r: any) => (
              <RecordCard
                key={r.id}
                record={r}
                isSelected={selectedRecord === r.id}
                onClick={() => setSelectedRecord(r.id === selectedRecord ? null : r.id)}
              />
            ))}
            {records.length === 0 && (
              <p className="text-sm text-slate-ink/30 font-body text-center py-8">
                No records extracted yet
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Bottom: Knowledge panel */}
      <KnowledgePanel terms={terms} />
    </div>
  );
}
```

- [ ] **Step 5: Add missing backend endpoints for page listing and page records**

Add to `backend/app/api/collections.py`:
```python
from app.db.models import Record
from sqlalchemy.orm import selectinload


@router.get("/{collection_id}/pages")
async def list_pages(collection_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Page).where(Page.collection_id == collection_id).order_by(Page.page_number)
    )
    pages = result.scalars().all()
    return [{"id": str(p.id), "page_number": p.page_number, "ocr_status": p.ocr_status} for p in pages]


@router.get("/{collection_id}/pages/{page_number}/records")
async def get_page_records(collection_id: uuid.UUID, page_number: int, session: AsyncSession = Depends(get_session)):
    page_result = await session.execute(
        select(Page).where(Page.collection_id == collection_id, Page.page_number == page_number)
    )
    page = page_result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    records_result = await session.execute(
        select(Record)
        .where(Record.page_id == page.id)
        .options(selectinload(Record.personnel))
        .order_by(Record.entry_number)
    )
    records = records_result.scalars().all()

    return {
        "page": {"id": str(page.id), "image_path": page.image_path, "page_number": page.page_number},
        "records": [
            {
                "id": str(r.id),
                "entry_number": r.entry_number,
                "date": str(r.date) if r.date else None,
                "unit_designation": r.unit_designation,
                "aircraft_type": r.aircraft_type,
                "werknummer": r.werknummer,
                "incident_type": r.incident_type,
                "damage_percentage": r.damage_percentage,
                "personnel": [
                    {
                        "rank_abbreviation": p.rank_abbreviation,
                        "surname": p.surname,
                        "first_name": p.first_name,
                        "fate_english": p.fate_english,
                    }
                    for p in r.personnel
                ],
            }
            for r in records
        ],
    }
```

- [ ] **Step 6: Add image serving endpoint**

Add to `backend/app/api/collections.py`:
```python
from fastapi.responses import FileResponse


@router.get("/pages/image")
async def serve_image(path: str):
    image_path = Path(path)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)
```

Note: Move this to a dedicated `pages` router if the collections router becomes too large.

- [ ] **Step 7: Verify in browser**

Start both backend and frontend. Navigate to a collection, verify the split-pane layout renders.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: Document Viewer with split-pane scan viewer, record cards, and knowledge panel"
```

---

### Task 18: Search Page

**Files:**
- Modify: `frontend/src/pages/Search.tsx`
- Create: `frontend/src/components/SearchBar.tsx`
- Create: `frontend/src/components/RecordTable.tsx`

- [ ] **Step 1: Create SearchBar component**

`frontend/src/components/SearchBar.tsx`:
```tsx
import { useState } from 'react';

interface SearchBarProps {
  onSearch: (query: string, filters: Record<string, string>) => void;
}

export default function SearchBar({ onSearch }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<Record<string, string>>({});

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(query, filters);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search records... (unit, aircraft, name, or ask a question)"
          className="flex-1 px-4 py-2.5 rounded-lg border border-parchment bg-white font-body text-slate-ink placeholder:text-slate-ink/30 focus:outline-none focus:border-archive-amber"
        />
        <button
          type="submit"
          className="px-6 py-2.5 rounded-lg bg-archive-amber text-white font-body text-sm hover:bg-archive-amber/90"
        >
          Search
        </button>
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className="px-3 py-2.5 rounded-lg border border-parchment text-slate-ink/60 hover:bg-parchment font-body text-sm"
        >
          Filters
        </button>
      </div>
      {showFilters && (
        <div className="grid grid-cols-4 gap-3 p-4 rounded-lg bg-white border border-parchment">
          {['unit', 'aircraft_type', 'incident_type', 'personnel_name'].map((field) => (
            <input
              key={field}
              type="text"
              placeholder={field.replace('_', ' ')}
              value={filters[field] || ''}
              onChange={(e) => setFilters({ ...filters, [field]: e.target.value })}
              className="px-3 py-1.5 rounded border border-parchment text-sm font-body text-slate-ink placeholder:text-slate-ink/30 focus:outline-none focus:border-archive-amber"
            />
          ))}
          <input type="date" placeholder="From" onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
            className="px-3 py-1.5 rounded border border-parchment text-sm font-body" />
          <input type="date" placeholder="To" onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
            className="px-3 py-1.5 rounded border border-parchment text-sm font-body" />
        </div>
      )}
    </form>
  );
}
```

- [ ] **Step 2: Create RecordTable component**

`frontend/src/components/RecordTable.tsx`:
```tsx
import { Link } from 'react-router-dom';

interface Record {
  id: string;
  page_id: string;
  entry_number: number | null;
  date: string | null;
  unit_designation: string | null;
  aircraft_type: string | null;
  incident_type: string | null;
  damage_percentage: number | null;
  personnel: Array<{ surname: string | null; fate_english: string | null }>;
}

export default function RecordTable({ records }: { records: Record[] }) {
  if (records.length === 0) {
    return (
      <p className="text-center text-slate-ink/30 font-body py-12">No results</p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-parchment">
      <table className="w-full text-sm font-body">
        <thead>
          <tr className="bg-parchment/50 text-left text-slate-ink/60">
            <th className="px-4 py-2.5">#</th>
            <th className="px-4 py-2.5">Date</th>
            <th className="px-4 py-2.5">Unit</th>
            <th className="px-4 py-2.5">Aircraft</th>
            <th className="px-4 py-2.5">Incident</th>
            <th className="px-4 py-2.5">Damage</th>
            <th className="px-4 py-2.5">Personnel</th>
            <th className="px-4 py-2.5"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-parchment">
          {records.map((r) => (
            <tr key={r.id} className="hover:bg-ivory/50">
              <td className="px-4 py-2 font-mono text-slate-ink/40">{r.entry_number}</td>
              <td className="px-4 py-2 text-slate-ink/80">{r.date}</td>
              <td className="px-4 py-2 font-semibold text-slate-ink">{r.unit_designation}</td>
              <td className="px-4 py-2 text-slate-ink/80">{r.aircraft_type}</td>
              <td className="px-4 py-2 text-slate-ink/60 italic">{r.incident_type}</td>
              <td className="px-4 py-2 font-mono text-slate-ink/60">
                {r.damage_percentage != null ? `${r.damage_percentage}%` : ''}
              </td>
              <td className="px-4 py-2 text-slate-ink/70">
                {r.personnel.map((p) => p.surname).filter(Boolean).join(', ')}
              </td>
              <td className="px-4 py-2">
                <Link to={`/viewer/${r.page_id}`} className="text-archive-amber hover:underline text-xs">
                  View source
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 3: Implement Search page**

`frontend/src/pages/Search.tsx`:
```tsx
import { useState } from 'react';
import { api } from '../api/client';
import SearchBar from '../components/SearchBar';
import RecordTable from '../components/RecordTable';

export default function Search() {
  const [results, setResults] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (query: string, filters: Record<string, string>) => {
    setLoading(true);
    setSearched(true);
    try {
      const data = await api.search({
        query: query || undefined,
        mode: 'direct',
        ...Object.fromEntries(Object.entries(filters).filter(([_, v]) => v)),
      });
      setResults(data.results);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="font-heading text-3xl text-slate-ink">Search Records</h2>
      <SearchBar onSearch={handleSearch} />

      {loading && <p className="text-slate-ink/50 font-body">Searching...</p>}

      {searched && !loading && (
        <>
          <p className="text-sm text-slate-ink/50 font-body">{total} results</p>
          <RecordTable records={results} />
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: Search page with filters, result table, and source links"
```

---

### Task 19: Knowledge Manager Page

**Files:**
- Modify: `frontend/src/pages/Knowledge.tsx`
- Create: `frontend/src/components/ReviewQueue.tsx`

- [ ] **Step 1: Implement Knowledge page with tabs and review queue**

`frontend/src/pages/Knowledge.tsx`:
```tsx
import { useEffect, useState } from 'react';
import { api } from '../api/client';

interface GlossaryEntry {
  id: string;
  term: string;
  definition: string;
  category: string;
  trust_level: string;
}

export default function Knowledge() {
  const [entries, setEntries] = useState<GlossaryEntry[]>([]);
  const [filter, setFilter] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const load = () => {
    const params: Record<string, string> = {};
    if (filter) params.trust_level = filter;
    if (categoryFilter) params.category = categoryFilter;
    api.listGlossary(params).then((data: any) => setEntries(data.entries));
  };

  useEffect(load, [filter, categoryFilter]);

  const handleReview = async (id: string, action: string) => {
    await api.reviewGlossary(id, { action });
    load();
  };

  const trustBadge = (level: string) => {
    const styles: Record<string, string> = {
      verified: 'bg-trust-verified/10 text-trust-verified',
      proposed: 'bg-trust-proposed/10 text-trust-proposed',
      ai_suggested: 'bg-trust-ai/10 text-trust-ai',
    };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${styles[level]}`}>
        {level.replace('_', ' ')}
      </span>
    );
  };

  const categories = ['rank', 'unit_type', 'incident_type', 'aircraft', 'location', 'fate', 'other'];

  return (
    <div className="space-y-6">
      <h2 className="font-heading text-3xl text-slate-ink">Knowledge Base</h2>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {[null, 'verified', 'proposed', 'ai_suggested'].map((level) => (
          <button
            key={level || 'all'}
            onClick={() => setFilter(level)}
            className={`px-3 py-1.5 rounded-full text-sm font-body transition-colors ${
              filter === level
                ? 'bg-archive-amber text-white'
                : 'bg-parchment text-slate-ink/60 hover:text-slate-ink'
            }`}
          >
            {level ? level.replace('_', ' ') : 'All'}
          </button>
        ))}
        <span className="text-slate-ink/20 self-center">|</span>
        {[null, ...categories].map((cat) => (
          <button
            key={cat || 'all-cat'}
            onClick={() => setCategoryFilter(cat)}
            className={`px-3 py-1.5 rounded-full text-sm font-body transition-colors ${
              categoryFilter === cat
                ? 'bg-slate-ink text-white'
                : 'bg-parchment text-slate-ink/60 hover:text-slate-ink'
            }`}
          >
            {cat || 'All categories'}
          </button>
        ))}
      </div>

      {/* Entries table */}
      <div className="rounded-lg border border-parchment overflow-hidden">
        <table className="w-full text-sm font-body">
          <thead>
            <tr className="bg-parchment/50 text-left text-slate-ink/60">
              <th className="px-4 py-2.5">Term</th>
              <th className="px-4 py-2.5">Definition</th>
              <th className="px-4 py-2.5">Category</th>
              <th className="px-4 py-2.5">Trust</th>
              <th className="px-4 py-2.5">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-parchment">
            {entries.map((e) => (
              <tr key={e.id} className="hover:bg-ivory/50">
                <td className="px-4 py-2 font-mono text-slate-ink font-semibold">{e.term}</td>
                <td className="px-4 py-2 text-slate-ink/80">{e.definition}</td>
                <td className="px-4 py-2 text-slate-ink/50">{e.category}</td>
                <td className="px-4 py-2">{trustBadge(e.trust_level)}</td>
                <td className="px-4 py-2 space-x-2">
                  {e.trust_level !== 'verified' && (
                    <button
                      onClick={() => handleReview(e.id, 'approve')}
                      className="text-xs text-trust-verified hover:underline"
                    >
                      Approve
                    </button>
                  )}
                  {e.trust_level === 'verified' && (
                    <button
                      onClick={() => handleReview(e.id, 'demote')}
                      className="text-xs text-trust-proposed hover:underline"
                    >
                      Demote
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat: Knowledge Manager page with filtering and review actions"
```

---

### Task 20: Analytics Dashboard

**Files:**
- Modify: `frontend/src/pages/Analytics.tsx`
- Create: `backend/app/api/analytics.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add analytics API endpoint**

`backend/app/api/analytics.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Record, Personnel

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(session: AsyncSession = Depends(get_session)):
    total_records = (await session.execute(select(func.count(Record.id)))).scalar()
    total_personnel = (await session.execute(select(func.count(Personnel.id)))).scalar()

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
            func.to_char(Record.date, 'YYYY-MM').label('month'),
            func.count(Record.id),
        )
        .where(Record.date.isnot(None))
        .group_by('month')
        .order_by('month')
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
```

Register in `main.py`:
```python
from app.api.analytics import router as analytics_router
app.include_router(analytics_router)
```

- [ ] **Step 2: Implement Analytics page with charts**

`frontend/src/pages/Analytics.tsx`:
```tsx
import { useEffect, useState } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#92400E', '#D97706', '#059669', '#6366F1', '#DC2626', '#8B5CF6', '#0891B2'];

export default function Analytics() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch('/api/analytics/overview').then(r => r.json()).then(setData);
  }, []);

  if (!data) return <div className="text-slate-ink/50 font-body">Loading analytics...</div>;

  return (
    <div className="space-y-8">
      <h2 className="font-heading text-3xl text-slate-ink">Analytics</h2>

      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-parchment p-6">
          <p className="text-3xl font-heading text-slate-ink">{data.total_records}</p>
          <p className="text-sm text-slate-ink/50 font-body">Total records</p>
        </div>
        <div className="bg-white rounded-lg border border-parchment p-6">
          <p className="text-3xl font-heading text-slate-ink">{data.total_personnel}</p>
          <p className="text-sm text-slate-ink/50 font-body">Personnel entries</p>
        </div>
      </div>

      {/* Losses over time */}
      {data.by_month.length > 0 && (
        <div className="bg-white rounded-lg border border-parchment p-6">
          <h3 className="font-heading text-lg text-slate-ink mb-4">Losses Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data.by_month}>
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#92400E" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* By aircraft type */}
      <div className="grid grid-cols-2 gap-6">
        {data.by_aircraft.length > 0 && (
          <div className="bg-white rounded-lg border border-parchment p-6">
            <h3 className="font-heading text-lg text-slate-ink mb-4">By Aircraft Type</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data.by_aircraft} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#92400E" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {data.by_fate.length > 0 && (
          <div className="bg-white rounded-lg border border-parchment p-6">
            <h3 className="font-heading text-lg text-slate-ink mb-4">Personnel Outcomes</h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={data.by_fate} dataKey="count" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
                  {data.by_fate.map((_: any, i: number) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: Analytics dashboard with loss trends, aircraft breakdown, and personnel outcomes"
```

---

## Phase 5: Integration & Polish

### Task 21: End-to-End Test with Real Data

**Files:**
- Create: `scripts/test_e2e.py`

- [ ] **Step 1: Create end-to-end test script**

This script imports the real RL 2-III/1190 collection, runs Kraken on a few pages, then runs Claude extraction on those pages.

```python
"""End-to-end test: import real scans, run OCR pipeline, verify records."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.database import SessionLocal
from app.services.import_service import import_scan_folder
from app.services.extraction import run_kraken_stage, run_claude_stage
from app.db.models import PipelineJob, Record, Personnel
from sqlalchemy import select, func


SCAN_FOLDER = Path.home() / "Desktop" / "RL 2-III_1190"


async def main():
    if not SCAN_FOLDER.exists():
        print(f"Scan folder not found: {SCAN_FOLDER}")
        return

    async with SessionLocal() as session:
        # 1. Import first 5 pages only (for testing)
        print("Importing collection...")
        collection = await import_scan_folder(
            session=session,
            folder_path=SCAN_FOLDER,
            name="RL 2-III/1190 (test)",
            source_reference="RL_2_III_1190",
            document_type="loss_report",
        )
        print(f"Imported: {collection.name} — {collection.page_count} pages")

        # 2. Run Kraken on first 5 pages
        print("\nRunning Kraken OCR...")
        job = PipelineJob(collection_id=collection.id, stage="kraken", total_pages=5)
        session.add(job)
        await session.commit()
        await run_kraken_stage(session, collection.id, job.id)
        await session.refresh(job)
        print(f"Kraken: {job.status} — {job.processed_pages} pages processed")

        # 3. Run Claude extraction
        print("\nRunning Claude extraction...")
        job2 = PipelineJob(collection_id=collection.id, stage="claude", total_pages=5)
        session.add(job2)
        await session.commit()
        await run_claude_stage(session, collection.id, job2.id)
        await session.refresh(job2)
        print(f"Claude: {job2.status} — {job2.processed_pages} pages processed")

        # 4. Check results
        record_count = (await session.execute(select(func.count(Record.id)))).scalar()
        personnel_count = (await session.execute(select(func.count(Personnel.id)))).scalar()
        print(f"\nResults: {record_count} records, {personnel_count} personnel entries")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run the e2e test**

```bash
cd ~/projects/luftarchiv
python scripts/test_e2e.py
```

Review output — verify records are being extracted correctly from the real scans.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: end-to-end test script for real scan data"
```

---

### Task 22: Font Loading & Final UI Polish

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Add Google Fonts to index.html**

Add to `<head>`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400&family=Playfair+Display:wght@400;600;700&display=swap" rel="stylesheet">
```

Update page title:
```html
<title>Luftarchiv — Archive Search Tool</title>
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat: font loading and final UI polish"
```

---

### Task 23: README & Open Source Setup

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `docs/contributing.md`

- [ ] **Step 1: Create README.md**

A clear, professional README covering: what the tool does, screenshot placeholder, quick start (docker compose + backend + frontend), architecture overview, contributing link, license.

- [ ] **Step 2: Create MIT LICENSE file**

- [ ] **Step 3: Create docs/contributing.md**

Covering: development setup, running tests, coding standards, how to contribute knowledge entries, PR process.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "docs: README, LICENSE, and contributing guide"
```

---

## Completion Checklist

After all tasks are complete, verify:

- [ ] `docker compose up -d` starts PostgreSQL with pgvector
- [ ] `alembic upgrade head` creates all tables in both schemas
- [ ] `python scripts/seed_knowledge.py` populates glossary
- [ ] Backend starts: `uvicorn app.main:app --reload --port 8000`
- [ ] Frontend starts: `cd frontend && npm run dev`
- [ ] Collections page loads at http://localhost:3001
- [ ] Import API accepts a folder path and creates collection + pages
- [ ] Kraken OCR processes pages and stores text + segmentation
- [ ] Claude extraction creates structured records with personnel
- [ ] Search works with direct field filters
- [ ] Knowledge manager shows entries with trust levels
- [ ] CSV export downloads correctly
- [ ] Analytics dashboard renders charts
- [ ] All backend tests pass: `cd backend && python -m pytest tests/ -v`
