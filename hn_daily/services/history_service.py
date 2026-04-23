import json
from pathlib import Path


class HistoryService:
    """Service to track processed Hacker News story keys."""

    def __init__(self, filename: str = "history.json"):
        """
        Initialize the history service.

        Args:
            filename: The name of the history file.
        """
        self.history_path = Path(filename)
        self.seen_urls = self._load_history()

    def _load_history(self) -> set[str]:
        """
        Load the history of seen story keys from the JSON file.

        Returns:
            A set of seen story keys.
        """
        if not self.history_path.exists():
            return set()

        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {
                        item
                        for item in data
                        if isinstance(item, str) and item
                    }
        except (json.JSONDecodeError, IOError):
            pass

        return set()

    def build_story_key(self, url: str | None, story_id: int) -> str:
        """Build a stable history key for a story."""
        return url or f"hn://item/{story_id}"

    def is_seen(self, story_key: str) -> bool:
        """
        Check if a story key has been seen before.

        Args:
            story_key: The story key to check.

        Returns:
            True if the story key has been seen, False otherwise.
        """
        return story_key in self.seen_urls

    def save_history(self, story_keys: list[str]):
        """
        Overwrite the history file with the provided story keys.
        This effectively keeps only the keys from the current run
        to avoid duplication between two consecutive days.

        Args:
            story_keys: The list of story keys to save.
        """
        sanitized_keys = list(
            dict.fromkeys(
                key for key in story_keys if isinstance(key, str) and key
            )
        )

        try:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(sanitized_keys, f, indent=2)
            self.seen_urls = set(sanitized_keys)
        except IOError:
            # Optionally log this error
            pass
