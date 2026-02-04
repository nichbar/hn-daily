"""Crawler service using crawl4ai for content extraction."""

import asyncio
import re
from typing import Optional
from html import unescape

import httpx

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from ..models import Story, CrawlResult


def clean_markdown_content(markdown: str) -> str:
    """Remove navigation elements and clean up markdown."""
    lines = markdown.split('\n')
    cleaned = []

    for line in lines:
        # Skip skip-to links
        if re.search(r'\[ Skip to .*?\]\(https?://', line):
            continue
        # Skip navigation list items
        if re.match(r'^\s*\*\s*\[', line):
            continue
        # Skip site logo lines
        if re.match(r'^\s*\[ !\[.*?\]\(.*?\)\s*\]\(.*?\)', line):
            continue
        # Skip standalone site name lines (often repeated in headers/footers)
        if re.match(r'^Kiel Institute\s*$', line.strip()):
            continue
        if re.match(r'^Search\s*$', line.strip()):
            continue
        # Skip empty lines
        if not line.strip():
            continue
        cleaned.append(line)

    return '\n'.join(cleaned)


def html_to_markdown(html: str) -> str:
    """Convert HTML to markdown (lightweight)."""
    text = unescape(html)
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", text)
    text = re.sub(r"(?is)<!--.*?-->", "", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</(p|div|section|article|li|h[1-6])>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class CrawlError(Exception):
    """Raised when crawling fails after all retries."""
    pass


class CrawlerService:
    """Crawls story content using crawl4ai."""

    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0):
        self.max_retries = max_retries
        self.initial_delay = initial_delay

    def _is_hn_url(self, url: str) -> bool:
        """Check if URL is from Hacker News."""
        return url.startswith("https://news.ycombinator.com/") or \
               url.startswith("http://news.ycombinator.com/")

    async def crawl_story(self, story: Story) -> CrawlResult:
        """
        Crawl a story and return the content.

        Args:
            story: The Story object to crawl

        Returns:
            CrawlResult with content or error
        """
        url = story.url or f"https://news.ycombinator.com/item?id={story.story_id}"
        return await self._crawl_with_retry(url, story.title)

    async def crawl_url(self, url: str, title: str = "") -> CrawlResult:
        """Crawl a specific URL."""
        return await self._crawl_with_retry(url, title)

    async def _crawl_with_retry(self, url: str, title: str) -> CrawlResult:
        """Crawl with exponential backoff retry logic."""
        last_error = None
        delay = self.initial_delay

        for attempt in range(self.max_retries):
            result = await self._do_crawl(url, title)
            if result.success:
                return result

            last_error = Exception(result.error_message or "Unknown crawl error")
            if attempt < self.max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff

        fallback_result = await self._fallback_fetch(url, title)
        if fallback_result.success:
            return fallback_result

        fallback_error = fallback_result.error_message or "Fallback fetch failed"

        return CrawlResult(
            url=url,
            title=title,
            markdown_content="",
            success=False,
            error_message=(
                f"Crawling failed after {self.max_retries} attempts: {str(last_error)}; "
                f"{fallback_error}"
            )
        )

    async def _do_crawl(self, url: str, title: str) -> CrawlResult:
        """Perform the actual crawl."""
        browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )

        # Apply CSS selector for HN URLs to extract only toptext content
        css_selector = "div.toptext" if self._is_hn_url(url) else None

        crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            excluded_tags=['nav', 'footer', 'header'],
            remove_overlay_elements=True,
            css_selector=css_selector
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(
                url=url,
                config=crawler_config
            )

            if result.success:
                # Extract title from markdown if available, otherwise use provided title
                first_line = result.markdown.strip().split('\n')[0] if result.markdown else ""
                extracted_title = first_line[:100] if len(first_line) > 3 else title
                cleaned_content = clean_markdown_content(result.markdown) if result.markdown else ""
                if len(cleaned_content) < 100:
                    return CrawlResult(
                        url=url,
                        title=title,
                        markdown_content="",
                        success=False,
                        error_message="Crawl returned insufficient content"
                    )
                return CrawlResult(
                    url=url,
                    title=title or extracted_title,
                    markdown_content=cleaned_content,
                    success=True
                )
            else:
                return CrawlResult(
                    url=url,
                    title=title,
                    markdown_content="",
                    success=False,
                    error_message=result.error_message or "Unknown crawl error"
                )

    async def _fallback_fetch(self, url: str, title: str) -> CrawlResult:
        """Fetch content with httpx when crawl4ai fails."""
        try:
            headers = {
                "User-Agent": "hn-daily/1.0",
                "Accept": "text/html,application/xhtml+xml"
            }
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=20.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                markdown = html_to_markdown(response.text)
                cleaned_content = clean_markdown_content(markdown) if markdown else ""
                if not cleaned_content:
                    return CrawlResult(
                        url=url,
                        title=title,
                        markdown_content="",
                        success=False,
                        error_message="Fallback fetch returned empty content"
                    )
                return CrawlResult(
                    url=url,
                    title=title,
                    markdown_content=cleaned_content,
                    success=True,
                    is_fallback=True
                )
        except Exception as e:
            return CrawlResult(
                url=url,
                title=title,
                markdown_content="",
                success=False,
                error_message=f"Fallback fetch failed: {e}"
            )

