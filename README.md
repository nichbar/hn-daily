# hn-daily

Hacker News daily digest fetcher with crawl4ai. Fetches top stories from yesterday, crawls content and comments, saves to markdown.

## Features

- Fetches top stories from Hacker News (yesterday) via Algolia API (default 10, configurable)
- Crawls story content and comments using crawl4ai
- Saves story markdown files to `drafts/` (configurable via `--output`)
- Daily digest posts are stored in `daily/` as `daily/YYYY/MM/YYYY-MM-DD.md` for the Hugo site
- Rich CLI output with progress tracking

## Installation

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Usage

```bash
# Run with defaults (yesterday's top 15 stories)
python -m hn_daily

# With options
python -m hn_daily --date 2025-01-19 --limit 15 --output my_drafts
```

## Output

Markdown files are saved to `drafts/` with format:
```
{story_title}_{YYYYMMDD}.md
```

Each file contains:
- Story metadata (author, points, URL, date)
- Crawled content
- Comments section

## Project Structure

```
hn-daily/
├── hn_daily/
│   ├── cli.py              # CLI entry point
│   ├── models.py           # Story, Comment, CrawlResult
│   └── services/
│       ├── story_service.py    # Fetch from HN API
│       ├── comment_service.py  # Fetch comments
│       ├── crawler_service.py  # crawl4ai integration
│       └── storage_service.py  # Save to markdown
├── tests/
├── drafts/
├── requirements.txt
└── pyproject.toml
```

## Requirements

- Python 3.10+
- Playwright browsers (`python -m playwright install chromium`)
