"""Crawler service using crawl4ai for content extraction."""

import asyncio
import re
from typing import Optional
from datetime import datetime

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
            try:
                return await self._do_crawl(url, title)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff

        return CrawlResult(
            url=url,
            title=title,
            markdown_content="",
            success=False,
            error_message=f"Crawling failed after {self.max_retries} attempts: {str(last_error)}"
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
