"""Unit tests for data models."""

from datetime import datetime, timezone
from hn_daily.models import Story, Comment, CrawlResult


def test_story_creation():
    """Test Story dataclass creation."""
    story = Story(
        object_id="12345",
        title="Test Story",
        url="https://example.com",
        author="testuser",
        points=100,
        created_at=datetime.now(timezone.utc),
        story_id=12345,
        num_comments=10
    )

    assert story.object_id == "12345"
    assert story.title == "Test Story"
    assert story.url == "https://example.com"
    assert story.author == "testuser"
    assert story.points == 100
    assert story.story_id == 12345
    assert story.num_comments == 10


def test_story_optional_url():
    """Test Story with optional URL."""
    story = Story(
        object_id="12345",
        title="Ask HN",
        url=None,
        author="testuser",
        points=50,
        created_at=datetime.now(timezone.utc),
        story_id=12345,
        num_comments=5
    )

    assert story.url is None


def test_comment_creation():
    """Test Comment dataclass creation."""
    comment = Comment(
        comment_id=1,
        author="commenter",
        text="This is a comment",
        created_at=datetime.now(timezone.utc),
        parent_id=12345,
        children=[]
    )

    assert comment.comment_id == 1
    assert comment.author == "commenter"
    assert comment.text == "This is a comment"
    assert comment.parent_id == 12345
    assert comment.children == []


def test_comment_with_children():
    """Test Comment with nested children."""
    child = Comment(
        comment_id=2,
        author="child",
        text="Reply",
        created_at=datetime.now(timezone.utc),
        parent_id=1,
        children=[]
    )

    parent = Comment(
        comment_id=1,
        author="parent",
        text="Parent comment",
        created_at=datetime.now(timezone.utc),
        parent_id=12345,
        children=[child]
    )

    assert len(parent.children) == 1
    assert parent.children[0].author == "child"


def test_crawl_result_success():
    """Test successful CrawlResult."""
    result = CrawlResult(
        url="https://example.com",
        title="Example",
        markdown_content="# Hello",
        success=True
    )

    assert result.success is True
    assert result.error_message is None


def test_crawl_result_failure():
    """Test failed CrawlResult."""
    result = CrawlResult(
        url="https://example.com",
        title="Example",
        markdown_content="",
        success=False,
        error_message="Connection timeout"
    )

    assert result.success is False
    assert result.error_message == "Connection timeout"
