"""Integration tests for StoryService with mocked Hacker News archive responses."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import respx
from httpx import Response

from hn_daily.services.story_service import ApiError, StoryService
from hn_daily.timezone import APP_TIMEZONE


class FrozenDateTime(datetime):
    """Frozen datetime helper for deterministic tests."""

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            tz = timezone.utc
        return cls(2025, 1, 20, 12, 0, 0, tzinfo=timezone.utc).astimezone(tz)


@pytest.fixture
def story_service():
    """Create a StoryService instance."""
    return StoryService(timeout=10.0)


def hn_archive_html(story_rows: str, more_link: str = "") -> str:
    """Wrap HN story rows in the minimal table structure used by the parser."""
    return f"""
    <html>
      <body>
        <table class="itemlist">
          {story_rows}
          {more_link}
        </table>
      </body>
    </html>
    """


def hn_story_row(
    story_id: int,
    title: str,
    url: str,
    author: str | None = "alice",
    points: int | None = 10,
    comments: str | None = "5 comments",
    timestamp: int | None = 1737259200,
) -> str:
    """Build a minimal HN story row plus subtext row."""
    score_html = "" if points is None else f'<span class="score" id="score_{story_id}">{points} points</span>'
    author_html = "" if author is None else f'<a href="user?id={author}" class="hnuser">{author}</a>'
    age_attrs = "" if timestamp is None else f' title="2025-01-19T12:00:00 {timestamp}"'
    comments_html = "" if comments is None else f'<a href="item?id={story_id}">{comments}</a>'

    return f"""
    <tr class="athing" id="{story_id}">
      <td class="title"><span class="titleline"><a href="{url}">{title}</a></span></td>
    </tr>
    <tr>
      <td class="subtext">
        {score_html}
        <span class="age"{age_attrs}><a href="item?id={story_id}">1 hour ago</a></span>
        {author_html}
        {comments_html}
      </td>
    </tr>
    """


def jina_archive_markdown() -> str:
    """Minimal Jina Reader markdown for a Hacker News front archive."""
    return """
Title: 06-23 front | Hacker News

URL Source: https://news.ycombinator.com/front?day=2026-06-23

