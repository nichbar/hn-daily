"""Story service for fetching stories from Algolia Hacker News API."""

import httpx
from datetime import datetime, timezone
from typing import Optional
from dateutil.parser import isoparse

from ..models import Story


class ApiError(Exception):
    """Raised when API request fails."""
    pass


class StoryService:
    """Fetches top stories from Algolia Hacker News API."""

    BASE_URL = "https://hn.algolia.com/api/v1/search"

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
        if date is None:
            yesterday = datetime.now(timezone.utc)
        else:
            yesterday = date.replace(tzinfo=timezone.utc)

        yesterday_start = yesterday.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        timestamp = int(yesterday_start.timestamp())

        url = self._build_url(timestamp, limit)
        response = await self._make_request(url)
        return self._parse_response(response)

    def _build_url(self, timestamp: int, limit: int) -> str:
        """Build the Algolia API URL with proper filters."""
        return (
            f"{self.BASE_URL}?"
            f"tags=story&"
            f"numericFilters=created_at_i>={timestamp}&"
            f"hitsPerPage={limit}"
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
            except (KeyError, ValueError) as e:
                continue  # Skip invalid entries
        return stories
