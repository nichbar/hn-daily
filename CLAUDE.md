# CLAUDE.md

This is a Hacker News daily digest project built with Python 3.10+, crawl4ai, and httpx.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
python -m playwright install chromium

# Run the tool
python -m hn_daily

# Run tests
python -m pytest tests/ -v
```

## Project Structure

- `hn_daily/cli.py` - CLI entry point with argparse (`--date`, `--limit`, `--output`)
- `hn_daily/models.py` - Story, Comment, CrawlResult dataclasses
- `hn_daily/services/` - Service layer:
  - `story_service.py` - Fetch stories from hn.algolia.com API
  - `comment_service.py` - Fetch comments recursively (max depth=2)
  - `crawler_service.py` - crawl4ai integration with retry logic
  - `storage_service.py` - Save to markdown, filename sanitization

## Key Design Notes

- The Algolia HN API doesn't support `sortBy` parameter - stories are returned by relevance by default
- crawl4ai requires Playwright browsers to be installed
- Failed crawls don't abort the batch - each story is processed independently
- Output files use `YYYYMMDD` in filename to avoid collisions
- `daily/` stores the final daily digest posts as `daily-YYYY-MM-DD.md` for the Hugo site

## Testing

Unit tests use `respx` for HTTP mocking:
- `tests/test_models.py` - Data model tests
- `tests/test_storage_service.py` - Storage and formatting tests
- `tests/test_story_service.py` - API integration tests with mocked responses
