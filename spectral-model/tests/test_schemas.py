"""Tests for schema models: TrainingPair, SourceDocument, RealWorldProblem."""

import pytest
from datetime import datetime

# Set up path for imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set dummy env vars before importing settings
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")


from schemas.enums import Domain, TaskType, SourceType
from schemas.training_pair import TrainingPair, SourceCitation
from schemas.document import SourceDocument, DocumentChunk
from schemas.problem import RealWorldProblem


class TestTrainingPair:
    """Tests for TrainingPair model validation."""

    def _valid_pair_data(self, **overrides) -> dict:
        data = {
            "domain": Domain.LDAP,
            "task_type": TaskType.EXPLAIN_CONCEPT,
            "source_type": SourceType.RFC,
            "difficulty": "intermediate",
            "instruction": "What is the purpose of the objectClass attribute in LDAP?",
            "output": (
                "The objectClass attribute is a fundamental LDAP attribute that specifies "
                "the structural, auxiliary, and abstract object classes that define "
                "the set of mandatory and optional attributes an entry may contain. "
                "Per RFC 4512, every LDAP entry MUST have an objectClass attribute. "
                "The attribute values determine which other attributes are allowed or required "
                "on the entry. For example, a 'person' objectClass requires 'sn' and 'cn' "
                "attributes and permits many others."
            ),
            "pipeline_id": "test_pipeline",
        }
        data.update(overrides)
        return data

    def test_valid_pair_creates_successfully(self):
        """A fully valid TrainingPair should be created without error."""
        pair = TrainingPair(**self._valid_pair_data())
        assert pair.domain == Domain.LDAP
        assert pair.task_type == TaskType.EXPLAIN_CONCEPT
        assert pair.source_type == SourceType.RFC
        assert pair.difficulty == "intermediate"
        assert pair.id is not None
        assert pair.generated_at is not None

    def test_output_too_short_raises_validation_error(self):
        """Output under 50 chars should fail validation."""
        with pytest.raises(Exception):
            TrainingPair(**self._valid_pair_data(output="Too short"))

    def test_empty_instruction_raises_validation_error(self):
        """Empty instruction should fail validation."""
        with pytest.raises(Exception):
            TrainingPair(**self._valid_pair_data(instruction="   "))

    def test_invalid_difficulty_raises_validation_error(self):
        """Invalid difficulty value should fail validation."""
        with pytest.raises(Exception):
            TrainingPair(**self._valid_pair_data(difficulty="super-hard"))

    def test_quality_score_out_of_range_raises_error(self):
        """Quality score > 1.0 should fail validation."""
        with pytest.raises(Exception):
            TrainingPair(**self._valid_pair_data(quality_score=1.5))

    def test_quality_score_negative_raises_error(self):
        """Quality score < 0.0 should fail validation."""
        with pytest.raises(Exception):
            TrainingPair(**self._valid_pair_data(quality_score=-0.1))

    def test_quality_score_zero_is_valid(self):
        """Quality score of 0.0 should be valid."""
        pair = TrainingPair(**self._valid_pair_data(quality_score=0.0))
        assert pair.quality_score == 0.0

    def test_quality_score_one_is_valid(self):
        """Quality score of 1.0 should be valid."""
        pair = TrainingPair(**self._valid_pair_data(quality_score=1.0))
        assert pair.quality_score == 1.0

    def test_default_values_are_set(self):
        """Default field values should be set correctly."""
        pair = TrainingPair(**self._valid_pair_data())
        assert pair.citations == []
        assert pair.tags == []
        assert pair.quality_score == 0.0
        assert pair.metadata == {}
        assert pair.input_context is None

    def test_with_citations(self):
        """Citations should be properly stored."""
        citation = SourceCitation(
            source_id="RFC4511",
            source_type=SourceType.RFC,
            title="LDAP: The Protocol",
            url="https://www.rfc-editor.org/rfc/rfc4511.txt",
            section="Section 4.5",
        )
        pair = TrainingPair(**self._valid_pair_data(citations=[citation]))
        assert len(pair.citations) == 1
        assert pair.citations[0].source_id == "RFC4511"

    def test_to_messages_format(self):
        """to_messages should return proper chat format."""
        pair = TrainingPair(**self._valid_pair_data())
        messages = pair.to_messages()
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"
        assert messages[1]["content"] == pair.instruction
        assert messages[2]["content"] == pair.output

    def test_to_messages_with_context(self):
        """to_messages with input_context should include context in user message."""
        pair = TrainingPair(**self._valid_pair_data(
            input_context="cn=user,dc=example,dc=com"
        ))
        messages = pair.to_messages()
        user_content = messages[1]["content"]
        assert "Context:" in user_content
        assert "cn=user,dc=example,dc=com" in user_content

    def test_all_domains_are_valid(self):
        """All Domain enum values should be usable."""
        for domain in Domain:
            pair = TrainingPair(**self._valid_pair_data(domain=domain))
            assert pair.domain == domain

    def test_all_task_types_are_valid(self):
        """All TaskType enum values should be usable."""
        for task_type in TaskType:
            pair = TrainingPair(**self._valid_pair_data(task_type=task_type))
            assert pair.task_type == task_type

    def test_all_source_types_are_valid(self):
        """All SourceType enum values should be usable."""
        for source_type in SourceType:
            pair = TrainingPair(**self._valid_pair_data(source_type=source_type))
            assert pair.source_type == source_type


