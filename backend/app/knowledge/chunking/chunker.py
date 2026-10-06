import re
from typing import List, Dict, Any

class DocumentChunker:
    """
    Intelligent document chunking system.
    Supports section-aware, heading-aware, and paragraph-aware chunking.
    Preserves document structure and contextual integrity.
    """
    def __init__(self, target_chunk_size: int = 500, overlap: int = 80):
        self.target_chunk_size = target_chunk_size
        self.overlap = overlap

    def chunk_text(
        self,
        text: str,
        document_id: str,
        default_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        if not text or not text.strip():
            return []

        default_metadata = default_metadata or {}
        chunks = []

        # 1. Detect headings or section breaks (e.g. "## Heading", "SECTION 1", "CHAPTER", or all-caps lines)
        sections = re.split(r'\n(?=[A-Z0-9\s]{3,40}\n|\#\#\s+|\b(?:SECTION|CHAPTER|PART|TOPIC)\b)', text)

        chunk_idx = 0
        current_page = default_metadata.get("page_number", 1)

        for sec_i, section in enumerate(sections):
            section_clean = section.strip()
            if not section_clean:
                continue

            # Extract section heading if present
            lines = section_clean.split('\n')
            section_title = lines[0].strip().replace("#", "").strip()
            if len(section_title) > 60:
                section_title = f"Section {sec_i + 1}"

            # Paragraph-based chunking within section
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n', section_clean) if p.strip()]

            current_chunk_text = ""
            for p in paragraphs:
                # Check for explicit page markers in text like "[Page 2]" or "Page 2 of 10"
                page_match = re.search(r'\[Page\s+(\d+)\]|Page\s+(\d+)\b', p, re.IGNORECASE)
                if page_match:
                    found_page = page_match.group(1) or page_match.group(2)
                    try:
                        current_page = int(found_page)
                    except ValueError:
                        pass

                if len(current_chunk_text) + len(p) <= self.target_chunk_size:
                    current_chunk_text = f"{current_chunk_text}\n\n{p}".strip() if current_chunk_text else p
                else:
                    if current_chunk_text:
                        chunk_id = f"{document_id}_chk_{chunk_idx:04d}"
                        chunk_meta = {
                            **default_metadata,
                            "document_id": document_id,
                            "chunk_id": chunk_id,
                            "section": section_title,
                            "page_number": current_page,
                        }
                        chunks.append({
                            "chunk_id": chunk_id,
                            "text": current_chunk_text,
                            "metadata": chunk_meta,
                        })
                        chunk_idx += 1

                    # If paragraph itself is larger than target_chunk_size, split by sentences
                    if len(p) > self.target_chunk_size:
                        sentences = re.split(r'(?<=[.!?])\s+', p)
                        sub_text = ""
                        for sent in sentences:
                            if len(sub_text) + len(sent) <= self.target_chunk_size:
                                sub_text = f"{sub_text} {sent}".strip() if sub_text else sent
                            else:
                                if sub_text:
                                    chunk_id = f"{document_id}_chk_{chunk_idx:04d}"
                                    chunks.append({
                                        "chunk_id": chunk_id,
                                        "text": sub_text,
                                        "metadata": {
                                            **default_metadata,
                                            "document_id": document_id,
                                            "chunk_id": chunk_id,
                                            "section": section_title,
                                            "page_number": current_page,
                                        }
                                    })
                                    chunk_idx += 1
                                sub_text = sent
                        current_chunk_text = sub_text
                    else:
                        current_chunk_text = p

            if current_chunk_text:
                chunk_id = f"{document_id}_chk_{chunk_idx:04d}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": current_chunk_text,
                    "metadata": {
                        **default_metadata,
                        "document_id": document_id,
                        "chunk_id": chunk_id,
                        "section": section_title,
                        "page_number": current_page,
                    }
                })
                chunk_idx += 1

        return chunks
