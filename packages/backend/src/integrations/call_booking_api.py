"""
Bijou AI - Call Booking API Router
==================================

REST API endpoints for call booking functionality including:
- Booking management
- Availability configuration
- Reminder system
- Schedule management

Author: W3J Bijou AI
Version: 1.0.0
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from supabase import Client, create_client

from src.core.bridge_client import BridgeClient

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/call-booking", tags=["call-booking"])

# Import verify_session from dashboard API
from src.core.dashboard_api_simple import verify_session


def get_supabase() -> Client:
    """Get Supabase client from environment"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=500, detail="Missing Supabase configuration")

    return create_client(supabase_url, supabase_key)


# ── Proactive messaging hook ─────────────────────────────────────────────────
# Set at startup by bijou.py so booking confirmations can trigger reminders.
_proactive_system = None


def set_proactive_system(system) -> None:
    """Inject the running ProactiveMessagingSystem into this module."""
    global _proactive_system
    _proactive_system = system
    logger.info("✅ call_booking_api: proactive_system wired — reminders enabled")
# ==================== PYDANTIC MODELS ====================

class CallBookingCreate(BaseModel):
    customer_jid: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    scheduled_time: str  # ISO format datetime
    duration_minutes: Optional[int] = 30
    call_type: Optional[str] = "consultation"
    notes: Optional[str] = None


class CallBookingResponse(BaseModel):
    id: str
    tenant_id: str
    customer_jid: str
    customer_name: Optional[str]
    customer_phone: Optional[str]
    scheduled_time: str
    duration_minutes: int
    call_type: str
    status: str
    notes: Optional[str]
    created_at: str


class AvailabilitySlot(BaseModel):
    day_of_week: int  # 0 = Monday, 6 = Sunday
    start_time: str  # HH:MM format
    end_time: str    # HH:MM format
    timezone: Optional[str] = "Asia/Kuala_Lumpur"


class CallSettings(BaseModel):
    tenant_id: str
    timezone: Optional[str] = "Asia/Kuala_Lumpur"
    buffer_minutes: Optional[int] = 15
    max_calls_per_day: Optional[int] = 8
    max_calls_per_hour: Optional[int] = 2
    advance_booking_days: Optional[int] = 30
    allow_same_day_booking: Optional[bool] = True


class HolidayException(BaseModel):
    date: str  # YYYY-MM-DD format
    title: Optional[str] = None
    description: Optional[str] = None
    is_recurring: Optional[bool] = False


class AvailabilityOverride(BaseModel):
    date: str  # YYYY-MM-DD format
    start_time: Optional[str] = None  # HH:MM format, None means closed all day
    end_time: Optional[str] = None    # HH:MM format
    is_available: bool = False
    reason: Optional[str] = None


class AvailableSlotResponse(BaseModel):
    date: str  # YYYY-MM-DD format
    start_time: str  # HH:MM format
    end_time: str    # HH:MM format
    timezone: str


class AvailabilitySchedule(BaseModel):
    weekly_schedule: List[AvailabilitySlot]
    holidays: List[HolidayException]
    overrides: List[AvailabilityOverride]
    settings: CallSettings

# ==================== HELPER FUNCTIONS ====================

async def _get_call_settings(tenant_id: str) -> dict:
    """Get call settings for a tenant with defaults"""
    try:
        supabase = get_supabase()
        result = supabase.table("call_settings").select("*").eq("tenant_id", tenant_id).execute()
        if result.data:
            return result.data[0]

        # Return defaults if no settings found
        return {
            "timezone": "Asia/Kuala_Lumpur",
            "buffer_minutes": 15,
            "max_calls_per_day": 8,
            "max_calls_per_hour": 2,
            "advance_booking_days": 30,
            "allow_same_day_booking": True
        }

    except Exception as e:
        logger.error(f"❌ Failed to fetch call settings for tenant {tenant_id}: {e}")
        # Return defaults on error
        return {
            "timezone": "Asia/Kuala_Lumpur",
            "buffer_minutes": 15,
            "max_calls_per_day": 8,
            "max_calls_per_hour": 2,
            "advance_booking_days": 30,
            "allow_same_day_booking": True
        }


