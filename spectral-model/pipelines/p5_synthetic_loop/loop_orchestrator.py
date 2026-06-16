"""Synthetic loop: invent → solve → critique → refine pipeline."""

import json
import logging
import asyncio
from typing import Optional

from schemas.training_pair import TrainingPair, SourceCitation
from schemas.enums import SourceType, Domain, TaskType
from pipelines.shared.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

# ── Prompts ────────────────────────────────────────────────────────────────────

INVENT_PROMPT = """
You are an IAM (Identity and Access Management) expert creating training scenarios.

Domain: {domain}
Task Type: {task_type}
Difficulty: {difficulty}

Invent a realistic, specific IAM problem or question for this domain and task type.
The problem should be:
- Technically realistic and grounded in real-world IAM engineering
- Specific enough to have a concrete answer (not vague)
- At the {difficulty} difficulty level
- Something an IAM engineer would actually encounter

If the task type involves configuration or code, include a realistic snippet as input context.

Return ONLY a JSON object:
{{
    "instruction": "The specific question or task description",
    "input_context": "Optional: relevant config/code/data snippet (or null)",
    "tags": ["relevant", "tags", "for", "this", "problem"]
}}
"""

SOLVE_PROMPT = """
You are a senior IAM engineer with deep expertise in {domain}.

Problem:
{instruction}

{context_section}

Provide a comprehensive, technically accurate solution.

Requirements:
- Be specific and concrete, not vague
- Include working code examples or configuration snippets where relevant
- Reference specific RFCs, standards, or specifications
- Explain the 'why' not just the 'what'
- Cover relevant security considerations
- Structure your answer clearly
- Aim for 300-600 words

Your solution:
"""

CRITIQUE_PROMPT = """
You are a senior IAM training data quality reviewer.

Review this training pair for quality:

INSTRUCTION: {instruction}

OUTPUT: {output}

Evaluate on these criteria (score each 1-5):
1. Technical accuracy: Is the information correct?
2. Specificity: Does it cite standards, RFCs, concrete examples?
3. Completeness: Does it fully address the question?
4. Clarity: Is it well-structured and clear?
5. Educational value: Would this help train an IAM AI assistant?

Return ONLY a JSON object:
{{
    "scores": {{
        "technical_accuracy": <1-5>,
        "specificity": <1-5>,
        "completeness": <1-5>,
        "clarity": <1-5>,
        "educational_value": <1-5>
    }},
    "overall_score": <1.0-5.0 average>,
    "issues": ["list", "of", "specific", "issues"],
    "suggestions": ["list", "of", "improvement", "suggestions"],
    "accept": <true if overall_score >= 3.5, false otherwise>
}}
"""

REFINE_PROMPT = """
You are a senior IAM engineer improving a training data response.

Original instruction:
{instruction}

Original output (which had issues):
{original_output}

Issues identified by reviewer:
{issues}

Suggestions for improvement:
{suggestions}

Rewrite the output to address all the issues. Make it:
- Technically precise and accurate
- Well-structured with clear sections
- Include concrete examples, code, or config where appropriate
- Reference relevant RFCs or specifications
- 300-600 words

Improved output:
"""


