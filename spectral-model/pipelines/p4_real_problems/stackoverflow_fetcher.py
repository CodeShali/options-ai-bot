"""Stack Exchange API fetcher for IAM-related Q&A data."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
import html

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

STACK_API_BASE = "https://api.stackexchange.com/2.3"


async def fetch_questions_by_tag(
    tag: str,
    min_score: int = 5,
    has_accepted: bool = True,
    page_size: int = 50,
    max_pages: int = 5,
    site: str = "stackoverflow",
) -> list[dict]:
    """
    Fetch questions with accepted answers from Stack Exchange API.

    Args:
        tag: Stack Overflow tag (e.g. 'ldap', 'oauth-2.0')
        min_score: Minimum question score to include
        has_accepted: If True, only include questions with accepted answers
        page_size: Items per page (max 100)
        max_pages: Maximum pages to fetch
        site: Stack Exchange site name

    Returns:
        List of dicts with question and answer information
    """
    cache_path = settings.raw_dir / "problems" / f"so_{tag.replace('/', '_')}.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        logger.info(f"Loading Stack Overflow [{tag}] from cache: {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    logger.info(f"Fetching Stack Overflow questions with tag: [{tag}]")
    all_items = []

    params = {
        "tagged": tag,
        "order": "desc",
        "sort": "votes",
        "site": site,
        "filter": "withbody",  # Include question/answer bodies
        "pagesize": min(page_size, 100),
        "min": min_score,
    }

    if has_accepted:
        params["accepted"] = "True"

    if settings.stack_exchange_api_key:
        params["key"] = settings.stack_exchange_api_key

    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"Accept-Encoding": "gzip"},
    ) as client:
        for page in range(1, max_pages + 1):
            params["page"] = page

            for attempt in range(3):
                try:
                    response = await client.get(f"{STACK_API_BASE}/questions", params=params)
                    response.raise_for_status()
                    data = response.json()
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        wait = 30.0 * (2**attempt)
                        logger.warning(f"Rate limited by Stack Exchange. Waiting {wait:.1f}s...")
                        await asyncio.sleep(wait)
                    elif attempt < 2:
                        await asyncio.sleep(5.0 * (2**attempt))
                    else:
                        logger.error(f"HTTP error fetching SO [{tag}] page {page}: {e}")
                        raise
                except httpx.RequestError as e:
                    if attempt < 2:
                        await asyncio.sleep(5.0 * (2**attempt))
                    else:
                        logger.error(f"Request error fetching SO [{tag}] page {page}: {e}")
                        raise
            else:
                break

            items = data.get("items", [])
            logger.info(f"SO [{tag}] page {page}: {len(items)} questions")

            if not items:
                break

            # Fetch accepted answers for these questions
            question_ids = [str(q["question_id"]) for q in items if q.get("accepted_answer_id")]

            if question_ids:
                answers = await _fetch_answers(client, question_ids, site, params.get("key"))
                answer_map = {a["question_id"]: a for a in answers}
            else:
                answer_map = {}

            for question in items:
                qid = question["question_id"]
                accepted_id = question.get("accepted_answer_id")
                answer = answer_map.get(qid) or None

                if has_accepted and not answer:
                    continue

                item = {
                    "question_id": qid,
                    "title": html.unescape(question.get("title", "")),
                    "body": _clean_html(question.get("body", "")),
                    "score": question.get("score", 0),
                    "tags": question.get("tags", []),
                    "link": question.get("link", ""),
                    "accepted_answer_id": accepted_id,
                    "answer_body": _clean_html(answer.get("body", "")) if answer else "",
                    "answer_score": answer.get("score", 0) if answer else 0,
                    "view_count": question.get("view_count", 0),
                    "creation_date": question.get("creation_date", 0),
                }
                all_items.append(item)

            # Respect API backoff
            backoff = data.get("backoff", 0)
            if backoff:
                logger.info(f"Stack Exchange backoff: {backoff}s")
                await asyncio.sleep(backoff)

            if not data.get("has_more", False):
                break

            # Rate limiting: 0.5 req/s without key, 2 req/s with key
            await asyncio.sleep(0.5 if not settings.stack_exchange_api_key else 0.2)

    logger.info(f"Fetched {len(all_items)} Q&A pairs for tag [{tag}]")

    # Cache results
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2)

    return all_items


async def _fetch_answers(
    client: httpx.AsyncClient,
    question_ids: list[str],
    site: str,
    api_key: Optional[str],
) -> list[dict]:
    """Fetch answers for a list of question IDs."""
    if not question_ids:
        return []

    ids_str = ";".join(question_ids[:30])  # API limit
    params = {
        "site": site,
        "filter": "withbody",
        "pagesize": 100,
    }
    if api_key:
        params["key"] = api_key

    try:
        response = await client.get(
            f"{STACK_API_BASE}/questions/{ids_str}/answers",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])
    except Exception as e:
        logger.warning(f"Failed to fetch answers: {e}")
        return []


def _clean_html(html_content: str) -> str:
    """Strip HTML tags from content, preserving code blocks."""
    if not html_content:
        return ""

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")

        # Preserve code blocks with markers
        for code in soup.find_all("code"):
            code_text = code.get_text()
            code.replace_with(f"\n```\n{code_text}\n```\n")

        for pre in soup.find_all("pre"):
            pre_text = pre.get_text()
            pre.replace_with(f"\n```\n{pre_text}\n```\n")

        text = soup.get_text(separator="\n")
        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(line for line in lines if line or lines.index(line) > 0)
        return text.strip()
    except ImportError:
        # Fallback: simple tag removal
        import re
        text = re.sub(r"<[^>]+>", " ", html_content)
        return html.unescape(text).strip()