Markdown Content:
1.[](https://news.ycombinator.com/vote?id=48645437&how=up&goto=front%3Fday%3D2026%266%3D23)[Show HN: TikZ Editor - WYSIWYG editor for figures in LaTeX](https://tikz.dev/editor/) ([tikz.dev](https://news.ycombinator.com/from?site=tikz.dev)) 382 points by [DominikPeters](https://news.ycombinator.com/user?id=DominikPeters)[17 hours ago](https://news.ycombinator.com/item?id=48645437) | [71 comments](https://news.ycombinator.com/item?id=48645437)
2.[](https://news.ycombinator.com/vote?id=48645173&how=up&goto=front%3Fday%3D2026%266%3D23)[What we call "age verification" is actually mass surveillance](https://pluralistic.net/2026/06/23/destroy-the-village/) ([pluralistic.net](https://news.ycombinator.com/from?site=pluralistic.net)) 824 points by [hn_acker](https://news.ycombinator.com/user?id=hn_acker)[18 hours ago](https://news.ycombinator.com/item?id=48645173) | [444 comments](https://news.ycombinator.com/item?id=48645173)
3.[](https://news.ycombinator.com/vote?id=48639240&how=up&goto=front%3Fday%3D2026%266%3D23)[VibeThinker: 3B param model that beats Opus 4.5 on reasoning with novel SFT+GRPO](https://arxiv.org/abs/2606.16140) ([arxiv.org](https://news.ycombinator.com/from?site=arxiv.org)) 383 points by [timhigins](https://news.ycombinator.com/user?id=timhigins)[1 day ago](https://news.ycombinator.com/item?id=48639240) | [200 comments](https://news.ycombinator.com/item?id=48639240)
4.[](https://news.ycombinator.com/vote?id=48643489&how=up&goto=front%3Fday%3D2026%266%3D23)[The Low-Tech AI of Elden Ring](https://nega.tv/posts/low-tech-ai-of-elden-ring.html) ([nega.tv](https://news.ycombinator.com/from?site=nega.tv)) 140 points by [g0xA52A2A](https://news.ycombinator.com/user?id=g0xA52A2A)[20 hours ago](https://news.ycombinator.com/item?id=48643489) | [discuss](https://news.ycombinator.com/item?id=48643489)
[More](https://news.ycombinator.com/front?day=2026-06-23&p=2)
    """


@respx.mock
@pytest.mark.asyncio
async def test_get_top_stories_from_date_fetches_jina_archive_and_sorts_by_points(story_service):
    """Stories should be fetched from Jina Reader markdown and ranked by points desc."""

    route = respx.route(
        method="GET",
        url="https://r.jina.ai/https://news.ycombinator.com/front?day=2026-06-23",
    ).mock(return_value=Response(200, text=jina_archive_markdown()))

    stories = await story_service.get_top_stories_from_yesterday(
        limit=2,
        date=datetime(2026, 6, 23),
    )

    assert route.call_count == 1
    assert [story.story_id for story in stories] == [48645173, 48639240]
    assert stories[0].object_id == "48645173"
    assert stories[0].title == 'What we call "age verification" is actually mass surveillance'
    assert stories[0].url == "https://pluralistic.net/2026/06/23/destroy-the-village/"
    assert stories[0].author == "hn_acker"
    assert stories[0].points == 824
    assert stories[0].num_comments == 444
    assert stories[0].created_at == datetime(2026, 6, 23, tzinfo=APP_TIMEZONE)


@respx.mock
@pytest.mark.asyncio
async def test_get_top_stories_from_yesterday_defaults_to_previous_utc8_day(story_service):
    """The default query date should be yesterday in UTC+8."""
    route = respx.route(
        method="GET",
        url="https://r.jina.ai/https://news.ycombinator.com/front?day=2025-01-19",
    ).mock(return_value=Response(200, text=hn_archive_html(hn_story_row(12345, "Default date story", "https://example.com"))))

    with patch("hn_daily.services.story_service.datetime", FrozenDateTime):
        stories = await story_service.get_top_stories_from_yesterday(limit=15)

    assert route.call_count == 1
    assert len(stories) == 1


@respx.mock
@pytest.mark.asyncio
async def test_get_top_stories_fetches_first_archive_page_only(story_service):
    """The first archive page should be used even when HN includes a More link."""
    more_link = '<tr class="morespace"></tr><tr><td><a class="morelink" href="front?day=2025-01-19&amp;p=2">More</a></td></tr>'
    route = respx.route(
        method="GET",
        url="https://r.jina.ai/https://news.ycombinator.com/front?day=2025-01-19",
    ).mock(return_value=Response(200, text=hn_archive_html(hn_story_row(111, "Only page one", "https://example.com"), more_link)))

    stories = await story_service.get_top_stories_from_yesterday(date=datetime(2025, 1, 19))

    assert route.call_count == 1
    assert str(route.calls.last.request.url) == "https://r.jina.ai/https://news.ycombinator.com/front?day=2025-01-19"
    assert [story.story_id for story in stories] == [111]


@respx.mock
@pytest.mark.asyncio
async def test_get_top_stories_empty_response(story_service):
    """Empty archive HTML should return no stories."""
    respx.route(
        method="GET",
        url="https://r.jina.ai/https://news.ycombinator.com/front?day=2025-01-19",
    ).mock(return_value=Response(200, text=hn_archive_html("")))

    stories = await story_service.get_top_stories_from_yesterday(date=datetime(2025, 1, 19))

    assert stories == []


@respx.mock
@pytest.mark.asyncio
async def test_get_top_stories_api_error(story_service):
    """HTTP errors should raise ApiError."""
    respx.route(
        method="GET",
        url="https://r.jina.ai/https://news.ycombinator.com/front?day=2025-01-19",
    ).mock(return_value=Response(500, text="Internal Server Error"))

    with pytest.raises(ApiError):
        await story_service.get_top_stories_from_yesterday(date=datetime(2025, 1, 19))


@respx.mock
@pytest.mark.asyncio
async def test_parse_response_missing_fields_use_defaults(story_service):
    """Missing HN subtext fields should use Story defaults."""
    html = hn_archive_html(
        hn_story_row(
            11111,
            "Minimal Story",
            "https://example.com/minimal",
            author=None,
            points=None,
            comments=None,
            timestamp=None,
        )
    )
    respx.route(
        method="GET",
        url="https://r.jina.ai/https://news.ycombinator.com/front?day=2025-01-19",
    ).mock(return_value=Response(200, text=html))

    stories = await story_service.get_top_stories_from_yesterday(date=datetime(2025, 1, 19, 8, 30, tzinfo=timezone.utc))

    assert len(stories) == 1
    assert stories[0].title == "Minimal Story"
    assert stories[0].author == "unknown"
    assert stories[0].points == 0
    assert stories[0].num_comments == 0
    assert stories[0].created_at == datetime(2025, 1, 19, tzinfo=APP_TIMEZONE)


def test_build_url_uses_front_archive_day(story_service):
    """URL building should target the HN front archive day."""
    url = story_service._build_url(datetime(2025, 1, 19, 20, 0, tzinfo=timezone.utc))

    assert url == "https://r.jina.ai/https://news.ycombinator.com/front?day=2025-01-20"


def test_resolve_target_date_defaults_to_yesterday_in_utc8(story_service):
    """Default target date should be yesterday on the app timezone calendar."""
    with patch("hn_daily.services.story_service.datetime", FrozenDateTime):
        target_date = story_service._resolve_target_date(None)

    assert target_date == datetime(2025, 1, 20, 20, 0, tzinfo=APP_TIMEZONE) - timedelta(days=1)


@pytest.mark.asyncio
async def test_close_service(story_service):
    """Test closing the service."""
    await story_service._get_client()
    await story_service.close()
    assert story_service._client is None or story_service._client.is_closed
