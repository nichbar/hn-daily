"""CLI module for hn-daily."""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from .services import (
    StoryService,
    CommentService,
    CrawlerService,
    StorageService,
    HistoryService
)


console = Console()


def check_python_version():
    """Ensure Python version is 3.10+."""
    if sys.version_info < (3, 10):
        console.print(f"[red]Error: Python 3.10+ required. Current version: {sys.version_info.major}.{sys.version_info.minor}[/red]")
        sys.exit(1)


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime."""
    return datetime.strptime(date_str, "%Y-%m-%d")


async def run_daily_digest(
    date: str | None = None,
    limit: int = 10,
    output_dir: str = "drafts"
):
    """
    Run the full daily digest workflow.

    Args:
        date: Date in YYYY-MM-DD format (defaults to yesterday)
        limit: Number of stories to fetch
        output_dir: Output directory for markdown files
    """
    check_python_version()

    target_date = parse_date(date) if date else None

    story_service = StoryService()
    comment_service = CommentService()
    crawler_service = CrawlerService()
    storage_service = StorageService(output_dir)
    history_service = HistoryService()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            # Fetch stories
            task = progress.add_task("Fetching stories from Hacker News...")
            all_stories = await story_service.get_top_stories_from_yesterday(limit, target_date)

            # Deduplicate stories
            stories = [s for s in all_stories if not history_service.is_seen(s.url)]
            skipped_count = len(all_stories) - len(stories)

            progress.update(task, completed=100, description=f"Found {len(all_stories)} stories ({skipped_count} skipped)")

            if not stories:
                console.print("[yellow]No new stories found for the specified date.[/yellow]")
                return

            # Process each story
            results = []
            successfully_processed_urls = []
            for i, story in enumerate(stories, 1):
                progress.console.print(f"\n[cyan]Processing {i}/{len(stories)}: {story.title[:50]}...[/cyan]")

                # Fetch comments
                task = progress.add_task(f"Fetching comments for story {i}...")
                comments = await comment_service.get_comments_for_story(story)
                progress.update(task, completed=100, description=f"Found {len(comments)} comments")

                # Crawl content
                task = progress.add_task(f"Crawling content...")
                crawl_result = await crawler_service.crawl_story(story)
                progress.update(task, completed=100, description="Crawl complete" if crawl_result.success else "Crawl failed")

                # Save to file
                task = progress.add_task(f"Saving to markdown...")
                try:
                    filepath = storage_service.save_content(story, crawl_result, comments)
                    if filepath:
                        results.append((story, filepath, crawl_result.success))
                        successfully_processed_urls.append(story.url)
                        progress.update(task, completed=100, description=f"Saved: {filepath.name}")
                    else:
                        results.append((story, None, False))
                        progress.update(task, completed=100, description=f"Skipped (crawl failed)")
                except Exception as e:
                    results.append((story, None, False))
                    progress.update(task, completed=100, description=f"Save failed: {e}")

        # Print summary
        _print_summary(results)

        # Save history
        if successfully_processed_urls:
            history_service.save_history(successfully_processed_urls)

    finally:
        await story_service.close()
        await comment_service.close()


def _print_summary(results: list):
    """Print a summary table of processed stories."""
    table = Table(title="Daily Digest Summary")
    table.add_column("Status", justify="center", style="green" if all(r[2] for r in results) else "yellow")
    table.add_column("Story", overflow="fold", max_width=50)
    table.add_column("File")

    success_count = sum(1 for r in results if r[2])

    for story, filepath, success in results:
        status = "[green]OK[/green]" if success else "[red]FAIL[/red]"
        filename = filepath.name if filepath else "N/A"
        table.add_row(status, story.title[:50] + "..." if len(story.title) > 50 else story.title, filename)

    console.print(table)
    console.print(f"\nProcessed: {len(results)} | Success: {success_count} | Failed: {len(results) - success_count}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Hacker News Daily Digest - Fetch top stories and save to markdown"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Date in YYYY-MM-DD format (defaults to yesterday)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of stories to fetch (default: 10)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="drafts",
        help="Output directory for markdown files (default: drafts)"
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_daily_digest(args.date, args.limit, args.output))
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
