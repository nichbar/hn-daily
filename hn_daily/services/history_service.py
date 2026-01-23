import json
from pathlib import Path

class HistoryService:
    """Service to track processed Hacker News story URLs."""

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
        Load the history of seen URLs from the JSON file.

        Returns:
            A set of seen URLs.
        """
        if not self.history_path.exists():
            return set()

        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
        except (json.JSONDecodeError, IOError):
            pass

        return set()

    def is_seen(self, url: str) -> bool:
        """
        Check if a URL has been seen before.

        Args:
            url: The URL to check.

        Returns:
            True if the URL has been seen, False otherwise.
        """
        return url in self.seen_urls

    def save_history(self, urls: list[str]):
        """
        Overwrite the history file with the provided URLs.
        This effectively keeps only the URLs from the current run
        to avoid duplication between two consecutive days.

        Args:
            urls: The list of URLs to save.
        """
        try:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(urls, f, indent=2)
            self.seen_urls = set(urls)
        except IOError:
            # Optionally log this error
            pass
