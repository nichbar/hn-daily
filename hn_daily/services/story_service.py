"""Story service for fetching stories from Algolia Hacker News API."""

import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional
from dateutil.parser import isoparse

from ..models import Story


class ApiError(Exception):
    """Raised when API request fails."""
    pass


class StoryService:
    """Fetches top stories from Algolia Hacker News API."""

    BASE_URL = "https://hn.algolia.com/api/v1/search_by_date"
    PAGE_SIZE = 100

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_top_stories_from_yesterday(
        self,
        limit: int = 15,
        date: Optional[datetime] = None
    ) -> list[Story]:
        """
        Fetch top stories from yesterday, ordered by points desc.

        Args:
            limit: Maximum number of stories to return
            date: Optional date to fetch stories from (defaults to yesterday)

        Returns:
            List of Story objects
        """
        if limit <= 0:
            return []

        target_date = self._resolve_target_date(date)
        start_timestamp, end_timestamp = self._get_day_timestamps(target_date)
        stories = await self._fetch_stories_for_window(start_timestamp, end_timestamp)
        stories.sort(
            key=lambda story: (story.points, story.num_comments, story.created_at),
            reverse=True,
        )
        return stories[:limit]

    def _resolve_target_date(self, date: Optional[datetime]) -> datetime:
        """Resolve the date to fetch, defaulting to yesterday in UTC."""
        if date is None:
            return datetime.now(timezone.utc) - timedelta(days=1)
        if date.tzinfo is None:
            return date.replace(tzinfo=timezone.utc)
        return date.astimezone(timezone.utc)

    def _get_day_timestamps(self, date: datetime) -> tuple[int, int]:
        """Return the inclusive start and exclusive end timestamps for a UTC day."""
        day_start = date.astimezone(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        next_day_start = day_start + timedelta(days=1)
        return int(day_start.timestamp()), int(next_day_start.timestamp())

    async def _fetch_stories_for_window(
        self,
        start_timestamp: int,
        end_timestamp: int,
    ) -> list[Story]:
        """Fetch all stories for a bounded day window and deduplicate them."""
        stories_by_id: dict[str, Story] = {}
        page = 0

        while True:
            url = self._build_url(
                start_timestamp,
                end_timestamp,
                page=page,
                hits_per_page=self.PAGE_SIZE,
            )
            response = await self._make_request(url)

            for story in self._parse_response(response):
                created_at_timestamp = int(story.created_at.astimezone(timezone.utc).timestamp())
                if start_timestamp <= created_at_timestamp < end_timestamp:
                    story_key = story.object_id or str(story.story_id)
                    stories_by_id[story_key] = story

            nb_pages = max(response.get("nbPages", 0), 1)
            if page + 1 >= nb_pages:
                break

            page += 1

        return list(stories_by_id.values())

    def _build_url(
        self,
        start_timestamp: int,
        end_timestamp: int,
        page: int = 0,
        hits_per_page: int = PAGE_SIZE,
    ) -> str:
        """Build the Algolia API URL with proper filters."""
        return (
            f"{self.BASE_URL}?"
            f"tags=story&"
            f"numericFilters=created_at_i>={start_timestamp},created_at_i<{end_timestamp}&"
            f"hitsPerPage={hits_per_page}&"
            f"page={page}"
        )

    async def _make_request(self, url: str) -> dict:
        """Make HTTP request to the API."""
        client = await self._get_client()
        print(f"[API] GET {url}")
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise ApiError(f"API returned error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise ApiError(f"Request failed: {str(e)}")

    def _parse_response(self, data: dict) -> list[Story]:
        """Parse API response into Story objects."""
        stories = []
        for hit in data.get("hits", []):
            try:
                story = Story(
                    object_id=hit.get("objectID", ""),
                    title=hit.get("title", "Untitled"),
                    url=hit.get("url"),
                    author=hit.get("author", "unknown"),
                    points=hit.get("points", 0),
                    created_at=isoparse(hit["created_at"]) if hit.get("created_at") else datetime.now(timezone.utc),
                    story_id=hit.get("story_id", 0),
                    num_comments=hit.get("num_comments", 0)
                )
                stories.append(story)
            except (KeyError, ValueError):
                continue  # Skip invalid entries
        return stories
