from typing import Any, Protocol


class JobHandler(Protocol):
    """Protocol for typed job handlers."""

    async def handle(self, payload: dict[str, Any]) -> None:
        ...


class JobDispatcher:
    """Registry mapping job_type strings to executable handlers."""

    def __init__(self):
        self._handlers: dict[str, JobHandler] = {}

    def register(self, job_type: str, handler: JobHandler) -> None:
        self._handlers[job_type] = handler

    def get_handler(self, job_type: str) -> JobHandler | None:
        return self._handlers.get(job_type)

    def registered_types(self) -> list[str]:
        return list(self._handlers.keys())