async def _get_available_slots_for_date(
    tenant_id: str,
    date_obj,
    duration_minutes: int,
    buffer_minutes: int,
    timezone_str: str
) -> List[dict]:
    """Generate available time slots for a specific date"""

    try:
        import calendar

        # Get day of week (0=Monday, 6=Sunday)
        weekday = date_obj.weekday()

        # Check if it's a holiday
        is_holiday = await _is_holiday(tenant_id, date_obj.strftime("%Y-%m-%d"))
        if is_holiday:
            return []

        # Get business hours for this day
        supabase = get_supabase()
        result = supabase.table("call_availability").select("*").eq(
            "tenant_id", tenant_id
        ).eq("day_of_week", weekday).eq("is_active", True).execute()
        business_hours = result.data or []

        if not business_hours:
            return []  # No business hours set for this day

        # Get existing bookings for this date
        existing_bookings = await _get_bookings_for_date(tenant_id, date_obj.strftime("%Y-%m-%d"))

        # Generate available slots
        available_slots = []

        for business_hour in business_hours:
            start_time = business_hour["start_time"]  # "09:00"
            end_time = business_hour["end_time"]      # "17:00"

            # Convert to datetime objects (handle both HH:MM and HH:MM:SS formats)
            start_time_str = start_time[:5] if len(start_time) > 5 else start_time  # "09:00:00" -> "09:00"
            end_time_str = end_time[:5] if len(end_time) > 5 else end_time      # "17:00:00" -> "17:00"

            start_dt = datetime.strptime(f"{date_obj.strftime('%Y-%m-%d')} {start_time_str}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date_obj.strftime('%Y-%m-%d')} {end_time_str}", "%Y-%m-%d %H:%M")

            # Generate slots
            current_time = start_dt
            while current_time + timedelta(minutes=duration_minutes) <= end_dt:
                slot_end = current_time + timedelta(minutes=duration_minutes)

                # Check if this slot conflicts with existing bookings
                is_available = True
                for booking in existing_bookings:
                    booking_start = datetime.fromisoformat(booking["scheduled_time"].replace('Z', '+00:00')).replace(tzinfo=None)
                    booking_end = booking_start + timedelta(minutes=booking.get("duration_minutes", 30))

                    # Add buffer time
                    booking_start_with_buffer = booking_start - timedelta(minutes=buffer_minutes)
                    booking_end_with_buffer = booking_end + timedelta(minutes=buffer_minutes)

                    # Check for overlap
                    if (current_time < booking_end_with_buffer and slot_end > booking_start_with_buffer):
                        is_available = False
                        break

                if is_available:
                    available_slots.append({
                        "date": date_obj.strftime("%Y-%m-%d"),
                        "start_time": current_time.strftime("%H:%M"),
                        "end_time": slot_end.strftime("%H:%M"),
                        "timezone": timezone_str
                    })

                # Move to next slot (with buffer)
                current_time += timedelta(minutes=duration_minutes + buffer_minutes)

        return available_slots

    except Exception as e:
        logger.error(f"❌ Error generating slots for {date_obj}: {e}")
        return []


async def _is_holiday(tenant_id: str, date_str: str) -> bool:
    """Check if a date is a holiday"""
    try:
        supabase = get_supabase()
        result = supabase.table("holiday_exceptions").select("*").eq(
            "tenant_id", tenant_id
        ).eq("date", date_str).execute()
        return len(result.data or []) > 0
    except Exception as e:
        logger.error(f"❌ Failed to check holiday status for tenant {tenant_id} on {date_str}: {e}")
        return False


async def _get_bookings_for_date(tenant_id: str, date_str: str) -> List[dict]:
    """Get existing bookings for a specific date"""
    try:
        supabase = get_supabase()
        result = supabase.table("call_bookings").select("*").eq(
            "tenant_id", tenant_id
        ).gte("scheduled_time", f"{date_str}T00:00:00Z").lt(
            "scheduled_time", f"{date_str}T23:59:59Z"
        ).in_("status", ["scheduled", "in_progress"]).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"❌ Error getting bookings for {date_str}: {e}")
        return []