class SyntheticLoop:
    """
    Synthetic data generation loop: Invent → Solve → Critique → Refine.

    For each iteration:
    1. Invent: Generate a realistic IAM problem
    2. Solve: Generate a comprehensive solution
    3. Critique: Score the pair on quality criteria
    4. Refine: If score is low, improve the solution
    """

    ACCEPT_THRESHOLD = 3.5  # Minimum average score (out of 5) to accept

    def __init__(
        self,
        claude_client: Optional[ClaudeClient] = None,
        max_refinements: int = 2,
    ):
        self.claude = claude_client or ClaudeClient()
        self.max_refinements = max_refinements

    async def _invent_problem(
        self,
        domain: Domain,
        task_type: TaskType,
        difficulty: str,
    ) -> dict:
        """Invent a realistic IAM problem."""
        prompt = INVENT_PROMPT.format(
            domain=domain.value,
            task_type=task_type.value,
            difficulty=difficulty,
        )

        system = (
            "You are an IAM expert creating realistic training scenarios. "
            "Return only valid JSON, no markdown fences."
        )

        raw_list = await self.claude.generate_json_list(
            prompt=prompt,
            system=system,
            max_tokens=1024,
        )

        if isinstance(raw_list, list) and raw_list:
            item = raw_list[0]
        elif isinstance(raw_list, dict):
            item = raw_list
        else:
            return {
                "instruction": f"Explain a key concept in {domain.value} related to {task_type.value}",
                "input_context": None,
                "tags": [domain.value, task_type.value],
            }

        return item if isinstance(item, dict) else {
            "instruction": f"Explain a key concept in {domain.value} related to {task_type.value}",
            "input_context": None,
            "tags": [domain.value, task_type.value],
        }

    async def _solve(
        self,
        domain: Domain,
        instruction: str,
        input_context: Optional[str],
    ) -> str:
        """Generate a solution for the problem."""
        context_section = ""
        if input_context:
            context_section = f"Context/Input:\n```\n{input_context}\n```\n"

        prompt = SOLVE_PROMPT.format(
            domain=domain.value,
            instruction=instruction,
            context_section=context_section,
        )

        system = (
            f"You are a senior IAM engineer specializing in {domain.value}. "
            "Provide technically precise, comprehensive solutions."
        )

        return await self.claude.generate(prompt, system, max_tokens=2048)

    async def _critique(self, instruction: str, output: str) -> dict:
        """Critique the quality of an instruction-output pair."""
        prompt = CRITIQUE_PROMPT.format(
            instruction=instruction,
            output=output[:3000],
        )

        system = (
            "You are an IAM training data quality reviewer. "
            "Return only valid JSON, no markdown fences."
        )

        try:
            raw_list = await self.claude.generate_json_list(
                prompt=prompt,
                system=system,
                max_tokens=1024,
            )
            if isinstance(raw_list, list) and raw_list:
                result = raw_list[0]
            elif isinstance(raw_list, dict):
                result = raw_list
            else:
                result = {}
        except Exception as e:
            logger.warning(f"Critique parsing failed: {e}")
            result = {}

        # Ensure required fields with defaults
        if "scores" not in result:
            result["scores"] = {
                "technical_accuracy": 3,
                "specificity": 3,
                "completeness": 3,
                "clarity": 3,
                "educational_value": 3,
            }
        if "overall_score" not in result:
            scores = list(result["scores"].values())
            result["overall_score"] = sum(scores) / len(scores) if scores else 3.0
        if "issues" not in result:
            result["issues"] = []
        if "suggestions" not in result:
            result["suggestions"] = []
        if "accept" not in result:
            result["accept"] = result["overall_score"] >= self.ACCEPT_THRESHOLD

        return result

    async def _refine(
        self,
        instruction: str,
        original_output: str,
        critique: dict,
    ) -> str:
        """Refine the output based on critique feedback."""
        issues_str = "\n".join(f"- {issue}" for issue in critique.get("issues", []))
        suggestions_str = "\n".join(
            f"- {s}" for s in critique.get("suggestions", [])
        )

        prompt = REFINE_PROMPT.format(
            instruction=instruction,
            original_output=original_output[:2000],
            issues=issues_str or "No specific issues listed",
            suggestions=suggestions_str or "Improve technical depth and specificity",
        )

        system = (
            "You are a senior IAM engineer. Improve the training data response based on feedback. "
            "Be specific, cite standards, include examples."
        )

        return await self.claude.generate(prompt, system, max_tokens=2048)

    async def generate_pair(
        self,
        domain: Domain,
        task_type: TaskType,
        difficulty: str = "intermediate",
    ) -> Optional[TrainingPair]:
        """
        Run the full invent → solve → critique → refine loop.

        Args:
            domain: IAM domain
            task_type: Type of task
            difficulty: Difficulty level

        Returns:
            TrainingPair if accepted, None if quality threshold not met
        """
        logger.debug(f"Synthetic loop: {domain.value}/{task_type.value}/{difficulty}")

        # Step 1: Invent problem
        try:
            problem = await self._invent_problem(domain, task_type, difficulty)
        except Exception as e:
            logger.error(f"Invent failed for {domain.value}/{task_type.value}: {e}")
            return None

        instruction = problem.get("instruction", "").strip()
        input_context = problem.get("input_context") or None
        tags = problem.get("tags", [domain.value, task_type.value])

        if not instruction:
            logger.warning("Invent returned empty instruction, skipping")
            return None

        # Step 2: Solve
        try:
            output = await self._solve(domain, instruction, input_context)
        except Exception as e:
            logger.error(f"Solve failed for '{instruction[:50]}': {e}")
            return None

        # Step 3: Critique → Refine loop
        critique = None
        for refinement_attempt in range(self.max_refinements + 1):
            try:
                critique = await self._critique(instruction, output)
            except Exception as e:
                logger.warning(f"Critique failed on attempt {refinement_attempt}: {e}")
                break

            overall_score = critique.get("overall_score", 0)
            accepted = critique.get("accept", False)

            logger.debug(
                f"Critique score: {overall_score:.2f} "
                f"({'ACCEPT' if accepted else 'REFINE'})"
            )

            if accepted or refinement_attempt >= self.max_refinements:
                break

            # Refine
            try:
                output = await self._refine(instruction, output, critique)
            except Exception as e:
                logger.warning(f"Refinement failed: {e}")
                break

        if not critique:
            critique = {"overall_score": 0.0, "accept": False}

        if not critique.get("accept", False):
            logger.debug(
                f"Pair rejected (score={critique.get('overall_score', 0):.2f}): "
                f"{instruction[:60]}..."
            )
            return None

        # Convert 1-5 score to 0-1 quality score
        quality_score = min(1.0, critique.get("overall_score", 3.0) / 5.0)

        try:
            pair = TrainingPair(
                domain=domain,
                task_type=task_type,
                source_type=SourceType.SYNTHETIC_LOOP,
                difficulty=difficulty,
                instruction=instruction,
                input_context=input_context,
                output=output.strip(),
                citations=[],
                tags=tags,
                quality_score=quality_score,
                pipeline_id="p5_synthetic_loop",
                metadata={
                    "critique_score": critique.get("overall_score", 0),
                    "critique_scores": critique.get("scores", {}),
                    "refinement_rounds": refinement_attempt,
                },
            )
            return pair
        except Exception as e:
            logger.warning(f"Failed to create TrainingPair: {e}")
            return None

    async def generate_batch(
        self,
        domain: Domain | str,
        task_type: TaskType | str,
        count: int,
        difficulty: str = "intermediate",
        max_concurrent: int = 3,
    ) -> list[TrainingPair]:
        """
        Generate a batch of synthetic training pairs.

        Args:
            domain: IAM domain (enum or string value)
            task_type: Task type (enum or string value)
            count: Number of pairs to attempt
            difficulty: Difficulty level
            max_concurrent: Max concurrent generation tasks

        Returns:
            List of accepted TrainingPairs
        """
        # Normalize enums
        if isinstance(domain, str):
            domain = Domain(domain)
        if isinstance(task_type, str):
            task_type = TaskType(task_type)

        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_one(_: int) -> Optional[TrainingPair]:
            async with semaphore:
                return await self.generate_pair(domain, task_type, difficulty)

        logger.info(
            f"Generating {count} synthetic pairs for {domain.value}/{task_type.value}"
        )

        results = await asyncio.gather(
            *[generate_one(i) for i in range(count)],
            return_exceptions=True,
        )

        pairs = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch generation error: {result}")
            elif result is not None:
                pairs.append(result)

        logger.info(
            f"Synthetic batch complete: {len(pairs)}/{count} pairs accepted "
            f"({len(pairs) / count * 100:.0f}% acceptance rate)"
        )
        return pairs

    async def generate_multi_domain_batch(
        self,
        domain_task_pairs: list[tuple[Domain, TaskType]],
        count_per_pair: int = 10,
        difficulty: str = "intermediate",
    ) -> list[TrainingPair]:
        """
        Generate pairs across multiple domain/task combinations.

        Args:
            domain_task_pairs: List of (domain, task_type) tuples
            count_per_pair: Pairs per combination
            difficulty: Difficulty level

        Returns:
            All accepted pairs
        """
        all_pairs = []

        for domain, task_type in domain_task_pairs:
            pairs = await self.generate_batch(
                domain=domain,
                task_type=task_type,
                count=count_per_pair,
                difficulty=difficulty,
            )
            all_pairs.extend(pairs)
            logger.info(
                f"Completed {domain.value}/{task_type.value}: {len(pairs)} pairs"
            )

        logger.info(
            f"Multi-domain batch complete: {len(all_pairs)} total pairs"
        )
        return all_pairs
