"""
WhatsApp Event Tool
===================

Handles WhatsApp event creation for in-chat calendar events.
Uses the WhatsApp Bridge API to create events that appear in WhatsApp conversations.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class WhatsAppEventTool:
    """
    WhatsApp Event integration tool for Bijou.

    Creates calendar events directly in WhatsApp conversations.
    Requires WhatsApp Bridge URL and API access.
    """

    def __init__(self, bridge_url: Optional[str] = None):
        """
        Initialize WhatsApp Event tool.

        Args:
            bridge_url: URL of the WhatsApp Bridge API
        """
        self.bridge_url = bridge_url or os.getenv("BRIDGE_URL", "http://localhost:3000")
        self._initialized = True

    def create_event(
        self,
        phone_number: str,
        name: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        call_link: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a WhatsApp event in a conversation.

        Args:
            phone_number: WhatsApp phone number to send event to (e.g., "1234567890")
            name: Event name/title
            start_time: Event start time (datetime object)
            end_time: Event end time (datetime object, optional)
            location: Event location (optional)
            description: Event description (optional)
            call_link: Video call link for the event (optional)

        Returns:
            Dictionary with event creation status and details

        Example:
            >>> tool = WhatsAppEventTool()
            >>> result = tool.create_event(
            ...     phone_number="1234567890",
            ...     name="Team Meeting",
            ...     start_time=datetime(2024, 3, 15, 14, 0),
            ...     end_time=datetime(2024, 3, 15, 15, 0),
            ...     location="Conference Room A"
            ... )
        """
        try:
            # Format phone number (remove any non-digits)
            phone = "".join(filter(str.isdigit, phone_number))

            # If no end time, default to 1 hour after start
            if end_time is None:
                from datetime import timedelta

                end_time = start_time + timedelta(hours=1)

            # Build event payload
            event_data = {
                "name": name,
                "startTime": int(start_time.timestamp()),
                "endTime": int(end_time.timestamp()),
            }

            if location:
                event_data["location"] = location

            if description:
                event_data["description"] = description

            if call_link:
                event_data["callLink"] = call_link

            # Send event via bridge API
            url = f"{self.bridge_url}/api/send-event"
            payload = {"phone": phone, "event": event_data}

            response = httpx.post(url, json=payload, timeout=30.0)
            response.raise_for_status()

            result = response.json()

            logger.info(f"WhatsApp event created successfully for {phone}")
            return {
                "success": True,
                "phone": phone,
                "event_name": name,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "message_id": result.get("messageId"),
            }

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error creating WhatsApp event: {e.response.status_code}"
            )
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
            }
        except httpx.RequestError as e:
            logger.error(f"Request error creating WhatsApp event: {e}")
            return {"success": False, "error": f"Request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Failed to create WhatsApp event: {e}")
            return {"success": False, "error": str(e)}

    def send_event_invite(
        self,
        phone_number: str,
        event_name: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        google_calendar_link: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an event invitation message (fallback if native events aren't supported).

        Args:
            phone_number: WhatsApp phone number
            event_name: Event name
            start_time: Event start time
            end_time: Event end time (optional)
            google_calendar_link: Link to Google Calendar event (optional)

        Returns:
            Dictionary with send status
        """
        try:
            # Format phone number
            phone = "".join(filter(str.isdigit, phone_number))

            # Format end time
            if end_time is None:
                from datetime import timedelta

                end_time = start_time + timedelta(hours=1)

            # Build invitation message
            message = f"📅 *Event Invitation*\n\n"
            message += f"*{event_name}*\n\n"
            message += f"🕒 Start: {start_time.strftime('%B %d, %Y at %I:%M %p')}\n"
            message += f"🕒 End: {end_time.strftime('%B %d, %Y at %I:%M %p')}\n"

            if google_calendar_link:
                message += f"\n🔗 Add to Calendar: {google_calendar_link}"

            # Send via bridge API
            url = f"{self.bridge_url}/api/send-message"
            payload = {"phone": phone, "message": message}

            response = httpx.post(url, json=payload, timeout=30.0)
            response.raise_for_status()

            result = response.json()

            logger.info(f"Event invitation sent to {phone}")
            return {
                "success": True,
                "phone": phone,
                "event_name": event_name,
                "message_id": result.get("messageId"),
            }

        except Exception as e:
            logger.error(f"Failed to send event invitation: {e}")
            return {"success": False, "error": str(e)}

    def create_recurring_event_message(
        self,
        phone_number: str,
        event_name: str,
        recurrence: str,
        time_slot: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a message about a recurring event.

        Args:
            phone_number: WhatsApp phone number
            event_name: Event name
            recurrence: Recurrence pattern (e.g., "Every Monday", "Weekly", "Monthly")
            time_slot: Time description (e.g., "2:00 PM - 3:00 PM")
            description: Event description (optional)

        Returns:
            Dictionary with send status
        """
        try:
            # Format phone number
            phone = "".join(filter(str.isdigit, phone_number))

            # Build message
            message = f"🔁 *Recurring Event*\n\n"
            message += f"*{event_name}*\n\n"
            message += f"📆 {recurrence}\n"
            message += f"🕒 {time_slot}\n"

            if description:
                message += f"\n📝 {description}"

            # Send via bridge API
            url = f"{self.bridge_url}/api/send-message"
            payload = {"phone": phone, "message": message}

            response = httpx.post(url, json=payload, timeout=30.0)
            response.raise_for_status()

            result = response.json()

            logger.info(f"Recurring event message sent to {phone}")
            return {
                "success": True,
                "phone": phone,
                "event_name": event_name,
                "message_id": result.get("messageId"),
            }

        except Exception as e:
            logger.error(f"Failed to send recurring event message: {e}")
            return {"success": False, "error": str(e)}
