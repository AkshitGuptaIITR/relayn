import datetime
from pydantic import BaseModel


class SyncTriggerResponse(BaseModel):
    message: str
    job_id: str | None = None
    new_messages: int = 0


class JobStatusResponse(BaseModel):
    sync_status: str  # idle, syncing, error, disconnected
    last_synced_at: datetime.datetime | None = None
    last_history_id: str | None = None
    sync_error: str | None = None
    
    queued_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    total_messages: int = 0
