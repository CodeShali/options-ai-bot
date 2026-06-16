"""JSONL writer for training pairs."""

import json
from pathlib import Path

from schemas.training_pair import TrainingPair
from config.settings import settings


class JSONLWriter:
    def __init__(self):
        settings.processed_dir.mkdir(parents=True, exist_ok=True)
        self._handles: dict[str, object] = {}

    def write(self, pair: TrainingPair) -> None:
        """Write a training pair to domain-specific and unified JSONL files."""
        domain = pair.domain.value
        path = settings.processed_dir / f"{domain}.jsonl"
        unified = settings.processed_dir / "spectral_iam_full.jsonl"

        record = self._to_record(pair)
        line = json.dumps(record, default=str) + "\n"

        for p in [path, unified]:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(line)

    def _to_record(self, pair: TrainingPair) -> dict:
        return {
            "id": pair.id,
            "domain": pair.domain.value,
            "task_type": pair.task_type.value,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Spectral-IAM, an expert AI assistant specializing in Identity "
                        "and Access Management, directory services, authentication protocols, "
                        "privileged access management, and non-human identity security."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        pair.instruction
                        if not pair.input_context
                        else f"{pair.instruction}\n\nContext:\n{pair.input_context}"
                    ),
                },
                {"role": "assistant", "content": pair.output},
            ],
            "citations": [c.model_dump() for c in pair.citations],
            "metadata": {
                "quality_score": pair.quality_score,
                "pipeline_id": pair.pipeline_id,
                "difficulty": pair.difficulty,
                "tags": pair.tags,
                "source_type": pair.source_type.value,
                "generated_at": pair.generated_at.isoformat(),
                **pair.metadata,
            },
        }

    def count_pairs(self) -> dict[str, int]:
        """Count pairs written per domain file."""
        counts = {}
        if settings.processed_dir.exists():
            for f in settings.processed_dir.glob("*.jsonl"):
                if f.name == "spectral_iam_full.jsonl":
                    continue
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        counts[f.stem] = sum(1 for _ in fp)
                except Exception:
                    counts[f.stem] = 0
        return counts
