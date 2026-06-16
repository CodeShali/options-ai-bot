from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from schemas.enums import SourceType, Domain
import uuid


class DocumentChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    content: str
    parent_section: Optional[str] = None
    chunk_index: int = 0
    token_estimate: int = 0


class SourceDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: SourceType
    source_id: str
    source_url: Optional[str] = None
    title: str
    content: str
    domain: Optional[Domain] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    chunks: list[DocumentChunk] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
