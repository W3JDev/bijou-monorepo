"""
Bijou AI - Email Service
========================

Handles all transactional emails with automatic multi-domain key rotation.

Sending domains (tried in order, rotates on HTTP 429 quota exhaustion):
  1. app.app.mybijou.xyz    — RESEND_API_KEY          (primary)
  2. getbijou.xyz   — RESEND_API_KEY_GETBIJOU
  3. mybijouai.xyz  — RESEND_API_KEY_MYBIJOUAI
  4. bijouboleh.xyz — RESEND_API_KEY_BIJOUBOLEH

On 429, the exhausted key is cooled down for 1 hour and the next key is
tried immediately — transparent to all callers.

Other environment variables:
  EMAIL_FROM     - Override primary sender address (optional)
  EMAIL_DOMAIN   - Primary sender domain fallback (default: app.app.mybijou.xyz)
  EMAIL_NOTIFY   - Internal notification recipient (optional)

Author: W3J Bijou AI
Version: 3.0.0 — multi-domain rotation
"""

import logging
import os
import time
from typing import Optional, Dict, Any, List

import httpx

from .email_templates import (
    BRAND as _BRAND,
    email_header as _email_header,
    email_footer as _email_footer,
    email_wrap as _email_wrap,
    cta_button as _cta_button,
    divider as _divider,
    support_row as _support_row,
)

logger = logging.getLogger(__name__)

# Resend API endpoint
RESEND_API_URL = "https://api.resend.com/emails"

# How long (seconds) to cool down a key after a 429 quota hit
_QUOTA_COOLDOWN_SECONDS = 3600  # 1 hour


