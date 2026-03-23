#!/bin/bash
set -e

echo "=== Luftarchiv ==="
echo "Waiting for database..."

# Wait for PostgreSQL to be ready
for i in $(seq 1 30); do
    if python -c "
import asyncio, asyncpg
async def check():
    try:
        conn = await asyncpg.connect('$DATABASE_URL'.replace('+asyncpg', ''))
        await conn.close()
        return True
    except:
        return False
exit(0 if asyncio.run(check()) else 1)
" 2>/dev/null; then
        echo "Database is ready."
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 2
done

# Run migrations
echo "Running migrations..."
python -m alembic upgrade head

# Seed knowledge base (idempotent)
echo "Seeding knowledge base..."
PYTHONPATH=/app python /app/scripts/seed_knowledge.py

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
