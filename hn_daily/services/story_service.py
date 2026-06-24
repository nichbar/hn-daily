"""Story service for fetching stories from the Hacker News front archive."""

from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import re
from typing import Optional
from urllib.parse import urljoin

import httpx

from ..models import Story
from ..timezone import APP_TIMEZONE


class ApiError(Exception):
    """Raised when API request fails."""
    pass


class HNFrontPageParser(HTMLParser):
    """Parse story rows from a Hacker News front archive page."""

    SITE_URL = "https://news.ycombinator.com/"

    def __init__(self, default_created_at: datetime):
        super().__init__(convert_charrefs=True)
        self.default_created_at = default_created_at
        self.stories: list[Story] = []

        self._current_story: Optional[dict] = None
        self._pending_story: Optional[dict] = None
        self._row_is_story = False
        self._in_titleline = False
        self._capturing_title = False
        self._title_href: Optional[str] = None
        self._title_text: list[str] = []

        self._in_subtext = False
        self._capturing_score = False
        self._capturing_author = False
        self._score_text: list[str] = []
        self._author_text: list[str] = []
        self._subtext_link_href: Optional[str] = None
        self._subtext_link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]):
        attrs_dict = dict(attrs)
        class_tokens = self._class_tokens(attrs_dict.get("class"))

        if tag == "tr":
            self._row_is_story = "athing" in class_tokens
            if self._row_is_story:
                story_id_text = attrs_dict.get("id", "")
                story_id = self._parse_int(story_id_text)
                self._current_story = {
                    "object_id": story_id_text,
                    "story_id": story_id,
                    "title": "Untitled",
                    "url": None,
                }
            return

        if self._row_is_story and tag == "span" and "titleline" in class_tokens:
            self._in_titleline = True
            return

        if self._row_is_story and self._in_titleline and tag == "a" and not self._capturing_title:
            self._capturing_title = True
            self._title_href = attrs_dict.get("href")
            self._title_text = []
            return

        if tag == "td" and "subtext" in class_tokens:
            self._in_subtext = True
            return

        if not self._in_subtext:
            return

        if tag == "span" and "score" in class_tokens:
            self._capturing_score = True
            self._score_text = []
            return

        if tag == "span" and "age" in class_tokens:
            self._set_created_at(attrs_dict.get("title"))
            return

        if tag == "a":
            self._subtext_link_href = attrs_dict.get("href")
            self._subtext_link_text = []
            if "hnuser" in class_tokens:
                self._capturing_author = True
                self._author_text = []

    def handle_data(self, data: str):
        if self._capturing_title:
            self._title_text.append(data)
        if self._capturing_score:
            self._score_text.append(data)
        if self._in_subtext and self._subtext_link_href is not None:
            self._subtext_link_text.append(data)
        if self._capturing_author:
            self._author_text.append(data)

    def handle_endtag(self, tag: str):
        if tag == "a" and self._capturing_title and self._current_story is not None:
            title = "".join(self._title_text).strip()
            if title:
                self._current_story["title"] = title
            if self._title_href:
                self._current_story["url"] = urljoin(self.SITE_URL, self._title_href)
            self._capturing_title = False
            self._title_href = None
            self._title_text = []
            return

        if tag == "span" and self._in_titleline:
            self._in_titleline = False
            return

        if tag == "tr" and self._row_is_story:
            self._pending_story = self._current_story
            self._current_story = None
            self._row_is_story = False
            self._in_titleline = False
            return

        if not self._in_subtext:
            return

        if tag == "span" and self._score_text:
            self._set_points("".join(self._score_text))
            self._capturing_score = False
            self._score_text = []
            return

        if tag == "a" and self._subtext_link_href is not None:
            link_text = "".join(self._subtext_link_text).strip()
            if self._capturing_author:
                self._set_author("".join(self._author_text))
                self._capturing_author = False
                self._author_text = []
            self._set_num_comments(self._subtext_link_href, link_text)
            self._subtext_link_href = None
            self._subtext_link_text = []
            return

        if tag == "td":
            self._append_pending_story()
            self._in_subtext = False

    def _append_pending_story(self):
        if self._pending_story is None:
            return

        story_data = {
            "author": "unknown",
            "points": 0,
            "created_at": self.default_created_at,
            "num_comments": 0,
            **self._pending_story,
        }
        self.stories.append(Story(**story_data))
        self._pending_story = None

    def _set_points(self, text: str):
        if self._pending_story is not None:
            self._pending_story["points"] = self._parse_int(text)

    def _set_author(self, text: str):
        author = text.strip()
        if author and self._pending_story is not None:
            self._pending_story["author"] = author

    def _set_created_at(self, title: Optional[str]):
        if not title or self._pending_story is None:
            return

        for token in reversed(title.split()):
            timestamp = self._parse_int(token)
            if 1_000_000_000 <= timestamp <= 4_102_444_800:
                self._pending_story["created_at"] = datetime.fromtimestamp(timestamp, timezone.utc)
                return

    def _set_num_comments(self, href: str, text: str):
        if self._pending_story is None or "item?id=" not in href:
            return
        if "comment" not in text and text != "discuss":
            return
        self._pending_story["num_comments"] = self._parse_int(text)

    @staticmethod
    def _class_tokens(class_attr: Optional[str]) -> set[str]:
        return set(class_attr.split()) if class_attr else set()

    @staticmethod
    def _parse_int(text: str) -> int:
        digits = "".join(char for char in text if char.isdigit())
        return int(digits) if digits else 0


