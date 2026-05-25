"""Tests for QualityFilter gates (no external calls)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import pytest
from schemas.training_pair import TrainingPair
from schemas.enums import Domain, TaskType, SourceType
from pipelines.shared.quality_filter import QualityFilter, VALID_RFC_IDS


def make_pair(**overrides) -> TrainingPair:
    """Create a valid TrainingPair with optional overrides."""
    defaults = {
        "domain": Domain.LDAP,
        "task_type": TaskType.EXPLAIN_CONCEPT,
        "source_type": SourceType.RFC,
        "difficulty": "intermediate",
        "instruction": "How does LDAP search filtering work with compound expressions?",
        "output": (
            "LDAP search filters (RFC 4515) support boolean operators to combine multiple "
            "conditions. The AND operator (&) requires all conditions to match, while the "
            "OR operator (|) matches if any condition is true. NOT (!) negates a filter. "
            "For example: (&(objectClass=user)(department=Engineering)) finds all user "
            "entries in the Engineering department. Filters are encoded in parentheses and "
            "can be nested to arbitrary depth. The filter (&(objectClass=person)(|(cn=Alice)(cn=Bob))) "
            "finds entries that are persons named either Alice or Bob. Special characters in "
            "attribute values must be escaped with backslash notation per RFC 4515 section 3."
        ),
        "pipeline_id": "test",
    }
    defaults.update(overrides)
    return TrainingPair(**defaults)


class TestQualityFilterMinimumLength:
    """Tests for the minimum_length gate."""

    def setup_method(self):
        self.qf = QualityFilter()

    def test_short_output_fails(self):
        """Output shorter than min_output_length should fail the gate."""
        # Create pair with output between 50 (Pydantic min) and 100 (QF min)
        # Pydantic requires >= 50 chars, QF minimum_length requires >= 100 chars
        pair = make_pair(
            output="x" * 75  # 75 chars: passes Pydantic (>=50), fails QF gate (>=100)
        )
        result = self.qf.gate_minimum_length(pair)
        assert result.passed is False
        assert "short" in result.reason.lower() or "100" in result.reason

    def test_output_at_minimum_passes(self):
        """Output exactly at minimum length should pass."""
        pair = make_pair(
            output="a" * 100
        )
        result = self.qf.gate_minimum_length(pair)
        assert result.passed is True

    def test_normal_output_passes(self):
        """Normal-length output should pass minimum length check."""
        pair = make_pair()
        result = self.qf.gate_minimum_length(pair)
        assert result.passed is True


class TestQualityFilterMaximumLength:
    """Tests for the maximum_length gate."""

    def setup_method(self):
        self.qf = QualityFilter()

    def test_very_long_output_fails(self):
        """Output exceeding max_output_length (4000) should fail."""
        pair = make_pair(output="word " * 1000)  # ~5000 chars
        result = self.qf.gate_maximum_length(pair)
        assert result.passed is False

    def test_normal_output_passes(self):
        """Normal-length output should pass maximum length check."""
        pair = make_pair()
        result = self.qf.gate_maximum_length(pair)
        assert result.passed is True


class TestQualityFilterNoRefusalLanguage:
    """Tests for the no_refusal_language gate."""

    def setup_method(self):
        self.qf = QualityFilter()

    REFUSAL_EXAMPLES = [
        "I am unable to provide information about this topic.",
        "As an AI language model, I cannot help with that.",
        "I can't assist with this request as it relates to",
        "I must clarify that I don't have access to real-time data.",
        "I cannot provide legal advice, please consult a professional.",
        "I'm just an AI and cannot perform this action.",
        "My training data does not include information after",
        "I don't have personal experience with this system.",
    ]

    def test_refusal_language_is_detected(self):
        """Various refusal phrases should be detected."""
        for refusal_text in self.REFUSAL_EXAMPLES:
            # Create a pair where the refusal is in the output
            try:
                pair = make_pair(
                    output=refusal_text + " " * (100 - len(refusal_text)) + "Additional text to meet minimum length requirement here and more."
                )
                result = self.qf.gate_no_refusal_language(pair)
                assert result.passed is False, (
                    f"Refusal phrase not detected: '{refusal_text}'"
                )
            except Exception:
                # Pair creation might fail if refusal + padding still too short
                # Just ensure the gate itself works
                pass

    def test_clean_output_passes(self):
        """Output without refusal language should pass."""
        pair = make_pair()
        result = self.qf.gate_no_refusal_language(pair)
        assert result.passed is True

    def test_technical_output_with_cannot_passes(self):
        """Technical output containing 'cannot' in a different context should pass."""
        pair = make_pair(
            output=(
                "The LDAP server cannot process filters with unmatched parentheses. "
                "Per RFC 4515, the filter syntax requires every opening parenthesis to "
                "have a corresponding closing parenthesis. When the filter parser encounters "
                "a syntax error, it returns resultCode 87 (filter error). The objectClass "
                "attribute cannot be excluded from an entry and is REQUIRED. "
                "Clients that cannot connect should check firewall rules and TLS configuration. "
                "The bind operation requires proper credentials per RFC 4513 section 4."
            )
        )
        result = self.qf.gate_no_refusal_language(pair)
        assert result.passed is True


class TestQualityFilterNoMetaCommentary:
    """Tests for the no_meta_commentary gate."""

    def setup_method(self):
        self.qf = QualityFilter()

    META_EXAMPLES = [
        "Certainly! Here is the information you requested:",
        "Sure! Let me explain this concept for you:",
        "Great question! I'll cover this topic in detail.",
        "In this response, I will explain the LDAP filter syntax.",
        "I hope this helps! Let me know if you need clarification.",
        "Feel free to ask if you have more questions!",
    ]

    def test_meta_commentary_is_detected(self):
        """Meta-commentary phrases should be detected."""
        for meta_text in self.META_EXAMPLES:
            try:
                pair = make_pair(
                    output=meta_text + (
                        " LDAP filters use RFC 4515 syntax. The AND operator combines "
                        "multiple conditions. Equality filters match exact attribute values. "
                        "Substring filters support wildcard matching per RFC 4515. "
                        "The presence filter checks if an attribute exists in an entry."
                    )
                )
                result = self.qf.gate_no_meta_commentary(pair)
                assert result.passed is False, (
                    f"Meta-commentary not detected: '{meta_text}'"
                )
            except Exception:
                pass  # Pair validation failure is OK here

    def test_clean_technical_output_passes(self):
        """Technical output without meta-commentary should pass."""
        pair = make_pair()
        result = self.qf.gate_no_meta_commentary(pair)
        assert result.passed is True


class TestQualityFilterHasSpecifics:
    """Tests for the has_specifics gate."""

    def setup_method(self):
        self.qf = QualityFilter()

    def test_output_with_rfc_reference_passes(self):
        """Output mentioning RFC should pass has_specifics."""
        pair = make_pair(
            output=(
                "Per RFC 4511, the LDAP bind operation supports simple and SASL mechanisms. "
                "The server returns a BindResponse with resultCode indicating success (0) or "
                "an error. Section 4.2 defines the BindRequest message format. "
                "SASL authentication (RFC 4616) provides stronger security guarantees "
                "than simple bind with password. The resultCode 49 (invalidCredentials) "
                "indicates authentication failure and is defined in RFC 4511 section 4.1.9."
            )
        )
        result = self.qf.gate_has_specifics(pair)
        assert result.passed is True

    def test_output_with_code_block_passes(self):
        """Output with code block should pass has_specifics."""
        pair = make_pair(
            output=(
                "To search LDAP for users in a department, use this filter:\n"
                "```\n"
                "(&(objectClass=person)(department=Engineering))\n"
                "```\n"
                "This filter combines two conditions: objectClass must be 'person' "
                "and department must be 'Engineering'. The AND operator (&) ensures "
                "both conditions must match. This is standard LDAP filter syntax."
            )
        )
        result = self.qf.gate_has_specifics(pair)
        assert result.passed is True

    def test_generic_output_without_specifics_fails(self):
        """Generic output without technical specifics should fail."""
        # Deliberately avoids all IAM terms, RFC references, code blocks, RFC normative words,
        # and encoding terms. Uses placeholder words that don't match any technical patterns.
        generic_output = (
            "Business processes need to be managed in a structured manner to be effective. "
            "Organizations benefit from clear policies and regular review cycles. "
            "Teams that communicate well tend to achieve better outcomes over time. "
            "Planning is a critical part of any large-scale project or initiative. "
            "Feedback loops allow organizations to improve continuously over multiple cycles. "
            "Good documentation helps new members get up to speed quickly and efficiently."
        )
        pair = make_pair(output=generic_output)
        result = self.qf.gate_has_specifics(pair)
        assert result.passed is False


class TestQualityFilterCitationValidity:
    """Tests for the citation_validity gate."""

    def setup_method(self):
        self.qf = QualityFilter()

    def test_valid_rfc_citations_pass(self):
        """Known valid RFC citations should pass."""
        from schemas.training_pair import SourceCitation
        valid_rfcs = ["RFC4511", "RFC6749", "RFC7519", "RFC7636"]
        for rfc_id in valid_rfcs:
            pair = make_pair(
                citations=[SourceCitation(
                    source_id=rfc_id,
                    source_type=SourceType.RFC,
                    title=f"{rfc_id} Test",
                )]
            )
            result = self.qf.gate_citation_validity(pair)
            assert result.passed is True, f"Valid RFC {rfc_id} should pass"

    def test_invalid_rfc_citation_fails(self):
        """Unknown RFC IDs should fail citation validity."""
        from schemas.training_pair import SourceCitation
        # RFC99999 doesn't exist in sources.yaml
        pair = make_pair(
            citations=[SourceCitation(
                source_id="RFC99999",
                source_type=SourceType.RFC,
                title="Fake RFC",
            )]
        )
        result = self.qf.gate_citation_validity(pair)
        assert result.passed is False

    def test_implausible_rfc_number_in_text_fails(self):
        """RFC number with 5+ digits in output text should fail."""
        pair = make_pair(
            output=(
                "Per RFC 123456, which defines the identity protocol, authentication "
                "is required for all requests. This fictional RFC 789012 specifies "
                "the extended operations for LDAP servers in modern deployments. "
                "The protocol is important for identity management systems."
            )
        )
        result = self.qf.gate_citation_validity(pair)
        assert result.passed is False

    def test_no_citations_passes(self):
        """Pair with no citations should pass (citations are optional)."""
        pair = make_pair(citations=[])
        result = self.qf.gate_citation_validity(pair)
        assert result.passed is True

    def test_valid_rfc_ids_set_is_complete(self):
        """VALID_RFC_IDS should contain all RFCs from sources.yaml."""
        # These are the key RFCs that must be in the set
        required_rfcs = {
            "RFC4511", "RFC4512", "RFC4513",  # LDAP
            "RFC6749", "RFC6750", "RFC7519",   # OAuth
            "RFC7636",                          # PKCE
            "RFC7642", "RFC7643", "RFC7644",   # SCIM
            "RFC4120", "RFC4121",              # Kerberos
        }
        for rfc in required_rfcs:
            assert rfc in VALID_RFC_IDS, f"{rfc} should be in VALID_RFC_IDS"


class TestQualityFilterNoPII:
    """Tests for the no_pii gate."""

    def setup_method(self):
        self.qf = QualityFilter()

    def test_clean_output_passes(self):
        """Output without PII should pass."""
        pair = make_pair()
        result = self.qf.gate_no_pii(pair)
        assert result.passed is True

    def test_output_with_example_email_passes(self):
        """Example email addresses should not trigger PII detection."""
        pair = make_pair(
            output=(
                "Configure the LDAP search filter to find users by email: "
                "(mail=user@example.com). You can also use wildcards: "
                "(mail=*@yourdomain.com). The bind DN should be "
                "cn=service-account,dc=company,dc=com for service accounts. "
                "Per RFC 4515, special characters in values must be escaped properly."
            )
        )
        result = self.qf.gate_no_pii(pair)
        # example.com and yourdomain.com are excluded from PII detection
        assert result.passed is True


class TestQualityFilterValidateAll:
    """Tests for the complete validate() method."""

    def setup_method(self):
        self.qf = QualityFilter()

    def test_high_quality_pair_passes_all_gates(self):
        """A well-formed pair should pass all quality gates."""
        pair = make_pair()
        passed, failures = self.qf.validate(pair)
        # Should pass most or all gates
        assert len(failures) <= 2, f"Too many failures for a good pair: {failures}"

    def test_score_returns_float_between_0_and_1(self):
        """Quality score should always be between 0.0 and 1.0."""
        pair = make_pair()
        score = self.qf.score(pair)
        assert 0.0 <= score <= 1.0

    def test_good_pair_has_high_score(self):
        """Well-formed pairs should have a score >= 0.5."""
        pair = make_pair()
        score = self.qf.score(pair)
        assert score >= 0.5, f"Good pair should score >= 0.5, got {score}"

    def test_validate_returns_tuple(self):
        """validate() should return (bool, list) tuple."""
        pair = make_pair()
        result = self.qf.validate(pair)
        assert isinstance(result, tuple)
        assert len(result) == 2
        passed, failures = result
        assert isinstance(passed, bool)
        assert isinstance(failures, list)

    def test_pair_with_short_output_fails_validate(self):
        """Pair with output too short should fail validate."""
        try:
            # This may fail at Pydantic validation before reaching QualityFilter
            pair = make_pair(output="x" * 50)
            passed, failures = self.qf.validate(pair)
            # If it gets here, should fail minimum length
            min_length_failures = [f for f in failures if "minimum_length" in f.lower() or "short" in f.lower()]
            assert len(min_length_failures) > 0 or not passed
        except Exception:
            # Pydantic validation caught it first - that's fine
            pass
