"""Document parser that auto-detects and parses RFC text, Markdown, HTML, and PDF."""

import io
import logging
import re
from typing import Union

from schemas.document import DocumentChunk

logger = logging.getLogger(__name__)


class DocumentParser:
    """
    Multi-format document parser.
    Returns list of DocumentChunk objects from text, markdown, HTML, or PDF input.
    """

    def parse(
        self,
        content: Union[str, bytes],
        format_hint: str = "auto",
        document_id: str = "unknown",
    ) -> list[DocumentChunk]:
        """
        Parse document content into chunks.

        Args:
            content: Document content as string or bytes
            format_hint: 'auto', 'text', 'markdown', 'html', 'pdf'
            document_id: ID to assign to chunks

        Returns:
            List of DocumentChunk objects
        """
        if format_hint == "auto":
            format_hint = self._detect_format(content)

        logger.debug(f"Parsing document as format: {format_hint}")

        if format_hint == "pdf":
            if isinstance(content, str):
                content = content.encode("utf-8")
            return self._parse_pdf(content, document_id)
        elif format_hint == "html":
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")
            return self._parse_html(content, document_id)
        elif format_hint == "markdown":
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")
            return self._parse_markdown(content, document_id)
        else:
            # Default: plain text
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")
            return self._parse_text(content, document_id)

    def _detect_format(self, content: Union[str, bytes]) -> str:
        """Auto-detect document format."""
        if isinstance(content, bytes):
            # Check for PDF magic bytes
            if content[:4] == b"%PDF":
                return "pdf"
            try:
                text = content.decode("utf-8", errors="replace")
            except Exception:
                return "text"
        else:
            text = content

        # Check for HTML
        if re.search(r"<html|<!DOCTYPE|<head|<body", text[:1000], re.IGNORECASE):
            return "html"

        # Check for Markdown
        if re.search(r"^#{1,6}\s+\w", text[:2000], re.MULTILINE):
            return "markdown"

        return "text"

    def _parse_text(self, text: str, document_id: str) -> list[DocumentChunk]:
        """Parse plain text (RFC-style) by section headers."""
        section_re = re.compile(
            r"^(\d+(?:\.\d+)*\.?|[A-Z]\.)\s+([A-Z][^\n]{3,80})$",
            re.MULTILINE,
        )

        chunks = []
        matches = list(section_re.finditer(text))

        if not matches:
            return self._fallback_chunks(text, document_id)

        for i, match in enumerate(matches):
            section_num = match.group(1).rstrip(".")
            section_title = match.group(2).strip()
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()

            if len(content) < 100:
                continue
            if len(content) > 3000:
                content = content[:3000]

            parent = None
            if "." in section_num:
                parent = section_num.rsplit(".", 1)[0]

            chunks.append(DocumentChunk(
                document_id=document_id,
                section_number=section_num,
                section_title=section_title,
                content=content,
                parent_section=parent,
                chunk_index=len(chunks),
                token_estimate=len(content) // 4,
            ))

        return chunks if chunks else self._fallback_chunks(text, document_id)

    def _parse_markdown(self, text: str, document_id: str) -> list[DocumentChunk]:
        """Parse Markdown document by heading sections."""
        # Split on h1-h3 headings
        heading_re = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
        matches = list(heading_re.finditer(text))

        if not matches:
            return self._fallback_chunks(text, document_id)

        chunks = []
        for i, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()

            if len(content) < 100:
                continue
            if len(content) > 3000:
                content = content[:3000]

            chunks.append(DocumentChunk(
                document_id=document_id,
                section_number=str(i + 1),
                section_title=title,
                content=content,
                parent_section=None,
                chunk_index=len(chunks),
                token_estimate=len(content) // 4,
            ))

        return chunks if chunks else self._fallback_chunks(text, document_id)

    def _parse_html(self, html: str, document_id: str) -> list[DocumentChunk]:
        """Parse HTML using trafilatura for clean text extraction."""
        try:
            import trafilatura
            text = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
            )
            if text:
                return self._parse_text(text, document_id)
        except ImportError:
            logger.warning("trafilatura not installed, falling back to BeautifulSoup")

        # Fallback to BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            # Remove script/style elements
            for elem in soup(["script", "style", "nav", "footer", "header"]):
                elem.decompose()

            text = soup.get_text(separator="\n", strip=True)
            return self._parse_text(text, document_id)
        except ImportError:
            logger.warning("BeautifulSoup not installed, treating as plain text")
            return self._parse_text(html, document_id)

    def _parse_pdf(self, pdf_bytes: bytes, document_id: str) -> list[DocumentChunk]:
        """Parse PDF using pypdf."""
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            full_text = "\n\n".join(pages)
            return self._parse_text(full_text, document_id)
        except ImportError:
            logger.warning("pypdf not installed, trying pdfplumber")
            try:
                import pdfplumber
                pages = []
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            pages.append(text)
                full_text = "\n\n".join(pages)
                return self._parse_text(full_text, document_id)
            except ImportError:
                logger.error("Neither pypdf nor pdfplumber is available")
                return []

    def _fallback_chunks(self, text: str, document_id: str, chunk_size: int = 3000) -> list[DocumentChunk]:
        """Split text into fixed-size chunks as fallback."""
        chunks = []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        current_chunk = []
        current_size = 0

        for para in paragraphs:
            if current_size + len(para) > chunk_size and current_chunk:
                content = "\n\n".join(current_chunk)
                if len(content) >= 100:
                    chunks.append(DocumentChunk(
                        document_id=document_id,
                        section_number=str(len(chunks) + 1),
                        section_title=f"Section {len(chunks) + 1}",
                        content=content,
                        chunk_index=len(chunks),
                        token_estimate=len(content) // 4,
                    ))
                current_chunk = [para]
                current_size = len(para)
            else:
                current_chunk.append(para)
                current_size += len(para)

        if current_chunk:
            content = "\n\n".join(current_chunk)
            if len(content) >= 100:
                chunks.append(DocumentChunk(
                    document_id=document_id,
                    section_number=str(len(chunks) + 1),
                    section_title=f"Section {len(chunks) + 1}",
                    content=content,
                    chunk_index=len(chunks),
                    token_estimate=len(content) // 4,
                ))

        return chunks
