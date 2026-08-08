"""
W3J Bijou AI - Google Sheets Integration
========================================

Integrates with Google Sheets for:
- Knowledge base management (updatable without code)
- FAQ database for RAG
- Conversation logs for analysis
- Performance metrics tracking
- Team collaboration

Features:
- OAuth2 authentication
- Real-time sync
- Automatic backup
- Change tracking

Author: W3J Bijou AI
Version: 2.1.0
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsRAG:
    """
    Google Sheets integration for knowledge base and RAG.
    """

    # Scopes for Google Sheets API
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(
        self,
        credentials_file: str = None,
        spreadsheet_id: Optional[str] = None,
    ):
        """
        Initialize Google Sheets RAG system.

        Args:
            credentials_file: Path to OAuth2 credentials file
            spreadsheet_id: ID of Google Sheets document
        """
        self.credentials_file = credentials_file or os.getenv(
            "GOOGLE_CREDENTIALS_PATH",
            "credentials/client_secret_698028267158-70rv95bqskigdhlgd84df7igaitjpbbu.apps.googleusercontent.com.json"
        )
        self.spreadsheet_id = spreadsheet_id or os.getenv("SHEETS_SPREADSHEET_ID")
        self.service = None
        self.knowledge_base = {}
        self.faq_cache = {}
        self.authenticate()

    def authenticate(self) -> None:
        """
        Authenticate with Google Sheets API.
        """
        try:
            creds = None

            # Load existing credentials if available
            if os.path.exists("token.json"):
                creds = Credentials.from_authorized_user_file("token.json", self.SCOPES)

            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save credentials for future use
                with open("token.json", "w") as token:
                    token.write(creds.to_json())

            self.service = build("sheets", "v4", credentials=creds)
            print("[OK] Google Sheets authenticated successfully")

        except Exception as e:
            print(f"[ERROR] Google Sheets authentication failed: {e}")
            self.service = None

    def load_knowledge_base(self) -> Dict[str, List[str]]:
        """
        Load knowledge base from 'FAQ' sheet.

        Returns:
            Dictionary of FAQs by category
        """
        if not self.service or not self.spreadsheet_id:
            return {}

        try:
            # Read FAQ sheet
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range="FAQ!A:D")
                .execute()
            )

            values = result.get("values", [])

            knowledge_base = {}
            headers = (
                values[0] if values else ["Category", "Question", "Answer", "Tags"]
            )

            for row in values[1:]:  # Skip header
                if len(row) >= 3:
                    category = row[0]
                    question = row[1]
                    answer = row[2]
                    tags = row[3] if len(row) > 3 else ""

                    if category not in knowledge_base:
                        knowledge_base[category] = []

                    knowledge_base[category].append(
                        {
                            "question": question,
                            "answer": answer,
                            "tags": tags.split(",") if tags else [],
                        }
                    )

            self.knowledge_base = knowledge_base
            print(f"[OK] Loaded {sum(len(v) for v in knowledge_base.values())} FAQs")
            return knowledge_base

        except HttpError as error:
            print(f"[ERROR] Google Sheets API error: {error}")
            return {}

    def search_knowledge_base(self, query: str, limit: int = 3) -> List[Dict[str, str]]:
        """
        Search knowledge base for relevant FAQs.

        Args:
            query: Search query
            limit: Max results to return

        Returns:
            List of relevant FAQs
        """
        if not self.knowledge_base:
            self.load_knowledge_base()

        results = []
        query_lower = query.lower()

        # Search through all categories
        for category, faqs in self.knowledge_base.items():
            for faq in faqs:
                question_lower = faq["question"].lower()
                answer_lower = faq["answer"].lower()

                # Simple keyword matching
                if (
                    any(word in question_lower for word in query_lower.split())
                    or any(word in answer_lower for word in query_lower.split())
                    or any(
                        tag in query_lower
                        for tag in faq["tags"]
                        if tag.lower() in query_lower
                    )
                ):
                    results.append(
                        {
                            "category": category,
                            "question": faq["question"],
                            "answer": faq["answer"],
                            "relevance": self._calculate_relevance(query, faq),
                        }
                    )

        # Sort by relevance and limit
        results = sorted(results, key=lambda x: x["relevance"], reverse=True)
        return results[:limit]

    def log_conversation(
        self,
        customer_jid: str,
        user_message: str,
        bot_response: str,
        emotion: str,
        csat_score: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log conversation to Google Sheets for analysis.

        Args:
            customer_jid: Customer's WhatsApp JID
            user_message: User's message
            bot_response: Bot's response
            emotion: Detected emotion
            csat_score: Estimated CSAT score
            metadata: Additional metadata

        Returns:
            True if logged successfully
        """
        if not self.service or not self.spreadsheet_id:
            return False

        try:
            timestamp = datetime.now().isoformat()
            values = [
                [
                    timestamp,
                    customer_jid,
                    user_message,
                    bot_response,
                    emotion,
                    csat_score,
                    json.dumps(metadata or {}),
                ]
            ]

            # Append to Conversations sheet
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range="Conversations!A:G",
                valueInputOption="USER_ENTERED",
                body={"values": values},
            ).execute()

            return True

        except HttpError as error:
            print(f"[ERROR] Failed to log conversation: {error}")
            return False

    def log_metrics(self, metrics: Dict[str, Any]) -> bool:
        """
        Log performance metrics to Google Sheets.

        Args:
            metrics: Metrics dictionary

        Returns:
            True if logged successfully
        """
        if not self.service or not self.spreadsheet_id:
            return False

        try:
            timestamp = datetime.now().isoformat()
            values = [
                [
                    timestamp,
                    metrics.get("total_messages", 0),
                    metrics.get("average_csat", 0),
                    metrics.get("average_response_time", 0),
                    json.dumps(metrics),
                ]
            ]

            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range="Metrics!A:E",
                valueInputOption="USER_ENTERED",
                body={"values": values},
            ).execute()

            return True

        except HttpError as error:
            print(f"[ERROR] Failed to log metrics: {error}")
            return False

    def update_knowledge_base_item(
        self, category: str, question: str, answer: str, tags: str = ""
    ) -> bool:
        """
        Add or update a knowledge base item.

        Args:
            category: FAQ category
            question: Question text
            answer: Answer text
            tags: Comma-separated tags

        Returns:
            True if updated successfully
        """
        if not self.service or not self.spreadsheet_id:
            return False

        try:
            values = [[category, question, answer, tags]]

            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range="FAQ!A:D",
                valueInputOption="USER_ENTERED",
                body={"values": values},
            ).execute()

            # Refresh cache
            self.load_knowledge_base()
            return True

        except HttpError as error:
            print(f"[ERROR] Failed to update knowledge base: {error}")
            return False

    def _calculate_relevance(self, query: str, faq: Dict[str, str]) -> float:
        """
        Calculate relevance score for FAQ match.

        Args:
            query: Search query
            faq: FAQ item

        Returns:
            Relevance score (0-1)
        """
        query_lower = query.lower()
        question_lower = faq["question"].lower()

        # Exact match
        if query_lower == question_lower:
            return 1.0

        # Keyword overlap
        query_words = set(query_lower.split())
        question_words = set(question_lower.split())

        if not query_words or not question_words:
            return 0.0

        overlap = len(query_words & question_words)
        total = len(query_words | question_words)

        return overlap / total if total > 0 else 0.0

    def get_sheet_data(self, range_name: str) -> List[List[str]]:
        """
        Get raw data from any sheet range.

        Args:
            range_name: Sheet range (e.g., "Sheet1!A1:Z")

        Returns:
            List of rows
        """
        if not self.service or not self.spreadsheet_id:
            return []

        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=range_name)
                .execute()
            )

            return result.get("values", [])

        except HttpError as error:
            print(f"[ERROR] Failed to get sheet data: {error}")
            return []


# Example setup for first time use
def create_google_sheets_template(credentials_file: str) -> str:
    """
    Create a new Google Sheets document with template structure.

    Args:
        credentials_file: Path to credentials file

    Returns:
        Spreadsheet ID
    """
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_file, GoogleSheetsRAG.SCOPES
        )
        creds = flow.run_local_server(port=0)
        service = build("sheets", "v4", credentials=creds)

        # Create new spreadsheet
        spreadsheet = {
            "properties": {
                "title": "W3J Bijou AI - Knowledge Base & Analytics",
                "locale": "en_US",
            },
            "sheets": [
                {"properties": {"title": "FAQ", "sheetId": 0}},
                {"properties": {"title": "Conversations", "sheetId": 1}},
                {"properties": {"title": "Metrics", "sheetId": 2}},
            ],
        }

        result = service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = result.get("spreadsheetId")

        print(f"[OK] Created Google Sheets: {spreadsheet_id}")
        print(
            f"[INFO] Share this with your team: https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        )

        return spreadsheet_id

    except Exception as e:
        print(f"[ERROR] Failed to create Google Sheets: {e}")
        return ""
