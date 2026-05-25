"""Convert real-world Stack Overflow / Reddit problems into training pairs."""

import logging
from typing import Optional

from schemas.training_pair import TrainingPair, SourceCitation
from schemas.problem import RealWorldProblem
from schemas.enums import SourceType, Domain, TaskType
from pipelines.shared.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

PROBLEM_TO_PAIR_SYSTEM = """You are an expert IAM engineer and training data curator.
Your task is to transform real-world IAM problems into high-quality training pairs.
The instruction should capture the essence of the problem.
The output should be a clear, accurate, technically precise solution."""

PROBLEM_TO_PAIR_PROMPT = """
Transform this real-world IAM problem into a training pair.

Title: {title}
Source: {source_url}
Tags: {tags}
Score: {score}

Problem:
---
{problem_body}
---

Solution/Answer:
---
{solution_body}
---

Create a single high-quality training pair:
1. The "instruction" should be a well-formed question or task based on the problem
2. The "output" should synthesize and improve on the solution, making it technically precise
3. If the solution has errors or is incomplete, correct them
4. Add relevant technical context (RFC references, standards, best practices)
5. Format code examples properly with markdown code blocks
6. Aim for 200-600 words in the output

Return a JSON object:
{{
    "instruction": "Clear, specific question or task",
    "input_context": "Relevant config/code from the problem (or null if none)",
    "output": "Comprehensive, accurate, well-structured answer",
    "task_type": "one of: explain_concept|answer_question|diagnose_problem|provide_solution|generate_query|assess_risk|review_access|map_compliance|audit_config|parse_assertion|explain_flow|remediate",
    "difficulty": "one of: beginner|intermediate|advanced|expert",
    "tags": ["relevant", "tags"],
    "domain": "one of: ldap|saml|oauth|oidc|scim|kerberos|webauthn_fido|active_directory|azure_ad_entra|aws_iam|gcp_iam|okta|sso_federation|iga_provisioning|pam|nhi|ai_agent_identity|mfa|zero_trust|compliance"
}}
"""

# Domain tag mapping for Stack Overflow tags
SO_TAG_TO_DOMAIN = {
    "ldap": Domain.LDAP,
    "active-directory": Domain.ACTIVE_DIRECTORY,
    "azure-active-directory": Domain.AZURE_AD_ENTRA,
    "azure-ad": Domain.AZURE_AD_ENTRA,
    "azure-ad-b2c": Domain.AZURE_AD_ENTRA,
    "msal": Domain.AZURE_AD_ENTRA,
    "oauth-2.0": Domain.OAUTH,
    "oauth": Domain.OAUTH,
    "jwt": Domain.OAUTH,
    "pkce": Domain.OAUTH,
    "dpop": Domain.OAUTH,
    "openid-connect": Domain.OIDC,
    "oidc": Domain.OIDC,
    "saml": Domain.SAML,
    "saml-2.0": Domain.SAML,
    "kerberos": Domain.KERBEROS,
    "scim": Domain.SCIM,
    "webauthn": Domain.WEBAUTHN_FIDO,
    "fido2": Domain.WEBAUTHN_FIDO,
    "okta": Domain.OKTA,
    "aws-iam": Domain.AWS_IAM,
    "aws-cognito": Domain.AWS_IAM,
    "google-cloud-iam": Domain.GCP_IAM,
    "hashicorp-vault": Domain.PAM,
    "cyberark": Domain.PAM,
    "privileged-access-management": Domain.PAM,
    "zero-trust": Domain.ZERO_TRUST,
    "keycloak": Domain.SSO_FEDERATION,
    "sso": Domain.SSO_FEDERATION,
    "adfs": Domain.ACTIVE_DIRECTORY,
    "identity": Domain.COMPLIANCE,
}


def _infer_domain_from_tags(tags: list[str]) -> Optional[Domain]:
    """Infer IAM domain from Stack Overflow tags."""
    for tag in tags:
        tag_lower = tag.lower()
        if tag_lower in SO_TAG_TO_DOMAIN:
            return SO_TAG_TO_DOMAIN[tag_lower]
    return None


