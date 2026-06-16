"""HTML/text normalizer for vendor documentation."""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def normalize_to_markdown(html_content: str, url: Optional[str] = None) -> str:
    """
    Convert HTML content to clean Markdown using trafilatura and BeautifulSoup.

    Args:
        html_content: Raw HTML string
        url: Optional URL for trafilatura context

    Returns:
        Clean Markdown-ish text string
    """
    # Try trafilatura first (best quality)
    try:
        import trafilatura
        options = {
            "include_comments": False,
            "include_tables": True,
            "no_fallback": False,
            "favor_precision": False,
            "include_formatting": True,
        }
        if url:
            options["url"] = url

        text = trafilatura.extract(html_content, **options)
        if text and len(text.strip()) > 100:
            return _post_process(text)
    except ImportError:
        logger.debug("trafilatura not available, using BeautifulSoup")
    except Exception as e:
        logger.debug(f"trafilatura extraction failed: {e}")

    # Fallback: BeautifulSoup-based extraction
    return _bs4_extract(html_content)


def _bs4_extract(html: str) -> str:
    """Extract text from HTML using BeautifulSoup with Markdown-style formatting."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        # Last resort: regex strip
        text = re.sub(r"<[^>]+>", " ", html)
        return _post_process(text)

    soup = BeautifulSoup(html, "lxml")

    # Remove noise elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    # Convert headings
    for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        level = int(h.name[1])
        prefix = "#" * level + " "
        h.replace_with(f"\n{prefix}{h.get_text().strip()}\n")

    # Convert code blocks
    for pre in soup.find_all("pre"):
        code_text = pre.get_text()
        pre.replace_with(f"\n```\n{code_text}\n```\n")

    # Convert inline code
    for code in soup.find_all("code"):
        code.replace_with(f"`{code.get_text()}`")

    # Convert lists
    for li in soup.find_all("li"):
        li.replace_with(f"\n- {li.get_text().strip()}")

    # Convert paragraphs
    for p in soup.find_all("p"):
        p.replace_with(f"\n{p.get_text().strip()}\n")

    # Convert links
    for a in soup.find_all("a", href=True):
        text = a.get_text().strip()
        href = a.get("href", "")
        if text:
            a.replace_with(f"[{text}]({href})")

    text = soup.get_text(separator="\n")
    return _post_process(text)


def _post_process(text: str) -> str:
    """Clean up extracted text."""
    # Remove multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove leading/trailing whitespace from lines
    lines = [line.rstrip() for line in text.split("\n")]

    # Remove very short lines that are likely navigation artifacts
    # (but keep blank lines for paragraph separation)
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Keep blank lines
        if not stripped:
            cleaned_lines.append("")
        # Keep lines with meaningful content
        elif len(stripped) > 3:
            cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def normalize_text(text: str) -> str:
    """
    Normalize plain text (not HTML).

    Args:
        text: Raw text content

    Returns:
        Normalized text
    """
    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove lines with only whitespace
    lines = [line for line in text.split("\n") if line.strip() or not line]

    return "\n".join(lines).strip()


def chunk_text(text: str, max_chunk_size: int = 3000, min_chunk_size: int = 200) -> list[str]:
    """
    Split text into manageable chunks, preferring paragraph boundaries.

    Args:
        text: Input text
        max_chunk_size: Maximum characters per chunk
        min_chunk_size: Minimum characters for a chunk to be included

    Returns:
        List of text chunks
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = []
    current_size = 0

    for para in paragraphs:
        if current_size + len(para) > max_chunk_size and current:
            chunk = "\n\n".join(current)
            if len(chunk) >= min_chunk_size:
                chunks.append(chunk)
            current = [para]
            current_size = len(para)
        else:
            current.append(para)
            current_size += len(para)

    if current:
        chunk = "\n\n".join(current)
        if len(chunk) >= min_chunk_size:
            chunks.append(chunk)

    return chunks
