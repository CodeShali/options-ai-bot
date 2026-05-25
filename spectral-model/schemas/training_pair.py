from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from schemas.enums import SourceType, Domain, TaskType
import uuid


class SourceCitation(BaseModel):
    source_id: str
    source_type: SourceType
    title: str
    url: Optional[str] = None
    section: Optional[str] = None
    quote: Optional[str] = None


class TrainingPair(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    domain: Domain
    task_type: TaskType
    source_type: SourceType
    difficulty: str = "intermediate"
    instruction: str
    input_context: Optional[str] = None
    output: str
    citations: list[SourceCitation] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    quality_score: float = 0.0
    pipeline_id: str = "unknown"
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

    @field_validator("output")
    @classmethod
    def output_min_length(cls, v: str) -> str:
        if len(v.strip()) < 50:
            raise ValueError(f"Output too short: {len(v.strip())} chars (min 50)")
        return v

    @field_validator("instruction")
    @classmethod
    def instruction_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Instruction cannot be empty")
        return v

    @field_validator("difficulty")
    @classmethod
    def valid_difficulty(cls, v: str) -> str:
        valid = {"beginner", "intermediate", "advanced", "expert"}
        if v not in valid:
            raise ValueError(f"Invalid difficulty '{v}', must be one of {valid}")
        return v

    @field_validator("quality_score")
    @classmethod
    def quality_score_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"quality_score must be between 0.0 and 1.0, got {v}")
        return v

    def to_messages(self) -> list[dict]:
        """Convert to OpenAI-style messages format."""
        system_msg = {
            "role": "system",
            "content": (
                "You are Spectral-IAM, an expert AI assistant specializing in Identity and "
                "Access Management, directory services, authentication protocols, privileged "
                "access management, and non-human identity security."
            ),
        }
        user_content = self.instruction
        if self.input_context:
            user_content = f"{self.instruction}\n\nContext:\n{self.input_context}"

        return [
            system_msg,
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": self.output},
        ]
