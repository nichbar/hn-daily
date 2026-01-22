"""Unit tests for StorageService."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from hn_daily.models import Story, Comment, CrawlResult
from hn_daily.services.storage_service import StorageService


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_story():
    """Create a sample story."""
    return Story(
        object_id="12345",
        title="Test Story: A Great Article!",
        url="https://example.com/article",
        author="testuser",
        points=100,
        created_at=datetime(2025, 1, 19, 10, 0, 0, tzinfo=timezone.utc),
        story_id=12345,
        num_comments=5
    )


@pytest.fixture
def sample_crawl_result():
    """Create a sample crawl result."""
    return CrawlResult(
        url="https://example.com/article",
        title="Test Story",
        markdown_content="# Article Content\n\nThis is the article content.",
        success=True
    )


@pytest.fixture
def sample_comments():
    """Create sample comments."""
    return [
        Comment(
            comment_id=1,
            author="user1",
            text="First comment",
            created_at=datetime(2025, 1, 19, 11, 0, 0, tzinfo=timezone.utc),
            parent_id=12345,
            children=[]
        ),
        Comment(
            comment_id=2,
            author="user2",
            text="Second comment",
            created_at=datetime(2025, 1, 19, 11, 30, 0, tzinfo=timezone.utc),
            parent_id=12345,
            children=[]
        )
    ]


def test_sanitize_title():
    """Test title sanitization for filenames."""
    service = StorageService()

    assert service._sanitize_title("Hello World") == "Hello_World"
    assert service._sanitize_title("Test: A Great Article!") == "Test_A_Great_Article"
    assert service._sanitize_title("Multiple   Spaces") == "Multiple_Spaces"
    assert service._sanitize_title("Special@#$%Characters") == "SpecialCharacters"


def test_sanitize_title_truncates_long():
    """Test that long titles are truncated."""
    service = StorageService()
    long_title = "A" * 200
    result = service._sanitize_title(long_title)
    assert len(result) == 100


def test_sanitize_title_empty():
    """Test sanitization of empty title."""
    service = StorageService()
    result = service._sanitize_title("")
    assert result == "untitled"


def test_generate_filename(temp_dir, sample_story):
    """Test filename generation."""
    service = StorageService(output_dir=str(temp_dir))
    filename = service._generate_filename(sample_story)

    assert filename.endswith(".md")
    assert "Test_Story_A_Great_Article" in filename
    assert "_2026" in filename  # Contains year


def test_create_markdown(sample_story, sample_crawl_result, sample_comments):
    """Test markdown generation."""
    service = StorageService()
    markdown = service._create_markdown(sample_story, sample_crawl_result, sample_comments)

    assert "# Test Story: A Great Article!" in markdown
    assert "**Author:** testuser" in markdown
    assert "**Points:** 100" in markdown
    assert "## Crawled Content" in markdown
    assert "# Article Content" in markdown
    assert "## Comments (2)" in markdown
    assert "user1" in markdown
    assert "First comment" in markdown


def test_create_markdown_failed_crawl(sample_story, sample_comments):
    """Test markdown generation with failed crawl."""
    service = StorageService()
    failed_result = CrawlResult(
        url="https://example.com",
        title="Test",
        markdown_content="",
        success=False,
        error_message="Connection timeout"
    )

    markdown = service._create_markdown(sample_story, failed_result, sample_comments)

    assert "*Crawl failed: Connection timeout*" in markdown


def test_save_content(temp_dir, sample_story, sample_crawl_result, sample_comments):
    """Test saving content to file."""
    service = StorageService(output_dir=str(temp_dir))
    filepath = service.save_content(sample_story, sample_crawl_result, sample_comments)

    assert filepath.exists()
    assert filepath.suffix == ".md"
    content = filepath.read_text()
    assert "Test Story" in content


def test_save_content_custom_output_dir(temp_dir, sample_story, sample_crawl_result, sample_comments):
    """Test saving to custom output directory."""
    service = StorageService()
    subdir = temp_dir / "custom"
    filepath = service.save_content(
        sample_story,
        sample_crawl_result,
        sample_comments,
        custom_output_dir=str(subdir)
    )

    assert filepath.exists()
    assert str(subdir) in str(filepath)


def test_save_content_failed_crawl(temp_dir, sample_story, sample_comments):
    """Test that save_content returns None when crawl fails."""
    service = StorageService(output_dir=str(temp_dir))
    failed_result = CrawlResult(
        url="https://example.com",
        title="Test",
        markdown_content="",
        success=False,
        error_message="Connection timeout"
    )

    filepath = service.save_content(sample_story, failed_result, sample_comments)

    assert filepath is None
    # Verify no file was created
    assert not any(temp_dir.glob("*.md"))


def test_format_comment_with_children():
    """Test comment formatting with nested children."""
    service = StorageService()

    child = Comment(
        comment_id=2,
        author="child_user",
        text="Child reply",
        created_at=datetime(2025, 1, 19, 12, 0, 0, tzinfo=timezone.utc),
        parent_id=1,
        children=[]
    )

    parent = Comment(
        comment_id=1,
        author="parent_user",
        text="Parent comment",
        created_at=datetime(2025, 1, 19, 11, 0, 0, tzinfo=timezone.utc),
        parent_id=12345,
        children=[child]
    )

    lines = service._format_comment(parent, depth=0)

    assert "### parent_user" in lines[0]
    assert "child_user" in " ".join(lines)  # Child appears in formatted output
    assert "Child reply" in " ".join(lines)  # Child text appears in output