class TestSourceCitation:
    """Tests for SourceCitation model."""

    def test_minimal_citation(self):
        """A minimal citation with just required fields should work."""
        citation = SourceCitation(
            source_id="RFC6749",
            source_type=SourceType.RFC,
            title="The OAuth 2.0 Authorization Framework",
        )
        assert citation.source_id == "RFC6749"
        assert citation.url is None
        assert citation.section is None

    def test_full_citation(self):
        """Full citation with all optional fields."""
        citation = SourceCitation(
            source_id="RFC6749",
            source_type=SourceType.RFC,
            title="The OAuth 2.0 Authorization Framework",
            url="https://www.rfc-editor.org/rfc/rfc6749.txt",
            section="Section 4.1",
            quote="The client MUST use TLS when making requests",
        )
        assert citation.quote is not None
        assert citation.url is not None


class TestSourceDocument:
    """Tests for SourceDocument model."""

    def test_valid_source_document(self):
        """Valid SourceDocument should be created successfully."""
        doc = SourceDocument(
            source_type=SourceType.RFC,
            source_id="RFC4511",
            title="LDAP: The Protocol",
            content="Full RFC text content here...",
            domain=Domain.LDAP,
        )
        assert doc.id is not None
        assert doc.fetched_at is not None
        assert doc.chunks == []
        assert doc.metadata == {}

    def test_source_document_with_chunks(self):
        """SourceDocument should support chunk list."""
        doc = SourceDocument(
            source_type=SourceType.RFC,
            source_id="RFC4511",
            title="LDAP: The Protocol",
            content="Full RFC text content here...",
        )
        chunk = DocumentChunk(
            document_id=doc.id,
            section_number="4.5",
            section_title="Search Operation",
            content="The Search operation allows clients to search for entries...",
            chunk_index=0,
        )
        doc.chunks.append(chunk)
        assert len(doc.chunks) == 1
        assert doc.chunks[0].section_number == "4.5"

    def test_document_chunk_defaults(self):
        """DocumentChunk should have sensible defaults."""
        chunk = DocumentChunk(
            document_id="test-doc-id",
            content="Some section content that is long enough",
        )
        assert chunk.id is not None
        assert chunk.chunk_index == 0
        assert chunk.token_estimate == 0
        assert chunk.section_number is None


class TestRealWorldProblem:
    """Tests for RealWorldProblem model."""

    def test_valid_problem(self):
        """Valid RealWorldProblem should be created successfully."""
        problem = RealWorldProblem(
            source_type=SourceType.STACK_OVERFLOW,
            source_url="https://stackoverflow.com/questions/12345/ldap-filter-question",
            title="How to search LDAP with complex filter?",
            problem_body="I need to find all users in a specific OU that are members of a group...",
            solution_body="You can use a compound filter with the AND operator: (&(ou=Sales)(memberOf=...))...",
            score=42,
            tags=["ldap", "active-directory"],
            domain=Domain.LDAP,
        )
        assert problem.id is not None
        assert problem.score == 42
        assert len(problem.tags) == 2
        assert problem.domain == Domain.LDAP

    def test_problem_defaults(self):
        """RealWorldProblem should have sensible defaults."""
        problem = RealWorldProblem(
            source_type=SourceType.STACK_OVERFLOW,
            source_url="https://example.com",
            title="Test Problem",
            problem_body="Some problem description",
            solution_body="Some solution",
        )
        assert problem.score == 0
        assert problem.tags == []
        assert problem.domain is None
        assert problem.metadata == {}
