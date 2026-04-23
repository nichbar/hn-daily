import json
from hn_daily.services.history_service import HistoryService

def test_history_service_init_empty(tmp_path):
    """Test initializing HistoryService with a non-existent file."""
    history_file = tmp_path / "history.json"
    service = HistoryService(str(history_file))
    assert len(service.seen_urls) == 0
    assert service.is_seen("https://example.com") is False

def test_history_service_save_and_load(tmp_path):
    """Test saving and loading history."""
    history_file = tmp_path / "history.json"
    service = HistoryService(str(history_file))

    urls = ["https://url1.com", "https://url2.com"]
    service.save_history(urls)

    assert history_file.exists()

    # Check if URLs are saved correctly
    with open(history_file, "r") as f:
        data = json.load(f)
        assert data == urls

    # New service instance should load the saved URLs
    new_service = HistoryService(str(history_file))
    assert new_service.is_seen("https://url1.com") is True
    assert new_service.is_seen("https://url2.com") is True
    assert new_service.is_seen("https://url3.com") is False

def test_history_service_overwrite(tmp_path):
    """Test that saving history overwrites the previous contents."""
    history_file = tmp_path / "history.json"
    service = HistoryService(str(history_file))

    service.save_history(["https://old.com"])
    service.save_history(["https://new.com"])

    assert service.is_seen("https://old.com") is False
    assert service.is_seen("https://new.com") is True

    with open(history_file, "r") as f:
        data = json.load(f)
        assert data == ["https://new.com"]

def test_history_service_corrupt_file(tmp_path):
    """Test handling of corrupt JSON file."""
    history_file = tmp_path / "history.json"
    with open(history_file, "w") as f:
        f.write("not json")

    service = HistoryService(str(history_file))
    assert len(service.seen_urls) == 0

def test_history_service_ignores_non_string_entries(tmp_path):
    """Test loading history with invalid entries from older files."""
    history_file = tmp_path / "history.json"
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(["https://valid.com", None, 123, ""], f)

    service = HistoryService(str(history_file))

    assert service.is_seen("https://valid.com") is True
    assert len(service.seen_urls) == 1

def test_build_story_key_for_hn_self_post(tmp_path):
    """Stories without URLs should use a stable item key."""
    history_file = tmp_path / "history.json"
    service = HistoryService(str(history_file))

    assert service.build_story_key(None, 12345) == "hn://item/12345"
    assert service.build_story_key("https://example.com", 12345) == "https://example.com"
