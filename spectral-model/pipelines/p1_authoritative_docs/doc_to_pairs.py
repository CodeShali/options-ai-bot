"""Convert authoritative document chunks into training pairs via Claude."""

import json
import logging
from typing import Optional

from schemas.training_pair import TrainingPair, SourceCitation
from schemas.enums import SourceType, Domain, TaskType
from pipelines.shared.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

PAIR_GENERATION_SYSTEM = """You are an expert IAM (Identity and Access Management) training data engineer.
Your task is to generate high-quality instruction-output pairs from authoritative IAM documents.
Each pair must be technically accurate, specific, and directly grounded in the provided source content.
Do not include vague or generic content. Include specific details from the text."""

PAIR_GENERATION_PROMPT = """
Source: {source_name}
Source ID: {source_id}
Domain: {domain}

Section Content:
---
{section_content}
---

Generate {n} diverse, high-quality training pairs from this section content.

Requirements:
1. Each instruction should be a realistic question, task, or scenario an IAM engineer might face.
2. Outputs must be technically precise and grounded in the section content above.
3. Vary task types: explain concepts, solve problems, generate configurations, troubleshoot, assess security.
4. Include specific details (numbers, names, algorithms, error codes) where present in the text.
5. Outputs should be 150-800 words each.

Return ONLY a JSON array with this exact structure:
[
  {{
    "instruction": "Specific question or task",
    "input_context": "Optional additional context or config snippet (can be null)",
    "output": "Detailed, accurate answer grounded in the source",
    "task_type": "one of: explain_concept|answer_question|diagnose_problem|provide_solution|generate_query|assess_risk|review_access|map_compliance|audit_config|parse_assertion|explain_flow|remediate",
    "difficulty": "one of: beginner|intermediate|advanced|expert",
    "tags": ["list", "of", "relevant", "tags"]
  }}
]

Schema JSON for reference: {schema_json}
"""


class DocToPairs:
    """Converts authoritative document chunks to training pairs using Claude."""

    def __init__(self, claude_client: Optional[ClaudeClient] = None):
        self.claude = claude_client or ClaudeClient()

    def _build_schema_json(self) -> str:
        """Build a compact schema reference for the prompt."""
        return json.dumps({
            "instruction": "string (the question/task)",
            "input_context": "string or null",
            "output": "string (the answer, 150-800 words)",
            "task_type": "explain_concept|answer_question|diagnose_problem|provide_solution|generate_query|assess_risk|review_access|map_compliance|audit_config|parse_assertion|explain_flow|remediate",
            "difficulty": "beginner|intermediate|advanced|expert",
            "tags": ["tag1", "tag2"],
        }, indent=2)

    async def generate_pairs(
        self,
        chunks: list[dict],
        source_name: str,
        source_id: str,
        source_type: SourceType,
        domain: Domain,
        n_per_chunk: int = 5,
    ) -> list[TrainingPair]:
        """
        Generate training pairs from document chunks.

        Args:
            chunks: List of {section_number, title, content, ...} dicts
            source_name: Human-readable source name (e.g. "RFC 6749: OAuth 2.0")
            source_id: Machine source ID (e.g. "RFC6749")
            source_type: Type of source
            domain: IAM domain
            n_per_chunk: Number of pairs to generate per chunk

        Returns:
            List of validated TrainingPair objects
        """
        all_pairs = []

        for i, chunk in enumerate(chunks):
            section_content = chunk.get("content", "")
            section_num = chunk.get("section_number", str(i))
            section_title = chunk.get("title", "")

            if len(section_content.strip()) < 100:
                logger.debug(f"Skipping short chunk {section_num} ({len(section_content)} chars)")
                continue

            prompt = PAIR_GENERATION_PROMPT.format(
                source_name=source_name,
                source_id=source_id,
                domain=domain.value,
                section_content=section_content[:2500],  # Trim to avoid token limits
                n=n_per_chunk,
                schema_json=self._build_schema_json(),
            )

            logger.info(
                f"Generating {n_per_chunk} pairs from {source_id} section {section_num}: {section_title}"
            )

            try:
                raw_list = await self.claude.generate_json_list(
                    prompt=prompt,
                    system=PAIR_GENERATION_SYSTEM,
                    max_tokens=4096,
                )
            except Exception as e:
                logger.error(f"Failed to generate pairs for {source_id} section {section_num}: {e}")
                continue

            citation = SourceCitation(
                source_id=source_id,
                source_type=source_type,
                title=source_name,
                section=f"Section {section_num}: {section_title}",
            )

            for item in raw_list:
                if not isinstance(item, dict):
                    continue
                try:
                    # Validate and coerce task_type
                    task_type_str = item.get("task_type", "answer_question")
                    try:
                        task_type = TaskType(task_type_str)
                    except ValueError:
                        task_type = TaskType.ANSWER_QUESTION

                    # Validate difficulty
                    difficulty = item.get("difficulty", "intermediate")
                    if difficulty not in {"beginner", "intermediate", "advanced", "expert"}:
                        difficulty = "intermediate"

                    pair = TrainingPair(
                        domain=domain,
                        task_type=task_type,
                        source_type=source_type,
                        difficulty=difficulty,
                        instruction=item.get("instruction", "").strip(),
                        input_context=item.get("input_context") or None,
                        output=item.get("output", "").strip(),
                        citations=[citation],
                        tags=item.get("tags", []),
                        pipeline_id=f"p1_{source_type.value}",
                        metadata={
                            "source_id": source_id,
                            "section": section_num,
                            "section_title": section_title,
                        },
                    )
                    all_pairs.append(pair)

                except Exception as e:
                    logger.warning(f"Skipping invalid pair from {source_id} section {section_num}: {e}")
                    continue

            logger.info(
                f"Generated {len(all_pairs)} total pairs so far from {source_id}"
            )

        logger.info(
            f"Completed {source_id}: {len(all_pairs)} valid pairs from {len(chunks)} chunks"
        )
        return all_pairs
