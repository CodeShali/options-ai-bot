"""Generate training pairs for a given IAM protocol topic using Claude."""

import json
import logging
from typing import Optional

from schemas.training_pair import TrainingPair, SourceCitation
from schemas.enums import SourceType, Domain, TaskType
from pipelines.shared.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

PROTOCOL_PAIR_PROMPT = """
You are an expert in {protocol} protocol and IAM systems.

Topic: {topic}
Subtopic: {subtopic}

Generate {n} diverse, high-quality training pairs covering this subtopic.
Each pair must be technically precise, cite specific RFCs/specs where applicable,
and cover different aspects:
- Concept explanation
- Worked example
- Troubleshooting scenario
- Security consideration

Requirements:
- Instructions should be realistic questions or tasks for IAM engineers
- Outputs must be specific and detailed (150-800 words)
- Include code examples, filter strings, or config snippets where appropriate
- Reference specific sections of RFCs or specifications
- Vary the difficulty levels

Return ONLY a JSON array matching: {schema_json}
"""

PROTOCOL_SYSTEM = """You are a senior IAM protocol expert and technical trainer.
Generate precise, actionable training data for an IAM AI model.
All information must be technically accurate. Cite specific RFCs, specs, or standards when possible.
Never include vague or generic content."""


class ProtocolToPairs:
    """Generates training pairs for specific IAM protocol topics."""

    def __init__(self, claude_client: Optional[ClaudeClient] = None):
        self.claude = claude_client or ClaudeClient()

    def _build_schema_json(self) -> str:
        return json.dumps([{
            "instruction": "Specific question or task",
            "input_context": "Optional context, config, or data snippet (can be null)",
            "output": "Detailed, accurate technical answer (150-800 words)",
            "task_type": "explain_concept|answer_question|diagnose_problem|provide_solution|generate_query|assess_risk|review_access|map_compliance|audit_config|parse_assertion|explain_flow|remediate",
            "difficulty": "beginner|intermediate|advanced|expert",
            "tags": ["list", "of", "tags"],
            "rfc_references": ["RFC4511", "RFC6749"],
        }], indent=2)

    async def generate_for_topic(
        self,
        protocol: str,
        topic: str,
        subtopic: str,
        domain: Domain,
        n: int = 5,
    ) -> list[TrainingPair]:
        """
        Generate training pairs for a specific protocol subtopic.

        Args:
            protocol: Protocol name (e.g. "LDAP", "OAuth 2.0")
            topic: Topic area (e.g. "filter_syntax")
            subtopic: Specific subtopic (e.g. "complex_filters")
            domain: IAM domain enum
            n: Number of pairs to generate

        Returns:
            List of TrainingPair objects
        """
        prompt = PROTOCOL_PAIR_PROMPT.format(
            protocol=protocol,
            topic=topic,
            subtopic=subtopic,
            n=n,
            schema_json=self._build_schema_json(),
        )

        logger.info(f"Generating {n} pairs for {protocol}/{topic}/{subtopic}")

        try:
            raw_list = await self.claude.generate_json_list(
                prompt=prompt,
                system=PROTOCOL_SYSTEM,
                max_tokens=4096,
            )
        except Exception as e:
            logger.error(f"Failed to generate pairs for {protocol}/{topic}/{subtopic}: {e}")
            return []

        pairs = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            try:
                task_type_str = item.get("task_type", "explain_concept")
                try:
                    task_type = TaskType(task_type_str)
                except ValueError:
                    task_type = TaskType.EXPLAIN_CONCEPT

                difficulty = item.get("difficulty", "intermediate")
                if difficulty not in {"beginner", "intermediate", "advanced", "expert"}:
                    difficulty = "intermediate"

                # Build citations from RFC references
                citations = []
                for rfc_ref in item.get("rfc_references", []):
                    rfc_upper = rfc_ref.upper().strip()
                    if rfc_upper.startswith("RFC"):
                        citations.append(SourceCitation(
                            source_id=rfc_upper,
                            source_type=SourceType.RFC,
                            title=f"{rfc_upper} ({protocol} specification)",
                        ))

                pair = TrainingPair(
                    domain=domain,
                    task_type=task_type,
                    source_type=SourceType.SYNTHETIC,
                    difficulty=difficulty,
                    instruction=item.get("instruction", "").strip(),
                    input_context=item.get("input_context") or None,
                    output=item.get("output", "").strip(),
                    citations=citations,
                    tags=item.get("tags", [protocol.lower(), topic, subtopic]),
                    pipeline_id=f"p3_{protocol.lower().replace(' ', '_').replace('.', '')}",
                    metadata={
                        "protocol": protocol,
                        "topic": topic,
                        "subtopic": subtopic,
                    },
                )
                pairs.append(pair)
            except Exception as e:
                logger.warning(
                    f"Skipping invalid pair for {protocol}/{topic}/{subtopic}: {e}"
                )
                continue

        logger.info(
            f"Generated {len(pairs)} valid pairs for {protocol}/{topic}/{subtopic}"
        )
        return pairs
