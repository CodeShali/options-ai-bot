from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from schemas.enums import Domain, SourceType
import uuid


class RealWorldProblem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: SourceType
    source_url: str
    title: str
    problem_body: str
    solution_body: str
    score: int = 0
    tags: list[str] = Field(default_factory=list)
    domain: Optional[Domain] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)
