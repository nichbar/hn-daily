"""Integration tests for StoryService with mocked API responses."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import respx
from httpx import Response
from urllib.parse import urlencode, quote

from hn_daily.services.story_service import StoryService, ApiError
from hn_daily.models import Story


@pytest.fixture
def story_service():
    """Create a StoryService instance."""
    return StoryService(timeout=10.0)


@pytest.fixture
def sample_api_response():
    """Sample API response from Algolia HN."""
    return {
        "hits": [
            {
                "objectID": "12345",
                "title": "Show HN: My New Project",
                "url": "https://example.com/project",
                "author": "developer",
                "points": 150,
                "created_at": "2025-01-19T10:00:00Z",
                "story_id": 12345,
                "num_comments": 25
            },
            {
                "objectID": "67890",
                "title": "Ask HN: Best practices?",
                "url": None,
                "author": "newbie",
                "points": 75,
                "created_at": "2025-01-19T09:00:00Z",
                "story_id": 67890,
                "num_comments": 10
            }
        ],
        "nbHits": 2,
        "page": 0,
        "nbPages": 1
    }


@respx.mock
@pytest.mark.asyncio
async def test_get_top_stories_from_yesterday(story_service, sample_api_response):
    """Test fetching stories from yesterday."""
    timestamp = int(datetime(2025, 1, 19, 0, 0, 0, tzinfo=timezone.utc).timestamp())

    # Use pattern matching for URL
    route = respx.route(
        method="GET",
        url__startswith=f"https://hn.algolia.com/api/v1/search?tags=story"
    ).mock(
        return_value=Response(200, json=sample_api_response)
    )

    stories = await story_service.get_top_stories_from_yesterday(limit=15)

    assert len(stories) == 2
    assert stories[0].title == "Show HN: My New Project"
    assert stories[0].points == 150
    assert stories[1].title == "Ask HN: Best practices?"
    assert stories[1].url is None


@respx.mock
@pytest.mark.asyncio
async def test_get_top_stories_with_limit(story_service, sample_api_response):
    """Test fetching stories with limit."""
    route = respx.route(
        method="GET",
        url__startswith="https://hn.algolia.com/api/v1/search?tags=story"
    ).mock(
        return_value=Response(200, json=sample_api_response)
    )

    stories = await story_service.get_top_stories_from_yesterday(limit=5)

    assert len(stories) == 2


@respx.mock
@pytest.mark.asyncio
async def test_get_top_stories_empty_response(story_service):
    """Test handling empty API response."""
    route = respx.route(
        method="GET",
        url__startswith="https://hn.algolia.com/api/v1/search?tags=story"
    ).mock(
        return_value=Response(200, json={"hits": [], "nbHits": 0})
    )

    stories = await story_service.get_top_stories_from_yesterday()

    assert len(stories) == 0


@respx.mock
@pytest.mark.asyncio
async def test_get_top_stories_api_error(story_service):
    """Test handling API error."""
    route = respx.route(
        method="GET",
        url__startswith="https://hn.algolia.com/api/v1/search?tags=story"
    ).mock(
        return_value=Response(500, text="Internal Server Error")
    )

    with pytest.raises(ApiError):
        await story_service.get_top_stories_from_yesterday()


@respx.mock
@pytest.mark.asyncio
async def test_parse_response_missing_fields(story_service):
    """Test parsing response with missing optional fields."""
    response = {
        "hits": [
            {
                "objectID": "11111",
                "title": "Minimal Story",
                # Missing optional fields
            }
        ]
    }

    route = respx.route(
        method="GET",
        url__startswith="https://hn.algolia.com/api/v1/search?tags=story"
    ).mock(
        return_value=Response(200, json=response)
    )

    stories = await story_service.get_top_stories_from_yesterday()
    assert len(stories) == 1
    assert stories[0].title == "Minimal Story"
    assert stories[0].author == "unknown"
    assert stories[0].points == 0


@pytest.mark.asyncio
async def test_build_url():
    """Test URL building."""
    service = StoryService()
    timestamp = 1704067200  # 2025-01-01 00:00:00 UTC
    url = service._build_url(timestamp, 10)

    assert "tags=story" in url
    assert "numericFilters=created_at_i>=1704067200" in url
    assert "hitsPerPage=10" in url
    # assert "sortBy=points" in url  # Not supported by API


@pytest.mark.asyncio
async def test_close_service(story_service):
    """Test closing the service."""
    await story_service._get_client()  # Initialize client
    await story_service.close()
    assert story_service._client is None or story_service._client.is_closed