class EmailService:
    """
    Service for sending transactional emails via Resend API.

    Supports automatic key rotation across up to 4 sending domains:
      1. app.app.mybijou.xyz    → RESEND_API_KEY          (primary)
      2. getbijou.xyz   → RESEND_API_KEY_GETBIJOU
      3. mybijouai.xyz  → RESEND_API_KEY_MYBIJOUAI
      4. bijouboleh.xyz → RESEND_API_KEY_BIJOUBOLEH

    On HTTP 429 (quota exhausted), the current key is marked as cooled-down
    for 1 hour and the next available key is tried automatically.
    """

    def __init__(self):
        self.notify_address: str = os.getenv("EMAIL_NOTIFY", "")

        # ------- Build ordered key pool -------
        # Each entry: {"key": str, "from": str, "domain": str}
        _raw_from = os.getenv("EMAIL_FROM", "")
        _primary_domain = os.getenv("EMAIL_DOMAIN", "app.app.mybijou.xyz")
        _primary_from = _raw_from if _raw_from else f"Bijou AI <hello@{_primary_domain}>"

        _pool_spec: List[Dict[str, str]] = [
            {
                "key": os.getenv("RESEND_API_KEY", ""),
                "from": _primary_from,
                "domain": _primary_domain,
            },
            {
                "key": os.getenv("RESEND_API_KEY_GETBIJOU", ""),
                "from": "Bijou AI <hello@getbijou.xyz>",
                "domain": "getbijou.xyz",
            },
            {
                "key": os.getenv("RESEND_API_KEY_MYBIJOUAI", ""),
                "from": "Bijou AI <hello@mybijouai.xyz>",
                "domain": "mybijouai.xyz",
            },
            {
                "key": os.getenv("RESEND_API_KEY_BIJOUBOLEH", ""),
                "from": "Bijou AI <hello@bijouboleh.xyz>",
                "domain": "bijouboleh.xyz",
            },
        ]

        # Only keep entries where a key is actually set
        self._key_pool: List[Dict[str, str]] = [
            e for e in _pool_spec if e["key"]
        ]

        # Primary api_key / from_address (for code that reads them directly)
        self.api_key: Optional[str] = self._key_pool[0]["key"] if self._key_pool else None
        self.from_address: str = self._key_pool[0]["from"] if self._key_pool else _primary_from

        # Quota cooldown tracker: key → unix timestamp when cooldown expires
        self._quota_exhausted_until: Dict[str, float] = {}

        if self._key_pool:
            domains = [e["domain"] for e in self._key_pool]
            logger.info(
                f"✅ EmailService initialised — {len(self._key_pool)} key(s) ready | "
                f"domains: {', '.join(domains)}"
            )
        else:
            logger.warning(
                "⚠️  No RESEND_API_KEY configured — email sending disabled"
            )

    # ------------------------------------------------------------------
    # Internal: key rotation
    # ------------------------------------------------------------------

    def _get_active_entry(self) -> Optional[Dict[str, str]]:
        """
        Return the first non-rate-limited key pool entry.
        Falls back to primary even if cooled-down (with a warning) if all are exhausted.
        """
        now = time.time()
        for entry in self._key_pool:
            exhausted_until = self._quota_exhausted_until.get(entry["key"], 0)
            if now >= exhausted_until:
                return entry

        # All keys are in cooldown — log and fall back to primary
        if self._key_pool:
            primary = self._key_pool[0]
            cooldown_remaining = int(
                self._quota_exhausted_until.get(primary["key"], 0) - now
            )
            logger.error(
                f"🚨 ALL Resend keys are quota-exhausted! Attempting primary key anyway. "
                f"Primary cooldown expires in ~{cooldown_remaining}s. "
                f"Consider upgrading Resend plans or spacing sends."
            )
            return primary
        return None

    def _mark_key_exhausted(self, key: str) -> None:
        """Mark a key as quota-exhausted for the cooldown period."""
        self._quota_exhausted_until[key] = time.time() + _QUOTA_COOLDOWN_SECONDS

    # ------------------------------------------------------------------
    # Core send helper
    # ------------------------------------------------------------------

    def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        """
        Send an email via the Resend REST API with automatic key rotation.

        On HTTP 429 from any key, that key is suspended for 1 hour and the
        next available domain key is tried immediately, up to all 4 keys.

        Args:
            to:        Recipient email address.
            subject:   Email subject line.
            html_body: HTML body content.
            text_body: Plain-text fallback (optional).

        Returns:
            True if the email was accepted by Resend (2xx response).
        """
        if not self._key_pool:
            logger.error("❌ Cannot send email — no RESEND_API_KEY configured")
            return False

        # Try each key in pool order, rotating on 429
        tried_keys: set = set()

        while True:
            entry = self._get_active_entry()
            if entry is None:
                logger.error(f"❌ No usable Resend key found for {to}")
                return False

            # Avoid infinite loop if somehow active entry keeps being the same exhausted one
            if entry["key"] in tried_keys:
                logger.error(
                    f"❌ All {len(self._key_pool)} Resend key(s) failed or exhausted "
                    f"for {to} | subject='{subject}'"
                )
                return False

            tried_keys.add(entry["key"])

            payload: Dict[str, Any] = {
                "from": entry["from"],
                "to": [to],
                "subject": subject,
                "html": html_body,
            }
            if text_body:
                payload["text"] = text_body

            try:
                response = httpx.post(
                    RESEND_API_URL,
                    headers={
                        "Authorization": f"Bearer {entry['key']}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=15.0,
                )

                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(
                        f"✅ Email sent to {to} | subject='{subject}' | "
                        f"domain={entry['domain']} | id={data.get('id')}"
                    )
                    return True

                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "~3600")
                    logger.warning(
                        f"🚫 Resend 429 quota hit on {entry['domain']} | "
                        f"to={to} | subject='{subject}' | Retry-After={retry_after}s | "
                        f"Rotating to next key..."
                    )
                    self._mark_key_exhausted(entry["key"])
                    # Loop: try next non-exhausted key

                else:
                    logger.error(
                        f"❌ Resend API error {response.status_code} on {entry['domain']} "
                        f"sending to {to} | subject='{subject}' | {response.text}"
                    )
                    return False

            except httpx.TimeoutException:
                logger.error(
                    f"❌ Resend API timeout on {entry['domain']} sending to {to}"
                )
                return False
            except Exception as exc:
                logger.error(
                    f"❌ Unexpected error sending email to {to} via {entry['domain']}: {exc}",
                    exc_info=True,
                )
                return False

    # ------------------------------------------------------------------
    # Brand shell helper  (private)
    # ------------------------------------------------------------------

    def _wrap(self, title: str, body: str, footer_note: str = "") -> str:
        """
        Wrap email body HTML in the Bijou AI dark brand shell.

        Now delegates to the shared Python helpers in `email_templates.base`,
        which mirror `bijou_templates/email-templates/shared/base.js` (the JS
        source of truth). Brand tokens are kept in lockstep — see rebrand-progress.md
        "Task 2: Brand palette consolidation" for the canonical values.
        """
        fn = footer_note or "You received this as a Bijou AI account holder."
        return _email_wrap(_email_header(title), body, _email_footer(fn))

    def _cta(self, href: str, text: str, color: str = None) -> str:
        """Render a Signal Gem gold CTA button block.

        `color` overrides the default Signal Gem gold; pass a CSS gradient or
        hex value. Defaults to BRAND.PRIMARY (Signal Gem gold).
        """
        return _cta_button(href, text, color=color or _BRAND["PRIMARY"])

    def _card(self, content: str, border_color: str = None, bg: str = None) -> str:
        """Render a dark info card block.

        Defaults to Signal Gem green-tinted card surface (matches the JS template).
        """
        bc = border_color or _BRAND["BORDER"]
        bg_ = bg or _BRAND["CARD_BG"]
        return f"""<table width="100%" cellpadding="0" cellspacing="0" style="background:{bg_};border:1px solid {bc};border-radius:12px;margin-bottom:20px;overflow:hidden;">
  <tr><td style="padding:18px 22px;">{content}</td></tr>
</table>"""

    # ------------------------------------------------------------------
    # Transactional email methods (public interface — do not rename)
    # ------------------------------------------------------------------

    def send_verification_email(
        self,
        to: str,
        business_name: str,
        verification_token: str,
        public_url: str,
    ) -> bool:
        """Send email-verification link to a new sign-up."""

        verify_link = (
            f"{public_url}/api/onboarding/verify-email?token={verification_token}"
        )

        subject = "✅ Verify your email for Bijou AI"

        first = business_name.split()[0] if business_name else "there"

        body = f"""
            <div style="text-align:center;margin-bottom:28px;">
              <div style="display:inline-block;width:72px;height:72px;background:linear-gradient(135deg,#0B3B2E,#0E4938);border-radius:20px;text-align:center;line-height:72px;font-size:36px;box-shadow:0 8px 32px rgba(227,180,87,0.3);">🔐</div>
            </div>

            <h2 style="margin:0 0 8px;font-size:24px;font-weight:900;color:#fff;text-align:center;">Confirm your email address</h2>
            <p style="margin:0 0 32px;font-size:15px;color:#94a3b8;line-height:1.7;text-align:center;">
              Hi <strong style="color:#e2e8f0;">{first}</strong>,<br>
              Click the button below to verify your email and activate your Bijou AI account.
            </p>

            {self._cta(verify_link, "✓ Verify My Email Address")}

            {self._card('''
            <table width="100%" cellpadding="0" cellspacing="0"><tr>
              <td width="32" style="vertical-align:top;padding-top:1px;padding-right:12px;font-size:18px;">&#x1F6E1;</td>
              <td>
                <p style="margin:0 0 4px;font-size:13px;font-weight:700;color:#a5b4fc;">Security Notice</p>
                <p style="margin:0;font-size:12px;color:#64748b;line-height:1.6;">
                  This link expires in <strong style="color:#f59e0b;">30 minutes</strong>.
                  If you didn't create a Bijou AI account, you can safely ignore this email.
                  We will never ask for your password.
                </p>
              </td>
            </tr></table>''', border_color="#1e3a2f")}

            <p style="margin:0 0 4px;font-size:12px;color:#475569;text-align:center;">Button not working? Paste this link into your browser:</p>
            <p style="margin:0;font-size:11px;color:#334155;text-align:center;word-break:break-all;">
              <a href="{verify_link}" style="color:#E3B457;text-decoration:none;">{verify_link}</a>
            </p>
        """

        html_body = self._wrap("Verify Your Email", body,
                               "You received this because someone signed up for Bijou AI using this email.")

        text_body = (
            f"Welcome to Bijou AI!\n\n"
            f"Hi {business_name}!\n\n"
            f"Please verify your email by visiting:\n{verify_link}\n\n"
            f"This link expires in 30 minutes.\n\n"
            f"Need help? WhatsApp us at +60 17-410 6981\n\n"
            f"Bijou AI — app.mybijou.xyz"
        )

        return self.send_email(to, subject, html_body, text_body)

    def send_welcome_email(
        self,
        to: str,
        business_name: str,
        onboarding_url: str,
    ) -> bool:
        """Send welcome email after email is verified."""

        subject = f"🚀 Fuyoh, welcome aboard, {business_name}! Your trial starts now"

        first = business_name.split()[0] if business_name else "Boss"

        body = f"""
            <h2 style="margin:0 0 6px;font-size:26px;font-weight:900;color:#fff;">Fuyoh, welcome aboard! 🎉</h2>
            <p style="margin:0 0 28px;font-size:15px;color:#94a3b8;line-height:1.8;">
              Hi <strong style="color:#e2e8f0;">{first}</strong>, your digital employee has just reported for duty at
              <strong style="color:#10b981;">{business_name}</strong>.
              Your <strong style="color:#10b981;">14-day free trial is active now</strong> — no credit card required.
            </p>

            <!-- Feature cards -->
            {self._card('''<table cellpadding="0" cellspacing="0"><tr>
              <td width="40" style="font-size:24px;padding-right:14px;vertical-align:middle;">💬</td>
              <td>
                <p style="margin:0 0 3px;font-size:14px;font-weight:800;color:#fff;">WhatsApp AI Agent</p>
                <p style="margin:0;font-size:13px;color:#64748b;line-height:1.5;">Handles enquiries 24/7, qualifies leads, books appointments — automatically.</p>
              </td>
            </tr></table>''')}
            {self._card('''<table cellpadding="0" cellspacing="0"><tr>
              <td width="40" style="font-size:24px;padding-right:14px;vertical-align:middle;">📊</td>
              <td>
                <p style="margin:0 0 3px;font-size:14px;font-weight:800;color:#fff;">Live Analytics Dashboard</p>
                <p style="margin:0;font-size:13px;color:#64748b;line-height:1.5;">See every chat, lead, and conversion tracked in real-time.</p>
              </td>
            </tr></table>''')}
            {self._card('''<table cellpadding="0" cellspacing="0"><tr>
              <td width="40" style="font-size:24px;padding-right:14px;vertical-align:middle;">🌍</td>
              <td>
                <p style="margin:0 0 3px;font-size:14px;font-weight:800;color:#fff;">Multi-Language Support</p>
                <p style="margin:0;font-size:13px;color:#64748b;line-height:1.5;">English, Malay, Chinese, Tamil — plus Manglish mode built-in.</p>
              </td>
            </tr></table>''')}

            <!-- Quick start CTA -->
            {self._cta(onboarding_url, "📱 Continue Setup → Connect WhatsApp")}

            <p style="margin:0;font-size:12px;color:#475569;text-align:center;">
              Questions? WhatsApp us at <a href="https://wa.me/60174106981" style="color:#E3B457;text-decoration:none;">+60 17-410 6981</a>
            </p>
        """

        html_body = self._wrap("14-Day Free Trial Started ✓", body,
                               "You received this because you signed up for Bijou AI.")

        return self.send_email(to, subject, html_body)

    def send_trial_expiry_warning(
        self,
        to: str,
        business_name: str,
        days_remaining: int,
        upgrade_url: str,
    ) -> bool:
        """Send trial expiry warning (7d, 3d, 1d before expiry)."""

        if days_remaining == 7:
            emoji, urgency, color, border = "⏰", "friendly reminder", "#3b82f6", "#1d4ed8"
        elif days_remaining == 3:
            emoji, urgency, color, border = "⚠️", "important reminder", "#f59e0b", "#d97706"
        else:  # 1 day
            emoji, urgency, color, border = "🚨", "final reminder", "#ef4444", "#dc2626"

        day_word = "day" if days_remaining == 1 else "days"
        subject = f"{emoji} Your Bijou AI trial expires in {days_remaining} {day_word}!"

        body = f"""
            <div style="text-align:center;margin-bottom:24px;">
              <div style="display:inline-block;background:linear-gradient(135deg,{border},{color});border-radius:16px;padding:20px 36px;">
                <p style="margin:0;font-size:48px;">{emoji}</p>
              </div>
            </div>

            <h2 style="margin:0 0 8px;font-size:24px;font-weight:900;color:#fff;text-align:center;">
              Trial ends in {days_remaining} {day_word}
            </h2>
            <p style="margin:0 0 28px;font-size:15px;color:#94a3b8;line-height:1.7;text-align:center;">
              Hi <strong style="color:#e2e8f0;">{business_name}</strong>, this is a <strong style="color:{color};">{urgency}</strong>
              that your Bijou AI trial expires in <strong style="color:{color};">{days_remaining} {day_word}</strong>.
            </p>

            {self._card(f'''
            <p style="margin:0 0 10px;font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">What you'll lose access to</p>
            <table cellpadding="0" cellspacing="0">
              <tr><td style="padding:4px 0;font-size:13px;color:#cbd5e1;">✨ AI-powered 24/7 WhatsApp responses</td></tr>
              <tr><td style="padding:4px 0;font-size:13px;color:#cbd5e1;">🌍 Multi-language support (EN, MS, ZH, TA)</td></tr>
              <tr><td style="padding:4px 0;font-size:13px;color:#cbd5e1;">📊 Real-time analytics &amp; customer insights</td></tr>
              <tr><td style="padding:4px 0;font-size:13px;color:#cbd5e1;">⚡ Instant auto-reply to every customer</td></tr>
            </table>''', border_color=f"{border}55", bg="#0a1f19")}

            {self._cta(upgrade_url, "🚀 Upgrade Now — Keep AI Running", f"linear-gradient(135deg,{border},{color})")}

            {self._card('''
            <p style="margin:0;font-size:13px;color:#94a3b8;">
              💰 <strong style="color:#fff;">Special offer:</strong> Upgrade before your trial ends and get
              <strong style="color:#10b981;">20% off your first month</strong>.
              Not ready? Reply to this email — we'll help you find the right plan.
            </p>''', border_color="#059669", bg="#022c22")}
        """

        html_body = self._wrap("Trial Expiry Reminder", body,
                               "You received this because your Bijou AI trial is ending soon.")

        return self.send_email(to, subject, html_body)

    def send_trial_expired_email(
        self,
        to: str,
        business_name: str,
        upgrade_url: str,
    ) -> bool:
        """Send email when the trial period has ended."""

        subject = "😢 Your Bijou AI trial has ended — Reactivate now"

        first = business_name.split()[0] if business_name else "there"

        body = f"""
            <div style="text-align:center;margin-bottom:24px;">
              <div style="display:inline-block;font-size:56px;">😢</div>
            </div>

            <h2 style="margin:0 0 8px;font-size:24px;font-weight:900;color:#fff;text-align:center;">Your trial has ended</h2>
            <p style="margin:0 0 28px;font-size:15px;color:#94a3b8;line-height:1.7;text-align:center;">
              Hi <strong style="color:#e2e8f0;">{first}</strong>, your 14-day Bijou AI trial has ended.
              <strong style="color:#fff;">Your AI assistant is now paused.</strong>
            </p>

            {self._card(f'''
            <p style="margin:0 0 10px;font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">Choose your plan to reactivate</p>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr><td style="padding:6px 0;border-bottom:1px solid #1a3a2c;">
                <p style="margin:0;font-size:14px;color:#fff;"><strong>PRO</strong> <span style="color:#10b981;">RM299/mo</span></p>
                <p style="margin:0;font-size:12px;color:#64748b;">For small businesses &amp; solo operators</p>
              </td></tr>
              <tr><td style="padding:6px 0;border-bottom:1px solid #1a3a2c;">
                <p style="margin:0;font-size:14px;color:#fff;"><strong>GROWTH</strong> <span style="color:#10b981;">RM499/mo</span></p>
                <p style="margin:0;font-size:12px;color:#64748b;">For growing teams with higher volume</p>
              </td></tr>
              <tr><td style="padding:6px 0;">
                <p style="margin:0;font-size:14px;color:#fff;"><strong>ENTERPRISE</strong> <span style="color:#E3B457;">Custom</span></p>
                <p style="margin:0;font-size:12px;color:#64748b;">Unlimited scale, dedicated support, SLA</p>
              </td></tr>
            </table>''', bg="#0a1f19")}

            {self._cta(upgrade_url, "✅ Reactivate Bijou AI Now")}

            {self._card('''
            <p style="margin:0;font-size:13px;color:#94a3b8;">
              💌 Not ready yet? Your conversation data is safe for <strong style="color:#fff;">30 days</strong>.
              Reactivate anytime and pick up right where you left off.
              <a href="mailto:support@app.mybijou.xyz" style="color:#E3B457;text-decoration:none;">Reply to this email</a> if you need help choosing a plan.
            </p>''', border_color="#f59e0b55", bg="#1c1400")}
        """

        html_body = self._wrap("Trial Ended", body,
                               "You received this because your Bijou AI trial period has concluded.")

        return self.send_email(to, subject, html_body)

    def send_payment_confirmation(
        self,
        to: str,
        business_name: str,
        plan_name: str,
        amount: str,
        invoice_url: str,
    ) -> bool:
        """Send payment confirmation after a successful Stripe charge."""

        subject = f"✅ Payment confirmed — Welcome to Bijou AI {plan_name}!"

        first = business_name.split()[0] if business_name else "there"

        body = f"""
            <div style="text-align:center;margin-bottom:24px;">
              <div style="display:inline-block;background:linear-gradient(135deg,#064e3b,#065f46);border-radius:20px;padding:20px 28px;">
                <p style="margin:0;font-size:40px;">🎉</p>
              </div>
            </div>

            <h2 style="margin:0 0 6px;font-size:24px;font-weight:900;color:#fff;text-align:center;">Payment Confirmed!</h2>
            <p style="margin:0 0 28px;font-size:15px;color:#94a3b8;line-height:1.7;text-align:center;">
              Thank you <strong style="color:#e2e8f0;">{first}</strong>! Welcome to
              <strong style="color:#10b981;">Bijou AI {plan_name}</strong>. Your AI assistant is now fully active.
            </p>

            {self._card(f'''
            <p style="margin:0 0 12px;font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">📄 Payment Details</p>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr><td style="padding:6px 0;border-bottom:1px solid #1e293b;">
                <span style="font-size:13px;color:#64748b;">Plan</span>
                <span style="float:right;font-size:13px;color:#fff;font-weight:700;">{plan_name}</span>
              </td></tr>
              <tr><td style="padding:6px 0;border-bottom:1px solid #1e293b;">
                <span style="font-size:13px;color:#64748b;">Amount</span>
                <span style="float:right;font-size:13px;color:#10b981;font-weight:700;">{amount}</span>
              </td></tr>
              <tr><td style="padding:6px 0;">
                <span style="font-size:13px;color:#64748b;">Status</span>
                <span style="float:right;font-size:13px;color:#10b981;font-weight:700;">✅ Paid</span>
              </td></tr>
            </table>
            <div style="text-align:center;margin-top:16px;">
              <a href="{invoice_url}" style="font-size:13px;color:#E3B457;text-decoration:none;font-weight:600;">📥 Download Invoice →</a>
            </div>''', bg="#0a1f19")}

            {self._card('''
            <p style="margin:0 0 10px;font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">✨ What's now active for you</p>
            <table cellpadding="0" cellspacing="0">
              <tr><td style="padding:3px 0;font-size:13px;color:#cbd5e1;">🤖 AI responses powered by Google Gemini</td></tr>
              <tr><td style="padding:3px 0;font-size:13px;color:#cbd5e1;">🌍 Multi-language (EN, MS, ZH, TA)</td></tr>
              <tr><td style="padding:3px 0;font-size:13px;color:#cbd5e1;">📊 Real-time analytics dashboard</td></tr>
              <tr><td style="padding:3px 0;font-size:13px;color:#cbd5e1;">⚡ Smart human escalation</td></tr>
            </table>''', border_color="#059669", bg="#022c22")}

            {self._cta("https://app.mybijou.xyz/dashboard", "Open My Dashboard →")}
        """

        html_body = self._wrap("Payment Confirmed", body,
                               "You received this as a payment confirmation for your Bijou AI subscription.")

        return self.send_email(to, subject, html_body)

    def send_dashboard_access_email(
        self,
        to: str,
        business_name: str,
        dashboard_url: str,
    ) -> bool:
        """
        Send dashboard access link after subscription is activated.

        Args:
            to:            Recipient email address.
            business_name: Tenant's business name.
            dashboard_url: Full URL (with access token) to the tenant's dashboard.

        Returns:
            True if email sent successfully.
        """
        subject = "🚀 Your Bijou AI Dashboard is Ready!"

        first = business_name.split()[0] if business_name else "there"

        body = f"""
            <div style="text-align:center;margin-bottom:28px;">
              <div style="display:inline-block;background:linear-gradient(135deg,#0B3B2E,#0E4938);border-radius:20px;width:72px;height:72px;text-align:center;line-height:72px;font-size:36px;box-shadow:0 8px 32px rgba(227,180,87,0.35);">🚀</div>
            </div>

            <h2 style="margin:0 0 8px;font-size:24px;font-weight:900;color:#fff;text-align:center;">Your dashboard is live!</h2>
            <p style="margin:0 0 28px;font-size:15px;color:#94a3b8;line-height:1.7;text-align:center;">
              Hi <strong style="color:#e2e8f0;">{first}</strong>, your Bijou AI subscription is now
              <strong style="color:#10b981;">active</strong>. Click below to open your personalised dashboard.
            </p>

            {self._cta(dashboard_url, "Open My Dashboard →")}

            {self._card(f'''
            <p style="margin:0 0 8px;font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">Or paste this URL into your browser</p>
            <p style="margin:0;font-size:11px;color:#E3B457;word-break:break-all;">{dashboard_url}</p>''', bg="#0a1f19")}

            {self._card('''
            <p style="margin:0 0 10px;font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">What&apos;s in your dashboard</p>
            <table cellpadding="0" cellspacing="0">
              <tr><td style="padding:4px 0;font-size:13px;color:#cbd5e1;">📥 <strong style='color:#fff;'>Inbox</strong> — read &amp; reply to every customer chat</td></tr>
              <tr><td style="padding:4px 0;font-size:13px;color:#cbd5e1;">📊 <strong style='color:#fff;'>Analytics</strong> — message volume, response times, sentiment</td></tr>
              <tr><td style="padding:4px 0;font-size:13px;color:#cbd5e1;">🤖 <strong style='color:#fff;'>AI Controls</strong> — toggle AI, enable Manglish mode</td></tr>
              <tr><td style="padding:4px 0;font-size:13px;color:#cbd5e1;">📚 <strong style='color:#fff;'>Knowledge Base</strong> — upload FAQs to train your AI</td></tr>
            </table>''')}
        """

        html_body = self._wrap("Dashboard Access", body,
                               "You received this because your Bijou AI dashboard access was granted.")

        return self.send_email(to, subject, html_body)

    def send_login_magic_link(
        self,
        to: str,
        business_name: str,
        magic_link_url: str,
    ) -> bool:
        """
        Send a branded magic-link login email.

        Args:
            to:             Recipient email address.
            business_name:  Tenant's business name (used for personalisation).
            magic_link_url: Full magic-link URL (includes token + tenant_id).

        Returns:
            True if sent successfully.
        """
        subject = "Your Bijou AI Login Link"
        first = business_name.split()[0] if business_name else "there"

        body = f"""
            <div style="text-align:center;margin-bottom:28px;">
              <div style="display:inline-block;background:linear-gradient(135deg,#0B3B2E,#0E4938);border-radius:20px;width:72px;height:72px;text-align:center;line-height:72px;font-size:36px;box-shadow:0 8px 32px rgba(227,180,87,0.35);">🔐</div>
            </div>

            <h2 style="margin:0 0 8px;font-size:24px;font-weight:900;color:#fff;text-align:center;">Log in to your dashboard</h2>
            <p style="margin:0 0 28px;font-size:15px;color:#94a3b8;line-height:1.7;text-align:center;">
              Hi <strong style="color:#e2e8f0;">{first}</strong>, click the button below to securely access your Bijou AI dashboard.
              No password needed.
            </p>

            {self._cta(magic_link_url, "Log In to My Dashboard →")}

            {self._card(f'''
            <p style="margin:0 0 8px;font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">Link not working? Paste this into your browser</p>
            <p style="margin:0;font-size:11px;color:#E3B457;word-break:break-all;">{magic_link_url}</p>''', bg="#0a1f19")}

            {self._card('''
            <p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">Security reminder</p>
            <p style="margin:0;font-size:13px;color:#cbd5e1;">This link expires in <strong style="color:#f59e0b;">24 hours</strong> and can only be used once.
            If you did not request this, you can safely ignore this email.</p>''', border_color="#78350f", bg="#1c1007")}
        """

        html_body = self._wrap(
            "Bijou AI Login",
            body,
            "You received this because a login was requested for your Bijou AI account.",
        )
        text_body = (
            f"Log in to your Bijou AI dashboard\n\n"
            f"Hi {first},\n\n"
            f"Click the link below to access your dashboard:\n{magic_link_url}\n\n"
            f"This link expires in 24 hours. If you did not request this, ignore this email."
        )
        return self.send_email(to, subject, html_body, text_body)

    def send_internal_notification(
        self,
        subject: str,
        body: str,
    ) -> bool:
        """
        Send an internal notification email to EMAIL_NOTIFY address.
        Useful for new sign-ups, payment events, escalations etc.

        Args:
            subject: Notification subject.
            body:    Plain-text body.

        Returns:
            True if sent, False if EMAIL_NOTIFY not configured or send fails.
        """
        if not self.notify_address:
            logger.debug("EMAIL_NOTIFY not set — skipping internal notification")
            return False

        card_body = self._card(
            f"<pre style='margin:0;font-family:monospace;font-size:13px;color:#10b981;white-space:pre-wrap;line-height:1.6;'>{body}</pre>",
            border_color="#064e3b", bg="#022c22"
        )
        html_body = self._wrap("Internal Notification", card_body,
                               "Internal Bijou AI system notification — do not forward.")
        return self.send_email(self.notify_address, subject, html_body, body)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Return (or create) the global EmailService singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
