"""Data models for hn-daily."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Comment:
    """Represents a Hacker News comment."""
    comment_id: int
    author: str
    text: str
    created_at: datetime
    parent_id: int
    children: list["Comment"] = field(default_factory=list)


@dataclass
class Story:
    """Represents a Hacker News story."""
    object_id: str
    title: str
    url: Optional[str]
    author: str
    points: int
    created_at: datetime
    story_id: int
    num_comments: int


@dataclass
class CrawlResult:
    """Result from crawling a story URL."""
    url: str
    title: str
    markdown_content: str
    success: bool
    error_message: Optional[str] = None
