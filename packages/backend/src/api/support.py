"""
Bijou AI - Support Ticket API
==============================

Public endpoint for submitting support tickets from the /help page.
Saves tickets to the help_tickets table and sends email notification.

Author: W3J Bijou AI
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/support", tags=["support"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SupportTicketRequest(BaseModel):
    name: str
    email: str
    issue_type: str
    message: str
    tenant_id: Optional[str] = None  # Optional — may be provided if user is logged in


# ---------------------------------------------------------------------------
# POST /api/support/ticket  (public — no auth required)
# ---------------------------------------------------------------------------

@router.post("/ticket")
async def create_support_ticket(req: SupportTicketRequest):
    """
    Submit a support ticket from the /help page or dashboard.
    Saves to help_tickets table and sends email notification to support team.
    """
    # Basic validation
    name = (req.name or "").strip()
    email = (req.email or "").strip()
    message = (req.message or "").strip()
    issue_type = (req.issue_type or "other").strip()

    if not name or not email or not message:
        raise HTTPException(status_code=422, detail="Name, email and message are required.")

    if len(message) > 5000:
        raise HTTPException(status_code=422, detail="Message is too long (max 5000 characters).")

    try:
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL", "").strip('"')
        supabase_key = (
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        ).strip('"')
        supabase = create_client(supabase_url, supabase_key)

        # Insert using the existing help_tickets schema
        # sender_name=name, sender_jid=email, group_jid="web-form", notes=issue_type
        ticket_number_prefix = "WEB"
        # Get next ticket number
        existing = supabase.table("web_support_tickets").select("ticket_number") \
            .order("created_at", desc=True).limit(1).execute()
        last_num = 0
        if existing.data:
            import re
            m = re.search(r"(\d+)$", existing.data[0].get("ticket_number", ""))
            if m:
                last_num = int(m.group(1))
        ticket_number = f"WEB-{(last_num + 1):04d}"

        ticket_data = {
            "ticket_number": ticket_number,
            "submitter_name": name,
            "submitter_email": email,
            "issue_type": issue_type,
            "message": message[:5000],
            "status": "open",
        }
        if req.tenant_id:
            ticket_data["tenant_id"] = req.tenant_id

        result = supabase.table("web_support_tickets").insert(ticket_data).execute()
        ticket_id = result.data[0].get("id") if result.data else "unknown"

        logger.info(f"✅ Support ticket created: {ticket_id} | {issue_type} | {email}")

        # Send email notification to support team (fire-and-forget)
        try:
            await _notify_support_team(ticket_id, name, email, issue_type, message)
        except Exception as mail_err:
            logger.warning(f"⚠️ Support email notification failed (ticket still saved): {mail_err}")

        return {
            "success": True,
            "ticket_id": str(ticket_id),
            "message": "Ticket submitted. We'll get back to you within 24 hours.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create support ticket: {e}")
        raise HTTPException(status_code=500, detail="Failed to save ticket. Please email support@mybijou.xyz directly.")


# ---------------------------------------------------------------------------
# Internal: email notification
# ---------------------------------------------------------------------------

async def _notify_support_team(ticket_id, name: str, email: str, issue_type: str, message: str):
    """Send email notification to support@mybijou.xyz when a new ticket arrives."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")

    if not smtp_user or not smtp_pass:
        logger.warning("⚠️ SMTP not configured — skipping support email notification")
        return

    support_inbox = os.getenv("SUPPORT_EMAIL", "support@mybijou.xyz")

    body = f"""New Support Ticket #{ticket_id}

From: {name} <{email}>
Issue Type: {issue_type}

Message:
{message}

---
Reply directly to {email} or log into the dashboard to manage tickets.
"""

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = support_inbox
    msg["Reply-To"] = email
    msg["Subject"] = f"[Support] {issue_type.title()} — {name}"
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, support_inbox, msg.as_string())

    logger.info(f"✅ Support email sent for ticket {ticket_id}")
