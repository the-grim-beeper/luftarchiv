# Luftarchiv — OCR Archive Search Tool for Luftwaffe Research

**Date:** 2026-03-22
**Status:** Design approved, pending implementation plan

## Purpose

An open-source, academic-grade tool for OCR-extracting, searching, and researching digitized German Luftwaffe archival documents from WWII. Built for the research community interested in German aircraft during the Second World War.

The tool makes scanned archival documents searchable by extracting structured data via a two-stage OCR pipeline (Kraken + Claude), storing it alongside an evolving knowledge base of abbreviations, unit designations, and aircraft types. An AI-powered search layer lets researchers query in natural English across German-language source material.

## Audience

Historians, archivists, and researchers working with Bundesarchiv Luftwaffe records. The tool is designed for academic rigor — original sources are always visible, corrections are tracked, and AI-suggested knowledge requires human verification.

## Core Principles

- **Document is king** — the original scan is always one click away from any data view
- **Trust hierarchy** — knowledge entries are verified, proposed, or AI-suggested; nothing becomes fact without human review
- **Corrections don't overwrite** — OCR originals are preserved alongside human corrections
- **Offline-capable baseline** — Kraken OCR works without API keys; Claude enhances but isn't required
- **Retrieval-only AI** — the search AI never invents information, only reasons over records in the database
- **English interface** — German source material preserved as-is in extracted data

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────┐
│                  React Frontend                  │
│  ┌───────────┐ ┌───────────┐ ┌───────────────┐  │
│  │ Document   │ │ Search &  │ │  Knowledge    │  │
│  │ Viewer     │ │ Analytics │ │  Manager      │  │
│  └───────────┘ └───────────┘ └───────────────┘  │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────┐
│              FastAPI Backend                     │
│  ┌──────┐ ┌────────┐ ┌──────────┐ ┌──────────┐  │
│  │ OCR  │ │ Search │ │Knowledge │ │  Export  │  │
│  │Engine│ │Service │ │ Service  │ │ Service  │  │
│  └──┬───┘ └───┬────┘ └────┬─────┘ └────┬─────┘  │
│     │    Claude API       │             │        │
└─────┼─────────┼───────────┼─────────────┼────────┘
      │         │           │             │
