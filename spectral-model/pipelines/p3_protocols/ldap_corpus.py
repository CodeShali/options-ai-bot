"""Build LDAP training corpus using a comprehensive topic taxonomy."""

import asyncio
import logging
from typing import Optional

from schemas.training_pair import TrainingPair
from schemas.enums import Domain
from pipelines.p3_protocols.protocol_to_pairs import ProtocolToPairs
from pipelines.shared.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

# Full LDAP topic taxonomy
LDAP_TOPIC_TAXONOMY = {
    "filter_syntax": [
        "basic_equality_filters",
        "substring_filters",
        "presence_filters",
        "comparison_filters",
        "boolean_operators_and_or_not",
        "nested_compound_filters",
        "extensible_match_filters",
        "approximate_match_filters",
        "filter_encoding_ber",
        "special_characters_escaping",
        "objectclass_filters",
        "operational_attribute_filters",
        "performance_optimization",
        "filter_syntax_errors",
        "ad_specific_filter_extensions",
    ],
    "dn_handling": [
        "dn_structure_components",
        "rdn_multi_valued",
        "dn_string_representation",
        "dn_escaping_special_chars",
        "dn_comparison_rules",
        "relative_vs_absolute_dn",
        "dn_normalization",
        "dn_manipulation_programmatic",
        "dn_case_sensitivity",
        "dc_style_vs_ou_style_dns",
    ],
    "schema": [
        "objectclass_types_structural_auxiliary_abstract",
        "attribute_type_definitions",
        "syntax_rules",
        "matching_rules",
        "schema_retrieval",
        "schema_extension",
        "dit_content_rules",
        "dit_structure_rules",
        "name_forms",
        "subschema_subentry",
        "operational_attributes",
        "core_schema_attributes",
        "standard_objectclasses",
        "schema_violations",
        "microsoft_ad_schema_extensions",
    ],
    "operations": [
        "bind_simple_sasl",
        "unbind",
        "search_base_one_sub",
        "add_entry",
        "modify_entry",
        "modify_dn_rename_move",
        "delete_entry",
        "compare_operation",
        "extended_operations",
        "abandon_operation",
        "search_size_time_limits",
        "search_referrals",
        "search_aliases",
        "paged_results_control",
        "sort_control",
        "vlv_control",
        "server_side_sort",
        "pre_read_post_read_controls",
        "transaction_control",
        "assertion_control",
        "proxied_authorization_control",
    ],
    "security": [
        "simple_bind_risks",
        "sasl_mechanisms_overview",
        "sasl_external_tls_certs",
        "sasl_gssapi_kerberos",
        "sasl_digest_md5",
        "starttls_upgrade",
        "ldaps_ssl",
        "certificate_validation",
        "access_control_aci",
        "password_policies",
        "account_lockout",
        "ldap_injection",
        "anonymous_access_risks",
        "privilege_escalation_vectors",
        "channel_binding",
    ],
    "operational": [
        "replication_models",
        "syncrepl_consumer",
        "delta_syncrepl",
        "referral_configuration",
        "chaining",
        "directory_structure_design",
        "index_configuration",
        "performance_tuning",
        "monitoring_statistics",
        "backup_restore",
        "high_availability",
        "load_balancing",
        "logging_auditing",
        "connection_pooling",
        "timeout_configuration",
    ],
    "vendor_extensions": [
        "microsoft_ad_ldap_extensions",
        "active_directory_specific_controls",
        "openldap_extensions",
        "389_directory_server",
        "oracle_unified_directory",
        "ping_directory_extensions",
        "novell_edirectory_ldap",
        "ibm_tivoli_directory",
        "sun_one_directory",
        "vendor_specific_error_codes",
    ],
}


async def build_ldap_corpus(
    n_per_subtopic: int = 5,
    claude_client: Optional[ClaudeClient] = None,
    max_concurrent: int = 3,
) -> list[TrainingPair]:
    """
    Build a comprehensive LDAP training corpus.

    Args:
        n_per_subtopic: Number of pairs to generate per subtopic
        claude_client: Shared Claude client (creates new one if not provided)
        max_concurrent: Max concurrent generation tasks

    Returns:
        All generated TrainingPair objects
    """
    client = claude_client or ClaudeClient()
    generator = ProtocolToPairs(client)
    semaphore = asyncio.Semaphore(max_concurrent)

    all_pairs: list[TrainingPair] = []

    async def generate_subtopic(topic: str, subtopic: str) -> list[TrainingPair]:
        async with semaphore:
            try:
                return await generator.generate_for_topic(
                    protocol="LDAP",
                    topic=topic,
                    subtopic=subtopic,
                    domain=Domain.LDAP,
                    n=n_per_subtopic,
                )
            except Exception as e:
                logger.error(f"Error generating LDAP pairs for {topic}/{subtopic}: {e}")
                return []

    # Build all tasks
    tasks = []
    for topic, subtopics in LDAP_TOPIC_TAXONOMY.items():
        for subtopic in subtopics:
            tasks.append(generate_subtopic(topic, subtopic))

    total_subtopics = len(tasks)
    logger.info(
        f"Building LDAP corpus: {total_subtopics} subtopics × {n_per_subtopic} pairs = "
        f"up to {total_subtopics * n_per_subtopic} pairs"
    )

    # Run all tasks concurrently (bounded by semaphore)
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Subtopic task failed: {result}")
        elif isinstance(result, list):
            all_pairs.extend(result)

    logger.info(
        f"LDAP corpus complete: {len(all_pairs)} pairs generated from {total_subtopics} subtopics"
    )
    return all_pairs


def get_all_subtopics() -> list[tuple[str, str]]:
    """Return all (topic, subtopic) pairs from the taxonomy."""
    return [
        (topic, subtopic)
        for topic, subtopics in LDAP_TOPIC_TAXONOMY.items()
        for subtopic in subtopics
    ]
