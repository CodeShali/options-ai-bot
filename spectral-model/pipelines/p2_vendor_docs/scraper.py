"""Vendor documentation scraper with httpx, trafilatura, and optional Playwright."""

import asyncio
import hashlib
import json
import logging
import re
from collections import deque
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

from config.settings import settings
from pipelines.shared.rate_limiter import DomainRateLimiter

logger = logging.getLogger(__name__)


def _get_domain_slug(url: str) -> str:
    """Extract a safe filesystem slug from a URL's domain."""
    parsed = urlparse(url)
    return re.sub(r"[^\w.-]", "_", parsed.netloc)


def _url_hash(url: str) -> str:
    """Generate a short hash for a URL to use as a cache key."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _extract_domain(url: str) -> str:
    """Extract the domain name from a URL."""
    return urlparse(url).netloc


class VendorDocScraper:
    """
    Crawls vendor documentation sites and extracts clean text.

    Uses httpx for static pages with trafilatura for content extraction.
    Optionally uses Playwright for JavaScript-heavy pages.
    Respects per-domain rate limits (1 req/sec default).
    Caches all fetched pages to disk.
    """

    def __init__(self, rate_limiter: Optional[DomainRateLimiter] = None):
        self.rate_limiter = rate_limiter or DomainRateLimiter(
            default_rate=1.0, default_capacity=3.0
        )
        self._playwright_available = None

    def _check_playwright(self) -> bool:
        """Check if Playwright is available."""
        if self._playwright_available is None:
            try:
                import playwright  # noqa: F401
                self._playwright_available = True
            except ImportError:
                self._playwright_available = False
                logger.info("Playwright not available; JS-heavy pages will be skipped")
        return self._playwright_available

    def _cache_path(self, domain_slug: str, url: str) -> Path:
        """Get cache file path for a URL."""
        cache_dir = settings.raw_dir / "vendors" / domain_slug
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{_url_hash(url)}.json"

    def _load_cache(self, domain_slug: str, url: str) -> Optional[dict]:
        """Load cached page if it exists."""
        path = self._cache_path(domain_slug, url)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def _save_cache(self, domain_slug: str, url: str, page_data: dict) -> None:
        """Save page data to cache."""
        path = self._cache_path(domain_slug, url)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(page_data, f, indent=2, ensure_ascii=False)

    def _extract_text(self, html: str, url: str) -> str:
        """Extract clean text from HTML using trafilatura."""
        try:
            import trafilatura
            text = trafilatura.extract(
                html,
                url=url,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=True,
            )
            if text and len(text.strip()) > 100:
                return text.strip()
        except ImportError:
            pass

        # Fallback to BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            for elem in soup(["script", "style", "nav", "footer", "header", "aside"]):
                elem.decompose()
            return soup.get_text(separator="\n", strip=True)
        except ImportError:
            return html

    def _extract_links(self, html: str, base_url: str, allowed_prefix: str) -> list[str]:
        """Extract internal links that match the allowed path prefix."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
        except ImportError:
            import re
            hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
            links = []
            for href in hrefs:
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                if parsed.path.startswith(allowed_prefix):
                    links.append(full_url.split("#")[0])
            return list(set(links))

        base_domain = urlparse(base_url).netloc
        links = []

        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            if not href or href.startswith(("#", "mailto:", "javascript:")):
                continue

            full_url = urljoin(base_url, href).split("#")[0]
            parsed = urlparse(full_url)

            if parsed.netloc == base_domain and parsed.path.startswith(allowed_prefix):
                links.append(full_url)

        return list(set(links))

    def _is_js_heavy(self, html: str) -> bool:
        """Heuristically detect if a page is JavaScript-rendered."""
        if len(html) < 5000:
            return True
        # Common SPA indicators
        indicators = [
            "__NEXT_DATA__",
            "ng-app",
            "data-reactroot",
            "vue-app",
            "angular",
            "__nuxt",
        ]
        return any(ind in html for ind in indicators)

    async def fetch_page(self, url: str) -> Optional[dict]:
        """
        Fetch a single page and extract clean text.

        Returns dict: {url, title, text, html, status_code} or None if failed
        """
        domain = _extract_domain(url)
        domain_slug = _get_domain_slug(url)

        # Check cache
        cached = self._load_cache(domain_slug, url)
        if cached:
            logger.debug(f"Cache hit: {url}")
            return cached

        # Rate limit
        await self.rate_limiter.acquire(domain)

        logger.debug(f"Fetching: {url}")

        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "SpectralIAM Training Pipeline/1.0 (research purposes)",
                    "Accept": "text/html,application/xhtml+xml",
                },
            ) as client:
                response = await client.get(url)

                if response.status_code == 404:
                    logger.debug(f"404: {url}")
                    return None

                response.raise_for_status()
                html = response.text

        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP {e.response.status_code} fetching {url}")
            return None
        except httpx.RequestError as e:
            logger.warning(f"Request error fetching {url}: {e}")
            return None

        # Try Playwright for JS-heavy pages
        if self._is_js_heavy(html) and self._check_playwright():
            html = await self._fetch_with_playwright(url) or html

        # Extract content
        text = self._extract_text(html, url)

        if not text or len(text.strip()) < 200:
            logger.debug(f"No meaningful content extracted from {url}")
            return None

        # Extract title
        title = url
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text().strip()
        except Exception:
            pass

        page_data = {
            "url": url,
            "title": title,
            "text": text,
            "char_count": len(text),
        }

        self._save_cache(domain_slug, url, page_data)
        return page_data

    async def _fetch_with_playwright(self, url: str) -> Optional[str]:
        """Use Playwright to render a JS-heavy page."""
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)
                html = await page.content()
                await browser.close()
                return html
        except Exception as e:
            logger.warning(f"Playwright failed for {url}: {e}")
            return None

    async def crawl(
        self,
        start_url: str,
        max_depth: int = 3,
        allowed_path_prefix: str = "/",
        max_pages: int = 200,
    ) -> list[dict]:
        """
        BFS crawl starting from start_url.

        Args:
            start_url: URL to start crawling from
            max_depth: Maximum link depth to follow
            allowed_path_prefix: Only follow links under this path prefix
            max_pages: Maximum pages to fetch

        Returns:
            List of page dicts: {url, title, text, char_count}
        """
        visited = set()
        pages = []
        queue = deque([(start_url, 0)])  # (url, depth)

        base_domain = _extract_domain(start_url)
        domain_slug = _get_domain_slug(start_url)

        logger.info(
            f"Starting crawl: {start_url} "
            f"(depth={max_depth}, prefix={allowed_path_prefix})"
        )

        while queue and len(pages) < max_pages:
            url, depth = queue.popleft()

            if url in visited:
                continue
            visited.add(url)

            # Verify URL is within allowed domain and prefix
            parsed = urlparse(url)
            if parsed.netloc != base_domain:
                continue
            if not parsed.path.startswith(allowed_path_prefix):
                continue

            page_data = await self.fetch_page(url)

            if page_data:
                pages.append(page_data)
                logger.info(
                    f"Crawled [{len(pages)}/{max_pages}] (depth {depth}): "
                    f"{url} ({page_data['char_count']} chars)"
                )

                # Don't follow links from max depth pages
                if depth < max_depth:
                    cached = self._load_cache(domain_slug, url)
                    if cached:
                        # Re-fetch HTML to extract links (expensive but necessary)
                        pass

                    # Extract links from in-memory HTML
                    try:
                        async with httpx.AsyncClient(
                            timeout=10.0, follow_redirects=True
                        ) as client:
                            resp = await client.get(url)
                            links = self._extract_links(
                                resp.text, url, allowed_path_prefix
                            )
                    except Exception:
                        links = []

                    for link in links:
                        if link not in visited:
                            queue.append((link, depth + 1))

        logger.info(
            f"Crawl complete: {len(pages)} pages fetched from {start_url}"
        )
        return pages