┌─────┴─────┐ ┌─┴───────────┴─┐     ┌────┴─────┐
│  Image    │ │  PostgreSQL    │     │  CSV/    │
│  Storage  │ │                │     │  Files   │
│(filesystem)│ ┌────┐ ┌─────┐ │     └──────────┘
│           │ │Data │ │Know-│ │
│           │ │ DB  │ │ledge│ │
│           │ └────┘ └─────┘ │
│           │  (two schemas)  │
└───────────┘ └──────────────┘
```

- One PostgreSQL instance with two schemas: `archive_data` and `archive_knowledge`
- Images stored on filesystem, referenced by path
- Claude API for intelligent OCR extraction and search interpretation
- CSV export as a first-class feature

### No Hard Path Dependencies

- Adding columns, tables, or new knowledge entity types is a standard migration
- Embedding dimension/model can be swapped with a re-embed
- Trust levels are a string enum, easily extended
- JSONB column definitions allow flexible document type schemas
- The two-schema split could be merged if needed without a rewrite

## Data Models

### Schema: `archive_data`

#### `collections`
A folder of scanned documents (e.g., "RL 2-III/1190").

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | text | Display name |
| source_reference | text | Archive reference code |
| description | text | Description of the collection |
| document_type | text | Type of documents in the collection |
| page_count | int | Number of pages |
| status | enum | pending / processing / complete |
| created_at | timestamp | |
| updated_at | timestamp | |

#### `pages`
Individual scanned images within a collection.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| collection_id | UUID | FK to collections |
| page_number | int | Sequential page number |
| image_path | text | Filesystem path to scan image |
| ocr_status | enum | pending / extracted / verified |
| ocr_confidence | float | Overall confidence score |
| raw_ocr_text | text | Kraken raw OCR output |
| segmentation_data | JSONB | Kraken line segmentation with bounding boxes — array of {text, bbox: {x,y,w,h}} |
| created_at | timestamp | |

#### `records`
Extracted structured data — one row per incident/entry. V1 is scoped to loss reports (Verlustmeldungen); columns reflect this document type. When other document types are added, a JSONB `extended_data` column or separate record tables per document type can be introduced without breaking existing data.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| page_id | UUID | FK to pages (primary page) |
| page_id_end | UUID | Nullable FK to pages (if entry spans pages) |
| entry_number | int | Sequential entry number from document |
| date | date | Date of incident |
| unit_designation | text | Unit as written in document |
| aircraft_type | text | Aircraft type as written |
| werknummer | text | Factory/serial number |
| incident_type | text | Type of incident (original German) |
| incident_description | text | Additional description |
| damage_percentage | int | Percentage of damage |
| location | text | Location as written |
| raw_text_original | text | Full raw text of this entry |
| bounding_boxes | JSONB | Array of {page_id, x, y, w, h} regions on the scan |
| search_embedding | vector(1024) | Embedding of natural language summary |
| created_at | timestamp | |

#### `personnel`
People mentioned in records. One record can have multiple personnel.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| record_id | UUID | FK to records |
| rank_abbreviation | text | Rank as abbreviated in document |
| rank_full | text | Full rank name |
| surname | text | |
| first_name | text | |
| fate | text | Free text — common values: gefallen, verwundet, vermisst, in Gefangenschaft, tot, uninjured |
| fate_english | text | Free text — common values: killed, wounded, missing, captured/POW, dead, uninjured |

#### `record_corrections`
Human corrections to OCR results. Originals are preserved.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| record_id | UUID | FK to records |
| field_name | text | Which field was corrected |
| original_value | text | What OCR produced |
| corrected_value | text | What the human corrected it to |
| corrected_by | text | Who made the correction |
| corrected_at | timestamp | |

#### `users`
Minimal identity model for tracking contributions and enforcing review permissions. V1 is single-user with no authentication — the user table provides referential integrity for audit trails. Multi-user auth is future scope.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| username | text | Unique display name |
| role | enum | admin / reviewer / contributor |
| created_at | timestamp | |

All `*_by` columns in other tables (corrected_by, proposed_by, verified_by, reviewer) are FKs to `users.id`. A seed migration creates a default admin user.

#### `pipeline_jobs`
Tracks OCR pipeline execution state for resume/retry capability.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| collection_id | UUID | FK to collections |
| stage | enum | kraken / claude / embedding |
| status | enum | pending / running / completed / failed |
| total_pages | int | Pages in this job |
| processed_pages | int | Pages completed so far |
| last_processed_page_id | UUID | For resume after failure |
| error_message | text | If failed |
| started_at | timestamp | |
| completed_at | timestamp | |

### Schema: `archive_knowledge`

#### `glossary`
Abbreviation definitions and terminology.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| term | text | The abbreviation or term |
| definition | text | What it means |
| category | enum | rank / unit_type / incident_type / aircraft / location / other |
| language | text | Source language (default: de) |
| trust_level | enum | verified / proposed / ai_suggested |
| source | text | Where the definition came from |
| proposed_by | text | Who proposed it |
| verified_by | text | Who verified it |
| verified_at | timestamp | |
| embedding | vector(1024) | Embedding for semantic matching |

#### `document_schemas`
Descriptions of document types and their column structures.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| document_type | text | E.g., "loss_report", "strength_return" |
| description | text | What this document type contains |
| column_definitions | JSONB | Column names, positions, data types |
| example_collection_id | UUID | Reference to a collection ID (not a cross-schema FK — stored as UUID, resolved in application code) |
| trust_level | enum | verified / proposed / ai_suggested |

#### `unit_designations`
Known Luftwaffe unit abbreviations and full names.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| abbreviation | text | Short form (e.g., "II./JG 54") |
| full_name | text | Full name |
| unit_type | text | Gruppe / Staffel / Geschwader / etc. |
| parent_unit_id | UUID | FK to parent unit (self-referential) |
| active_from | date | |
| active_to | date | |
| notes | text | |
| trust_level | enum | verified / proposed / ai_suggested |

#### `aircraft_types`
Aircraft identification reference.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| designation | text | E.g., "Bf 109 G-4" |
| manufacturer | text | E.g., "Messerschmitt" |
| common_name | text | Common English name if any |
| variants | JSONB | Known sub-variants |
| trust_level | enum | verified / proposed / ai_suggested |

#### `knowledge_reviews`
Audit trail for the trust system.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| entity_type | text | Which knowledge table |
| entity_id | UUID | FK to the reviewed entity |
| action | enum | propose / approve / reject / demote |
| old_trust_level | enum | |
| new_trust_level | enum | |
| reviewer | text | |
| reason | text | |
| reviewed_at | timestamp | |

## OCR & Extraction Pipeline

### Two-Stage Design

**Stage 1: Kraken (local, free, deterministic)**
- Line segmentation and raw text extraction
- Output stored in `pages.raw_ocr_text`
- Runs entirely offline — no API key needed
- Can be fine-tuned on corrected output over time

**Stage 2: Claude Sonnet (API, contextual, structured)**
- Receives: scan image + Kraken raw text + relevant glossary entries from knowledge DB
- Returns: JSON array of structured records with personnel
- Marks confidence per field
- New abbreviations encountered are flagged as `ai_suggested` knowledge entries

### Extraction Flow

```
1. Import scan folder → create collection + page records
2. Kraken pass:
   - Line segmentation with bounding boxes
   - Raw text extraction
   - Store text in pages.raw_ocr_text, geometry in pages.segmentation_data
