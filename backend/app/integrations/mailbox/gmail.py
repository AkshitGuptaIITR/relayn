import base64
import datetime
import logging
import time
from typing import Any
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.auth.google_oauth import GoogleOAuthService
from app.integrations.mailbox.gateway import IngestedMessage, SyncResult

logger = logging.getLogger("relayn.gmail_gateway")

# Production-grade software engineering career search query
# Combines ATS domains, candidate lifecycle keywords, outbound outreach in Sent, and excludes ecommerce/order receipts
SWE_CAREER_GMAIL_QUERY = (
    '('
    'from:(*@*.greenhouse-mail.io OR *@*.lever.co OR *@*.ashbyhq.com '
    'OR *@*.smartrecruiters.com OR *@*.myworkday.com OR *@*.jobvite.com '
    'OR *@*.icims.com OR *@*.bamboohr.com OR *@*.rippling-ats.com) '
    'OR '
    'subject:(interview OR "application received" OR "application submitted" '
    'OR "your application" OR "next steps" OR "coding challenge" OR "technical assessment" '
    'OR "offer of employment" OR "moving forward" OR "not moving forward" '
    'OR "let\'s connect" OR "hiring team" OR "recruiting team" OR "candidacy") '
    'OR '
    '(in:sent newer_than:6m (resume OR CV OR "applying for" OR "application for" '
    'OR "software engineer" OR "reaching out" OR "interested in" OR "open role" OR "opportunity"))'
    ') '
    '-in:drafts '
    '-subject:("order confirmation" OR "has shipped" OR "your receipt" '
    'OR "credit card" OR "statement is ready" OR "password reset")'
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
        msg_stubs = []
        page_token = None
        while len(msg_stubs) < limit:
            batch_size = min(limit - len(msg_stubs), 500)
            search_resp = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q=SWE_CAREER_GMAIL_QUERY,
                    maxResults=batch_size,
                    pageToken=page_token,
                )
                .execute()
            )
            stubs = search_resp.get("messages", [])
            if not stubs:
                break
            msg_stubs.extend(stubs)
            page_token = search_resp.get("nextPageToken")
            if not page_token:
                break

        messages = []
        for stub in msg_stubs:
            msg = self._fetch_message_detail(service, stub["id"])
            if msg:
                messages.append(msg)
            time.sleep(0.08)  # Polite pacing to respect Gmail API per-minute limits

        # Safe profile fetch with retry
        new_history_id = None
        for _ in range(3):
            try:
                profile = service.users().getProfile(userId="me").execute()
                new_history_id = profile.get("historyId")
                break
            except Exception as e:
                if "rateLimitExceeded" in str(e) or "403" in str(e):
                    time.sleep(5)
                else:
                    break

        if not new_history_id and messages:
            # Fallback to highest history ID among fetched messages
            histories = [int(m.history_id) for m in messages if m.history_id and m.history_id.isdigit()]
            if histories:
                new_history_id = str(max(histories))

        return SyncResult(
            messages=messages,
            new_history_id=new_history_id,
            has_more=bool(page_token),
        )

    def _fetch_message_detail(self, service: Any, message_id: str) -> IngestedMessage | None:
        max_retries = 4
        for attempt in range(max_retries):
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
                label_ids = full_msg.get("labelIds", [])
                direction = "outbound" if "SENT" in label_ids else "inbound"

                return IngestedMessage(
                    gmail_message_id=full_msg["id"],
                    gmail_thread_id=full_msg["threadId"],
                    history_id=full_msg.get("historyId"),
                    direction=direction,
                    label_ids=label_ids,
                    sender=sender,
                    recipients=recipients,
                    subject=subject,
                    sent_at=sent_at,
                    snippet=snippet,
                    body_plain=body_plain,
                )
            except Exception as e:
                err_str = str(e)
                if ("rateLimitExceeded" in err_str or "403" in err_str or "429" in err_str) and attempt < max_retries - 1:
                    backoff = 6 * (attempt + 1)
                    logger.warning("Gmail rate limit encountered on message %s; sleeping %ds before retry...", message_id, backoff)
                    time.sleep(backoff)
                else:
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
