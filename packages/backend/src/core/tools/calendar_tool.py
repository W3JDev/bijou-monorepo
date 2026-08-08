"""
Cal.com Integration Tool
========================

Handles booking operations via Cal.com REST API v1:
- List available event types
- Check availability / free-busy
- Create bookings
- List existing bookings
- Cancel a booking

Auth: CAL_API_KEY env var (appended as ?apiKey=... on every request)
Username: CAL_USERNAME env var (e.g. "getbijou")

No OAuth, no pickle files, no Google dependencies.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

CAL_API_BASE = "https://api.cal.com/v1"


class CalendarTool:
    """
    Cal.com booking integration tool for Bijou.

    Provides methods to list event types, check availability,
    create/list/cancel bookings — all via Cal.com REST API v1.

    Required env vars:
        CAL_API_KEY   — Cal.com API key (cal_live_...)
        CAL_USERNAME  — Cal.com username slug (e.g. "getbijou")
    """

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize CalendarTool.

        Args:
            credentials_path: Ignored (kept for signature compatibility).
                              Cal.com uses CAL_API_KEY env var instead.
        """
        self.api_key    = os.getenv("CAL_API_KEY", "")
        self.username   = os.getenv("CAL_USERNAME", "")
        self.oauth_token: Optional[str] = None  # set when OAuth-connected tenant
        self._initialized = bool(self.api_key)

        if self._initialized:
            logger.info(f"✅ Cal.com calendar tool ready (user={self.username})")
        else:
            logger.warning("⚠️ CAL_API_KEY not set — Cal.com calendar tool disabled")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Auth helpers — supports both API-key (v1) and OAuth Bearer (v2)
    # ------------------------------------------------------------------

    @property
    def _use_oauth(self) -> bool:
        """True when this instance has been configured with an OAuth token."""
        return bool(self.oauth_token)

    def _api_base(self) -> str:
        return "https://api.cal.com/v2" if self._use_oauth else CAL_API_BASE

    def _headers(self) -> Dict[str, str]:
        """Return auth headers appropriate for the configured auth mode."""
        if self._use_oauth:
            return {
                "Authorization": f"Bearer {self.oauth_token}",
                "cal-api-version": "2024-08-13",
                "Content-Type": "application/json",
            }
        return {}

    def _params(self, extra: Optional[Dict] = None) -> Dict:
        """Build query-param dict.  API-key mode appends apiKey; OAuth mode skips it."""
        if self._use_oauth:
            return extra or {}
        p: Dict[str, Any] = {"apiKey": self.api_key}
        if extra:
            p.update(extra)
        return p

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        """Synchronous GET against Cal.com API (v1 or v2 depending on auth mode)."""
        url = f"{self._api_base()}{path}"
        try:
            resp = httpx.get(url, params=self._params(params), headers=self._headers(), timeout=15)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"❌ Cal.com GET {path} → HTTP {e.response.status_code}: {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"❌ Cal.com GET {path} failed: {e}")
            raise

    def _post(self, path: str, body: Dict) -> Dict:
        """Synchronous POST against Cal.com API (v1 or v2 depending on auth mode)."""
        url = f"{self._api_base()}{path}"
        try:
            resp = httpx.post(url, params=self._params(), headers=self._headers(), json=body, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"❌ Cal.com POST {path} → HTTP {e.response.status_code}: {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"❌ Cal.com POST {path} failed: {e}")
            raise

    def _delete(self, path: str) -> Dict:
        """Synchronous DELETE against Cal.com API (v1 or v2 depending on auth mode)."""
        url = f"{self._api_base()}{path}"
        try:
            resp = httpx.delete(url, params=self._params(), headers=self._headers(), timeout=15)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"❌ Cal.com DELETE {path} → HTTP {e.response.status_code}: {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"❌ Cal.com DELETE {path} failed: {e}")
            raise

    def _check_ready(self) -> Optional[Dict]:
        """Return error dict if not initialised, else None."""
        if not self._initialized:
            return {"success": False, "error": "Cal.com API key not configured"}
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        """
        Re-check credentials (kept for backward compatibility).

        Returns:
            True if CAL_API_KEY is set, False otherwise
        """
        self.api_key = os.getenv("CAL_API_KEY", "")
        self.username = os.getenv("CAL_USERNAME", "")
        self._initialized = bool(self.api_key)
        return self._initialized

    def get_event_types(self) -> Dict[str, Any]:
        """
        List all event types configured on the Cal.com account.

        Returns:
            Dict with 'event_types' list or 'error'
        """
        err = self._check_ready()
        if err:
            return err
        try:
            data = self._get("/event-types")
            types = data.get("event_types", [])
            formatted = [
                {
                    "id": et.get("id"),
                    "slug": et.get("slug"),
                    "title": et.get("title"),
                    "description": et.get("description", ""),
                    "length_minutes": et.get("length"),
                }
                for et in types
            ]
            return {"success": True, "event_types": formatted, "count": len(formatted)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_availability(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        event_type_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get available slots for the Cal.com user.

        Args:
            date_from: ISO date string, e.g. "2026-02-25" (defaults to today)
            date_to:   ISO date string, e.g. "2026-03-07" (defaults to +7 days)
            event_type_id: Optional event type to filter slots

        Returns:
            Dict with 'slots' and 'busy' or 'error'
        """
        err = self._check_ready()
        if err:
            return err
        try:
            today = datetime.utcnow()
            params: Dict[str, Any] = {
                "username": self.username,
                "dateFrom": date_from or today.strftime("%Y-%m-%d"),
                "dateTo": date_to or (today + timedelta(days=7)).strftime("%Y-%m-%d"),
            }
            if event_type_id:
                params["eventTypeId"] = event_type_id

            data = self._get("/availability", params)
            return {
                "success": True,
                "slots": data.get("slots", {}),
                "busy": data.get("busy", []),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_event(
        self,
        title: str,
        start_time: str,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        event_type_id: Optional[int] = None,
        timezone: str = "UTC",
    ) -> Dict[str, Any]:
        """
        Create a Cal.com booking.

        Args:
            title:         Booking title / reason
            start_time:    ISO 8601 datetime string, e.g. "2026-02-25T10:00:00Z"
            end_time:      ISO 8601 datetime string (optional)
            description:   Optional notes / context
            attendees:     List of attendee email strings
            event_type_id: Cal.com event type ID (uses first available if omitted)
            timezone:      Timezone string, e.g. "Asia/Kuala_Lumpur"

        Returns:
            Dict with booking details or 'error'
        """
        err = self._check_ready()
        if err:
            return err
        try:
            # Resolve event type ID if not supplied
            if not event_type_id:
                et_resp = self.get_event_types()
                if not et_resp.get("success") or not et_resp.get("event_types"):
                    return {
                        "success": False,
                        "error": "No event types found on Cal.com account",
                    }
                event_type_id = et_resp["event_types"][0]["id"]

            # Build attendees — Cal.com requires at least one
            guests = attendees or []
            primary_email = guests[0] if guests else "customer@example.com"
            primary_name = (
                primary_email.split("@")[0].replace(".", " ").replace("_", " ").title()
            )

            body: Dict[str, Any] = {
                "eventTypeId": event_type_id,
                "start": start_time,
                "responses": {
                    "name": primary_name,
                    "email": primary_email,
                    "notes": description or title,
                    "guests": guests[1:] if len(guests) > 1 else [],
                },
                "timeZone": timezone,
                "language": "en",
                "metadata": {"source": "bijou-ai", "title": title},
            }

            result = self._post("/bookings", body)
            booking_id = result.get("id") or result.get("uid")
            logger.info(f"✅ Cal.com booking created: id={booking_id}")

            return {
                "success": True,
                "booking_id": booking_id,
                "event_link": (result.get("attendees") or [{}])[0].get("url", ""),
                "title": title,
                "start": start_time,
                "end": end_time or result.get("endTime", ""),
                "status": result.get("status", "ACCEPTED"),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_events(
        self,
        max_results: int = 10,
        time_min: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List upcoming Cal.com bookings.

        Args:
            max_results: Maximum number of bookings to return
            time_min:    Lower bound ISO date or "today" (default: today)

        Returns:
            Dict with 'events' list or 'error'
        """
        err = self._check_ready()
        if err:
            return err
        try:
            if not time_min or time_min == "today":
                time_min = datetime.utcnow().strftime("%Y-%m-%dT00:00:00Z")

            data = self._get(
                "/bookings",
                {"take": max_results, "afterStart": time_min},
            )
            bookings = data.get("bookings", [])

            formatted = [
                {
                    "id": b.get("id") or b.get("uid"),
                    "title": b.get("title"),
                    "start": b.get("startTime"),
                    "end": b.get("endTime"),
                    "status": b.get("status"),
                    "attendees": [a.get("email") for a in b.get("attendees", [])],
                    "description": b.get("description", ""),
                }
                for b in bookings
            ]

            return {"success": True, "events": formatted, "count": len(formatted)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_events(
        self,
        max_results: int = 10,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        """
        Alias for list_events() — maintains backward compatibility.

        Args:
            max_results: Maximum number of events
            time_min:    Lower bound datetime (optional)
            time_max:    Upper bound datetime (ignored — Cal.com paginates differently)
            calendar_id: Ignored (Cal.com doesn't use calendar IDs)
        """
        t_min = time_min.strftime("%Y-%m-%dT%H:%M:%SZ") if time_min else None
        return self.list_events(max_results=max_results, time_min=t_min)

    def cancel_booking(
        self, booking_id: str, reason: str = "Cancelled via Bijou AI"
    ) -> Dict[str, Any]:
        """
        Cancel a Cal.com booking.

        Args:
            booking_id: Cal.com booking ID or UID
            reason:     Cancellation reason shown to attendees

        Returns:
            Dict with success status or 'error'
        """
        err = self._check_ready()
        if err:
            return err
        try:
            result = self._delete(f"/bookings/{booking_id}/cancel")
            logger.info(f"✅ Cal.com booking cancelled: {booking_id}")
            return {"success": True, "booking_id": booking_id, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_event(
        self, event_id: str, calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """Alias for cancel_booking() — backward compatibility."""
        return self.cancel_booking(event_id)
