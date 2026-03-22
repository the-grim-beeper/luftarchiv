"""End-to-end test: import real scans, run OCR pipeline, verify records."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


async def main():
    scan_folder = Path.home() / "Desktop" / "RL 2-III_1190"

    if not scan_folder.exists():
        print(f"Scan folder not found: {scan_folder}")
        print("Place scanned images at ~/Desktop/RL 2-III_1190/ to run this test.")
        return

    try:
        from app.db.database import SessionLocal
        from app.services.import_service import import_scan_folder
        from app.services.extraction import run_kraken_stage, run_claude_stage
        from app.db.models import PipelineJob, Record, Personnel
        from sqlalchemy import select, func
    except ImportError as e:
        print(f"Import error: {e}")
        print("Run from backend/ with venv activated.")
        return

    try:
        async with SessionLocal() as session:
            print("1. Importing collection (first 5 pages)...")

            # Collect only the first 5 image files for the test run
            supported = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
            all_images = sorted(
                f for f in scan_folder.iterdir()
                if f.is_file() and f.suffix.lower() in supported
            )
            if not all_images:
                print("   No supported image files found in scan folder.")
                return

            test_images = all_images[:5]
            print(f"   Using {len(test_images)} of {len(all_images)} available images.")

            # Write a temporary subfolder with only the first 5 pages so that
            # import_scan_folder picks them up without touching the originals.
            import tempfile, shutil
            with tempfile.TemporaryDirectory(prefix="luftarchiv_e2e_") as tmp_dir:
                tmp_path = Path(tmp_dir)
                for img in test_images:
                    shutil.copy2(img, tmp_path / img.name)

                collection = await import_scan_folder(
                    session=session,
                    folder_path=tmp_path,
                    name="RL 2-III/1190 (e2e test)",
                    source_reference="RL_2_III_1190",
                    document_type="loss_report",
                )
            print(f"   Imported: {collection.name} — {collection.page_count} pages")

            print("\n2. Running Kraken OCR (this may take a while)...")
            job = PipelineJob(
                collection_id=collection.id,
                stage="kraken",
                total_pages=collection.page_count,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            await run_kraken_stage(session, collection.id, job.id)
            await session.refresh(job)
            print(f"   Kraken: {job.status} — {job.processed_pages} pages processed")
            if job.error_message:
                print(f"   Error: {job.error_message}")

            print("\n3. Running Claude extraction...")
            job2 = PipelineJob(
                collection_id=collection.id,
                stage="claude",
                total_pages=collection.page_count,
            )
            session.add(job2)
            await session.commit()
            await session.refresh(job2)
            await run_claude_stage(session, collection.id, job2.id)
            await session.refresh(job2)
            print(f"   Claude: {job2.status} — {job2.processed_pages} pages processed")
            if job2.error_message:
                print(f"   Error: {job2.error_message}")

            record_count = (
                await session.execute(select(func.count(Record.id)))
            ).scalar()
            personnel_count = (
                await session.execute(select(func.count(Personnel.id)))
            ).scalar()
            print(f"\nResults: {record_count} records, {personnel_count} personnel entries")

    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("  1. Docker is running: docker compose up -d")
        print("  2. Migrations applied: cd backend && alembic upgrade head")
        print("  3. ANTHROPIC_API_KEY is set in .env")


if __name__ == "__main__":
    asyncio.run(main())