3. Claude pass:
   - Send image + Kraken text + knowledge base context
   - Claude returns structured JSON
   - Store in records + personnel tables
   - New abbreviations → ai_suggested glossary entries
4. Human review queue:
   - Low-confidence pages flagged
   - Corrections saved to record_corrections
   - Corrections optionally proposed as knowledge entries
   - Corrections can retrain Kraken model
```

### Why Two Stages

- **Cost**: Kraken is free; Claude only needed for interpretation. Scales to thousands of pages.
- **Offline**: Researchers without API budgets get basic OCR.
- **Reproducibility**: Kraken output is deterministic — important for academic work.
- **Trainability**: Kraken can be fine-tuned on corrections, reducing Claude dependency over time.

### Embedding Strategy

Search embeddings are generated using `fastembed` with `BAAI/bge-large-en-v1.5` (1024 dimensions). Each record's embedding is computed from a template-generated natural language summary:

> "On {date}, a {aircraft_type} (WNr {werknummer}) from {unit_designation} experienced {incident_type} at {location}. {damage_percentage}% damage. Personnel: {personnel_list with fates}."

The knowledge base enriches these summaries — if the glossary has a verified entry for an abbreviation, the resolved form is used. Glossary embeddings use term + definition concatenated.

### Image Preprocessing

Accepted formats: JPEG, PNG, TIFF. Multi-page TIFFs and PDFs are split into individual page images on import. Kraken handles deskewing internally. No additional preprocessing in V1 — Kraken's defaults are sufficient for clean typewritten scans. Preprocessing pipeline can be extended later for degraded documents.

### Cost Estimate
- ~$0.02-0.15 per page with Claude Sonnet (varies with page density and knowledge context size)
- ~$15-35 for a 333-page collection
- One-time cost per collection

### Retrieval-Only AI Enforcement

The analytical search mode enforces retrieval-only behavior through:
1. Claude receives only retrieved records as context — never the full database
2. The prompt requires structured output with `record_id` citations for every claim
3. Post-processing validates that all cited record IDs exist in the database
4. Responses with unverifiable citations are flagged and the offending claims stripped

## AI Search Layer

### Three Search Modes

**1. Direct Search (no AI, fast)**
- SQL + full-text search against structured fields
- Filter by date range, unit, aircraft type, incident type, personnel name
- The default, everyday search mode

**2. Semantic Search (pgvector)**
- Each record has an embedding computed from a natural language summary of all fields
- Finds relevant records even when terminology doesn't match exactly
- Knowledge base enriches summaries with resolved abbreviations and full unit names

**3. Analytical Search (Claude API)**
- Natural language questions translated to SQL + semantic search
- Claude retrieves candidate records, aggregates, and synthesizes answers
- Every claim cites specific record IDs — no hallucination
- Retrieval-only: Claude never invents information

### Search Flow

```
User query
    │
    ├─ Structured filter? → Direct search (SQL)
    │
    └─ Natural language? → Claude interprets
          ├─ Generates SQL filters where possible
          ├─ Falls back to semantic search
          ├─ Combines results
          └─ Summarizes with record citations
