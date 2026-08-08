"""
Bijou AI — Email Templates (Python port)
========================================

Python mirror of `bijou_templates/email-templates/` (the JS source of truth).

This package provides the **shared shell** (BRAND constants + header/footer/wrap
helpers) so any Python caller can produce an email that matches the Signal Gem
brand without re-implementing the chrome. The 10 specific transactional
templates (welcome, verification, payment, etc.) live in the JS folder and are
NOT mirrored here yet — porting the detailed bodies is a follow-up task tracked
in rebrand-progress.md.

When you build a new transactional email from Python, use these helpers so the
chrome stays consistent with the JS templates and the rest of the brand.

Brand tokens (canonical — mirror of `--bj-*` in CSS):
  BJ_GREEN = #0B3B2E
  BJ_GOLD  = #E3B457
  BJ_CREAM = #F7F4EC
  BJ_INK   = #0A0A0A

Public API:
  BRAND              — dict of brand constants
  email_header(...)  — render the Signal Gem header row
  email_footer(...)  — render the Signal Gem footer row
  email_wrap(...)    — render the full <html> document
  cta_button(...)    — render a Signal Gem gold CTA
  divider            — horizontal divider row (str)
  support_row(...)   — "Need help?" contact block
"""

from .base import (
    BRAND,
    email_header,
    email_footer,
    email_wrap,
    cta_button,
    divider,
    support_row,
)

__all__ = [
    "BRAND",
    "email_header",
    "email_footer",
    "email_wrap",
    "cta_button",
    "divider",
    "support_row",
]
