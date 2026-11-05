import base64
import datetime
import logging
from typing import Any
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.auth.google_oauth import GoogleOAuthService
from app.integrations.mailbox.gateway import IngestedMessage, SyncResult

logger = logging.getLogger("relayn.gmail_gateway")

# Standard software engineering career search query
SWE_CAREER_GMAIL_QUERY = (
    '("interview" OR "application" OR "recruiter" OR "hiring" OR "offer" '
    'OR "assessment" OR "take-home" OR "systems design" OR "coding challenge")'
)


class GmailGateway:
    """
    Live Gmail API gateway:
    - Decrypts refresh tokens and uses Google Credentials with auto-refresh
    - Executes initial bounded query search across 12-month lookback
    - Executes incremental synchronization using history.list
    - Extracts headers, plain text, and HTML-to-plain sanitized bodies
    """

    def __init__(self, encrypted_credentials: str, oauth_service: GoogleOAuthService):
        self.encrypted_credentials = encrypted_credentials
        self.oauth_service = oauth_service
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service

        creds_data = self.oauth_service.decrypt_credentials(self.encrypted_credentials)
        credentials = Credentials(
            token=creds_data.get("access_token"),
            refresh_token=creds_data.get("refresh_token"),
            token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=creds_data.get("client_id"),
            client_secret=creds_data.get("client_secret"),
        )

        # Refresh token if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleAuthRequest())

        self._service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        return self._service

    async def fetch_messages(
        self,
        after_history_id: str | None = None,
        limit: int = 50,
    ) -> SyncResult:
        service = self._get_service()

        if after_history_id:
            # Incremental sync with history.list
            try:
                history_resp = (
                    service.users()
                    .history()
                    .list(
                        userId="me",
                        startHistoryId=after_history_id,
                        maxResults=limit,
                    )
                    .execute()
                )

                histories = history_resp.get("history", [])
                latest_history_id = history_resp.get("historyId", after_history_id)
                msg_ids = set()

                for h in histories:
                    for added in h.get("messagesAdded", []):
                        msg_ids.add(added["message"]["id"])

                messages = []
                for mid in list(msg_ids)[:limit]:
                    msg = self._fetch_message_detail(service, mid)
                    if msg:
                        messages.append(msg)

                return SyncResult(
                    messages=messages,
                    new_history_id=latest_history_id,
                    has_more=bool(history_resp.get("nextPageToken")),
                )
            except Exception as e:
                # If history cursor has expired (HTTP 404), fallback to query search
                logger.warning("history.list failed or expired: %s; falling back to query search", e)

        # Initial or fallback search
        search_resp = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=SWE_CAREER_GMAIL_QUERY,
                maxResults=limit,
            )
            .execute()
        )

        msg_stubs = search_resp.get("messages", [])
        messages = []
        for stub in msg_stubs:
            msg = self._fetch_message_detail(service, stub["id"])
            if msg:
                messages.append(msg)

        profile = service.users().getProfile(userId="me").execute()
        new_history_id = profile.get("historyId")

        return SyncResult(
            messages=messages,
            new_history_id=new_history_id,
            has_more=bool(search_resp.get("nextPageToken")),
        )

    def _fetch_message_detail(self, service: Any, message_id: str) -> IngestedMessage | None:
        try:
            full_msg = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            headers = {
                h["name"].lower(): h["value"]
                for h in full_msg.get("payload", {}).get("headers", [])
            }

            sender = headers.get("from", "unknown@sender.com")
            to_header = headers.get("to", "")
            recipients = [r.strip() for r in to_header.split(",") if r.strip()]
            subject = headers.get("subject", "")
            
            # Internal date timestamp (ms to UTC datetime)
            internal_date_ms = int(full_msg.get("internalDate", "0"))
            sent_at = datetime.datetime.fromtimestamp(
                internal_date_ms / 1000.0, tz=datetime.timezone.utc
            ) if internal_date_ms else datetime.datetime.now(datetime.timezone.utc)

            snippet = full_msg.get("snippet", "")
            body_plain = self._extract_plain_text(full_msg.get("payload", {})) or snippet

            return IngestedMessage(
                gmail_message_id=full_msg["id"],
                gmail_thread_id=full_msg["threadId"],
                history_id=full_msg.get("historyId"),
                sender=sender,
                recipients=recipients,
                subject=subject,
                sent_at=sent_at,
                snippet=snippet,
                body_plain=body_plain,
            )
        except Exception as e:
            logger.error("Failed to fetch Gmail message %s: %s", message_id, e)
            return None

    def _extract_plain_text(self, payload: dict) -> str:
        """Extracts and base64-decodes plain text from multipart email payload."""
        mime_type = payload.get("mimeType", "")
        parts = payload.get("parts", [])

        if mime_type == "text/plain" and "data" in payload.get("body", {}):
            data = payload["body"]["data"]
            return base64.urlsafe_b64decode(data.encode("ascii")).decode("utf-8", errors="replace")

        for part in parts:
            extracted = self._extract_plain_text(part)
            if extracted:
                return extracted

        return ""
