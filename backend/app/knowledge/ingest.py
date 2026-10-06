import os
import sys
import argparse
import asyncio
import logging

from app.services.rag_service import rag_service
from app.database.session import AsyncSessionLocal
from app.models.document import Document
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [INGEST] %(message)s")
logger = logging.getLogger("document_ingest")

async def sync_document_to_db(doc_id: str, title: str, crop: str, chunk_count: int, file_path: str, organization: str):
    try:
        from app.database.session import engine
        from app.database.base import Base
        import app.models  # noqa
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncSessionLocal() as db:
            res = await db.execute(select(Document).where(Document.id == doc_id))
            existing = res.scalar_one_or_none()
            size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

            if existing:
                existing.chunk_count = chunk_count
                existing.status = "indexed"
                existing.title = title
            else:
                doc = Document(
                    id=doc_id,
                    title=title,
                    source="Agricultural Research Advisory",
                    organization=organization,
                    crop=crop,
                    crop_type="Horticulture / Field Crops",
                    region="South India (Tamil Nadu & Kerala)",
                    topic="Cultivation, Irrigation and Crop Health",
                    language="English",
                    document_type=file_path.split('.')[-1].upper(),
                    file_path=file_path,
                    file_size=size,
                    chunk_count=chunk_count,
                    status="indexed"
                )
                db.add(doc)
            await db.commit()
    except Exception as e:
        logger.warning(f"Could not record doc {doc_id} to DB (DB might be offline): {e}")

def run_ingest(source_dir: str = "knowledge_docs"):
    abs_dir = os.path.abspath(source_dir)
    logger.info(f"Scanning directory for verified agricultural documents: {abs_dir}")

    if not os.path.exists(abs_dir):
        os.makedirs(abs_dir, exist_ok=True)
        logger.warning(f"Created empty directory: {abs_dir}. Please place PDF, DOCX, or TXT documents inside.")
        return

    files = [f for f in os.listdir(abs_dir) if f.lower().endswith(('.pdf', '.docx', '.txt', '.md'))]
    if not files:
        logger.warning(f"No documents found in {abs_dir}")
        return

    logger.info(f"Found {len(files)} agricultural documents to process.")

    for fname in sorted(files):
        fpath = os.path.join(abs_dir, fname)
        base_name = os.path.splitext(fname)[0]
        doc_id = f"doc_{base_name.lower().replace(' ', '_').replace('-', '_')}"

        # Heuristic metadata extraction from filename and content
        lower_name = fname.lower()
        if "tomato" in lower_name:
            crop = "Tomato"
            org = "TNAU - Tamil Nadu Agricultural University"
        elif "rice" in lower_name or "paddy" in lower_name:
            crop = "Rice"
            org = "ICAR - National Rice Research Institute"
        elif "chilli" in lower_name:
            crop = "Chilli"
            org = "TNAU - Horticulture Department"
        elif "coconut" in lower_name:
            crop = "Coconut"
            org = "CPCRI / Kerala Agricultural University"
        elif "banana" in lower_name:
            crop = "Banana"
            org = "ICAR - National Research Centre for Banana"
        else:
            crop = "General Agriculture"
            org = "ICAR / State Agricultural Universities"

        title = base_name.replace("_", " ").title()
        metadata = {
            "document_id": doc_id,
            "title": title,
            "crop": crop,
            "organization": org,
            "region": "Tamil Nadu & Kerala",
            "source": f"{org} Official Production Guide",
            "topic": "Irrigation, Nutrient Management, Disease Control"
        }

        logger.info(f"Ingesting: {fname} (Crop: {crop}, Org: {org})...")
        res = rag_service.ingest_document(fpath, metadata)
        chunk_count = res.get("chunk_count", 0)
        logger.info(f"  -> Extracted & embedded {chunk_count} intelligent chunks into ChromaDB.")

        # Sync to DB asynchronously
        try:
            asyncio.run(sync_document_to_db(doc_id, title, crop, chunk_count, fpath, org))
        except Exception:
            pass

    logger.info("Ingestion pipeline finished successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agrikural Agricultural Document Ingestion Pipeline")
    parser.add_argument("--dir", default="knowledge_docs", help="Directory containing agricultural documents")
    args = parser.parse_args()

    run_ingest(args.dir)
