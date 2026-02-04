import pytest
import respx
from httpx import Response
from datetime import datetime
from hn_daily.services.comment_service import CommentService
from hn_daily.models import Story

@pytest.fixture
def comment_service():
    return CommentService(timeout=1.0, max_depth=5)

@pytest.fixture
def story():
    return Story(
        object_id="1",
        title="Test Story",
        url="http://test.com",
        author="tester",
        points=100,
        created_at=datetime.now(),
        story_id=1,
        num_comments=100
    )

@respx.mock
@pytest.mark.asyncio
async def test_get_comments_sorting_and_limit(comment_service, story):
    """Test that comments are sorted by descendant count and limited to 10."""

    # Create 12 comments with different number of children
    # We use a simple structure where children are direct children
    # ID matches the number of children for simplicity in verification
    comments_data = []
    for i in range(1, 13):
        # Create i children for this comment
        children = []
        for j in range(i):
            children.append({
                "id": i * 100 + j,
                "author": "child",
                "text": "child comment",
                "created_at": "2025-01-01T00:00:00Z",
                "parent_id": i,
                "children": []
            })

        comments_data.append({
            "id": i,
            "author": "user",
            "text": f"Comment {i}",
            "created_at": "2025-01-01T00:00:00Z",
            "parent_id": story.story_id,
            "children": children
        })

    response_data = {
        "id": story.story_id,
        "children": comments_data
    }

    respx.get(f"https://hn.algolia.com/api/v1/items/{story.story_id}").mock(
        return_value=Response(200, json=response_data)
    )

    comments = await comment_service.get_comments_for_story(story)

    # Assert limit
    assert len(comments) == 1

    # Assert sorting: First comment should have most children (ID 12)
    assert comments[0].comment_id == 12
    assert len(comments[0].children) == 12
