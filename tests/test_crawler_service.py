"""Tests for CrawlerService."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response

from hn_daily.models import CrawlResult, Story
from hn_daily.services.crawler_service import CrawlerService


def _make_story(url: str | None = "https://example.com/article") -> Story:
    """Create a sample story."""
    return Story(
        object_id="12345",
        title="Example Story",
        url=url,
        author="testuser",
        points=100,
        created_at=datetime(2025, 1, 19, 10, 0, 0, tzinfo=timezone.utc),
        story_id=12345,
        num_comments=5,
    )


def _make_result(
    url: str = "https://example.com/article",
    title: str = "Example Story",
    markdown_content: str | None = None,
    success: bool = True,
    error_message: str | None = None,
    is_fallback: bool = False,
) -> CrawlResult:
    """Create a crawl result."""
    return CrawlResult(
        url=url,
        title=title,
        markdown_content=markdown_content or ("Content " * 30),
        success=success,
        error_message=error_message,
        is_fallback=is_fallback,
    )


@pytest.mark.asyncio
async def test_crawl_story_prefers_jina_reader_for_external_urls():
    """External article URLs should use Jina Reader before local crawling."""
    service = CrawlerService()
    story = _make_story()

    with patch.object(service, "_fetch_with_jina_reader", AsyncMock(return_value=_make_result())) as reader_mock, \
         patch.object(service, "_do_crawl", AsyncMock()) as crawl_mock, \
         patch.object(service, "_fallback_fetch", AsyncMock()) as fallback_mock:
        result = await service.crawl_story(story)

    assert result.success is True
    reader_mock.assert_awaited_once_with(story.url, story.title)
    crawl_mock.assert_not_awaited()
    fallback_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_crawl_story_skips_jina_reader_for_hn_pages():
    """Hacker News item pages should stay on the local crawl path."""
    service = CrawlerService()
    story = _make_story("https://news.ycombinator.com/item?id=12345")

    with patch.object(service, "_fetch_with_jina_reader", AsyncMock()) as reader_mock, \
         patch.object(service, "_do_crawl", AsyncMock(return_value=_make_result(url=story.url))) as crawl_mock:
        result = await service.crawl_story(story)

    assert result.success is True
    reader_mock.assert_not_awaited()
    crawl_mock.assert_awaited_once_with(story.url, story.title)


@pytest.mark.asyncio
async def test_crawl_story_falls_back_to_local_crawl_when_jina_reader_fails():
    """Local crawling should run when Jina Reader does not return usable content."""
    service = CrawlerService()
    story = _make_story()
    jina_failure = _make_result(
        url=story.url,
        success=False,
        markdown_content="",
        error_message="Jina Reader returned insufficient content",
    )
    local_success = _make_result(url=story.url)

    with patch.object(service, "_fetch_with_jina_reader", AsyncMock(return_value=jina_failure)) as reader_mock, \
         patch.object(service, "_do_crawl", AsyncMock(return_value=local_success)) as crawl_mock, \
         patch.object(service, "_fallback_fetch", AsyncMock()) as fallback_mock:
        result = await service.crawl_story(story)

    assert result.success is True
    assert result.is_fallback is False
    reader_mock.assert_awaited_once_with(story.url, story.title)
    crawl_mock.assert_awaited_once_with(story.url, story.title)
    fallback_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_crawl_story_uses_http_fallback_after_crawler_exception():
    """Crawler exceptions should not abort the run when fallback fetch succeeds."""
    service = CrawlerService(max_retries=2, initial_delay=0, use_jina_reader=False)
    story = _make_story()
    fallback_success = _make_result(url=story.url, is_fallback=True)

    with patch.object(service, "_do_crawl", AsyncMock(side_effect=RuntimeError("browser failed"))) as crawl_mock, \
         patch.object(service, "_fallback_fetch", AsyncMock(return_value=fallback_success)) as fallback_mock:
        result = await service.crawl_story(story)

    assert result.success is True
    assert result.is_fallback is True
    assert crawl_mock.await_count == 2
    fallback_mock.assert_awaited_once_with(story.url, story.title)


@respx.mock
@pytest.mark.asyncio
async def test_fetch_with_jina_reader_returns_markdown_content():
    """Jina Reader responses should become successful crawl results."""
    service = CrawlerService(jina_timeout=5.0)
    url = "https://example.com/article"
    markdown = "# Article\n\n" + ("Detailed content.\n" * 20)

    respx.get(f"https://r.jina.ai/{url}").mock(return_value=Response(200, text=markdown))

    result = await service._fetch_with_jina_reader(url, "Example Story")

    assert result.success is True
    assert result.markdown_content.startswith("# Article")
