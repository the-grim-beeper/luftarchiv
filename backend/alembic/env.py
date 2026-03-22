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
