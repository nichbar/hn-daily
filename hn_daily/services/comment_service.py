"""Comment service for fetching comments from Hacker News."""

import httpx
from datetime import datetime, timezone
from typing import Optional
from dateutil.parser import isoparse
import asyncio

from ..models import Story, Comment


class CommentService:
    """Fetches comments associated with stories."""

    def __init__(self, timeout: float = 30.0, max_depth: int = 2):
        self.timeout = timeout
        self.max_depth = max_depth
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

    async def get_comments_for_story(self, story: Story) -> list[Comment]:
        """
        Fetch all top-level comments for a story.

        Args:
            story: The Story object to fetch comments for

        Returns:
            List of Comment objects
        """
        if story.num_comments == 0:
            return []

        url = f"https://hn.algolia.com/api/v1/items/{story.story_id}"
        client = await self._get_client()
        print(f"[API] GET {url}")

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError:
            return []
        except httpx.RequestError:
            return []

        children_map = {}
        comments = []

        for item in data.get("children", []):
            comment = self._parse_comment(item, depth=0)
            children_map[comment.comment_id] = comment

            if comment.parent_id == 0 or comment.parent_id == story.story_id:
                comments.append(comment)
            else:
                parent = children_map.get(comment.parent_id)
                if parent and len(parent.children) < 10:  # Limit children per comment
                    parent.children.append(comment)

        # Sort by total descendants (descending)
        comments.sort(key=self._get_descendant_count, reverse=True)

        # Limit to top 2
        return comments[:2]

    def _parse_comment(self, data: dict, depth: int = 0) -> Comment:
        """Parse a comment from API data."""
        children = []
        if depth < self.max_depth:
            for child_data in data.get("children", []):
                child = self._parse_comment(child_data, depth + 1)
                children.append(child)

        return Comment(
            comment_id=data.get("id", 0),
            author=data.get("author", "unknown"),
            text=data.get("text", ""),
            created_at=isoparse(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            parent_id=data.get("parent_id", 0),
            children=children
        )

    def _get_descendant_count(self, comment: Comment) -> int:
        """Recursive count of all descendants."""
        count = len(comment.children)
        for child in comment.children:
            count += self._get_descendant_count(child)
        return count
