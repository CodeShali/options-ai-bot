"""Pipeline runner: orchestrates all sub-pipelines with quality filtering and dedup."""

import asyncio
import logging
import uuid
from typing import Optional

from schemas.training_pair import TrainingPair
from schemas.enums import Domain, SourceType
from pipelines.shared.claude_client import ClaudeClient
from pipelines.shared.dedup import SemanticDedup
from pipelines.shared.quality_filter import QualityFilter
from storage.db import Database
from storage.jsonl_writer import JSONLWriter
from config.settings import settings

logger = logging.getLogger(__name__)


class PipelineRunner:
    """
    Central pipeline runner that wires together all sub-pipelines.

    Responsibilities:
    - Run individual pipeline modules
    - Apply quality filtering
    - Apply semantic deduplication
    - Save accepted pairs to JSONL and DB
    - Track pipeline run statistics
    """

    def __init__(
        self,
        claude: ClaudeClient,
        dedup: SemanticDedup,
        quality: QualityFilter,
        writer: JSONLWriter,
        db: Database,
    ):
        self.claude = claude
        self.dedup = dedup
        self.quality = quality
        self.writer = writer
        self.db = db

    async def _process_pairs(
        self,
        pairs: list[TrainingPair],
        pipeline_id: str,
        run_id: str,
    ) -> tuple[int, int, int]:
        """
        Apply quality filter + dedup to a list of pairs, then save accepted ones.

        Returns:
            (generated, accepted, rejected) counts
        """
        generated = len(pairs)
        accepted = 0
        rejected = 0

        for pair in pairs:
            # Save as candidate
            await self.db.save_candidate_pair(pair)

            # Quality filter
            passed, failures = self.quality.validate(pair)
            if not passed:
                logger.debug(
                    f"Pair {pair.id} failed quality ({len(failures)} failures): "
                    f"{failures[0] if failures else ''}"
                )
                rejected += 1
                continue

            # Compute quality score
            quality_score = self.quality.score(pair)
            if quality_score < settings.quality_score_threshold:
                logger.debug(
                    f"Pair {pair.id} quality score {quality_score:.3f} "
                    f"< threshold {settings.quality_score_threshold}"
                )
                rejected += 1
                continue

            pair.quality_score = quality_score

            # Dedup check
            text = f"{pair.instruction} {pair.output[:500]}"
            is_dup = await self.dedup.is_duplicate(text)
            if is_dup:
                logger.debug(f"Pair {pair.id} is a duplicate, skipping")
                rejected += 1
                continue

            # Accept: add to dedup store, save to DB and JSONL
            await self.dedup.add(text, pair.id, {"domain": pair.domain.value})
            await self.db.accept_pair(pair)
            self.writer.write(pair)
            accepted += 1

        logger.info(
            f"[{pipeline_id}] run {run_id}: "
            f"{generated} generated, {accepted} accepted, {rejected} rejected"
        )
        return generated, accepted, rejected

    async def run_p1_rfcs(self, rfc_ids: list[str]) -> int:
        """
        Fetch RFCs and generate training pairs.

        Args:
            rfc_ids: List of RFC IDs (e.g. ["RFC4511", "RFC6749"])

        Returns:
            Number of accepted pairs
        """
        from pipelines.p1_authoritative_docs.rfc_fetcher import RFCFetcher
        from pipelines.p1_authoritative_docs.doc_to_pairs import DocToPairs

        pipeline_id = "p1_rfcs"
        run_id = str(uuid.uuid4())
        await self.db.start_pipeline_run(run_id, pipeline_id)

        fetcher = RFCFetcher()
        generator = DocToPairs(self.claude)

        # RFC ID → Domain mapping
        rfc_domain_map = {
            "RFC4510": Domain.LDAP, "RFC4511": Domain.LDAP, "RFC4512": Domain.LDAP,
            "RFC4513": Domain.LDAP, "RFC4514": Domain.LDAP, "RFC4515": Domain.LDAP,
            "RFC4516": Domain.LDAP, "RFC4517": Domain.LDAP, "RFC4518": Domain.LDAP,
            "RFC4519": Domain.LDAP, "RFC4522": Domain.LDAP, "RFC4523": Domain.LDAP,
            "RFC4524": Domain.LDAP, "RFC4525": Domain.LDAP, "RFC4526": Domain.LDAP,
            "RFC4529": Domain.LDAP, "RFC3062": Domain.LDAP, "RFC3672": Domain.LDAP,
            "RFC3673": Domain.LDAP, "RFC2696": Domain.LDAP, "RFC2891": Domain.LDAP,
            "RFC4533": Domain.LDAP, "RFC3909": Domain.LDAP,
            "RFC6749": Domain.OAUTH, "RFC6750": Domain.OAUTH, "RFC7009": Domain.OAUTH,
            "RFC7519": Domain.OAUTH, "RFC7521": Domain.OAUTH, "RFC7523": Domain.OAUTH,
            "RFC7636": Domain.OAUTH, "RFC7591": Domain.OAUTH, "RFC7592": Domain.OAUTH,
            "RFC8414": Domain.OAUTH, "RFC8628": Domain.OAUTH, "RFC8693": Domain.OAUTH,
            "RFC9068": Domain.OAUTH, "RFC9101": Domain.OAUTH, "RFC9126": Domain.OAUTH,
            "RFC9449": Domain.OAUTH, "RFC7662": Domain.OAUTH,
            "RFC7515": Domain.OAUTH, "RFC7516": Domain.OAUTH, "RFC7517": Domain.OAUTH,
            "RFC7518": Domain.OAUTH,
            "RFC4120": Domain.KERBEROS, "RFC4121": Domain.KERBEROS,
            "RFC6113": Domain.KERBEROS, "RFC4556": Domain.KERBEROS,
            "RFC6806": Domain.KERBEROS,
            "RFC7642": Domain.SCIM, "RFC7643": Domain.SCIM, "RFC7644": Domain.SCIM,
            "RFC4422": Domain.LDAP, "RFC4616": Domain.LDAP, "RFC5801": Domain.LDAP,
        }

        total_accepted = 0
        total_generated = 0
        total_rejected = 0
        error_msg = None

        try:
            for rfc_id in rfc_ids:
                rfc_upper = rfc_id.upper()
                domain = rfc_domain_map.get(rfc_upper, Domain.COMPLIANCE)

                try:
                    logger.info(f"Processing {rfc_upper} (domain: {domain.value})")
                    chunks = await fetcher.fetch_and_chunk(rfc_id)

                    pairs = await generator.generate_pairs(
                        chunks=chunks,
                        source_name=f"{rfc_upper}",
                        source_id=rfc_upper,
                        source_type=SourceType.RFC,
                        domain=domain,
                        n_per_chunk=5,
                    )

                    gen, acc, rej = await self._process_pairs(pairs, pipeline_id, run_id)
                    total_generated += gen
                    total_accepted += acc
                    total_rejected += rej

                except Exception as e:
                    logger.error(f"Error processing {rfc_id}: {e}")
                    continue

        except Exception as e:
            error_msg = str(e)
            logger.error(f"P1 RFC pipeline error: {e}")
        finally:
            await self.db.end_pipeline_run(
                run_id, total_generated, total_accepted, total_rejected, error_msg
            )

        logger.info(f"P1 RFCs complete: {total_accepted} pairs accepted")
        return total_accepted

    async def run_p3_ldap(self, n_per_subtopic: int = 5) -> int:
        """
        Build LDAP corpus using the protocol topic taxonomy.

        Returns:
            Number of accepted pairs
        """
        from pipelines.p3_protocols.ldap_corpus import build_ldap_corpus

        pipeline_id = "p3_ldap"
        run_id = str(uuid.uuid4())
        await self.db.start_pipeline_run(run_id, pipeline_id)

        total_accepted = 0
        total_generated = 0
        total_rejected = 0
        error_msg = None

        try:
            pairs = await build_ldap_corpus(
                n_per_subtopic=n_per_subtopic,
                claude_client=self.claude,
            )

            gen, acc, rej = await self._process_pairs(pairs, pipeline_id, run_id)
            total_generated, total_accepted, total_rejected = gen, acc, rej

        except Exception as e:
            error_msg = str(e)
            logger.error(f"P3 LDAP pipeline error: {e}")
        finally:
            await self.db.end_pipeline_run(
                run_id, total_generated, total_accepted, total_rejected, error_msg
            )

        logger.info(f"P3 LDAP complete: {total_accepted} pairs accepted")
        return total_accepted

    async def run_p4_stackoverflow(
        self,
        tags: list[str],
        min_score: int = 5,
    ) -> int:
        """
        Fetch Stack Overflow Q&A and convert to training pairs.

        Args:
            tags: Stack Overflow tags to fetch
            min_score: Minimum question score

        Returns:
            Number of accepted pairs
        """
        from pipelines.p4_real_problems.stackoverflow_fetcher import fetch_questions_by_tag
        from pipelines.p4_real_problems.problems_to_pairs import ProblemsToPairs

        pipeline_id = "p4_stackoverflow"
        run_id = str(uuid.uuid4())
        await self.db.start_pipeline_run(run_id, pipeline_id)

        converter = ProblemsToPairs(self.claude)
        total_accepted = 0
        total_generated = 0
        total_rejected = 0
        error_msg = None

        try:
            for tag in tags:
                logger.info(f"Fetching Stack Overflow questions: [{tag}]")
                try:
                    questions = await fetch_questions_by_tag(
                        tag=tag,
                        min_score=min_score,
                        has_accepted=True,
                        page_size=50,
                        max_pages=3,
                    )

                    pairs = await converter.convert_batch(questions, max_concurrent=2)

                    gen, acc, rej = await self._process_pairs(pairs, pipeline_id, run_id)
                    total_generated += gen
                    total_accepted += acc
                    total_rejected += rej

                except Exception as e:
                    logger.error(f"Error processing SO tag [{tag}]: {e}")
                    continue

        except Exception as e:
            error_msg = str(e)
            logger.error(f"P4 Stack Overflow pipeline error: {e}")
        finally:
            await self.db.end_pipeline_run(
                run_id, total_generated, total_accepted, total_rejected, error_msg
            )

        logger.info(f"P4 Stack Overflow complete: {total_accepted} pairs accepted")
        return total_accepted

    async def run_p5_synthetic(
        self,
        domain: str,
        count: int,
        task_types: Optional[list[str]] = None,
        difficulty: str = "intermediate",
    ) -> int:
        """
        Run synthetic loop generation for a domain.

        Args:
            domain: Domain value string (e.g. "oauth", "ldap")
            count: Number of pairs to attempt generating
            task_types: Optional list of task type values to use (cycles through them)
            difficulty: Difficulty level

        Returns:
            Number of accepted pairs
        """
        from pipelines.p5_synthetic_loop.loop_orchestrator import SyntheticLoop
        from schemas.enums import TaskType

        pipeline_id = "p5_synthetic_loop"
        run_id = str(uuid.uuid4())
        await self.db.start_pipeline_run(run_id, pipeline_id)

        domain_enum = Domain(domain)
        default_task_types = [
            TaskType.EXPLAIN_CONCEPT,
            TaskType.DIAGNOSE_PROBLEM,
            TaskType.PROVIDE_SOLUTION,
            TaskType.ASSESS_RISK,
            TaskType.EXPLAIN_FLOW,
        ]

        if task_types:
            task_type_enums = [TaskType(tt) for tt in task_types]
        else:
            task_type_enums = default_task_types

        loop = SyntheticLoop(claude_client=self.claude)

        total_accepted = 0
        total_generated = 0
        total_rejected = 0
        error_msg = None

        try:
            # Distribute count across task types
            per_type = max(1, count // len(task_type_enums))
            remainder = count - per_type * len(task_type_enums)

            all_pairs = []
            for i, tt in enumerate(task_type_enums):
                n = per_type + (1 if i < remainder else 0)
                pairs = await loop.generate_batch(
                    domain=domain_enum,
                    task_type=tt,
                    count=n,
                    difficulty=difficulty,
                )
                all_pairs.extend(pairs)

            gen, acc, rej = await self._process_pairs(all_pairs, pipeline_id, run_id)
            total_generated, total_accepted, total_rejected = gen, acc, rej

        except Exception as e:
            error_msg = str(e)
            logger.error(f"P5 Synthetic pipeline error: {e}")
        finally:
            await self.db.end_pipeline_run(
                run_id, total_generated, total_accepted, total_rejected, error_msg
            )

        logger.info(f"P5 Synthetic complete: {total_accepted} pairs accepted")
        return total_accepted

    async def run_p2_vendor(
        self,
        vendor_name: str,
        start_url: str,
        domain: Domain,
        product_name: Optional[str] = None,
        max_depth: int = 3,
        allowed_path_prefix: str = "/",
        max_pages: int = 50,
    ) -> int:
        """
        Crawl vendor documentation and generate training pairs.

        Args:
            vendor_name: Vendor name (e.g. "Microsoft")
            start_url: Starting URL for crawl
            domain: IAM domain
            product_name: Product name (defaults to vendor_name)
            max_depth: Crawl depth
            allowed_path_prefix: URL path prefix to restrict crawl
            max_pages: Maximum pages to crawl

        Returns:
            Number of accepted pairs
        """
        from pipelines.p2_vendor_docs.scraper import VendorDocScraper
        from pipelines.p2_vendor_docs.vendor_to_pairs import VendorToPairs

        product = product_name or vendor_name
        pipeline_id = f"p2_{vendor_name.lower().replace(' ', '_')}"
        run_id = str(uuid.uuid4())
        await self.db.start_pipeline_run(run_id, pipeline_id)

        total_accepted = 0
        total_generated = 0
        total_rejected = 0
        error_msg = None

        try:
            scraper = VendorDocScraper()
            pages = await scraper.crawl(
                start_url=start_url,
                max_depth=max_depth,
                allowed_path_prefix=allowed_path_prefix,
                max_pages=max_pages,
            )

            logger.info(f"Crawled {len(pages)} pages from {vendor_name}")

            generator = VendorToPairs(self.claude)
            pairs = await generator.generate_pairs(
                pages=pages,
                vendor=vendor_name,
                product=product,
                domain=domain,
            )

            gen, acc, rej = await self._process_pairs(pairs, pipeline_id, run_id)
            total_generated, total_accepted, total_rejected = gen, acc, rej

        except Exception as e:
            error_msg = str(e)
            logger.error(f"P2 Vendor pipeline error for {vendor_name}: {e}")
        finally:
            await self.db.end_pipeline_run(
                run_id, total_generated, total_accepted, total_rejected, error_msg
            )

        logger.info(f"P2 Vendor ({vendor_name}) complete: {total_accepted} pairs accepted")
        return total_accepted
