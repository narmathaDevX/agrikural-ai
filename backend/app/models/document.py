import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from app.database.base import Base, utc_now

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(100), primary_key=True)  # document_id
    title = Column(String(255), nullable=False)
    source = Column(String(255), default="Agricultural Extension Advisory")
    organization = Column(String(255), default="TNAU / ICAR")
    author = Column(String(255), default="Agronomy & Crop Physiology Dept")
    publication_date = Column(String(50), default="2024")
    crop = Column(String(100), index=True, default="General")
    crop_type = Column(String(100), default="Horticulture")
    state = Column(String(100), default="Tamil Nadu")
    district = Column(String(100), default="All")
    region = Column(String(100), index=True, default="South India")
    soil_type = Column(String(100), default="Red Loam / Clay Loam")
    topic = Column(String(100), index=True, default="Cultivation & Irrigation")
    language = Column(String(20), default="English")
    document_type = Column(String(50), default="Advisory Guide")  # PDF, TXT, DOCX
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    status = Column(String(50), default="indexed")  # indexed, processing, error
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
