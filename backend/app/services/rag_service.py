import os
import re
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config.settings import settings
from app.services.embedding_service import embedding_service
from app.knowledge.chunking.chunker import DocumentChunker
from app.schemas.rag import SourceCitation

logger = logging.getLogger("agrikural.rag")

class RAGService:
    def __init__(self):
        self.chroma_path = settings.CHROMA_PATH
        self.collection_name = settings.CHROMA_COLLECTION
        self.chunker = DocumentChunker(target_chunk_size=450, overlap=60)
        os.makedirs(self.chroma_path, exist_ok=True)
        
        # Initialize persistent ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Agrikural agricultural knowledge vector database"}
        )
        logger.info(f"Initialized ChromaDB collection '{self.collection_name}' with {self.collection.count()} chunks.")

    def extract_text(self, file_path: str) -> tuple[str, int]:
        """
        Extracts clean text and page count from PDF, DOCX, or TXT.
        Returns (text, page_count).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = file_path.lower().split('.')[-1]
        text_content = ""
        page_count = 1

        if ext == "pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                page_count = len(reader.pages)
                pages_text = []
                for idx, page in enumerate(reader.pages):
                    pt = page.extract_text() or ""
                    pages_text.append(f"\n[Page {idx + 1}]\n{pt}")
                text_content = "\n".join(pages_text)
            except Exception as e:
                logger.error(f"Error reading PDF {file_path}: {e}")
                raise

        elif ext in ["docx", "doc"]:
            try:
                import docx
                doc = docx.Document(file_path)
                paras = [p.text for p in doc.paragraphs if p.text.strip()]
                text_content = "\n\n".join(paras)
                page_count = max(1, len(paras) // 10)
            except Exception as e:
                logger.error(f"Error reading DOCX {file_path}: {e}")
                raise

        else:
            # TXT, Markdown, etc.
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = f.read()
            page_count = max(1, len(text_content) // 2500)

        # Basic cleanup
        clean_text = re.sub(r'\r\n', '\n', text_content)
        clean_text = re.sub(r'[\t ]+', ' ', clean_text)
        return clean_text, page_count

    def ingest_document(self, file_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full ingestion pipeline:
        Document -> Text Extraction -> Cleaning -> Chunking -> Embedding -> ChromaDB
        """
        document_id = metadata.get("document_id") or os.path.splitext(os.path.basename(file_path))[0]
        text, page_count = self.extract_text(file_path)

        if not text.strip():
            logger.warning(f"No text extracted from {file_path}")
            return {"document_id": document_id, "chunk_count": 0, "status": "empty"}

        # Delete existing chunks for this document if re-indexing
        try:
            self.collection.delete(where={"document_id": document_id})
        except Exception:
            pass

        # Intelligent chunking
        base_meta = {
            "document_id": document_id,
            "title": str(metadata.get("title", document_id)),
            "source": str(metadata.get("source", "TNAU / ICAR")),
            "organization": str(metadata.get("organization", "ICAR")),
            "crop": str(metadata.get("crop", "General")),
            "crop_type": str(metadata.get("crop_type", "Horticulture")),
            "region": str(metadata.get("region", "South India")),
            "topic": str(metadata.get("topic", "Irrigation & Soil")),
            "language": str(metadata.get("language", "English")),
        }

        chunks = self.chunker.chunk_text(text, document_id=document_id, default_metadata=base_meta)
        if not chunks:
            return {"document_id": document_id, "chunk_count": 0, "status": "no_chunks"}

        chunk_texts = [c["text"] for c in chunks]
        chunk_ids = [c["chunk_id"] for c in chunks]
        chunk_metas = [c["metadata"] for c in chunks]

        # Generate embeddings
        embeddings = embedding_service.embed_documents(chunk_texts)

        # Ingest into ChromaDB
        self.collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=chunk_metas
        )

        logger.info(f"Successfully indexed document {document_id} with {len(chunks)} chunks into ChromaDB.")
        return {
            "document_id": document_id,
            "title": base_meta["title"],
            "chunk_count": len(chunks),
            "status": "indexed"
        }

    def ingest_directory(self, dir_path: str) -> List[Dict[str, Any]]:
        """Scans directory and ingests all supported files."""
        results = []
        if not os.path.exists(dir_path):
            return results

        for fname in sorted(os.listdir(dir_path)):
            ext = fname.lower().split('.')[-1]
            if ext in ["pdf", "docx", "txt", "md"]:
                fpath = os.path.join(dir_path, fname)
                doc_id = os.path.splitext(fname)[0]
                meta = {
                    "document_id": doc_id,
                    "title": doc_id.replace("_", " ").title(),
                    "source": "Verified Agricultural Advisory",
                    "organization": "TNAU / ICAR",
                    "crop": "Tomato" if "tomato" in fname.lower() else ("Rice" if "rice" in fname.lower() else "General"),
                    "topic": "Irrigation, Cultivation and Management",
                }
                res = self.ingest_document(fpath, meta)
                results.append(res)
        return results

    def retrieve(
        self,
        query: str,
        crop: Optional[str] = None,
        region: Optional[str] = None,
        topic: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Semantic vector retrieval with metadata filtering.
        """
        if not query or not query.strip():
            return []

        query_embedding = embedding_service.embed_query(query)

        # Build where clause if metadata filters are specified
        where_filter = {}
        if crop and crop.lower() != "all" and crop.lower() != "general":
            where_filter["crop"] = crop

        count = self.collection.count()
        if count == 0:
            return []

        query_top_k = min(top_k or settings.TOP_K, count)

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=query_top_k,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            logger.warning(f"Filter query error: {e}. Retrying without metadata filter.")
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=query_top_k,
                include=["documents", "metadatas", "distances"]
            )

        retrieved = []
        if results and results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

            for doc_text, meta, dist in zip(docs, metas, distances):
                # Convert distance to similarity score
                similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0))) if dist is not None else 0.85
                retrieved.append({
                    "text": doc_text,
                    "metadata": meta,
                    "relevance_score": round(similarity, 3)
                })

        # Rank by score descending
        retrieved.sort(key=lambda x: x["relevance_score"], reverse=True)
        return retrieved

    def get_sources(self, retrieved_chunks: List[Dict[str, Any]]) -> List[SourceCitation]:
        """Formats retrieved chunks into clean SourceCitation objects."""
        sources = []
        seen = set()
        for chk in retrieved_chunks:
            meta = chk.get("metadata", {})
            doc_id = meta.get("document_id", "doc")
            page = meta.get("page_number", 1)
            key = f"{doc_id}_{page}"
            if key not in seen:
                seen.add(key)
                snippet = chk.get("text", "")[:140] + "..." if len(chk.get("text", "")) > 140 else chk.get("text", "")
                sources.append(SourceCitation(
                    title=meta.get("title", "Agricultural Advisory Manual"),
                    organization=meta.get("organization", "TNAU / ICAR"),
                    page=page,
                    section=meta.get("section", "General Advisory"),
                    document_id=doc_id,
                    relevance_score=chk.get("relevance_score", 0.90),
                    crop=meta.get("crop", "General"),
                    topic=meta.get("topic", "Management"),
                    snippet=snippet
                ))
        return sources

    def delete_document(self, document_id: str) -> bool:
        """Removes all chunks of a document from ChromaDB."""
        try:
            self.collection.delete(where={"document_id": document_id})
            logger.info(f"Deleted document {document_id} from ChromaDB")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False

rag_service = RAGService()
