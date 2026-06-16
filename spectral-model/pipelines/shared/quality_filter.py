"""Quality filter with programmatic gates for training pair validation."""

import logging
import re
from typing import Optional

from schemas.training_pair import TrainingPair
from config.settings import settings

logger = logging.getLogger(__name__)

# Valid RFC IDs drawn from sources.yaml
VALID_RFC_IDS = {
    "RFC4510", "RFC4511", "RFC4512", "RFC4513", "RFC4514", "RFC4515", "RFC4516",
    "RFC4517", "RFC4518", "RFC4519", "RFC4522", "RFC4523", "RFC4524", "RFC4525",
    "RFC4526", "RFC4529", "RFC3062", "RFC3672", "RFC3673", "RFC2696", "RFC2891",
    "RFC4533", "RFC3909", "RFC6749", "RFC6750", "RFC7009", "RFC7519", "RFC7521",
    "RFC7523", "RFC7636", "RFC7591", "RFC7592", "RFC8414", "RFC8628", "RFC8693",
    "RFC9068", "RFC9101", "RFC9126", "RFC9449", "RFC7662", "RFC4120", "RFC4121",
    "RFC6113", "RFC4556", "RFC6806", "RFC8446", "RFC7515", "RFC7516", "RFC7517",
    "RFC7518", "RFC4422", "RFC4616", "RFC5801", "RFC7642", "RFC7643", "RFC7644",
}

REFUSAL_PATTERNS = [
    r"i(?:'m| am) (?:unable|not able) to",
    r"i can(?:'t| not) (?:help|provide|answer|assist)",
    r"as an ai(?:\s+language model)?",
    r"i (?:don't|do not) have (?:access|the ability|personal)",
    r"i (?:must|need to) (?:clarify|note|mention) that",
    r"i (?:cannot|can't) (?:provide|give|offer) (?:professional|legal|medical) advice",
    r"please (?:consult|contact) (?:a professional|an expert|your)",
    r"i'm just an ai",
    r"my training (?:data|cutoff)",
]

META_COMMENTARY_PATTERNS = [
    r"in this response,? i (?:will|am going to|shall)",
    r"(?:certainly|sure|of course|absolutely)!?\s+(?:here(?:'s| is)|let me)",
    r"great (?:question|topic)!",
    r"(?:i hope this|this should) (?:helps?|answers?|clarifies?)",
    r"feel free to (?:ask|let me know)",
    r"let me know if you (?:need|have|want)",
    r"please let me know if",
    r"is there anything else",
]

HALLUCINATION_MARKERS = [
    r"RFC\s*\d{5,}",  # RFC numbers with 5+ digits don't exist
    r"(?:RFC|NIST|CIS)\s*[A-Z]{5,}",  # Implausible identifier formats
    r"(?:in|per|according to)\s+(?:RFC|NIST)\s+(?:section\s+)?\d+\.\d+\.\d+\.\d+\.\d+",  # Too deep nesting
]

SPECIFICS_PATTERNS = [
    r"\b(?:RFC|NIST|CIS|ISO|OASIS|W3C)\s*\d+",  # Standards references
    r"\b(?:section|§)\s*\d+",
    r"(?:https?://|www\.)\S+",  # URLs
    r"(?:code|error|status)[\s:]+\d{3,4}",  # Error/status codes
    r"\b(?:base64|hex|ASN\.1|DER|PEM|BER)\b",  # Technical encoding terms (word boundaries)
    r"(?:0x[0-9A-Fa-f]+)",  # Hex values
    r"```[\s\S]+?```",  # Code blocks
]

# Case-sensitive RFC normative language (ALL CAPS only — lowercase "recommended" is not a signal)
NORMATIVE_LANGUAGE_PATTERN = re.compile(r"\b(?:SHALL|MUST NOT|MUST|SHOULD NOT|SHOULD|MAY|REQUIRED|RECOMMENDED)\b")

PII_PATTERNS = [
    r"\b[A-Za-z0-9._%+-]+@(?!example\.com|yourdomain\.com|company\.com)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b",  # SSN pattern
    r"\b\d{16}\b",  # Credit card
    r"\b(?:password|passwd|secret|api.?key|access.?token)\s*=\s*[^\s\"']+\b",  # Credentials in plain text
]


class GateResult:
    def __init__(self, passed: bool, reason: str):
        self.passed = passed
        self.reason = reason

    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"GateResult({status}: {self.reason})"


