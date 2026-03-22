# Luftarchiv

**Open-source OCR archive search tool for WWII Luftwaffe research documents**

Luftarchiv ingests folders of scanned historical documents, runs a two-stage OCR pipeline (Kraken layout analysis + Claude structured extraction), and exposes a searchable archive with full-text and semantic search. Personnel records, unit designations, and aircraft types are extracted automatically and cross-referenced through a built-in knowledge base, making it practical to research loss reports, sortie records, and similar primary sources at scale.

<!-- TODO: Add screenshot -->

---

## Quick Start

```bash
# Prerequisites: Docker, Python 3.12+, Node.js 20+

# 1. Start database
docker compose up -d

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env  # Add your ANTHROPIC_API_KEY
alembic upgrade head
python ../scripts/seed_knowledge.py
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev

# Open http://localhost:3001
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     React Frontend                      │
│  Collections · Pipeline · Search · Records · Knowledge  │
└────────────────────────┬────────────────────────────────┘
                         │ REST / SSE
┌────────────────────────▼────────────────────────────────┐
│                   FastAPI Backend                       │
│                                                         │
│  Import ──► Kraken OCR ──► Claude Extraction            │
│                                   │                     │
│  Search (FTS + pgvector) ◄── Records + Personnel        │
│                                                         │
│  Knowledge Base (Glossary · Units · Aircraft)           │
│  Export (CSV / JSON)                                    │
└────────────────────────┬────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │  PostgreSQL 16      │
              │  + pgvector         │
              └─────────────────────┘
```

**Pipeline stages**

| Stage | Tool | What happens |
|---|---|---|
| Import | Python | Copy images into managed storage, create `Collection` + `Page` rows |
| Kraken | [Kraken](https://kraken.re) | Layout segmentation and baseline OCR on each page image |
| Claude | Anthropic API | Structured extraction of records, personnel, dates, and units from OCR text |

---

## Features

- **Bulk import** — drop a folder of JPG/PNG/TIFF scans and import in one step
- **Two-stage OCR** — Kraken for layout-aware text extraction, Claude for structured data parsing
- **Full-text search** — PostgreSQL `tsvector` search across all extracted record text
- **Semantic search** — pgvector embeddings for concept-level queries
- **Personnel index** — extracted names linked to their source records
- **Knowledge base** — community-editable glossary, unit designations, aircraft types with trust levels
- **Human corrections** — flag and correct OCR errors; corrections feed back into future extractions
- **Export** — download records as CSV or JSON for use in other tools
- **Pipeline monitoring** — real-time progress tracking for each OCR job

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript, Tailwind CSS v4 |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2 (async) |
| Database | PostgreSQL 16 + pgvector |
| OCR | Kraken + Anthropic Claude API |
| Embeddings | pgvector |
| Infrastructure | Docker Compose |

---

## Running the E2E Test

```bash
cd backend && source .venv/bin/activate
python ../scripts/test_e2e.py
```

The script imports the first 5 pages from `~/Desktop/RL 2-III_1190/`, runs both pipeline stages, and prints a record/personnel count summary. See the script for prerequisites.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Contributing

See [docs/contributing.md](docs/contributing.md).
