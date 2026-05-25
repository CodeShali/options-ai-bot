"""Main orchestrator entry point for Week 1 pipeline run."""

import asyncio
import logging

from orchestrator.pipeline_runner import PipelineRunner
from pipelines.shared.claude_client import ClaudeClient
from pipelines.shared.dedup import SemanticDedup
from pipelines.shared.quality_filter import QualityFilter
from storage.db import Database
from storage.jsonl_writer import JSONLWriter
from config.settings import settings

logger = logging.getLogger(__name__)


async def build_week1() -> dict:
    """
    Run the full Week 1 pipeline.

    Covers:
    - P1: Core RFC documents (LDAP, OAuth, SCIM)
    - P3: LDAP corpus from topic taxonomy
    - P4: Stack Overflow IAM tags
    - P5: Synthetic loop for OAuth domain

    Returns:
        Dict of pipeline_id → accepted_pairs_count
    """
    db = Database(settings.db_path)
    await db.initialize()

    claude = ClaudeClient()
    dedup = SemanticDedup()
    quality = QualityFilter()
    writer = JSONLWriter()

    runner = PipelineRunner(claude, dedup, quality, writer, db)

    stats = {}

    logger.info("Starting Week 1 pipeline run")

    # P1: Fetch top LDAP and OAuth RFCs
    logger.info("P1: Fetching authoritative RFC documents...")
    p1_rfcs = [
        "RFC4511", "RFC4512", "RFC4513",  # LDAP core
        "RFC6749", "RFC6750", "RFC7519",   # OAuth 2.0 + JWT
        "RFC7636",                          # PKCE
        "RFC7642", "RFC7643", "RFC7644",   # SCIM
    ]
    stats["p1_rfcs"] = await runner.run_p1_rfcs(p1_rfcs)
    logger.info(f"P1 complete: {stats['p1_rfcs']} pairs accepted")

    # P3: LDAP corpus
    logger.info("P3: Building LDAP protocol corpus...")
    stats["p3_ldap"] = await runner.run_p3_ldap(n_per_subtopic=3)
    logger.info(f"P3 complete: {stats['p3_ldap']} pairs accepted")

    # P4: Stack Overflow (top IAM tags)
    logger.info("P4: Fetching Stack Overflow IAM Q&A...")
    so_tags = [
        "active-directory",
        "ldap",
        "oauth-2.0",
        "saml",
        "openid-connect",
    ]
    stats["p4_stackoverflow"] = await runner.run_p4_stackoverflow(so_tags, min_score=5)
    logger.info(f"P4 complete: {stats['p4_stackoverflow']} pairs accepted")

    # P5: Synthetic loop
    logger.info("P5: Running synthetic generation loop for OAuth...")
    stats["p5_synthetic"] = await runner.run_p5_synthetic("oauth", 50)
    logger.info(f"P5 complete: {stats['p5_synthetic']} pairs accepted")

    total = sum(stats.values())
    logger.info(f"Week 1 pipeline complete. Total accepted pairs: {total}")
    logger.info(f"Breakdown: {stats}")

    final_stats = await db.get_stats()
    stats["db_stats"] = final_stats

    return stats


async def build_full() -> dict:
    """
    Run the complete multi-week pipeline across all domains.

    This is the production-scale run. Use build_week1() for development.
    """
    db = Database(settings.db_path)
    await db.initialize()

    claude = ClaudeClient()
    dedup = SemanticDedup()
    quality = QualityFilter()
    writer = JSONLWriter()

    runner = PipelineRunner(claude, dedup, quality, writer, db)

    stats = {}

    # All core RFCs
    from pipelines.shared.quality_filter import VALID_RFC_IDS
    all_rfcs = [rfc for rfc in VALID_RFC_IDS if rfc.startswith("RFC")]
    stats["p1_all_rfcs"] = await runner.run_p1_rfcs(all_rfcs)

    # All protocol corpora
    stats["p3_ldap"] = await runner.run_p3_ldap(n_per_subtopic=5)

    # Stack Overflow (all IAM tags)
    so_tags = [
        "ldap", "active-directory", "azure-active-directory", "oauth-2.0",
        "openid-connect", "saml", "kerberos", "jwt", "scim", "webauthn",
        "okta", "aws-iam", "google-cloud-iam", "azure-ad-b2c", "msal",
        "pkce", "keycloak", "sso", "adfs", "hashicorp-vault",
    ]
    stats["p4_stackoverflow"] = await runner.run_p4_stackoverflow(so_tags, min_score=3)

    # Synthetic loops across domains
    from schemas.enums import Domain
    domains = [d.value for d in Domain]
    for domain in domains:
        key = f"p5_{domain}"
        stats[key] = await runner.run_p5_synthetic(domain, count=100)

    return stats


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    mode = sys.argv[1] if len(sys.argv) > 1 else "week1"

    if mode == "week1":
        result = asyncio.run(build_week1())
    elif mode == "full":
        result = asyncio.run(build_full())
    else:
        print(f"Unknown mode: {mode}. Use 'week1' or 'full'")
        sys.exit(1)

    print("Results:", result)
