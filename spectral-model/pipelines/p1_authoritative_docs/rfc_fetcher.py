"""RFC fetcher: downloads, caches, and chunks RFC text documents."""

import asyncio
import logging
import re
from pathlib import Path

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

RFC_BASE_URL = "https://www.rfc-editor.org/rfc/{rfc_id}.txt"


class RFCFetcher:
    """Fetches RFC documents from rfc-editor.org with disk caching."""

    def __init__(self):
        self.cache_dir = settings.raw_dir / "rfcs"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_rfc_id(self, rfc_id: str) -> str:
        """Normalize RFC ID to lowercase without spaces (e.g. 'RFC6749' -> 'rfc6749')."""
        return rfc_id.strip().lower().replace(" ", "")

    def _cache_path(self, rfc_id: str) -> Path:
        return self.cache_dir / f"{rfc_id}.txt"

    async def fetch(self, rfc_id: str) -> str:
        """
        Fetch RFC text from rfc-editor.org or disk cache.

        Args:
            rfc_id: RFC identifier e.g. 'RFC6749' or 'rfc6749'

        Returns:
            Full RFC text as string
        """
        rfc_id = self._normalize_rfc_id(rfc_id)
        cache_path = self._cache_path(rfc_id)

        if cache_path.exists():
            logger.info(f"Loading {rfc_id} from cache: {cache_path}")
            return cache_path.read_text(encoding="utf-8", errors="replace")

        url = RFC_BASE_URL.format(rfc_id=rfc_id)
        logger.info(f"Fetching {rfc_id} from {url}")

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    text = response.text
                    cache_path.write_text(text, encoding="utf-8")
                    logger.info(f"Cached {rfc_id} to {cache_path} ({len(text)} chars)")
                    return text
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error fetching {url}: {e}")
                raise
            except httpx.RequestError as e:
                wait = 2.0 * (2**attempt)
                logger.warning(f"Request error on attempt {attempt + 1}: {e}. Waiting {wait:.1f}s...")
                if attempt < 2:
                    await asyncio.sleep(wait)
                else:
                    raise

    def chunk_by_section(self, text: str) -> list[dict]:
        """
        Split RFC text into sections based on numbered section headers.

        Args:
            text: Full RFC text content

        Returns:
            List of dicts: {section_number, title, content, parent_section, char_count}
        """
        # RFC section headers: lines like "1.", "2.1.", "A." etc.
        # Pattern: line starting with digit(s) followed by optional sub-sections and dot
        section_header_re = re.compile(
            r"^(\d+(?:\.\d+)*\.?|[A-Z]\.)\s+([A-Z][^\n]{3,80})$",
            re.MULTILINE,
        )

        chunks = []
        lines = text.split("\n")
        full_text = text

        # Find all section starts
        matches = list(section_header_re.finditer(full_text))

        if not matches:
            # Fallback: split into 3000-char chunks
            logger.debug("No section headers found, using character-based chunking")
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

        # Extract content between consecutive section headers
        for i, match in enumerate(matches):
            section_num = match.group(1).rstrip(".")
            section_title = match.group(2).strip()

            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)

            content = full_text[start:end].strip()

            # Skip very short sections
            if len(content) < 100:
                continue

            # Truncate very long sections
            if len(content) > 3000:
                content = content[:3000]

            # Determine parent section
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

        logger.info(f"Extracted {len(chunks)} chunks from RFC text")
        return chunks

    async def fetch_and_chunk(self, rfc_id: str) -> list[dict]:
        """
        Fetch RFC and return chunked sections.

        Args:
            rfc_id: RFC identifier

        Returns:
            List of section chunks
        """
        text = await self.fetch(rfc_id)
        chunks = self.chunk_by_section(text)
        logger.info(f"{rfc_id}: {len(chunks)} sections extracted")
        return chunks
