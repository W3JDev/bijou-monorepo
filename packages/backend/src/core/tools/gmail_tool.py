"""
Gmail Integration Tool
======================

Handles Gmail operations: send, read, search emails.
Uses Gmail API with OAuth2 authentication.
"""

import base64
import logging
import os
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GmailTool:
    """
    Gmail integration tool for Bijou.

    Provides methods to send, read, and search emails using Gmail API.
    Requires Google Cloud credentials and Gmail API enabled.
    """

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Gmail tool.

        Args:
            credentials_path: Path to Google OAuth2 credentials JSON file
        """
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH")
        self.service = None
        self._initialized = False

    def initialize(self) -> bool:
        """
        Initialize Gmail API connection.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Import Gmail API libraries (lazy import)
            import pickle

            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
            creds = None

            # Token file stores user's access and refresh tokens
            token_path = os.getenv("GMAIL_TOKEN_PATH", "token.pickle")

            # Load credentials from token file if it exists
            if os.path.exists(token_path):
                with open(token_path, "rb") as token:
                    creds = pickle.load(token)

            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not self.credentials_path or not os.path.exists(
                        self.credentials_path
                    ):
                        logger.error("Gmail credentials file not found")
                        return False

                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save credentials for next run
                with open(token_path, "wb") as token:
                    pickle.dump(creds, token)

            # Build Gmail API service
            self.service = build("gmail", "v1", credentials=creds)
            self._initialized = True
            logger.info("Gmail API initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Gmail API: {e}")
            return False

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        html: bool = False,
    ) -> Dict[str, Any]:
        """
        Send an email via Gmail.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            cc: CC recipients (comma-separated)
            bcc: BCC recipients (comma-separated)
            attachments: List of file paths to attach
            html: Whether body is HTML (default: plain text)

        Returns:
            Dictionary with status and message ID or error
        """
        if not self._initialized and not self.initialize():
            return {"success": False, "error": "Gmail API not initialized"}

        try:
            # Create message
            message = (
                MIMEMultipart()
                if attachments
                else MIMEText(body, "html" if html else "plain")
            )

            if attachments:
                message.attach(MIMEText(body, "html" if html else "plain"))
            else:
                message = MIMEText(body, "html" if html else "plain")
                message["to"] = to
                message["subject"] = subject
                if cc:
                    message["cc"] = cc
                if bcc:
                    message["bcc"] = bcc

            # Add headers for multipart
            if attachments:
                message["to"] = to
                message["subject"] = subject
                if cc:
                    message["cc"] = cc
                if bcc:
                    message["bcc"] = bcc

                # Attach files
                for filepath in attachments:
                    if not os.path.exists(filepath):
                        logger.warning(f"Attachment not found: {filepath}")
                        continue

                    with open(filepath, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())

                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(filepath)}",
                    )
                    message.attach(part)

            # Encode and send
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            result = (
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )

            logger.info(f"Email sent successfully. Message ID: {result['id']}")
            return {
                "success": True,
                "message_id": result["id"],
                "to": to,
                "subject": subject,
            }

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {"success": False, "error": str(e)}

    def read_emails(
        self,
        max_results: int = 10,
        query: Optional[str] = None,
        unread_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Read emails from Gmail inbox.

        Args:
            max_results: Maximum number of emails to retrieve
            query: Gmail search query (e.g., 'from:someone@example.com')
            unread_only: Only fetch unread emails

        Returns:
            Dictionary with list of emails or error
        """
        if not self._initialized and not self.initialize():
            return {"success": False, "error": "Gmail API not initialized"}

        try:
            # Build query
            search_query = query or ""
            if unread_only:
                search_query = f"{search_query} is:unread".strip()

            # Get message list
            results = (
                self.service.users()
                .messages()
                .list(userId="me", maxResults=max_results, q=search_query)
                .execute()
            )

            messages = results.get("messages", [])

            if not messages:
                return {"success": True, "emails": [], "count": 0}

            # Fetch full message details
            emails = []
            for msg in messages:
                try:
                    message = (
                        self.service.users()
                        .messages()
                        .get(userId="me", id=msg["id"], format="full")
                        .execute()
                    )

                    # Extract headers
                    headers = message["payload"]["headers"]
                    subject = next(
                        (h["value"] for h in headers if h["name"] == "Subject"),
                        "No Subject",
                    )
                    from_email = next(
                        (h["value"] for h in headers if h["name"] == "From"), "Unknown"
                    )
                    date = next(
                        (h["value"] for h in headers if h["name"] == "Date"), ""
                    )

                    # Extract body
                    body = self._get_message_body(message["payload"])

                    emails.append(
                        {
                            "id": msg["id"],
                            "subject": subject,
                            "from": from_email,
                            "date": date,
                            "snippet": message.get("snippet", ""),
                            "body": body[:500]
                            if body
                            else message.get("snippet", ""),  # Truncate body
                            "unread": "UNREAD" in message.get("labelIds", []),
                        }
                    )

                except Exception as e:
                    logger.error(f"Error fetching message {msg['id']}: {e}")
                    continue

            return {"success": True, "emails": emails, "count": len(emails)}

        except Exception as e:
            logger.error(f"Failed to read emails: {e}")
            return {"success": False, "error": str(e)}

    def _get_message_body(self, payload: Dict) -> str:
        """
        Extract message body from Gmail API payload.

        Args:
            payload: Message payload from Gmail API

        Returns:
            Decoded message body
        """
        try:
            if "parts" in payload:
                # Multipart message
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain":
                        if "data" in part["body"]:
                            return base64.urlsafe_b64decode(
                                part["body"]["data"]
                            ).decode("utf-8")
                    elif part["mimeType"] == "text/html":
                        if "data" in part["body"]:
                            return base64.urlsafe_b64decode(
                                part["body"]["data"]
                            ).decode("utf-8")
                    elif "parts" in part:
                        # Nested parts
                        return self._get_message_body(part)
            else:
                # Simple message
                if "data" in payload.get("body", {}):
                    return base64.urlsafe_b64decode(payload["body"]["data"]).decode(
                        "utf-8"
                    )

            return ""

        except Exception as e:
            logger.error(f"Error extracting message body: {e}")
            return ""

    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark an email as read.

        Args:
            message_id: Gmail message ID

        Returns:
            Dictionary with success status
        """
        if not self._initialized and not self.initialize():
            return {"success": False, "error": "Gmail API not initialized"}

        try:
            self.service.users().messages().modify(
                userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()

            return {"success": True, "message_id": message_id}

        except Exception as e:
            logger.error(f"Failed to mark email as read: {e}")
            return {"success": False, "error": str(e)}

    def search_emails(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Search emails using Gmail query syntax.

        Args:
            query: Gmail search query
                   Examples:
                   - "from:someone@example.com"
                   - "subject:invoice after:2024/01/01"
                   - "has:attachment newer_than:7d"
            max_results: Maximum number of results

        Returns:
            Dictionary with search results
        """
        return self.read_emails(max_results=max_results, query=query)
