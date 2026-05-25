"""NIST SP document fetcher: downloads and extracts text from NIST PDF documents."""

import asyncio
import io
import logging
from pathlib import Path
from typing import Optional
import re

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

NIST_SP_BASE = "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/"

# Known SP PDF URLs by SP ID
NIST_SP_URLS = {
    "SP800-63A": f"{NIST_SP_BASE}NIST.SP.800-63a.pdf",
    "SP800-63B": f"{NIST_SP_BASE}NIST.SP.800-63b.pdf",
    "SP800-63C": f"{NIST_SP_BASE}NIST.SP.800-63c.pdf",
    "SP800-207": f"{NIST_SP_BASE}NIST.SP.800-207.pdf",
    "SP800-162": f"{NIST_SP_BASE}NIST.SP.800-162.pdf",
    "SP800-53r5": f"{NIST_SP_BASE}NIST.SP.800-53r5.pdf",
    "SP800-178": f"{NIST_SP_BASE}NIST.SP.800-178.pdf",
}


class NISTFetcher:
    """Fetches NIST Special Publication documents, extracts text from PDF."""

    def __init__(self):
        self.cache_dir = settings.raw_dir / "rfcs"  # Share cache dir with RFCs
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, sp_id: str) -> Path:
        safe_id = sp_id.replace("/", "_").replace(" ", "_")
        return self.cache_dir / f"nist_{safe_id}.txt"

    def _pdf_cache_path(self, sp_id: str) -> Path:
        safe_id = sp_id.replace("/", "_").replace(" ", "_")
        return self.cache_dir / f"nist_{safe_id}.pdf"

    def _extract_pdf_text(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes using pypdf."""
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n\n".join(pages)
        except ImportError:
            logger.warning("pypdf not installed, trying pdfplumber")
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    pages = []
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            pages.append(text)
                    return "\n\n".join(pages)
            except ImportError:
                logger.error("Neither pypdf nor pdfplumber is installed")
                raise RuntimeError("PDF extraction requires pypdf or pdfplumber")

    async def fetch(self, sp_id: str) -> str:
        """
        Fetch NIST SP document text (from cache or PDF download).

        Args:
            sp_id: SP identifier e.g. 'SP800-63B'

        Returns:
            Extracted text content
        """
        cache_path = self._cache_path(sp_id)

        if cache_path.exists():
            logger.info(f"Loading {sp_id} from text cache: {cache_path}")
            return cache_path.read_text(encoding="utf-8", errors="replace")

        pdf_cache = self._pdf_cache_path(sp_id)
        if pdf_cache.exists():
            logger.info(f"Extracting text from cached PDF: {pdf_cache}")
            pdf_bytes = pdf_cache.read_bytes()
            text = self._extract_pdf_text(pdf_bytes)
            cache_path.write_text(text, encoding="utf-8")
            return text

        # Determine URL
        url = NIST_SP_URLS.get(sp_id)
        if not url:
            # Try to construct URL
            sp_num = sp_id.replace("SP", "").replace("-", ".").lower()
            url = f"{NIST_SP_BASE}NIST.SP.{sp_num}.pdf"

        logger.info(f"Downloading NIST {sp_id} from {url}")

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(
                    timeout=120.0,
                    follow_redirects=True,
                    headers={"User-Agent": "SpectralIAM Training Pipeline/1.0"},
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    pdf_bytes = response.content

                    # Cache the PDF
                    pdf_cache.write_bytes(pdf_bytes)
                    logger.info(f"Downloaded {sp_id} PDF ({len(pdf_bytes)} bytes)")

                    # Extract and cache text
                    text = self._extract_pdf_text(pdf_bytes)
                    cache_path.write_text(text, encoding="utf-8")
                    logger.info(f"Extracted {len(text)} chars from {sp_id}")
                    return text

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error fetching NIST {sp_id}: {e.response.status_code}")
                raise
            except httpx.RequestError as e:
                wait = 5.0 * (2**attempt)
                logger.warning(f"Request error on attempt {attempt + 1}: {e}. Waiting {wait:.1f}s...")
                if attempt < 2:
                    await asyncio.sleep(wait)
                else:
                    raise

    def chunk_by_section(self, text: str) -> list[dict]:
        """
        Split NIST document text into sections.

        Returns:
            List of dicts: {section_number, title, content, parent_section, char_count}
        """
        # NIST documents use numbered sections like "2.1 Something"
        section_re = re.compile(
            r"^(\d+(?:\.\d+)*)\s+([A-Z][^\n]{5,100})\n",
            re.MULTILINE,
        )

        chunks = []
        matches = list(section_re.finditer(text))

        if not matches:
            # Fallback: 3000-char chunks
            chunk_size = 3000
            for i in range(0, len(text), chunk_size):
                chunk_text = text[i : i + chunk_size]
                if len(chunk_text.strip()) >= 100:
                    chunks.append({
                        "section_number": str(i // chunk_size + 1),
                        "title": f"Section {i // chunk_size + 1}",
                        "content": chunk_text.strip(),
                        "parent_section": None,
                        "char_count": len(chunk_text),
                    })
            return chunks

        for i, match in enumerate(matches):
            section_num = match.group(1)
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

            chunks.append({
                "section_number": section_num,
                "title": section_title,
                "content": content,
                "parent_section": parent,
                "char_count": len(content),
            })

        logger.info(f"Extracted {len(chunks)} chunks from NIST document")
        return chunks

    async def fetch_and_chunk(self, sp_id: str) -> list[dict]:
        """Fetch NIST SP and return chunked sections."""
        text = await self.fetch(sp_id)
        chunks = self.chunk_by_section(text)
        logger.info(f"{sp_id}: {len(chunks)} sections extracted")
        return chunks