async def _send_booking_confirmation_whatsapp(
    customer_jid: str,
    customer_name: Optional[str],
    scheduled_time: str,
    duration_minutes: int,
    tenant_id: str
) -> Dict[str, Any]:
    """
    Send WhatsApp booking confirmation to customer.

    Args:
        customer_jid: Customer WhatsApp JID (phone@s.whatsapp.net)
        customer_name: Customer's name (optional)
        scheduled_time: ISO format datetime string
        duration_minutes: Call duration in minutes
        tenant_id: Tenant UUID

    Returns:
        Dict with status and message_id or error
    """
    try:
        # Get tenant details for business name
        supabase = get_supabase()
        tenant_result = supabase.table("tenants").select("business_name").eq("id", tenant_id).execute()

        business_name = "Our Team"
        if tenant_result.data and len(tenant_result.data) > 0:
            business_name = tenant_result.data[0].get("business_name", "Our Team")

        # Parse scheduled time
        scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00')).replace(tzinfo=None)
        booking_date = scheduled_dt.strftime("%A, %B %d, %Y")  # "Monday, February 26, 2026"
        booking_time = scheduled_dt.strftime("%I:%M %p")  # "02:00 PM"

        # Format message
        greeting = f"Hi {customer_name}! " if customer_name else "Hi! "
        message = f"""{greeting}✅ *Appointment Confirmed!*

📅 *Date:* {booking_date}
🕐 *Time:* {booking_time}
⏱️ *Duration:* {duration_minutes} minutes

You'll receive a reminder 1 hour before your appointment.

Need to reschedule? Just reply with "reschedule" or give us a call.

- {business_name}"""

        # Initialize bridge client
        bridge = BridgeClient()

        # Send message via bridge
        response = await bridge.post(
            "/send/message",
            json={
                "to": customer_jid,
                "message": message
            }
        )

        # Parse response
        if response.status == 200:
            response_data = await response.json()
            logger.info(f"✅ Booking confirmation sent to {customer_jid}")
            return {"status": "sent", "message_id": response_data.get("id", "unknown")}
        else:
            error_text = await response.text()
            logger.error(f"❌ Failed to send booking confirmation: HTTP {response.status} - {error_text}")
            return {"status": "failed", "error": f"HTTP {response.status}"}

    except Exception as e:
        logger.error(f"❌ Failed to send booking confirmation to {customer_jid}: {e}")
        # Don't fail booking if WhatsApp fails
        return {"status": "failed", "error": str(e)}


# ==================== API ENDPOINTS ====================

