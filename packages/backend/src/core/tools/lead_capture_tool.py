"""
Lead Capture Tool
=================

Captures leads and sends them to Zapier/Make webhooks for marketing automation.
Supports lead quality scoring and tenant-specific webhook configurations.

Phase 4: Marketing & Analytics Integration
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Email template for lead confirmation
LEAD_CONFIRMATION_EMAIL_TEMPLATE = """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #667eea;">Thank you for your inquiry, {name}!</h2>
        
        <p>We've received your message and one of our team members will get back to you shortly.</p>
        
        <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #667eea; margin: 20px 0;">
            <p><strong>Your inquiry:</strong></p>
            <p style="font-style: italic; color: #666;">{message}</p>
        </div>
        
        <p><strong>What happens next?</strong></p>
        <ul>
            <li>A team member will review your inquiry</li>
            <li>You'll receive a response within 24 hours</li>
            <li>We'll contact you at: {contact_info}</li>
        </ul>
        
        <p>If you have any urgent questions, feel free to reply to this email.</p>
        
        <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
        
        <p style="font-size: 12px; color: #999;">
            This is an automated confirmation from {business_name}.<br>
            Powered by Bijou AI - W3J Consulting
        </p>
    </div>
</body>
</html>
"""


class LeadCaptureTool:
    """
    Lead capture and webhook integration tool for Bijou.

    Features:
    - Capture lead information (name, phone, email, message)
    - Send to Zapier/Make webhooks
    - Lead quality scoring
    - Tenant-specific webhook URLs
    - FB CAPI / Google Ads integration support
    """

    def __init__(
        self,
        default_webhook_url: Optional[str] = None,
        timeout: int = 30,
        gmail_tool=None,
    ):
        """
        Initialize Lead Capture tool.

        Args:
            default_webhook_url: Default Zapier/Make webhook URL
            timeout: HTTP request timeout in seconds
            gmail_tool: GmailTool instance for sending confirmation emails
        """
        self.default_webhook_url = default_webhook_url or os.getenv("LEAD_WEBHOOK_URL")
        self.timeout = timeout
        self.gmail_tool = gmail_tool
        self._initialized = bool(self.default_webhook_url)

        if not self._initialized:
            logger.warning(
                "Lead capture tool initialized without webhook URL. "
                "Set LEAD_WEBHOOK_URL environment variable."
            )
        else:
            logger.info(
                f"✅ Lead capture tool initialized with webhook: {self._mask_url(self.default_webhook_url)}"
            )
        
        if self.gmail_tool:
            logger.info("✅ Gmail integration enabled for lead confirmation emails")

    async def capture_lead(
        self,
        name: str,
        phone: str,
        message: str,
        email: Optional[str] = None,
        tenant_id: Optional[str] = None,
        business_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        webhook_url: Optional[str] = None,
        send_confirmation_email: bool = True,
        business_name: str = "Our Team",
    ) -> Dict[str, Any]:
        """
        Capture a lead and send to webhook + confirmation email.

        Args:
            name: Lead's name
            phone: Lead's phone number (WhatsApp JID or Telegram handle)
            message: Lead's message/inquiry
            email: Lead's email (optional)
            tenant_id: Tenant UUID
            business_type: Type of business (Gaming, Dental, Property, etc.)
            metadata: Additional metadata (source, campaign, etc.)
            webhook_url: Override webhook URL (tenant-specific)
            send_confirmation_email: Whether to send confirmation email to customer
            business_name: Name of business for email template

        Returns:
            Dictionary with capture results including email_sent status

        Example:
            >>> tool = LeadCaptureTool()
            >>> result = tool.capture_lead(
            ...     name="John Doe",
            ...     phone="+60123456789",
            ...     message="Interested in your service",
            ...     email="john@example.com",
            ...     business_type="Dental"
            ... )
            >>> print(result["success"])
        """
        if not self._initialized and not webhook_url:
            return {
                "success": False,
                "error": "No webhook URL configured",
            }

        try:
            # Calculate lead quality score
            quality_score = self._calculate_quality_score(
                name=name,
                phone=phone,
                email=email,
                message=message,
            )

            # Build lead payload
            lead_data = {
                "name": name,
                "phone": phone,
                "email": email or "",
                "message": message,
                "quality_score": quality_score,
                "quality_label": self._get_quality_label(quality_score),
                "tenant_id": tenant_id or "",
                "business_type": business_type or "",
                "captured_at": datetime.utcnow().isoformat(),
                "source": "bijou_ai",
                "metadata": metadata or {},
            }

            # Send confirmation email if email provided and enabled
            email_sent = False
            email_error = None
            
            if email and send_confirmation_email and self.gmail_tool:
                try:
                    # Generate email content
                    email_html = LEAD_CONFIRMATION_EMAIL_TEMPLATE.format(
                        name=name,
                        message=message,
                        contact_info=email,
                        business_name=business_name
                    )
                    
                    # Send email
                    email_result = self.gmail_tool.send_email(
                        to=email,
                        subject=f"Thank you for contacting {business_name}",
                        body=email_html,
                        is_html=True
                    )
                    
                    if email_result.get("success"):
                        email_sent = True
                        logger.info(f"✅ Confirmation email sent to {email}")
                    else:
                        email_error = email_result.get("error", "Unknown error")
                        logger.warning(f"⚠️ Failed to send confirmation email: {email_error}")
                        
                except Exception as e:
                    email_error = str(e)
                    logger.error(f"❌ Email sending exception: {e}")
            
            # Send to webhook
            webhook = webhook_url or self.default_webhook_url
            webhook_result = await self._send_to_webhook(webhook, lead_data)

            if webhook_result.get("success"):
                logger.info(
                    f"✅ Lead captured: {name} ({phone}) - Quality: {quality_score}/100 | Email: {email_sent}"
                )
                return {
                    "success": True,
                    "lead_id": lead_data.get("captured_at"),
                    "quality_score": quality_score,
                    "quality_label": self._get_quality_label(quality_score),
                    "webhook_status": webhook_result.get("status_code"),
                    "email_sent": email_sent,
                    "email_error": email_error,
                    "data": lead_data,
                }
            else:
                logger.error(
                    f"❌ Failed to send lead to webhook: {webhook_result.get('error')}"
                )
                return {
                    "success": False,
                    "error": f"Webhook failed: {webhook_result.get('error')}",
                    "email_sent": email_sent,
                    "email_error": email_error,
                    "data": lead_data,
                }

        except Exception as e:
            logger.error(f"❌ Lead capture failed: {e}")
            return {"success": False, "error": str(e)}

    def analyze_lead_quality(
        self,
        name: str,
        phone: str,
        message: str,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze lead quality without sending to webhook.

        Args:
            name: Lead's name
            phone: Lead's phone number
            message: Lead's message
            email: Lead's email (optional)

        Returns:
            Dictionary with quality analysis

        Example:
            >>> tool = LeadCaptureTool()
            >>> result = tool.analyze_lead_quality(
            ...     name="John Doe",
            ...     phone="+60123456789",
            ...     message="I need a dentist urgently"
            ... )
            >>> print(f"Score: {result['score']}/100 - {result['label']}")
        """
        try:
            score = self._calculate_quality_score(name, phone, email, message)
            label = self._get_quality_label(score)

            return {
                "success": True,
                "score": score,
                "label": label,
                "factors": self._explain_quality_score(name, phone, email, message),
            }

        except Exception as e:
            logger.error(f"Failed to analyze lead quality: {e}")
            return {"success": False, "error": str(e)}

    def send_high_quality_signal(
        self,
        lead_data: Dict[str, Any],
        platform: str = "facebook",
        conversion_event: str = "Lead",
    ) -> Dict[str, Any]:
        """
        Send high-quality lead signal to ad platforms (FB CAPI / Google Ads).

        Args:
            lead_data: Lead information
            platform: Target platform ("facebook" or "google")
            conversion_event: Event name

        Returns:
            Dictionary with signal status

        Note:
            This is a placeholder for future FB CAPI / Google Ads integration.
            Currently logs the signal for manual processing.
        """
        try:
            quality_score = lead_data.get("quality_score", 0)

            # Only send signals for high-quality leads
            if quality_score < 70:
                return {
                    "success": False,
                    "reason": f"Lead quality too low ({quality_score}/100). Threshold: 70",
                }

            logger.info(
                f"📊 High-quality lead signal: {platform.upper()} - "
                f"Event: {conversion_event} - Score: {quality_score}/100"
            )
            logger.info(
                f"Lead data: {lead_data.get('name')} ({lead_data.get('phone')})"
            )

            # TODO: Implement actual FB CAPI / Google Ads integration
            # For now, log for manual processing or Zapier forwarding

            return {
                "success": True,
                "platform": platform,
                "event": conversion_event,
                "quality_score": quality_score,
                "note": "Signal logged for processing (FB CAPI/Google Ads integration pending)",
            }

        except Exception as e:
            logger.error(f"Failed to send conversion signal: {e}")
            return {"success": False, "error": str(e)}

    def _calculate_quality_score(
        self,
        name: str,
        phone: str,
        email: Optional[str],
        message: str,
    ) -> int:
        """
        Calculate lead quality score (0-100).

        Scoring factors:
        - Name completeness (0-20 points)
        - Phone validity (0-20 points)
        - Email provided (0-15 points)
        - Message quality (0-45 points)
        """
        score = 0

        # Name completeness (0-20)
        if name and len(name.strip()) > 0:
            score += 10
            if " " in name.strip():  # Has first and last name
                score += 10

        # Phone validity (0-20)
        if phone and len(phone.strip()) > 0:
            score += 10
            # Check if it looks like a valid phone
            clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
            if len(clean_phone) >= 10:
                score += 10

        # Email provided (0-15)
        if email and "@" in email and "." in email:
            score += 15

        # Message quality (0-45)
        if message:
            msg_len = len(message.strip())
            if msg_len > 0:
                score += 10  # Has message
            if msg_len > 20:
                score += 10  # Detailed message
            if msg_len > 50:
                score += 10  # Very detailed

            # Check for intent signals (high-intent keywords)
            high_intent_keywords = [
                "urgent",
                "need",
                "want",
                "interested",
                "appointment",
                "booking",
                "schedule",
                "buy",
                "purchase",
                "price",
                "cost",
                "how much",
                "when",
                "available",
                "contact",
            ]

            message_lower = message.lower()
            intent_matches = sum(
                1 for keyword in high_intent_keywords if keyword in message_lower
            )

            if intent_matches > 0:
                score += min(intent_matches * 5, 15)  # Max 15 points for intent

        return min(score, 100)  # Cap at 100

    def _get_quality_label(self, score: int) -> str:
        """Get quality label from score."""
        if score >= 80:
            return "High Quality"
        elif score >= 60:
            return "Medium Quality"
        elif score >= 40:
            return "Low Quality"
        else:
            return "Very Low Quality"

    def _explain_quality_score(
        self,
        name: str,
        phone: str,
        email: Optional[str],
        message: str,
    ) -> Dict[str, Any]:
        """Explain quality score factors."""
        factors = {
            "name_complete": bool(name and " " in name),
            "phone_valid": bool(
                phone
                and len(phone.replace("+", "").replace(" ", "").replace("-", "")) >= 10
            ),
            "email_provided": bool(email and "@" in email),
            "message_detailed": bool(message and len(message) > 50),
            "high_intent": any(
                keyword in message.lower()
                for keyword in [
                    "urgent",
                    "need",
                    "want",
                    "interested",
                    "appointment",
                    "buy",
                ]
            )
            if message
            else False,
        }
        return factors

    async def _send_to_webhook(
        self,
        webhook_url: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send data to webhook (Zapier/Make).

        Args:
            webhook_url: Target webhook URL
            data: Payload to send

        Returns:
            Dictionary with send result
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=data,
                    timeout=self.timeout,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "BijouAI/1.0",
                    },
                )

                response.raise_for_status()

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response": response.text[:200],  # First 200 chars
                }

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Webhook HTTP error {e.response.status_code}: {e.response.text}"
            )
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}",
                "details": e.response.text[:200],
            }
        except httpx.RequestError as e:
            logger.error(f"Webhook request error: {e}")
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _mask_url(self, url: str) -> str:
        """Mask webhook URL for logging."""
        if not url:
            return "None"
        # Show only domain
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}/***"
        except Exception:
            return "***masked***"
