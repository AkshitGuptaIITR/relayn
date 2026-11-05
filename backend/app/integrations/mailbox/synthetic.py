import json
from pathlib import Path
from typing import Any
from app.integrations.mailbox.gateway import IngestedMessage, SyncResult

FIXTURES_PATH = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures" / "synthetic_emails.json"


class SyntheticMailboxGateway:
    """
    Simulates Gmail API sync against a rich fixture library of 50+ career emails.
    Supports initial sync pagination, incremental history changes, and known threads.
    """

    def __init__(self, fixtures_file: Path | None = None):
        self.fixtures_file = fixtures_file or FIXTURES_PATH
        self._messages: list[dict[str, Any]] = []
        self._load_fixtures()

    def _load_fixtures(self) -> None:
        if self.fixtures_file.exists():
            with open(self.fixtures_file, "r", encoding="utf-8") as f:
                self._messages = json.load(f)
        else:
            self._messages = []

    async def fetch_messages(
        self,
        after_history_id: str | None = None,
        limit: int = 50,
    ) -> SyncResult:
        """
        Simulates initial or incremental message fetching.
        If after_history_id is provided, only returns messages with higher numerical history_id.
        """
        filtered = self._messages
        if after_history_id:
            try:
                cursor = int(after_history_id)
                filtered = [m for m in self._messages if int(m.get("history_id", 0)) > cursor]
            except ValueError:
                pass

        # Sort by sent_at asc
        filtered.sort(key=lambda m: m["sent_at"])
        page = filtered[:limit]
        has_more = len(filtered) > limit

        ingested = [IngestedMessage(**m) for m in page]
        latest_history = page[-1]["history_id"] if page else after_history_id

        return SyncResult(
            messages=ingested,
            new_history_id=latest_history,
            has_more=has_more,
        )