class QualityFilter:
    """
    Runs a series of programmatic quality gates on a TrainingPair.
    All gates are purely algorithmic — no LLM calls.
    """

    def __init__(self):
        self._refusal_re = [re.compile(p, re.IGNORECASE) for p in REFUSAL_PATTERNS]
        self._meta_re = [re.compile(p, re.IGNORECASE) for p in META_COMMENTARY_PATTERNS]
        self._hallucination_re = [re.compile(p, re.IGNORECASE) for p in HALLUCINATION_MARKERS]
        self._specifics_re = [re.compile(p, re.IGNORECASE) for p in SPECIFICS_PATTERNS]
        self._pii_re = [re.compile(p, re.IGNORECASE) for p in PII_PATTERNS]
        self._rfc_ref_re = re.compile(r"\bRFC\s*(\d+)\b", re.IGNORECASE)

    # ── Individual gates ────────────────────────────────────────────────────

    def gate_minimum_length(self, pair: TrainingPair) -> GateResult:
        length = len(pair.output.strip())
        if length < settings.min_output_length:
            return GateResult(False, f"Output too short: {length} < {settings.min_output_length} chars")
        return GateResult(True, f"Output length OK: {length} chars")

    def gate_maximum_length(self, pair: TrainingPair) -> GateResult:
        length = len(pair.output.strip())
        if length > settings.max_output_length:
            return GateResult(False, f"Output too long: {length} > {settings.max_output_length} chars")
        return GateResult(True, f"Output length OK: {length} chars")

    def gate_no_refusal_language(self, pair: TrainingPair) -> GateResult:
        output = pair.output
        for pattern in self._refusal_re:
            match = pattern.search(output)
            if match:
                return GateResult(False, f"Refusal language detected: '{match.group()}'")
        return GateResult(True, "No refusal language found")

    def gate_no_meta_commentary(self, pair: TrainingPair) -> GateResult:
        output = pair.output
        for pattern in self._meta_re:
            match = pattern.search(output)
            if match:
                return GateResult(False, f"Meta-commentary detected: '{match.group()}'")
        return GateResult(True, "No meta-commentary found")

    def gate_has_specifics(self, pair: TrainingPair) -> GateResult:
        """Check that output has at least one specific technical reference."""
        output = pair.output
        for pattern in self._specifics_re:
            if pattern.search(output):
                return GateResult(True, "Output contains technical specifics")
        if NORMATIVE_LANGUAGE_PATTERN.search(output):
            return GateResult(True, "Output contains RFC normative language")
        # Also check for domain-specific terms
        technical_terms = [
            "ldap", "saml", "oauth", "oidc", "scim", "kerberos", "webauthn", "fido",
            "active directory", "entra", "aws iam", "okta", "token", "assertion",
            "principal", "credential", "certificate", "cipher", "hash", "digest",
            "bind", "search filter", "distinguished name", "objectclass",
            "grant", "scope", "audience", "issuer", "subject", "claim",
        ]
        lower_output = output.lower()
        for term in technical_terms:
            if term in lower_output:
                return GateResult(True, f"Output contains technical term: '{term}'")
        return GateResult(False, "Output lacks technical specifics or IAM terminology")

    def gate_no_hallucination_markers(self, pair: TrainingPair) -> GateResult:
        output = pair.output
        for pattern in self._hallucination_re:
            match = pattern.search(output)
            if match:
                return GateResult(False, f"Possible hallucination marker: '{match.group()}'")
        return GateResult(True, "No obvious hallucination markers")

    def gate_citation_validity(self, pair: TrainingPair) -> GateResult:
        """Check that RFC citations in citations list are from the known-valid set."""
        for citation in pair.citations:
            source_id = citation.source_id.upper().strip()
            if source_id.startswith("RFC"):
                if source_id not in VALID_RFC_IDS:
                    return GateResult(
                        False,
                        f"Unknown or invalid RFC citation: {source_id}",
                    )
        # Also check for obviously fake RFCs in output text
        for match in self._rfc_ref_re.finditer(pair.output):
            rfc_num = int(match.group(1))
            if rfc_num > 9999:
                return GateResult(
                    False,
                    f"RFC number {rfc_num} is implausibly large (possible hallucination)",
                )
        return GateResult(True, "All citations appear valid")

    def gate_no_pii(self, pair: TrainingPair) -> GateResult:
        """Check for personally identifiable information in output."""
        full_text = f"{pair.instruction} {pair.output}"
        for pattern in self._pii_re:
            match = pattern.search(full_text)
            if match:
                return GateResult(False, f"Possible PII detected: '{match.group()[:50]}...'")
        return GateResult(True, "No PII detected")

    def gate_instruction_not_trivial(self, pair: TrainingPair) -> GateResult:
        """Check instruction is non-trivial (has reasonable length and content)."""
        instr = pair.instruction.strip()
        if len(instr) < 15:
            return GateResult(False, f"Instruction too short: {len(instr)} chars")
        if instr.lower() in {"what is iam?", "explain iam", "what is ldap?"}:
            return GateResult(False, "Instruction is too generic/trivial")
        return GateResult(True, "Instruction appears non-trivial")

    # ── Main validation ──────────────────────────────────────────────────────

    def validate(self, pair: TrainingPair) -> tuple[bool, list[str]]:
        """
        Run all quality gates.

        Returns:
            (passed: bool, failure_reasons: list[str])
        """
        gates = [
            self.gate_minimum_length,
            self.gate_maximum_length,
            self.gate_no_refusal_language,
            self.gate_no_meta_commentary,
            self.gate_has_specifics,
            self.gate_no_hallucination_markers,
            self.gate_citation_validity,
            self.gate_no_pii,
            self.gate_instruction_not_trivial,
        ]

        failures = []
        for gate in gates:
            result = gate(pair)
            if not result.passed:
                logger.debug(f"Quality gate failed [{gate.__name__}]: {result.reason}")
                failures.append(f"{gate.__name__}: {result.reason}")

        passed = len(failures) == 0
        if passed:
            logger.debug(f"Pair {pair.id} passed all quality gates")
        else:
            logger.debug(f"Pair {pair.id} failed {len(failures)} gate(s)")

        return passed, failures

    def score(self, pair: TrainingPair) -> float:
        """
        Compute a quality score between 0.0 and 1.0.
        Score = fraction of gates passed.
        """
        gates = [
            self.gate_minimum_length,
            self.gate_maximum_length,
            self.gate_no_refusal_language,
            self.gate_no_meta_commentary,
            self.gate_has_specifics,
            self.gate_no_hallucination_markers,
            self.gate_citation_validity,
            self.gate_no_pii,
            self.gate_instruction_not_trivial,
        ]
        passed_count = sum(1 for gate in gates if gate(pair).passed)
        return passed_count / len(gates)