class ProblemsToPairs:
    """Converts real-world IAM problems into training pairs using Claude."""

    def __init__(self, claude_client: Optional[ClaudeClient] = None):
        self.claude = claude_client or ClaudeClient()

    async def convert(self, problem: RealWorldProblem) -> Optional[TrainingPair]:
        """
        Convert a RealWorldProblem into a TrainingPair.

        Args:
            problem: The real-world problem to convert

        Returns:
            TrainingPair if successful, None if conversion fails
        """
        if not problem.solution_body or len(problem.solution_body.strip()) < 50:
            logger.debug(f"Skipping problem with no/short solution: {problem.title}")
            return None

        if len(problem.problem_body.strip()) < 30:
            logger.debug(f"Skipping problem with no/short body: {problem.title}")
            return None

        prompt = PROBLEM_TO_PAIR_PROMPT.format(
            title=problem.title,
            source_url=problem.source_url,
            tags=", ".join(problem.tags),
            score=problem.score,
            problem_body=problem.problem_body[:2000],
            solution_body=problem.solution_body[:2000],
        )

        logger.debug(f"Converting problem: {problem.title[:60]}")

        try:
            raw = await self.claude.generate_json_list(
                prompt=prompt,
                system=PROBLEM_TO_PAIR_SYSTEM,
                max_tokens=2048,
            )
            # Expects a single object wrapped in list, or just the object
            if isinstance(raw, list) and raw:
                item = raw[0]
            elif isinstance(raw, dict):
                item = raw
            else:
                logger.warning(f"Unexpected response type for problem: {problem.title}")
                return None
        except Exception as e:
            logger.error(f"Claude error converting problem '{problem.title}': {e}")
            return None

        if not isinstance(item, dict):
            return None

        try:
            # Infer domain
            domain_str = item.get("domain", "")
            try:
                domain = Domain(domain_str) if domain_str else (problem.domain or Domain.COMPLIANCE)
            except ValueError:
                domain = problem.domain or Domain.COMPLIANCE

            task_type_str = item.get("task_type", "diagnose_problem")
            try:
                task_type = TaskType(task_type_str)
            except ValueError:
                task_type = TaskType.DIAGNOSE_PROBLEM

            difficulty = item.get("difficulty", "intermediate")
            if difficulty not in {"beginner", "intermediate", "advanced", "expert"}:
                difficulty = "intermediate"

            citation = SourceCitation(
                source_id=f"so_{problem.metadata.get('question_id', problem.id)}",
                source_type=problem.source_type,
                title=problem.title,
                url=problem.source_url,
            )

            pair = TrainingPair(
                domain=domain,
                task_type=task_type,
                source_type=problem.source_type,
                difficulty=difficulty,
                instruction=item.get("instruction", problem.title).strip(),
                input_context=item.get("input_context") or None,
                output=item.get("output", "").strip(),
                citations=[citation],
                tags=item.get("tags", problem.tags),
                pipeline_id="p4_stackoverflow",
                metadata={
                    "source_url": problem.source_url,
                    "score": problem.score,
                    "original_title": problem.title,
                },
            )
            return pair

        except Exception as e:
            logger.warning(f"Failed to create TrainingPair from problem '{problem.title}': {e}")
            return None

    async def convert_so_question(self, question_data: dict) -> Optional[TrainingPair]:
        """
        Convert a Stack Overflow question dict directly into a TrainingPair.

        Args:
            question_data: Dict from stackoverflow_fetcher with question/answer info

        Returns:
            TrainingPair if successful, None otherwise
        """
        if not question_data.get("answer_body"):
            return None

        tags = question_data.get("tags", [])
        domain = _infer_domain_from_tags(tags)

        problem = RealWorldProblem(
            source_type=SourceType.STACK_OVERFLOW,
            source_url=question_data.get("link", ""),
            title=question_data.get("title", ""),
            problem_body=question_data.get("body", ""),
            solution_body=question_data.get("answer_body", ""),
            score=question_data.get("score", 0),
            tags=tags,
            domain=domain,
            metadata={
                "question_id": question_data.get("question_id"),
                "accepted_answer_id": question_data.get("accepted_answer_id"),
                "view_count": question_data.get("view_count", 0),
                "answer_score": question_data.get("answer_score", 0),
            },
        )

        return await self.convert(problem)

    async def convert_batch(
        self,
        questions: list[dict],
        max_concurrent: int = 3,
    ) -> list[TrainingPair]:
        """
        Convert a batch of Stack Overflow questions concurrently.

        Args:
            questions: List of question dicts from stackoverflow_fetcher
            max_concurrent: Max concurrent conversions

        Returns:
            List of successfully created TrainingPairs
        """
        import asyncio
        semaphore = asyncio.Semaphore(max_concurrent)

        async def convert_one(q: dict) -> Optional[TrainingPair]:
            async with semaphore:
                return await self.convert_so_question(q)

        results = await asyncio.gather(
            *[convert_one(q) for q in questions],
            return_exceptions=True,
        )

        pairs = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch conversion error: {result}")
            elif result is not None:
                pairs.append(result)

        logger.info(
            f"Batch conversion complete: {len(pairs)}/{len(questions)} pairs created"
        )
        return pairs
