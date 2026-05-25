"""Tests for Pipeline 1 document fetchers and parsers (no network calls)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import pytest
from pipelines.p1_authoritative_docs.rfc_fetcher import RFCFetcher
from pipelines.p1_authoritative_docs.doc_parser import DocumentParser
from schemas.document import DocumentChunk


# Sample RFC-formatted text (mimics real RFC structure)
SAMPLE_RFC_TEXT = """
Network Working Group                                    J. Hodges
Request for Comments: 4511                               Oblix
Obsoletes: 2251, 2830, 3771                             R. Morgan
Category: Standards Track                                University of Washington
                                                        June 2006


Lightweight Directory Access Protocol (LDAP): The Protocol

Status of This Memo

   This document specifies an Internet standards track protocol for the
   Internet community, and requests discussion and suggestions for
   improvements.

1.  Introduction

   The Lightweight Directory Access Protocol (LDAP) [RFC4510] is an
   Internet protocol for accessing distributed directory services that
   act in accordance with X.500 data and service models.

   This document describes the protocol elements, along with their
   semantics and encodings, of the Lightweight Directory Access
   Protocol (LDAP).

2.  Directory Model

   LDAP aims to describe the core LDAP protocol elements. These
   elements are described in terms of Abstract Syntax Notation One
   (ASN.1).

2.1.  The Directory Information Model

   The directory contains entries that are structured according to
   the directory information model. Each entry has a distinguished
   name (DN) that uniquely identifies it in the directory.

3.  Protocol Model

   The LDAP protocol is asymmetric: clients send requests to servers
   and servers send responses to clients.

3.1.  Operation Types

   LDAP provides the following operations:
   - Bind: Authenticate to the server
   - Search: Find entries matching criteria
   - Modify: Change attribute values
   - Add: Add a new entry
   - Delete: Remove an entry

4.  Security Considerations

   LDAP can transfer sensitive information. Implementors SHOULD use
   Transport Layer Security (TLS) to protect communications. Simple
   bind authentication with cleartext passwords SHOULD only be used
   over TLS-protected connections.

4.1.  Authentication Mechanisms

   LDAP supports multiple authentication mechanisms through the SASL
   framework. Common mechanisms include GSSAPI (Kerberos), EXTERNAL
   (TLS certificates), and DIGEST-MD5.

"""

SAMPLE_MARKDOWN_TEXT = """
# LDAP Search Filters

LDAP search filters allow clients to find specific entries in the directory.

## Basic Filter Syntax

Filters are enclosed in parentheses and follow this pattern:
`(attributeType=value)`

### Equality Filter

The most common filter is the equality filter:
```
(cn=John Smith)
(mail=user@example.com)
```

### Presence Filter

Check if an attribute exists:
```
(mail=*)
(telephoneNumber=*)
```

## Compound Filters

Multiple filters can be combined using logical operators.

### AND Filter

The AND operator (&) requires all conditions to match:
```
(&(objectClass=person)(department=Engineering))
```

### OR Filter

The OR operator (|) matches if any condition is true:
```
(|(cn=Alice)(cn=Bob))
```
"""

SAMPLE_HTML_TEXT = """
<!DOCTYPE html>
<html>
<head><title>OAuth 2.0 Authorization Code Flow</title></head>
<body>
<nav>Navigation links here</nav>
<main>
<h1>OAuth 2.0 Authorization Code Flow</h1>
<p>The authorization code flow is the most secure OAuth 2.0 grant type.
It is designed for server-side applications where the source code is not publicly exposed.</p>

<h2>Step 1: Authorization Request</h2>
<p>The client redirects the user to the authorization endpoint with the following parameters:</p>
<ul>
<li>response_type=code</li>
<li>client_id=your_client_id</li>
<li>redirect_uri=https://yourapp.com/callback</li>
<li>scope=openid profile email</li>
</ul>

