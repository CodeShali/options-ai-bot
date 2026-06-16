"""Generate training pairs from vendor documentation pages."""

import json
import logging
from typing import Optional

from schemas.training_pair import TrainingPair, SourceCitation
from schemas.enums import SourceType, Domain, TaskType
from pipelines.shared.claude_client import ClaudeClient
from pipelines.p2_vendor_docs.normalizer import chunk_text

logger = logging.getLogger(__name__)

VENDOR_SYSTEM = """You are an expert IAM training data engineer.
Your task is to generate high-quality training pairs from vendor documentation.
Focus on practical, implementation-specific knowledge that users of this product would need.
Be technically precise and include concrete examples from the documentation."""

VENDOR_PAIR_PROMPT = """
Vendor: {vendor}
Product: {product}
Domain: {domain}
Source URL: {url}

Documentation Content:
---
{content}
---

Generate {n} diverse, high-quality training pairs from this vendor documentation.

Requirements:
1. Instructions should reflect real scenarios: configuration, troubleshooting, integration, security hardening.
2. Outputs should be specific to {vendor}/{product}, not generic IAM advice.
3. Include concrete examples, API calls, configuration snippets, or CLI commands where present in the docs.
4. Vary task types across the {n} pairs.
5. Reference the specific product features, settings, or capabilities mentioned in the content.
6. Outputs should be 150-600 words.

Return ONLY a JSON array:
[
  {{
    "instruction": "Specific question or task about {product}",
    "input_context": "Optional: relevant config/error/code from the docs (or null)",
    "output": "Detailed, vendor-specific answer",
    "task_type": "one of: explain_concept|answer_question|diagnose_problem|provide_solution|generate_query|assess_risk|review_access|map_compliance|audit_config|parse_assertion|explain_flow|remediate",
    "difficulty": "one of: beginner|intermediate|advanced|expert",
    "tags": ["vendor-specific", "tags"]
  }}
]
"""


class VendorToPairs:
    """Converts vendor documentation pages into training pairs using Claude."""

    def __init__(self, claude_client: Optional[ClaudeClient] = None):
        self.claude = claude_client or ClaudeClient()

    async def generate_for_page(
        self,
        page: dict,
        vendor: str,
        product: str,
        domain: Domain,
        n: int = 3,
    ) -> list[TrainingPair]:
        """
        Generate training pairs from a single documentation page.

        Args:
            page: Page dict with 'url', 'title', 'text' keys
            vendor: Vendor name (e.g. "Microsoft")
            product: Product name (e.g. "Entra ID")
            domain: IAM domain
            n: Number of pairs to generate per chunk

        Returns:
            List of TrainingPair objects
        """
        text = page.get("text", "")
        url = page.get("url", "")
        title = page.get("title", url)

        if len(text.strip()) < 200:
            logger.debug(f"Skipping short page: {url} ({len(text)} chars)")
            return []

        # Split long pages into chunks
        chunks = chunk_text(text, max_chunk_size=2500, min_chunk_size=200)
        if not chunks:
            chunks = [text[:2500]]

        all_pairs = []

        for chunk_idx, chunk in enumerate(chunks[:3]):  # Max 3 chunks per page
            prompt = VENDOR_PAIR_PROMPT.format(
                vendor=vendor,
                product=product,
                domain=domain.value,
                url=url,
                content=chunk,
                n=n,
            )

            logger.debug(
                f"Generating {n} pairs from {vendor}/{product} page chunk "
                f"{chunk_idx + 1}/{len(chunks)}: {url}"
            )

            try:
                raw_list = await self.claude.generate_json_list(
                    prompt=prompt,
                    system=VENDOR_SYSTEM,
                    max_tokens=3000,
                )
            except Exception as e:
                logger.error(f"Failed to generate pairs for {url}: {e}")
                continue

            citation = SourceCitation(
                source_id=f"{vendor.lower()}_{product.lower().replace(' ', '_')}",
                source_type=SourceType.VENDOR_DOC,
                title=f"{vendor} {product}: {title}",
                url=url,
            )

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

                    pair = TrainingPair(
                        domain=domain,
                        task_type=task_type,
                        source_type=SourceType.VENDOR_DOC,
                        difficulty=difficulty,
                        instruction=item.get("instruction", "").strip(),
                        input_context=item.get("input_context") or None,
                        output=item.get("output", "").strip(),
                        citations=[citation],
                        tags=item.get("tags", [vendor.lower(), product.lower()]),
                        pipeline_id=f"p2_{vendor.lower().replace(' ', '_')}",
                        metadata={
                            "vendor": vendor,
                            "product": product,
                            "source_url": url,
                            "page_title": title,
                        },
                    )
                    all_pairs.append(pair)
                except Exception as e:
                    logger.warning(f"Skipping invalid pair from {url}: {e}")
                    continue

        return all_pairs

    async def generate_pairs(
        self,
        pages: list[dict],
        vendor: str,
        product: str,
        domain: Domain,
        n_per_chunk: int = 3,
        max_pages: int = 50,
    ) -> list[TrainingPair]:
        """
        Generate training pairs from a list of vendor documentation pages.

        Args:
            pages: List of page dicts from the scraper
            vendor: Vendor name
            product: Product name
            domain: IAM domain
            n_per_chunk: Pairs to generate per content chunk
            max_pages: Maximum pages to process

        Returns:
            List of all generated TrainingPair objects
        """
        all_pairs = []
        pages_to_process = pages[:max_pages]

        logger.info(
            f"Generating pairs from {len(pages_to_process)} {vendor}/{product} pages"
        )

        for i, page in enumerate(pages_to_process):
            logger.info(
                f"Processing page {i + 1}/{len(pages_to_process)}: {page.get('url', 'unknown')}"
            )
            pairs = await self.generate_for_page(
                page=page,
                vendor=vendor,
                product=product,
                domain=domain,
                n=n_per_chunk,
            )
            all_pairs.extend(pairs)

        logger.info(
            f"Vendor docs complete for {vendor}/{product}: "
            f"{len(all_pairs)} pairs from {len(pages_to_process)} pages"
        )
        return all_pairs