class HNFrontMarkdownParser:
    """Parse story entries from Jina Reader markdown for a Hacker News archive page."""

    SITE_URL = "https://news.ycombinator.com/"
    STORY_RE = re.compile(
        r"(?P<rank>\d+)\.\[\]"
        r"\(https://news\.ycombinator\.com/vote\?id=(?P<story_id>\d+)[^)]*\)"
        r"\[(?P<title>.*?)\]\((?P<url>.*?)\)"
        r"(?: \(\[[^\]]+\]\([^)]+\)\))? "
        r"(?P<points>\d+) points by "
        r"\[(?P<author>[^\]]+)\]\(https://news\.ycombinator\.com/user\?id=[^)]*\)"
        r"\[[^\]]+\]\(https://news\.ycombinator\.com/item\?id=(?P=story_id)\)"
        r" \| \[(?P<comments>\d+ comments|discuss)\]"
        r"\(https://news\.ycombinator\.com/item\?id=(?P=story_id)\)",
        re.DOTALL,
    )

    def __init__(self, default_created_at: datetime):
        self.default_created_at = default_created_at

    def parse(self, markdown: str) -> list[Story]:
        """Parse Jina Reader markdown into Story objects."""
        stories = []
        for match in self.STORY_RE.finditer(markdown):
            story_id = int(match.group("story_id"))
            stories.append(
                Story(
                    object_id=str(story_id),
                    title=self._clean_text(match.group("title")),
                    url=urljoin(self.SITE_URL, match.group("url")),
                    author=self._clean_text(match.group("author")) or "unknown",
                    points=int(match.group("points")),
                    created_at=self.default_created_at,
                    story_id=story_id,
                    num_comments=self._parse_int(match.group("comments")),
                )
            )
        return stories

    @staticmethod
    def _clean_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _parse_int(text: str) -> int:
        digits = "".join(char for char in text if char.isdigit())
        return int(digits) if digits else 0


class StoryService:
    """Fetches top stories from the Hacker News front archive."""

    HN_BASE_URL = "https://news.ycombinator.com/front"
    READER_BASE_URL = "https://r.jina.ai/"
    BASE_URL = f"{READER_BASE_URL}{HN_BASE_URL}"

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
        Fetch top stories for a target day, ordered by points desc.

        Args:
            limit: Maximum number of stories to return
            date: Optional date to fetch stories from (defaults to yesterday in UTC+8)

        Returns:
            List of Story objects
        """
        if limit <= 0:
            return []

        target_date = self._resolve_target_date(date)
        url = self._build_url(target_date)
        html = await self._make_request(url)
        stories = self._parse_response(html, target_date)
        stories.sort(
            key=lambda story: (story.points, story.num_comments, story.created_at),
            reverse=True,
        )
        return stories[:limit]

    def _resolve_target_date(self, date: Optional[datetime]) -> datetime:
        """Resolve the date to fetch, defaulting to yesterday in UTC+8."""
        if date is None:
            return datetime.now(APP_TIMEZONE) - timedelta(days=1)
        if date.tzinfo is None:
            return date.replace(tzinfo=APP_TIMEZONE)
        return date.astimezone(APP_TIMEZONE)

    def _build_url(self, date: datetime) -> str:
        """Build the Jina Reader URL for a Hacker News front archive day."""
        target_day = date.astimezone(APP_TIMEZONE).strftime("%Y-%m-%d")
        return f"{self.BASE_URL}?day={target_day}"

    async def _make_request(self, url: str) -> str:
        """Make HTTP request to the Hacker News archive."""
        client = await self._get_client()
        print(f"[API] GET {url}")
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            raise ApiError(f"API returned error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise ApiError(f"Request failed: {str(e)}")

    def _parse_response(self, html: str, target_date: datetime) -> list[Story]:
        """Parse Hacker News archive HTML or Jina Reader markdown into Story objects."""
        default_created_at = target_date.astimezone(APP_TIMEZONE).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        markdown_parser = HNFrontMarkdownParser(default_created_at)
        stories = markdown_parser.parse(html)
        if stories:
            return stories

        parser = HNFrontPageParser(default_created_at)
        parser.feed(html)
        return parser.stories
