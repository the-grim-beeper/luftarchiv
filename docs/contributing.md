# Contributing to Luftarchiv

Thank you for your interest in contributing. Luftarchiv is a small open-source project and welcomes improvements to the OCR pipeline, knowledge base content, UI, and documentation.

---

## Development Setup

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

## Running Tests

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

The end-to-end test (requires real scan data) is run separately:

```bash
python ../scripts/test_e2e.py
```

---

## Code Style

- **Python** — standard library conventions; no formatter is enforced, but keep existing style consistent. Type hints are used throughout; please add them to new code.
- **TypeScript** — standard TypeScript conventions. The frontend uses Tailwind CSS v4; avoid inline styles.

---

## Contributing Knowledge Entries

The knowledge base (glossary terms, unit designations, aircraft types) is the most accessible place to contribute without needing a development environment.

**Option A — Edit the seed CSV directly**

Add rows to `scripts/glossary-seed.csv` and open a PR. Column format:

```
term,definition,category,trust_level
```

Valid trust levels: `verified`, `proposed`, `flagged`.

**Option B — Use the UI**

Run the app locally, navigate to the Knowledge Manager page, and add or edit entries through the interface. Export your changes and include them in your PR if appropriate.

---

## Pull Request Process

1. Fork the repository and create a feature branch from `main`.
2. Make your changes with clear, focused commits.
3. Run the test suite and confirm it passes.
4. Open a PR with a short description of what was changed and why.
5. A maintainer will review and merge, or leave feedback.

For larger changes (new pipeline stages, schema migrations, major UI rework), open an issue first to discuss the approach.