```

## UI Design

### Views

**1. Collection Browser** — Landing page. Collections as cards with progress indicators.

**2. Document Viewer** — The core experience. Split-pane:
- Left: zoomable original scan with region highlighting
- Right: extracted record cards
- Bottom: collapsible knowledge panel showing abbreviation definitions and trust levels
- Correction workflow inline — click to edit, original preserved

**3. Search View** — Single search bar handling all three modes. Results as sortable/filterable table. Each row links to document viewer at the relevant page. Faceted sidebar for filtering.

**4. Knowledge Manager** — Browse/filter/review all knowledge entries by trust level. Review queue for proposed entries. Contribution history. Bulk CSV import.

**5. Analytics Dashboard** — Loss statistics over time, breakdowns by aircraft/incident/unit. Exportable charts. No AI interpretation — pure aggregation.

### Visual Identity

- **Typography-driven**: serif headings (archival feel) + clean sans for data
- **Muted, warm palette**: aged paper tones, dark navy/slate text, minimal accent color
- **Document-first**: maximum space for scan images, minimal UI chrome
- **No gratuitous animation**: subtle transitions, solid feel
- **Desktop-first**: optimized for research workstation screens

## Tech Stack

### Backend
- Python 3.12+
- FastAPI + uvicorn
- SQLAlchemy (async) + asyncpg + alembic
- pgvector (Python bindings)
- kraken (OCR engine)
- anthropic (Claude API)
- fastembed (local embedding generation)
- Pillow (image handling)

### Frontend
- React 19 + TypeScript
- Vite
- TailwindCSS v4
- OpenSeadragon or similar (deep zoom for scans)
- Recharts (analytics charts)
- TanStack Table (sortable/filterable record tables)

### Infrastructure
- PostgreSQL 16 + pgvector extension (Docker, port 5435)
- Frontend on port 3001
- Images on filesystem (referenced by path)

### Open Source
- MIT license
- `.env.example` with `ANTHROPIC_API_KEY` as the only required secret
- `docker-compose up -d` for database
- Seed script for initial Luftwaffe abbreviation glossary
- Kraken functional without API key for offline use

## Project Structure

```
luftarchiv/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   └── models/
│   │   │       ├── collection.py
│   │   │       ├── page.py
│   │   │       ├── record.py
│   │   │       ├── personnel.py
│   │   │       ├── correction.py
│   │   │       ├── user.py
│   │   │       ├── pipeline_job.py
│   │   │       ├── glossary.py
│   │   │       ├── document_schema.py
│   │   │       ├── unit_designation.py
│   │   │       ├── aircraft_type.py
│   │   │       └── knowledge_review.py
│   │   ├── api/
│   │   │   ├── collections.py
│   │   │   ├── pages.py
│   │   │   ├── records.py
│   │   │   ├── search.py
│   │   │   ├── knowledge.py
│   │   │   └── export.py
│   │   └── services/
│   │       ├── ocr_kraken.py
│   │       ├── ocr_claude.py
│   │       ├── extraction.py
│   │       ├── search.py
│   │       ├── embeddings.py
│   │       └── export.py
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Collections.tsx
│   │   │   ├── DocumentViewer.tsx
│   │   │   ├── Search.tsx
│   │   │   ├── Knowledge.tsx
│   │   │   └── Analytics.tsx
│   │   ├── components/
│   │   │   ├── ScanViewer.tsx
│   │   │   ├── RecordCard.tsx
│   │   │   ├── RecordTable.tsx
│   │   │   ├── KnowledgePanel.tsx
│   │   │   ├── CorrectionForm.tsx
│   │   │   ├── SearchBar.tsx
│   │   │   ├── ReviewQueue.tsx
│   │   │   └── charts/
│   │   ├── api/
│   │   │   └── client.ts
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── docs/
│   ├── glossary-seed.csv
│   └── contributing.md
├── scripts/
│   └── seed_knowledge.py
└── README.md
```

## Future Scope (Not In V1)

- Narrative document support (Kriegstagebücher, reports)
- Photo/map/technical drawing handling
- Multi-user authentication and permissions
- Collaborative annotation
- Graph-based relationship queries (unit reorganizations, personnel transfers)
- Transkribus integration for handwritten document support
