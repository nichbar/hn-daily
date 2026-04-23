"""Integration tests for StoryService with mocked API responses."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import respx
from httpx import Response

from hn_daily.services.story_service import StoryService, ApiError


class FrozenDateTime(datetime):
    """Frozen datetime helper for deterministic tests."""

    @classmethod
    def now(cls, tz=None):
        return cls(2025, 1, 20, 12, 0, 0, tzinfo=tz or timezone.utc)


@pytest.fixture
def story_service():
    """Create a StoryService instance."""
    return StoryService(timeout=10.0)


@respx.mock
@pytest.mark.asyncio
async def test_get_top_stories_from_date_fetches_full_day_and_sorts_by_points(story_service):
    """Stories should be fetched for one day and ranked by points desc."""
    page_one = {
        "hits": [
            {
                "objectID": "111",
                "title": "Morning story",
                "url": "https://example.com/morning",
                "author": "alice",
                "points": 50,
                "created_at": "2025-01-19T08:00:00Z",
                "story_id": 111,
                "num_comments": 5,
            },
            {
                "objectID": "112",
                "title": "Overnight story",
                "url": "https://example.com/overnight",
                "author": "bob",
                "points": 10,
                "created_at": "2025-01-19T01:00:00Z",
                "story_id": 112,
                "num_comments": 2,
            },
        ],
        "nbHits": 4,
        "page": 0,
        "nbPages": 2,
    }
    page_two = {
        "hits": [
            {
                "objectID": "113",
                "title": "Top story",
                "url": "https://example.com/top",
                "author": "carol",
                "points": 150,
                "created_at": "2025-01-19T12:00:00Z",
                "story_id": 113,
                "num_comments": 25,
            },
            {
                "objectID": "114",
                "title": "Runner up",
                "url": None,
                "author": "dave",
                "points": 120,
                "created_at": "2025-01-19T15:00:00Z",
                "story_id": 114,
                "num_comments": 12,
            },
        ],
        "nbHits": 4,
        "page": 1,
        "nbPages": 2,
    }

    route = respx.route(
        method="GET",
        url__startswith=story_service.BASE_URL,
    ).mock(side_effect=[Response(200, json=page_one), Response(200, json=page_two)])

    stories = await story_service.get_top_stories_from_yesterday(
        limit=2,
        date=datetime(2025, 1, 19),
    )

    assert route.call_count == 2
    assert [story.story_id for story in stories] == [113, 114]
    assert stories[0].points == 150
    assert stories[1].url is None


@respx.mock
@pytest.mark.asyncio
async def test_get_top_stories_from_yesterday_defaults_to_previous_utc_day(story_service):
    """The default query date should be yesterday in UTC."""
    response = {
        "hits": [
            {
                "objectID": "12345",
                "title": "Default date story",
                "url": "https://example.com/project",
                "author": "developer",
                "points": 150,
                "created_at": "2025-01-19T10:00:00Z",
                "story_id": 12345,
                "num_comments": 25,
            }
        ],
        "nbHits": 1,
        "page": 0,
        "nbPages": 1,
    }

    route = respx.route(
        method="GET",
        url__startswith=story_service.BASE_URL,
    ).mock(return_value=Response(200, json=response))

    with patch("hn_daily.services.story_service.datetime", FrozenDateTime):
        stories = await story_service.get_top_stories_from_yesterday(limit=15)

    request_url = str(route.calls.last.request.url)
    assert "created_at_i%3E=1737244800" in request_url
    assert "created_at_i%3C1737331200" in request_url
    assert len(stories) == 1


@respx.mock
@pytest.mark.asyncio
async def test_get_top_stories_empty_response(story_service):
    """Test handling empty API response."""
    respx.route(
        method="GET",
        url__startswith=story_service.BASE_URL,
    ).mock(return_value=Response(200, json={"hits": [], "nbHits": 0, "nbPages": 0}))

    stories = await story_service.get_top_stories_from_yesterday(date=datetime(2025, 1, 19))

    assert len(stories) == 0


@respx.mock
@pytest.mark.asyncio
async def test_get_top_stories_api_error(story_service):
    """Test handling API error."""
    respx.route(
        method="GET",
        url__startswith=story_service.BASE_URL,
    ).mock(return_value=Response(500, text="Internal Server Error"))

    with pytest.raises(ApiError):
        await story_service.get_top_stories_from_yesterday(date=datetime(2025, 1, 19))


@respx.mock
@pytest.mark.asyncio
async def test_parse_response_missing_fields(story_service):
    """Test parsing response with missing optional fields."""
    response = {
        "hits": [
            {
                "objectID": "11111",
                "title": "Minimal Story",
                "created_at": "2025-01-19T00:00:00Z",
            }
        ],
        "nbHits": 1,
        "page": 0,
        "nbPages": 1,
    }

    respx.route(
        method="GET",
        url__startswith=story_service.BASE_URL,
    ).mock(return_value=Response(200, json=response))

    stories = await story_service.get_top_stories_from_yesterday(date=datetime(2025, 1, 19))
    assert len(stories) == 1
    assert stories[0].title == "Minimal Story"
    assert stories[0].author == "unknown"
    assert stories[0].points == 0


def test_build_url():
    """Test URL building for a bounded day window."""
    service = StoryService()
    start_timestamp = 1704067200  # 2024-01-01 00:00:00 UTC
    end_timestamp = 1704153600    # 2024-01-02 00:00:00 UTC
    url = service._build_url(start_timestamp, end_timestamp, page=3, hits_per_page=100)

    assert "tags=story" in url
    assert "numericFilters=created_at_i>=1704067200,created_at_i<1704153600" in url
    assert "hitsPerPage=100" in url
    assert "page=3" in url


def test_get_day_timestamps_uses_single_utc_day(story_service):
    """Day timestamp helper should return the current day's UTC bounds."""
    start_timestamp, end_timestamp = story_service._get_day_timestamps(
        datetime(2025, 1, 19, 8, 30, tzinfo=timezone.utc)
    )

    assert start_timestamp == 1737244800
    assert end_timestamp == 1737331200


@pytest.mark.asyncio
async def test_close_service(story_service):
    """Test closing the service."""
    await story_service._get_client()
    await story_service.close()
    assert story_service._client is None or story_service._client.is_closed