<h2>Step 2: Token Exchange</h2>
<p>After the user authorizes, exchange the code for tokens at the token endpoint.</p>
</main>
<footer>Footer content</footer>
</body>
</html>
"""


class TestRFCFetcher:
    """Tests for RFCFetcher (no network calls needed for chunking tests)."""

    def setup_method(self):
        self.fetcher = RFCFetcher()

    def test_normalize_rfc_id_uppercase(self):
        """RFC IDs should be normalized to lowercase."""
        assert self.fetcher._normalize_rfc_id("RFC6749") == "rfc6749"
        assert self.fetcher._normalize_rfc_id("RFC4511") == "rfc4511"

    def test_normalize_rfc_id_already_lowercase(self):
        """Already-lowercase RFC IDs should remain unchanged."""
        assert self.fetcher._normalize_rfc_id("rfc6749") == "rfc6749"

    def test_normalize_rfc_id_strips_whitespace(self):
        """Leading/trailing whitespace should be stripped."""
        assert self.fetcher._normalize_rfc_id("  RFC4511  ") == "rfc4511"

    def test_chunk_by_section_extracts_sections(self):
        """chunk_by_section should extract numbered sections."""
        chunks = self.fetcher.chunk_by_section(SAMPLE_RFC_TEXT)
        assert len(chunks) > 0
        # Check section structure
        for chunk in chunks:
            assert "section_number" in chunk
            assert "title" in chunk
            assert "content" in chunk
            assert "char_count" in chunk
            assert len(chunk["content"]) >= 100

    def test_chunk_by_section_skips_short_sections(self):
        """Sections with less than 100 chars should be skipped."""
        chunks = self.fetcher.chunk_by_section(SAMPLE_RFC_TEXT)
        for chunk in chunks:
            assert chunk["char_count"] >= 100

    def test_chunk_by_section_truncates_long_sections(self):
        """Chunks should not exceed 3000 chars."""
        chunks = self.fetcher.chunk_by_section(SAMPLE_RFC_TEXT)
        for chunk in chunks:
            assert len(chunk["content"]) <= 3000

    def test_chunk_by_section_extracts_parent_section(self):
        """Sub-sections should have parent_section set."""
        chunks = self.fetcher.chunk_by_section(SAMPLE_RFC_TEXT)
        subsections = [c for c in chunks if "." in c["section_number"]]
        for chunk in subsections:
            assert chunk["parent_section"] is not None

    def test_chunk_by_section_empty_text(self):
        """Empty text should return empty list or fallback chunks."""
        chunks = self.fetcher.chunk_by_section("")
        assert isinstance(chunks, list)

    def test_chunk_by_section_no_headers_uses_fallback(self):
        """Text without section headers should use character-based fallback."""
        text = "A" * 5000  # No section headers
        chunks = self.fetcher.chunk_by_section(text)
        assert isinstance(chunks, list)
        # Fallback chunks should be created
        assert len(chunks) > 0

    def test_chunk_preserves_rfc_content(self):
        """Chunk content should contain actual text from the RFC."""
        chunks = self.fetcher.chunk_by_section(SAMPLE_RFC_TEXT)
        all_content = " ".join(c["content"] for c in chunks)
        assert "LDAP" in all_content or "directory" in all_content.lower()


class TestDocumentParser:
    """Tests for DocumentParser format detection and parsing."""

    def setup_method(self):
        self.parser = DocumentParser()

    def test_detect_format_html(self):
        """HTML content should be detected as html."""
        fmt = self.parser._detect_format(SAMPLE_HTML_TEXT)
        assert fmt == "html"

    def test_detect_format_markdown(self):
        """Markdown with headings should be detected as markdown."""
        fmt = self.parser._detect_format(SAMPLE_MARKDOWN_TEXT)
        assert fmt == "markdown"

    def test_detect_format_plain_text(self):
        """Plain RFC text should be detected as text."""
        fmt = self.parser._detect_format(SAMPLE_RFC_TEXT)
        assert fmt == "text"

    def test_detect_format_pdf_bytes(self):
        """Bytes starting with %PDF should be detected as pdf."""
        fake_pdf = b"%PDF-1.4 fake content"
        fmt = self.parser._detect_format(fake_pdf)
        assert fmt == "pdf"

    def test_parse_plain_text_returns_chunks(self):
        """Parsing plain text should return DocumentChunk objects."""
        chunks = self.parser.parse(SAMPLE_RFC_TEXT, format_hint="text", document_id="test-doc")
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, DocumentChunk)
            assert chunk.document_id == "test-doc"

    def test_parse_markdown_returns_chunks(self):
        """Parsing markdown should return DocumentChunk objects."""
        chunks = self.parser.parse(SAMPLE_MARKDOWN_TEXT, format_hint="markdown", document_id="md-doc")
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, DocumentChunk)

    def test_parse_markdown_extracts_titles(self):
        """Markdown parser should extract heading titles."""
        chunks = self.parser.parse(SAMPLE_MARKDOWN_TEXT, format_hint="markdown", document_id="md-doc")
        titles = [c.section_title for c in chunks if c.section_title]
        assert len(titles) > 0

    def test_parse_assigns_chunk_index(self):
        """Chunks should have sequential chunk_index values."""
        chunks = self.parser.parse(SAMPLE_RFC_TEXT, format_hint="text", document_id="test")
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_parse_auto_detects_format(self):
        """Auto format detection should work for all sample texts."""
        # Plain text
        chunks = self.parser.parse(SAMPLE_RFC_TEXT, format_hint="auto")
        assert len(chunks) > 0

        # Markdown
        chunks = self.parser.parse(SAMPLE_MARKDOWN_TEXT, format_hint="auto")
        assert len(chunks) > 0

    def test_parse_html_extracts_content(self):
        """HTML parsing should extract meaningful content."""
        try:
            from bs4 import BeautifulSoup
            has_bs4 = True
        except ImportError:
            has_bs4 = False

        try:
            import trafilatura
            has_trafilatura = True
        except ImportError:
            has_trafilatura = False

        if not (has_bs4 or has_trafilatura):
            pytest.skip("Neither BeautifulSoup nor trafilatura is available")

        chunks = self.parser.parse(SAMPLE_HTML_TEXT, format_hint="html", document_id="html-doc")
        assert isinstance(chunks, list)
        # Should have extracted some content
        all_text = " ".join(c.content for c in chunks)
        # At minimum, we should see IAM-related content
        assert len(all_text) > 50

    def test_fallback_chunks_respect_min_size(self):
        """Fallback chunks should meet minimum size requirement."""
        text = "Short paragraph.\n\n" * 100
        chunks = self.parser._fallback_chunks(text, "test-id")
        for chunk in chunks:
            assert len(chunk.content) >= 100

    def test_parse_bytes_input(self):
        """Parser should handle bytes input."""
        text_bytes = SAMPLE_RFC_TEXT.encode("utf-8")
        chunks = self.parser.parse(text_bytes, format_hint="text", document_id="bytes-doc")
        assert isinstance(chunks, list)
