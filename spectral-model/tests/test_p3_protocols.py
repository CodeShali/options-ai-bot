"""Tests for Pipeline 3 protocol corpus generation."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import pytest
from pipelines.p3_protocols.ldap_corpus import LDAP_TOPIC_TAXONOMY, get_all_subtopics
from pipelines.p3_protocols.protocol_to_pairs import ProtocolToPairs, PROTOCOL_PAIR_PROMPT


class TestLDAPTopicTaxonomy:
    """Tests for the LDAP topic taxonomy coverage and structure."""

    EXPECTED_TOPICS = {
        "filter_syntax",
        "dn_handling",
        "schema",
        "operations",
        "security",
        "operational",
        "vendor_extensions",
    }

    def test_all_expected_topics_present(self):
        """All 7 major LDAP topics should be in the taxonomy."""
        taxonomy_topics = set(LDAP_TOPIC_TAXONOMY.keys())
        assert self.EXPECTED_TOPICS.issubset(taxonomy_topics), (
            f"Missing topics: {self.EXPECTED_TOPICS - taxonomy_topics}"
        )

    def test_filter_syntax_topic_has_subtopics(self):
        """filter_syntax should have multiple subtopics."""
        subtopics = LDAP_TOPIC_TAXONOMY.get("filter_syntax", [])
        assert len(subtopics) >= 5, f"Expected >= 5 filter_syntax subtopics, got {len(subtopics)}"

    def test_operations_topic_covers_core_ops(self):
        """operations topic should cover core LDAP operations."""
        subtopics = LDAP_TOPIC_TAXONOMY.get("operations", [])
        # Check for key operations
        subtopic_str = " ".join(subtopics).lower()
        assert "bind" in subtopic_str or "search" in subtopic_str

    def test_security_topic_has_subtopics(self):
        """security topic should have security-related subtopics."""
        subtopics = LDAP_TOPIC_TAXONOMY.get("security", [])
        assert len(subtopics) >= 5

    def test_all_topics_have_at_least_one_subtopic(self):
        """Every topic should have at least one subtopic."""
        for topic, subtopics in LDAP_TOPIC_TAXONOMY.items():
            assert len(subtopics) >= 1, f"Topic '{topic}' has no subtopics"

    def test_no_duplicate_subtopics_within_topic(self):
        """Within a topic, subtopics should be unique."""
        for topic, subtopics in LDAP_TOPIC_TAXONOMY.items():
            assert len(subtopics) == len(set(subtopics)), (
                f"Topic '{topic}' has duplicate subtopics: "
                f"{[s for s in subtopics if subtopics.count(s) > 1]}"
            )

    def test_subtopics_are_snake_case(self):
        """Subtopics should use snake_case format (letters, digits, underscores only)."""
        import re
        # Allow subtopics to start with a digit (e.g. 389_directory_server)
        snake_case_re = re.compile(r"^[a-z0-9][a-z0-9_]*$")
        for topic, subtopics in LDAP_TOPIC_TAXONOMY.items():
            for subtopic in subtopics:
                assert snake_case_re.match(subtopic), (
                    f"Subtopic '{subtopic}' in topic '{topic}' is not snake_case"
                )

    def test_total_subtopic_count(self):
        """Total number of subtopics should be substantial for good coverage."""
        all_subtopics = get_all_subtopics()
        assert len(all_subtopics) >= 50, (
            f"Expected >= 50 total subtopics for comprehensive coverage, "
            f"got {len(all_subtopics)}"
        )

    def test_get_all_subtopics_returns_tuples(self):
        """get_all_subtopics should return (topic, subtopic) tuples."""
        all_subtopics = get_all_subtopics()
        assert isinstance(all_subtopics, list)
        assert len(all_subtopics) > 0
        for item in all_subtopics:
            assert isinstance(item, tuple)
            assert len(item) == 2
            topic, subtopic = item
            assert topic in LDAP_TOPIC_TAXONOMY
            assert subtopic in LDAP_TOPIC_TAXONOMY[topic]

    def test_vendor_extensions_topic_present(self):
        """vendor_extensions should include major LDAP vendors."""
        subtopics = LDAP_TOPIC_TAXONOMY.get("vendor_extensions", [])
        all_text = " ".join(subtopics).lower()
        # At least one major vendor should be mentioned
        assert any(vendor in all_text for vendor in ["microsoft", "openldap", "389", "oracle", "ping"])

    def test_dn_handling_covers_dn_concepts(self):
        """dn_handling should cover DN-related concepts."""
        subtopics = LDAP_TOPIC_TAXONOMY.get("dn_handling", [])
        assert len(subtopics) >= 5
        all_text = " ".join(subtopics).lower()
        assert "dn" in all_text or "distinguished" in all_text


class TestProtocolToPairsPrompt:
    """Tests for ProtocolToPairs prompt construction."""

    def test_prompt_contains_protocol(self):
        """Generated prompt should contain the protocol name."""
        prompt = PROTOCOL_PAIR_PROMPT.format(
            protocol="LDAP",
            topic="filter_syntax",
            subtopic="basic_equality_filters",
            n=5,
            schema_json="[]",
        )
        assert "LDAP" in prompt

    def test_prompt_contains_topic_and_subtopic(self):
        """Generated prompt should contain topic and subtopic."""
        prompt = PROTOCOL_PAIR_PROMPT.format(
            protocol="OAuth 2.0",
            topic="pkce",
            subtopic="code_verifier_generation",
            n=3,
            schema_json="[]",
        )
        assert "pkce" in prompt
        assert "code_verifier_generation" in prompt

    def test_prompt_contains_n_count(self):
        """Generated prompt should contain the requested count."""
        for n in [1, 5, 10]:
            prompt = PROTOCOL_PAIR_PROMPT.format(
                protocol="SAML",
                topic="bindings",
                subtopic="http_redirect",
                n=n,
                schema_json="[]",
            )
            assert str(n) in prompt

    def test_prompt_mentions_rfc_citations(self):
        """Prompt should request RFC/spec citations in outputs."""
        prompt = PROTOCOL_PAIR_PROMPT.format(
            protocol="LDAP",
            topic="operations",
            subtopic="search_operation",
            n=5,
            schema_json="[]",
        )
        # Should mention citing RFCs or specs
        lower_prompt = prompt.lower()
        assert "rfc" in lower_prompt or "spec" in lower_prompt

    def test_prompt_schema_json_included(self):
        """Schema JSON should be included in the prompt."""
        schema_json = '{"instruction": "string", "output": "string"}'
        prompt = PROTOCOL_PAIR_PROMPT.format(
            protocol="Kerberos",
            topic="ticket_granting",
            subtopic="tgt_acquisition",
            n=5,
            schema_json=schema_json,
        )
        assert schema_json in prompt

    def test_protocol_to_pairs_init(self):
        """ProtocolToPairs should initialize without error."""
        # This should work without a real Claude client since we skip generation
        # Just test that the class can be instantiated
        from unittest.mock import MagicMock
        mock_client = MagicMock()
        generator = ProtocolToPairs(claude_client=mock_client)
        assert generator.claude is mock_client

    def test_schema_json_is_valid_json(self):
        """_build_schema_json should return valid JSON."""
        import json
        from unittest.mock import MagicMock
        generator = ProtocolToPairs(claude_client=MagicMock())
        schema_str = generator._build_schema_json()
        parsed = json.loads(schema_str)
        assert isinstance(parsed, list)
        assert len(parsed) > 0
        item = parsed[0]
        assert "instruction" in item
        assert "output" in item
        assert "task_type" in item


class TestLDAPCorpusCoverage:
    """Tests for LDAP corpus completeness."""

    def test_covers_ldap_filter_subtopics(self):
        """LDAP corpus should cover filter-related subtopics."""
        filter_subtopics = LDAP_TOPIC_TAXONOMY.get("filter_syntax", [])
        expected_filter_topics = [
            "basic_equality_filters",
            "boolean_operators_and_or_not",
            "substring_filters",
        ]
        for expected in expected_filter_topics:
            assert expected in filter_subtopics, (
                f"Expected filter subtopic '{expected}' not found in taxonomy"
            )

    def test_covers_security_subtopics(self):
        """LDAP corpus should cover security-related subtopics."""
        security_subtopics = LDAP_TOPIC_TAXONOMY.get("security", [])
        assert "ldap_injection" in security_subtopics or any(
            "inject" in s for s in security_subtopics
        ), "LDAP injection should be in security subtopics"

    def test_covers_sasl_mechanisms(self):
        """Security topic should mention SASL."""
        security_subtopics = LDAP_TOPIC_TAXONOMY.get("security", [])
        all_text = " ".join(security_subtopics).lower()
        assert "sasl" in all_text, "SASL mechanisms should be covered"

    def test_covers_operational_topics(self):
        """Operational topic should include replication and monitoring."""
        operational_subtopics = LDAP_TOPIC_TAXONOMY.get("operational", [])
        all_text = " ".join(operational_subtopics).lower()
        assert "replication" in all_text or "replica" in all_text
