"""Web search wrapper supporting Tavily as primary backend."""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SearchClient:
    """Unified search client with Tavily as primary and fallback to empty list."""

    def __init__(self):
        self._tavily_client = None
        self._initialized = False

    def _initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        from config.settings import settings

        if settings.tavily_api_key:
            try:
                from tavily import TavilyClient
                self._tavily_client = TavilyClient(api_key=settings.tavily_api_key)
                logger.info("Tavily search client initialized")
            except ImportError:
                logger.warning("tavily-python not installed, search will be disabled")
        else:
            logger.warning("TAVILY_API_KEY not set, search functionality disabled")

    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "basic",
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Search the web for the given query.

        Returns:
            List of dicts with keys: title, url, content, score
        """
        self._initialize()

        if self._tavily_client is None:
            logger.debug(f"Search skipped (no client): {query}")
            return []

        for attempt in range(3):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self._tavily_search(
                        query, max_results, search_depth, include_domains, exclude_domains
                    ),
                )
                return response
            except Exception as e:
                wait = 2.0 * (2**attempt)
                logger.warning(
                    f"Search error on attempt {attempt + 1}: {e}. Waiting {wait:.1f}s..."
                )
                if attempt < 2:
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"Search failed after 3 attempts: {e}")
                    return []

        return []

    def _tavily_search(
        self,
        query: str,
        max_results: int,
        search_depth: str,
        include_domains: Optional[list[str]],
        exclude_domains: Optional[list[str]],
    ) -> list[dict]:
        """Synchronous Tavily search (called in executor)."""
        kwargs = {
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
        }
        if include_domains:
            kwargs["include_domains"] = include_domains
        if exclude_domains:
            kwargs["exclude_domains"] = exclude_domains

        response = self._tavily_client.search(**kwargs)
        results = response.get("results", [])

        normalized = []
        for r in results:
            normalized.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "score": r.get("score", 0.0),
            })

        return normalized

    async def search_iam_topic(self, topic: str, domain: str) -> list[dict]:
        """Specialized search for IAM topics with domain-specific queries."""
        queries = [
            f"{domain} {topic} IAM",
            f"{topic} identity access management",
            f"{domain} {topic} configuration guide",
        ]

        all_results = []
        seen_urls = set()

        for q in queries[:2]:  # Limit to 2 queries per topic
            results = await self.search(q, max_results=5)
            for r in results:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    all_results.append(r)

        return all_results


# Global singleton
_search_client: Optional[SearchClient] = None


def get_search_client() -> SearchClient:
    global _search_client
    if _search_client is None:
        _search_client = SearchClient()
    return _search_client