@router.post("/book")
async def book_call(booking_data: CallBookingCreate, tenant_id: str = Depends(verify_session)):
    """
    Book a new call appointment with availability validation.
    """

    try:
        # ==================== AVAILABILITY VALIDATION ====================
        # Parse requested datetime
        try:
            requested_dt = datetime.fromisoformat(booking_data.scheduled_time.replace('Z', '+00:00')).replace(tzinfo=None)
            requested_date = requested_dt.date()
            requested_time = requested_dt.time()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid scheduled_time format: {e}")

        # Check if booking is too far in advance
        settings = await _get_call_settings(tenant_id)
        advance_booking_days = settings.get("advance_booking_days", 30)
        max_advance_date = datetime.now().date() + timedelta(days=advance_booking_days)

        if requested_date > max_advance_date:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot book more than {advance_booking_days} days in advance"
            )

        # Check if same-day booking is allowed
        if not settings.get("allow_same_day_booking", True) and requested_date == datetime.now().date():
            raise HTTPException(status_code=400, detail="Same-day booking is not allowed")

        # Check if requested slot is available
        buffer_minutes = settings.get("buffer_minutes", 15)
        available_slots = await _get_available_slots_for_date(
            tenant_id,
            requested_date,
            booking_data.duration_minutes or 30,
            buffer_minutes,
            settings.get("timezone", "Asia/Kuala_Lumpur")
        )

        # Check if the requested time matches any available slot
        requested_time_str = requested_time.strftime("%H:%M")
        slot_available = False

        for slot in available_slots:
            if slot["start_time"] == requested_time_str:
                slot_available = True
                break

        if not slot_available:
            raise HTTPException(
                status_code=409,
                detail=f"Requested time slot {requested_time_str} on {requested_date} is not available. Please check available slots first."
            )

        # Check daily/hourly limits
        existing_bookings_count = len(await _get_bookings_for_date(tenant_id, requested_date.strftime("%Y-%m-%d")))
        max_calls_per_day = settings.get("max_calls_per_day", 8)

        if existing_bookings_count >= max_calls_per_day:
            raise HTTPException(
                status_code=409,
                detail=f"Maximum daily booking limit ({max_calls_per_day}) reached for {requested_date}"
            )

        # ===================== END VALIDATION ==========================

        booking_id = str(uuid.uuid4())

        # Insert into Supabase
        supabase = get_supabase()
        result = supabase.table("call_bookings").insert({
            "id": booking_id,
            "tenant_id": tenant_id,
            "customer_jid": booking_data.customer_jid,
            "customer_name": booking_data.customer_name,
            "customer_phone": booking_data.customer_phone,
            "scheduled_time": booking_data.scheduled_time,
            "duration_minutes": booking_data.duration_minutes,
            "call_type": booking_data.call_type,
            "status": "scheduled",
            "notes": booking_data.notes,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "reminder_sent": False,
            "confirmation_sent": False
        }).execute()

        logger.info(f"✅ Call booking created: {booking_id}")

        # Send WhatsApp confirmation to customer
        whatsapp_result = await _send_booking_confirmation_whatsapp(
            customer_jid=booking_data.customer_jid,
            customer_name=booking_data.customer_name,
            scheduled_time=booking_data.scheduled_time,
            duration_minutes=booking_data.duration_minutes or 30,
            tenant_id=tenant_id
        )

        # Update confirmation_sent flag if WhatsApp was successful
        if whatsapp_result.get("status") == "sent":
            supabase.table("call_bookings").update({
                "confirmation_sent": True
            }).eq("id", booking_id).eq("tenant_id", tenant_id).execute()
            logger.info(f"✅ WhatsApp confirmation sent for booking {booking_id}")
        else:
            logger.warning(f"⚠️ WhatsApp confirmation failed for booking {booking_id}: {whatsapp_result.get('error')}")

        # ── Schedule reminders (24h & 1h before call) ───────────────────────
        if _proactive_system is not None:
            try:
                # Fetch business name for reminder message branding
                biz_res = supabase.table("tenants").select("business_name").eq("id", tenant_id).execute()
                business_name = (biz_res.data or [{}])[0].get("business_name", "Our Team")

                asyncio.create_task(
                    _proactive_system.schedule_call_reminders(
                        tenant_id=tenant_id,
                        booking_id=booking_id,
                        customer_jid=booking_data.customer_jid,
                        customer_name=booking_data.customer_name or "Customer",
                        call_time=requested_dt,
                        call_type=booking_data.call_type or "consultation",
                        duration_minutes=booking_data.duration_minutes or 30,
                        business_name=business_name,
                    )
                )
                logger.info(f"📅 Reminder tasks queued for booking {booking_id}")
            except Exception as reminder_err:
                logger.warning(f"⚠️ Could not schedule reminders for {booking_id}: {reminder_err}")
        else:
            logger.debug("ℹ️ Proactive system not wired — skipping reminder scheduling")

        return {
            "booking_id": booking_id,
            "message": "Call booking created successfully",
            "whatsapp_confirmation": whatsapp_result.get("status"),
            "booking": {
                "id": booking_id,
                "tenant_id": tenant_id,
                "customer_jid": booking_data.customer_jid,
                "customer_name": booking_data.customer_name,
                "customer_phone": booking_data.customer_phone,
                "scheduled_time": booking_data.scheduled_time,
                "duration_minutes": booking_data.duration_minutes,
                "call_type": booking_data.call_type,
                "status": "scheduled",
                "notes": booking_data.notes
            }
        }

    except HTTPException:
        # Let genuine 400 (bad input) / 409 (slot unavailable, limit reached)
        # propagate with their real status + message instead of being masked as 500.
        raise
    except Exception as e:
        logger.error(f"❌ Error booking call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_call_bookings(tenant_id: str = Depends(verify_session), status: Optional[str] = None):
    """
    Get all call bookings for a tenant, optionally filtered by status.
    """
    try:
        supabase = get_supabase()
        query = supabase.table("call_bookings").select("*").eq("tenant_id", tenant_id)
        if status:
            query = query.eq("status", status)
        result = query.order("scheduled_time", desc=False).execute()
        bookings = result.data or []

        return {"bookings": bookings}

    except Exception as e:
        logger.error(f"❌ Error listing call bookings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CallStatusUpdate(BaseModel):
    status: str


@router.put("/{booking_id}/status")
async def update_call_status(
    booking_id: str,
    body: CallStatusUpdate,
    tenant_id: str = Depends(verify_session),
):
    """
    Update the status of a call booking (scheduled, in_progress, completed, cancelled).

    The dashboard sends the new status in the JSON body ({"status": "..."}); accept
    it there rather than as a query param (which returned 422).
    """
    status = body.status

    valid_statuses = ["scheduled", "in_progress", "completed", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid_statuses}")

    try:
        supabase = get_supabase()
        result = supabase.table("call_bookings").update({
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", booking_id).eq("tenant_id", tenant_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Booking not found")

        return {"success": True, "booking_id": booking_id, "new_status": status}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating call status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/availability")
async def set_availability(
    availability: List[AvailabilitySlot],
    tenant_id: str = Depends(verify_session),
):
    """
    Set weekly availability slots for call bookings.
    """
    try:
        supabase = get_supabase()

        # Clear existing availability
        supabase.table("call_availability").delete().eq("tenant_id", tenant_id).execute()

        # Insert new availability slots
        for slot in availability:
            supabase.table("call_availability").insert({
                "tenant_id": tenant_id,
                "day_of_week": slot.day_of_week,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "timezone": slot.timezone,
                "is_active": True,
                "created_at": datetime.utcnow().isoformat()
            }).execute()

        return {"success": True, "slots_added": len(availability)}

    except Exception as e:
        logger.error(f"❌ Error setting availability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/availability")
async def get_availability(tenant_id: str = Depends(verify_session)):
    """
    Get weekly availability slots for call bookings.
    """
    try:
        supabase = get_supabase()
        result = supabase.table("call_availability").select("*").eq("tenant_id", tenant_id).eq("is_active", True).order("day_of_week").execute()
        slots = result.data or []

        return {"availability": slots}

    except Exception as e:
        logger.error(f"❌ Error getting availability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/availability/default")
async def setup_default_availability(tenant_id: str = Depends(verify_session)):
    """
    Setup default business hours for a new tenant.
    Default: Monday-Friday 9:00 AM - 5:00 PM (Asia/Kuala_Lumpur timezone)
    """
    try:
        # Default business hours: Monday-Friday 9:00 AM - 5:00 PM
        default_slots = []
        for day in range(5):  # 0-4 = Monday to Friday
            default_slots.append(AvailabilitySlot(
                day_of_week=day,
                start_time="09:00",
                end_time="17:00",
                timezone="Asia/Kuala_Lumpur"
            ))

        supabase = get_supabase()

        # Clear existing availability
        supabase.table("call_availability").delete().eq("tenant_id", tenant_id).execute()

        # Insert default availability slots
        for slot in default_slots:
            supabase.table("call_availability").insert({
                "tenant_id": tenant_id,
                "day_of_week": slot.day_of_week,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "timezone": slot.timezone,
                "is_active": True,
                "created_at": datetime.utcnow().isoformat()
            }).execute()

        # Insert default call settings.
        # NOTE (2026-08-06): the previous `.upsert({...})` had no
        # `on_conflict=...`, so the Supabase client fell back to the primary
        # key (`id`) for conflict resolution. Since the row already existed
        # for this tenant (UNIQUE on `tenant_id`), the upsert was treated as
        # a fresh insert and blew up with `23505 duplicate key value
        # violates unique constraint "call_settings_tenant_id_key"`. Passing
        # `on_conflict="tenant_id"` makes the upsert actually update on
        # conflict.
        supabase.table("call_settings").upsert({
            "tenant_id": tenant_id,
            "timezone": "Asia/Kuala_Lumpur",
            "buffer_minutes": 15,
            "max_calls_per_day": 8,
            "max_calls_per_hour": 2,
            "advance_booking_days": 30,
            "allow_same_day_booking": True,
            "updated_at": datetime.utcnow().isoformat()
        }, on_conflict="tenant_id").execute()

        return {
            "success": True,
            "message": "Default business hours setup completed",
            "schedule": "Monday-Friday 9:00 AM - 5:00 PM (Asia/Kuala_Lumpur)",
            "slots_created": len(default_slots)
        }

    except Exception as e:
        logger.error(f"❌ Error setting up default availability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available-slots")
async def get_available_slots(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    duration_minutes: int = Query(30, description="Call duration in minutes"),
    x_tenant_id: str = Header(None)
):
    """
    Get available time slots for booking within a date range.
    Considers business hours, existing bookings, holidays, and buffer times.
    """
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header required")

    try:
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Get call settings
        settings = await _get_call_settings(x_tenant_id)
        timezone_str = settings.get("timezone", "Asia/Kuala_Lumpur")
        buffer_minutes = settings.get("buffer_minutes", 15)

        # Get availability slots
        available_slots = []
        current_date = start_dt

        while current_date <= end_dt:
            day_slots = await _get_available_slots_for_date(
                x_tenant_id, current_date, duration_minutes, buffer_minutes, timezone_str
            )
            available_slots.extend(day_slots)
            current_date += timedelta(days=1)

        return {
            "available_slots": available_slots,
            "total_slots": len(available_slots),
            "timezone": timezone_str
        }

    except Exception as e:
        logger.error(f"❌ Error getting available slots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/availability/holidays")
async def manage_holidays(
    holidays: List[HolidayException],
    tenant_id: str = Depends(verify_session),
):
    """
    Add or update holiday exceptions.
    """
    try:
        supabase = get_supabase()

        for holiday in holidays:
            supabase.table("holiday_exceptions").upsert({
                "tenant_id": tenant_id,
                "date": holiday.date,
                "title": holiday.title,
                "description": holiday.description,
                "is_recurring": holiday.is_recurring,
                "created_at": datetime.utcnow().isoformat()
            }).execute()

        return {"success": True, "holidays_added": len(holidays)}

    except Exception as e:
        logger.error(f"❌ Error managing holidays: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/availability/settings")
async def get_call_settings(tenant_id: str = Depends(verify_session)):
    """
    Get call booking settings (buffer times, limits, timezone, etc.)
    """
    try:
        settings = await _get_call_settings(tenant_id)
        return {
            "success": True,
            "settings": settings
        }

    except Exception as e:
        logger.error(f"❌ Error getting call settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/availability/settings")
async def update_call_settings(
    settings: CallSettings,
    tenant_id: str = Depends(verify_session),
):
    """
    Update call booking settings (buffer times, limits, timezone, etc.)
    """
    try:
        supabase = get_supabase()
        result = supabase.table("call_settings").upsert({
            "tenant_id": tenant_id,
            "timezone": settings.timezone,
            "buffer_minutes": settings.buffer_minutes,
            "max_calls_per_day": settings.max_calls_per_day,
            "max_calls_per_hour": settings.max_calls_per_hour,
            "advance_booking_days": settings.advance_booking_days,
            "allow_same_day_booking": settings.allow_same_day_booking,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()

        return {"success": True, "message": "Call settings updated successfully"}

    except Exception as e:
        logger.error(f"❌ Error updating call settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/availability/schedule")
async def get_full_availability_schedule(tenant_id: str = Depends(verify_session)):
    """
    Get complete availability schedule including weekly slots, holidays, and settings.
    """
    try:
        # Get weekly schedule
        weekly_result = await get_availability(tenant_id)
        weekly_schedule = weekly_result.get("availability", [])

        supabase = get_supabase()

        # Get holidays
        holidays_result = supabase.table("holiday_exceptions").select("*").eq("tenant_id", tenant_id).execute()
        holidays = holidays_result.data or []

        # Get overrides
        overrides_result = supabase.table("availability_overrides").select("*").eq("tenant_id", tenant_id).execute()
        overrides = overrides_result.data or []

        # Get settings
        settings = await _get_call_settings(tenant_id)

        return {
            "weekly_schedule": weekly_schedule,
            "holidays": holidays,
            "overrides": overrides,
            "settings": settings
        }

    except Exception as e:
        logger.error(f"❌ Error getting full availability schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reminders")
async def get_pending_reminders(tenant_id: str = Depends(verify_session)):
    """
    Get list of pending call reminders for a tenant.
    """
    try:
        supabase = get_supabase()

        # Get pending reminders from scheduled_messages table.
        # NOTE (2026-08-06): the previous query filtered on
        # `message_type IN ('call_reminder_24h', 'call_reminder_1h',
        # 'owner_notification')` and ordered by `scheduled_time`, but the
        # `scheduled_messages` table has neither of those columns (status
        # holds 'pending'|'sent'|... and times live in `created_at`/`updated_at`).
        # PostgREST returned `42703 column ... does not exist` and the route
        # 500'd. Filter on `status='pending'` and order by `updated_at`.
        result = supabase.table("scheduled_messages").select("*").eq(
            "tenant_id", tenant_id
        ).eq("status", "pending").order("updated_at", desc=True).execute()

        reminders = result.data or []

        return {
            "reminders": reminders,
            "count": len(reminders)
        }

    except Exception as e:
        logger.error(f"❌ Error getting pending reminders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reminders/{reminder_id}/send")
async def send_reminder_manually(reminder_id: str, tenant_id: str = Depends(verify_session)):
    """
    Manually send a scheduled reminder immediately.
    """
    try:
        supabase = get_supabase()

        # Get the reminder
        result = supabase.table("scheduled_messages").select("*").eq(
            "id", reminder_id
        ).eq("tenant_id", tenant_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Reminder not found")

        reminder = result.data[0]

        # For now, we'll just mark as sent since bridge adapter access needs refactoring
        # TODO: Implement proper WhatsApp bridge integration
        now = datetime.utcnow()
        supabase.table("scheduled_messages").update({
            "status": "sent",
            "sent_at": now.isoformat()
        }).eq("tenant_id", tenant_id).eq("id", reminder_id).execute()

        logger.info(f"✅ Manually marked reminder {reminder_id} as sent")
        return {"success": True, "message": "Reminder marked as sent successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error sending manual reminder: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send reminder: {e}")


@router.delete("/reminders/{reminder_id}")
async def cancel_reminder(reminder_id: str, tenant_id: str = Depends(verify_session)):
    """
    Cancel a scheduled reminder.
    """
    try:
        supabase = get_supabase()

        # Update reminder status to cancelled
        result = supabase.table("scheduled_messages").update({
            "status": "cancelled"
        }).eq("id", reminder_id).eq("tenant_id", tenant_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Reminder not found")

        logger.info(f"🚫 Cancelled reminder {reminder_id}")
        return {"success": True, "message": "Reminder cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error cancelling reminder: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel reminder: {e}")


@router.put("/{booking_id}/reschedule")
async def reschedule_call_with_reminders(
    booking_id: str,
    reschedule_data: dict,
    tenant_id: str = Depends(verify_session),
):
    """
    Reschedule a call and update all associated reminders.
    """
    try:
        new_time = reschedule_data.get("scheduled_time")
        if not new_time:
            raise HTTPException(status_code=400, detail="scheduled_time is required")

        supabase = get_supabase()

        # Get booking details
        booking_result = supabase.table("call_bookings").select("*").eq(
            "id", booking_id
        ).eq("tenant_id", tenant_id).execute()

        if not booking_result.data:
            raise HTTPException(status_code=404, detail="Booking not found")

        booking = booking_result.data[0]

        # Update booking time (scoped to tenant)
        supabase.table("call_bookings").update({
            "scheduled_time": new_time,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", booking_id).eq("tenant_id", tenant_id).execute()

        # Cancel existing reminders (simplified approach for now)
        supabase.table("scheduled_messages").update({
            "status": "cancelled"
        }).eq("tenant_id", tenant_id).like("metadata", f'%"booking_id": "{booking_id}"%').execute()

        # Note: Proactive messaging integration would be implemented here
        # when the bridge adapter and messaging system is properly integrated

        logger.info(f"📅 Rescheduled call {booking_id} to {new_time}")
        return {
            "success": True,
            "message": "Call rescheduled successfully",
            "booking_id": booking_id,
            "new_time": new_time
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error rescheduling call: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reschedule call: {e}")


@router.get("/daily-digest/{tenant_id}")
async def trigger_daily_digest(tenant_id: str):
    """
    Trigger daily digest of upcoming calls for business owner.
    Note: Proactive messaging integration to be implemented when bridge adapter is properly integrated.
    """
    try:
        # TODO: Implement daily digest functionality when proactive messaging is integrated
        return {"success": False, "message": "Daily digest functionality not yet implemented"}

    except Exception as e:
        logger.error(f"❌ Error sending daily digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))
