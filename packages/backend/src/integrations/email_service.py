"""
Email Service
=============

Handles email sending for:
- Booking confirmations
- Escalation alerts
- Welcome emails

Uses SMTP with template system from database.

Author: W3J Consulting
Date: 2026-03-03
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email sending service with template support.

    Uses SMTP (Gmail, SendGrid, etc.) configured via env vars.
    Templates stored in database (email_templates table).
    """

    def __init__(self, supabase_client=None):
        """
        Initialize email service.

        Args:
            supabase_client: Supabase client for template queries and tenant config
        """
        self.db = supabase_client

        # Fallback SMTP config (for backwards compatibility or system-wide use)
        self.default_smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.default_smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.default_smtp_user = os.getenv("SMTP_USER", "")
        self.default_smtp_pass = os.getenv("SMTP_PASS", "")
        self.default_from_email = os.getenv("FROM_EMAIL", self.default_smtp_user)
        self.default_from_name = os.getenv("FROM_NAME", "Bijou AI")

        self._has_default_config = bool(self.default_smtp_user and self.default_smtp_pass)

        if self._has_default_config:
            logger.info(f"✅ Email service initialized with default SMTP: {self.default_smtp_host}:{self.default_smtp_port}")
        else:
            logger.warning("⚠️ No default SMTP credentials - will use tenant-specific configs only")

    def get_tenant_email_config(self, tenant_id: str) -> Optional[Dict]:
        """
        Fetch tenant-specific SMTP configuration from database.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dict with smtp_host, smtp_port, smtp_user, smtp_pass, from_email, from_name
            or None if not found
        """
        if not self.db:
            logger.warning("No database client - cannot fetch tenant email config")
            return None

        try:
            result = self.db.table("tenant_email_config")\
                .select("*")\
                .eq("tenant_id", tenant_id)\
                .eq("is_active", True)\
                .limit(1)\
                .execute()

            if result.data and len(result.data) > 0:
                config = result.data[0]
                logger.debug(f"Fetched tenant email config: {config.get('smtp_host')}")
                return config
            else:
                logger.warning(f"No email config found for tenant: {tenant_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch tenant email config: {e}")
            return None

    def get_template(self, template_type: str, tenant_id: Optional[str] = None) -> Optional[Dict]:
        """
        Fetch email template from database.

        Priority:
        1. Tenant-specific template (if tenant_id provided)
        2. System-wide template (tenant_id = NULL)

        Args:
            template_type: 'booking_confirmation', 'escalation_alert', etc.
            tenant_id: Optional tenant UUID for custom templates

        Returns:
            Dict with subject, body_html, body_text, variables
            or None if not found
        """
        if not self.db:
            logger.warning("No database client - using fallback template")
            return None

        try:
            # Try tenant-specific template first
            if tenant_id:
                result = self.db.table("email_templates")\
                    .select("*")\
                    .eq("tenant_id", tenant_id)\
                    .eq("template_type", template_type)\
                    .eq("is_active", True)\
                    .limit(1)\
                    .execute()

                if result.data and len(result.data) > 0:
                    logger.debug(f"Using tenant-specific template: {template_type}")
                    return result.data[0]

            # Fall back to system template
            result = self.db.table("email_templates")\
                .select("*")\
                .is_("tenant_id", "null")\
                .eq("template_type", template_type)\
                .eq("is_active", True)\
                .limit(1)\
                .execute()

            if result.data and len(result.data) > 0:
                logger.debug(f"Using system template: {template_type}")
                return result.data[0]
            else:
                logger.warning(f"No template found for type: {template_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch email template: {e}")
            return None

    def render_template(self, template: Dict, variables: Dict) -> Dict[str, str]:
        """
        Render email template with variables.

        Args:
            template: Template dict with subject, body_html, body_text
            variables: Dict of variable substitutions

        Returns:
            Dict with 'subject', 'html', 'text'
        """
        subject = template.get("subject", "")
        html = template.get("body_html", "")
        text = template.get("body_text", "")

        # Simple variable substitution ({{variable_name}})
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            html = html.replace(placeholder, str(value))
            text = text.replace(placeholder, str(value))

        return {
            "subject": subject,
            "html": html,
            "text": text
        }

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        to_name: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send email via SMTP (tenant-specific or default).

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text fallback (optional)
            to_name: Recipient name (optional)
            tenant_id: Tenant UUID for tenant-specific SMTP (optional)

        Returns:
            Dict with success status and error if failed
        """
        # Determine SMTP config (tenant-specific or default)
        smtp_config = None
        if tenant_id:
            smtp_config = self.get_tenant_email_config(tenant_id)

        if smtp_config:
            # Use tenant-specific SMTP
            smtp_host = smtp_config.get("smtp_host")
            smtp_port = smtp_config.get("smtp_port", 587)
            smtp_user = smtp_config.get("smtp_user")
            smtp_pass = smtp_config.get("smtp_pass")
            smtp_use_tls = smtp_config.get("smtp_use_tls", True)
            from_email = smtp_config.get("from_email")
            from_name = smtp_config.get("from_name")

            # Validate required fields
            if not all([smtp_host, smtp_user, smtp_pass, from_email, from_name]):
                logger.error(f"Incomplete tenant email config for {tenant_id}")
                return {
                    "success": False,
                    "error": "Incomplete tenant SMTP configuration"
                }

            logger.debug(f"Using tenant-specific SMTP for {tenant_id}")
        elif self._has_default_config:
            # Fall back to default SMTP
            smtp_host = self.default_smtp_host
            smtp_port = self.default_smtp_port
            smtp_user = self.default_smtp_user
            smtp_pass = self.default_smtp_pass
            smtp_use_tls = True
            from_email = self.default_from_email
            from_name = self.default_from_name
            logger.debug("Using default SMTP config")
        else:
            return {
                "success": False,
                "error": "No SMTP config available (neither tenant-specific nor default)"
            }

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{from_name} <{from_email}>"
            msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email

            # Attach text and HTML parts
            if text_body:
                part1 = MIMEText(text_body, 'plain')
                msg.attach(part1)

            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)

            # Send via SMTP
            # Type assertions: these are guaranteed to be strings after validation above
            assert isinstance(smtp_host, str) and isinstance(smtp_user, str)
            assert isinstance(smtp_pass, str) and isinstance(from_email, str)

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if smtp_use_tls:
                    server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, to_email, msg.as_string())

            logger.info(f"✅ Email sent: {subject} → {to_email} (via {smtp_host})")
            return {"success": True}

        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def send_booking_confirmation(
        self,
        tenant_id: str,
        customer_name: str,
        customer_email: str,
        property_name: str,
        booking_date: str,
        booking_time: str,
        calendar_link: str,
        duration: int = 30,
        agent_name: Optional[str] = None,
        agent_phone: Optional[str] = None,
        agent_email: Optional[str] = None,
        property_address: Optional[str] = None,
        meeting_point: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send booking confirmation email to customer.

        Args:
            tenant_id: Tenant UUID
            customer_name: Customer's name
            customer_email: Customer's email
            property_name: Property name
            booking_date: Human-readable date (e.g., "Tuesday, March 4, 2026")
            booking_time: Human-readable time (e.g., "2:00 PM")
            calendar_link: Cal.com booking link
            duration: Booking duration in minutes
            agent_name: Agent name (optional)
            agent_phone: Agent phone (optional)
            agent_email: Agent email (optional)
            property_address: Property address (optional)
            meeting_point: Meeting point instructions (optional)

        Returns:
            Dict with success status
        """
        # Get template
        template = self.get_template("booking_confirmation", tenant_id)

        if not template:
            # Fallback to inline template
            logger.warning("Using fallback booking confirmation template")
            return self._send_fallback_booking_confirmation(
                customer_name, customer_email, property_name,
                booking_date, booking_time, calendar_link,
                tenant_id=tenant_id
            )

        # Prepare variables
        variables = {
            "customer_name": customer_name,
            "property_name": property_name,
            "booking_date": booking_date,
            "booking_time": booking_time,
            "duration": str(duration),
            "calendar_link": calendar_link,
            "agent_name": agent_name or "Your Property Agent",
            "agent_phone": agent_phone or "(Contact via WhatsApp)",
            "agent_email": agent_email or "(Contact via WhatsApp)",
            "property_address": property_address or "Address will be shared by agent",
            "meeting_point": meeting_point or "Agent will confirm meeting point",
            "business_name": "Bijou AI"  # TODO: Fetch from tenant table
        }

        # Render template
        rendered = self.render_template(template, variables)

        # Send email (with tenant-specific SMTP)
        return self.send_email(
            to_email=customer_email,
            subject=rendered["subject"],
            html_body=rendered["html"],
            text_body=rendered["text"],
            to_name=customer_name,
            tenant_id=tenant_id  # Pass tenant_id for tenant-specific SMTP
        )

    def send_escalation_alert(
        self,
        tenant_id: str,
        agent_email: str,
        customer_name: str,
        customer_phone: str,
        customer_email: str,
        urgency: str,
        lead_data: Dict,
        conversation_summary: str,
        dashboard_link: Optional[str] = None,
        calendar_link: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send escalation alert to human agent.

        Args:
            tenant_id: Tenant UUID
            agent_email: Agent's email address
            customer_name: Customer's name
            customer_phone: Customer's phone
            customer_email: Customer's email
            urgency: 'URGENT', 'HIGH', 'NORMAL'
            lead_data: Dict with budget, timeline, requirements, etc.
            conversation_summary: AI-generated summary
            dashboard_link: Link to dashboard (optional)
            calendar_link: Link to booked calendar event (optional)

        Returns:
            Dict with success status
        """
        template = self.get_template("escalation_alert", tenant_id)

        if not template:
            # Fallback
            subject = f"🚨 URGENT: New Lead - {customer_name}"
            html_body = f"""
<h2>New Lead Escalation</h2>
<p><strong>Customer:</strong> {customer_name}</p>
<p><strong>Phone:</strong> {customer_phone}</p>
<p><strong>Email:</strong> {customer_email}</p>
<p><strong>Urgency:</strong> {urgency}</p>
<h3>Conversation Summary:</h3>
<p>{conversation_summary}</p>
            """

            return self.send_email(
                to_email=agent_email,
                subject=subject,
                html_body=html_body,
                tenant_id=tenant_id
            )

        # Render template with full variables
        variables = {
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "customer_email": customer_email,
            "urgency": urgency,
            "budget": lead_data.get("budget", "Not specified"),
            "timeline": lead_data.get("timeline", "Not specified"),
            "property_type": lead_data.get("property_type", "Not specified"),
            "requirements": lead_data.get("requirements", "Not specified"),
            "booking_date": lead_data.get("booking_date", "Not booked yet"),
            "booking_time": lead_data.get("booking_time", ""),
            "calendar_link": calendar_link or "#",
            "conversation_summary": conversation_summary,
            "dashboard_link": dashboard_link or "#"
        }

        rendered = self.render_template(template, variables)

        return self.send_email(
            to_email=agent_email,
            subject=rendered["subject"],
            html_body=rendered["html"],
            text_body=rendered["text"],
            tenant_id=tenant_id
        )

    def _send_fallback_booking_confirmation(
        self,
        customer_name: str,
        customer_email: str,
        property_name: str,
        booking_date: str,
        booking_time: str,
        calendar_link: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fallback booking confirmation email (minimal)"""
        subject = f"Property Viewing Confirmed - {property_name}"
        html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #4CAF50;">✅ Your Viewing is Confirmed!</h2>
    <p>Hi <strong>{customer_name}</strong>,</p>
    <p>Your property viewing has been confirmed:</p>
    <ul>
        <li><strong>Property:</strong> {property_name}</li>
        <li><strong>Date:</strong> {booking_date}</li>
        <li><strong>Time:</strong> {booking_time}</li>
    </ul>
    <p><a href="{calendar_link}" style="display: inline-block; padding: 12px 24px; background: #4CAF50; color: white; text-decoration: none; border-radius: 4px;">📅 Add to Calendar</a></p>
    <p><em>Your agent will contact you shortly with more details.</em></p>
    <p style="margin-top: 30px; font-size: 12px; color: #666;">Powered by Bijou AI</p>
</body>
</html>
        """

        text_body = f"""
✅ Your Viewing is Confirmed!

Hi {customer_name},

Your property viewing has been confirmed:
- Property: {property_name}
- Date: {booking_date}
- Time: {booking_time}

Add to calendar: {calendar_link}

Your agent will contact you shortly with more details.

---
Powered by Bijou AI
        """

        return self.send_email(
            to_email=customer_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            to_name=customer_name,
            tenant_id=tenant_id
        )


# ============================================================================
# Convenience function
# ============================================================================

def create_email_service(supabase_client=None) -> EmailService:
    """
    Factory function to create EmailService instance.

    Args:
        supabase_client: Supabase client instance

    Returns:
        EmailService instance
    """
    return EmailService(supabase_client=supabase_client)
