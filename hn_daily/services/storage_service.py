"""Storage service for saving content to markdown files."""

import re
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..models import Story, Comment, CrawlResult


class StorageService:
    """Saves story content to markdown files."""

    def __init__(self, output_dir: str = "drafts"):
        self.output_dir = Path(output_dir)
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """Create output directory if it doesn't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_content(
        self,
        story: Story,
        crawl_result: CrawlResult,
        comments: list[Comment],
        custom_output_dir: Optional[str] = None
    ) -> Optional[Path]:
        """
        Save story content and comments to a markdown file.

        Args:
            story: The Story object
            crawl_result: The CrawlResult with content
            comments: List of comments
            custom_output_dir: Optional override for output directory

        Returns:
            Path to the saved file, or None if crawl failed
        """
        # Don't create markdown file if crawling failed and no fallback content
        if not crawl_result.success and not crawl_result.is_fallback:
            return None

        output_dir = Path(custom_output_dir) if custom_output_dir else self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = self._generate_filename(story)
        filepath = output_dir / filename

        markdown = self._create_markdown(story, crawl_result, comments)
        filepath.write_text(markdown, encoding="utf-8")

        return filepath

    def _generate_filename(self, story: Story) -> str:
        """Generate a safe filename from the story title."""
        timestamp = datetime.now().strftime("%Y%m%d")
        sanitized = self._sanitize_title(story.title)
        return f"{sanitized}_{timestamp}.md"

    def _sanitize_title(self, title: str) -> str:
        """Convert story title to a safe filename."""
        # Replace spaces with underscores, remove special chars
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'[\s_-]+', '_', sanitized)
        sanitized = sanitized.strip('_')
        # Limit length
        return sanitized[:100] if sanitized else "untitled"

    def _create_markdown(
        self,
        story: Story,
        crawl_result: CrawlResult,
        comments: list[Comment]
    ) -> str:
        """Generate markdown content with proper formatting."""
        lines = [
            f"# {story.title}",
            "",
            f"**Author:** {story.author} | **Points:** {story.points} | **Comments:** {story.num_comments}",
            f"**URL:** {story.url or f'https://news.ycombinator.com/item?id={story.story_id}'}",
            f"**Date:** {story.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## Crawled Content",
            "",
        ]

        if crawl_result.success or crawl_result.is_fallback:
            lines.append(crawl_result.markdown_content)
            if crawl_result.is_fallback:
                lines.append("")
                lines.append("*Content fetched via fallback HTTP GET.*")
        else:
            lines.append(f"*Crawl failed: {crawl_result.error_message}*")

        lines.extend([
            "",
            "---",
            "",
            f"## Comments ({len(comments)})",
            "",
        ])

        for comment in comments:
            lines.extend(self._format_comment(comment, depth=0))

        return "\n".join(lines)

    def _format_comment(self, comment: Comment, depth: int) -> list[str]:
        """Format a comment and its children as markdown."""
        lines = []
        indent = "  " * depth

        lines.extend([
            f"{indent}### {comment.author}",
            f"{indent}_{comment.created_at.strftime('%Y-%m-%d %H:%M')}_",
            "",
            f"{indent}{comment.text}",
            "",
        ])

        for child in comment.children:
            lines.extend(self._format_comment(child, depth + 1))

        return lines
