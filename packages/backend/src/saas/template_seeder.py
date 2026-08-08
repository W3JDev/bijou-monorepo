"""
Bijou AI - Official Template Seeder
======================================

Seeds the `message_templates` table with Bijou-official templates for
a given tenant.

Features:
- Idempotent: skips templates that already exist
  (matched on name + source='bijou_official' + tenant_id).
- Jaccard similarity check for keyword_auto templates:
  warns if >0.75 overlap with any existing keyword_auto template.

Author: W3J Bijou AI
Version: 1.0.0
"""

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Jaccard Similarity
# ─────────────────────────────────────────────────────────────────────────────

def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """
    Compute Jaccard similarity between two keyword sets.

    Args:
        set_a: First set of keywords.
        set_b: Second set of keywords.

    Returns:
        Float in [0.0, 1.0] where 1.0 = identical sets.
    """
    if not set_a and not set_b:
        return 1.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

BIJOU_OFFICIAL_TEMPLATES: List[Dict[str, Any]] = [
    # ── Property Sales ────────────────────────────────────────────────────────
    {
        "name": "Request to Send Brochure",
        "category": "property_sales",
        "trigger_keywords": ["brochure", "pdf", "floor plan", "floorplan", "details", "more info", "layout"],
        "content": (
            "Sure! Let me send you the full brochure right away 📄 "
            "It includes floor plans, pricing, and full project details. One moment!"
        ),
        "trigger_mode": "keyword_auto",
        "source": "bijou_official",
    },
    {
        "name": "Schedule Site Visit",
        "category": "property_sales",
        "trigger_keywords": ["visit", "viewing", "site visit", "see the unit", "show unit", "boleh tengok"],
        "content": (
            "Great news — I'd love to arrange a viewing for you! 🏠\n\n"
            "Could you share:\n"
            "📅 Preferred date\n"
            "🕐 Preferred time\n"
            "👤 Your name\n\n"
            "I'll confirm the appointment with our consultant right away!"
        ),
        "trigger_mode": "keyword_auto",
        "source": "bijou_official",
    },
    {
        "name": "Post-Viewing Follow Up",
        "category": "property_sales",
        "trigger_keywords": None,
        "content": (
            "Hi {{name}}! Hope you enjoyed the viewing today 😊 "
            "What did you think of the unit? I'm happy to answer any questions "
            "or help with the next steps — booking, loan eligibility, or a second viewing!"
        ),
        "trigger_mode": "manual_only",
        "source": "bijou_official",
    },
    {
        "name": "Investor ROI Summary",
        "category": "property_sales",
        "trigger_keywords": ["investment", "rental yield", "roi", "returns", "rent out", "passive income"],
        "content": (
            "Great question on investment! Here's a quick overview 📊\n\n"
            "✅ Estimated rental yield: 4–6% p.a.\n"
            "✅ Projected capital appreciation based on location\n"
            "✅ Tenant demand: high (KLCC/MRT catchment)\n"
            "✅ Freehold — strong resale value\n\n"
            "Want me to send a full investment breakdown PDF?"
        ),
        "trigger_mode": "keyword_auto",
        "source": "bijou_official",
    },
    {
        "name": "Loan & Financing Info",
        "category": "property_sales",
        "trigger_keywords": ["loan", "financing", "mortgage", "bank", "downpayment", "down payment", "eligible", "afford"],
        "content": (
            "For financing, here's a general guide 💰\n\n"
            "🏦 Most banks offer up to 90% margin (first 2 properties)\n"
            "📋 You'll need: 3 months payslip, EPF statement, IC\n"
            "💳 Estimated monthly instalment available on request\n\n"
            "Would you like me to connect you with our panel banker for a free eligibility check?"
        ),
        "trigger_mode": "keyword_auto",
        "source": "bijou_official",
    },
    # ── F&B ───────────────────────────────────────────────────────────────────
    {
        "name": "Table Reservation Confirmation",
        "category": "fnb",
        "trigger_keywords": ["reserve", "reservation", "book table", "tempah meja", "sit", "seating"],
        "content": (
            "Sure! I can help you reserve a table 🍽️\n\n"
            "Please share:\n"
            "📅 Date\n"
            "🕐 Time\n"
            "👥 Number of guests\n"
            "👤 Name for reservation\n\n"
            "We'll confirm shortly!"
        ),
        "trigger_mode": "keyword_auto",
        "source": "bijou_official",
    },
    {
        "name": "Menu Inquiry Response",
        "category": "fnb",
        "trigger_keywords": ["menu", "food", "what do you serve", "dishes", "halal", "vegetarian", "vegan"],
        "content": (
            "Here's what we're known for! 🍜\n\n"
            "🔥 Our specialties include [DISHES]\n"
            "✅ Halal certified\n"
            "🌿 Vegetarian options available\n\n"
            "Would you like to see our full menu PDF or make a reservation?"
        ),
        "trigger_mode": "keyword_auto",
        "source": "bijou_official",
    },
    # ── Universal ─────────────────────────────────────────────────────────────
    {
        "name": "Business Hours",
        "category": "universal",
        "trigger_keywords": ["open", "hours", "operating hours", "what time", "bila buka", "close", "closed"],
        "content": (
            "Our operating hours are:\n"
            "🕘 Mon–Fri: [TIME]\n"
            "🕘 Sat: [TIME]\n"
            "❌ Sun & Public Holidays: Closed\n\n"
            "Feel free to WhatsApp us anytime — I'll get back to you during business hours!"
        ),
        "trigger_mode": "keyword_auto",
        "source": "bijou_official",
    },
    {
        "name": "Pricing Inquiry",
        "category": "universal",
        "trigger_keywords": ["price", "cost", "how much", "berapa", "rate", "fee", "charges"],
        "content": (
            "Great question! Pricing depends on your requirements 💬\n\n"
            "Could you share a bit more about what you're looking for? "
            "I'll get you the most accurate quote right away."
        ),
        "trigger_mode": "keyword_auto",
        "source": "bijou_official",
    },
    {
        "name": "Human Agent Takeover Notice",
        "category": "universal",
        "trigger_keywords": None,
        "content": (
            "I'm connecting you with one of our team members right now. "
            "They'll be with you shortly! 🙋 "
            "In the meantime, feel free to share any additional details."
        ),
        "trigger_mode": "manual_only",
        "source": "bijou_official",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SEEDER FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

async def seed_bijou_official_templates(
    supabase_client: Any,
    tenant_id: str,
) -> Dict[str, Any]:
    """
    Idempotently seed Bijou-official message templates for a tenant.

    For each template:
    1. Checks if a record with matching ``name``, ``source='bijou_official'``
       and ``tenant_id`` already exists — skips if so.
    2. For ``keyword_auto`` templates, performs Jaccard similarity check
       against all existing keyword_auto templates for the tenant.
       Logs a WARNING if similarity > 0.75 (does not abort).
    3. Inserts the template.

    Args:
        supabase_client: An initialised `supabase.Client` instance.
        tenant_id: UUID of the tenant to seed templates for.

    Returns:
        Dict with keys:
            - ``seeded``: number of templates inserted
            - ``skipped``: number of templates already present
            - ``warnings``: list of warning messages (keyword overlaps)
    """
    seeded = 0
    skipped = 0
    warnings: List[str] = []

    # Fetch all existing keyword_auto templates for this tenant (for Jaccard check)
    try:
        existing_result = (
            supabase_client.table("message_templates")
            .select("template_name, trigger_keywords")
            .eq("tenant_id", tenant_id)
            .eq("trigger_mode", "keyword_auto")
            .execute()
        )
        existing_kw_templates: List[Dict[str, Any]] = existing_result.data or []
    except Exception as exc:
        logger.error(f"❌ Failed to fetch existing templates for Jaccard check: {exc}")
        existing_kw_templates = []

    for tpl in BIJOU_OFFICIAL_TEMPLATES:
        name: str = tpl["name"]

        # ── Idempotency check ────────────────────────────────────────────────
        try:
            exists_result = (
                supabase_client.table("message_templates")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("template_name", name)
                .eq("source", "bijou_official")
                .execute()
            )
            if exists_result.data:
                logger.debug(f"⏭️ Skipping '{name}' — already exists for tenant {tenant_id}")
                skipped += 1
                continue
        except Exception as exc:
            logger.error(f"❌ Idempotency check failed for '{name}': {exc}")
            # Continue to attempt insert rather than silently skip
            pass

        # ── Jaccard overlap check (keyword_auto templates only) ───────────────
        if tpl.get("trigger_mode") == "keyword_auto" and tpl.get("trigger_keywords"):
            new_kw_set: Set[str] = set(
                kw.lower() for kw in (tpl["trigger_keywords"] or [])
            )
            for existing_tpl in existing_kw_templates:
                existing_kw_list = existing_tpl.get("trigger_keywords") or []
                existing_kw_set: Set[str] = set(
                    kw.lower() for kw in existing_kw_list
                )
                similarity = jaccard_similarity(new_kw_set, existing_kw_set)
                if similarity > 0.75:
                    warning_msg = (
                        f"⚠️ Keyword overlap WARNING: '{name}' has Jaccard "
                        f"similarity {similarity:.2f} with existing template "
                        f"'{existing_tpl['template_name']}'"
                    )
                    logger.warning(warning_msg)
                    warnings.append(warning_msg)

        # ── Build insert payload ─────────────────────────────────────────────
        payload: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "template_name": name,
            "category": tpl.get("category"),
            "template_content": tpl["content"],
            "trigger_mode": tpl["trigger_mode"],
            "source": tpl["source"],
        }
        if tpl.get("trigger_keywords") is not None:
            payload["trigger_keywords"] = tpl["trigger_keywords"]

        # ── Insert ───────────────────────────────────────────────────────────
        try:
            supabase_client.table("message_templates").insert(payload).execute()
            logger.info(f"✅ Seeded template '{name}' for tenant {tenant_id}")
            seeded += 1

            # Track new keyword_auto template for subsequent Jaccard checks
            if tpl.get("trigger_mode") == "keyword_auto":
                existing_kw_templates.append(
                    {"template_name": name, "trigger_keywords": tpl.get("trigger_keywords", [])}
                )
        except Exception as exc:
            logger.error(f"❌ Failed to seed template '{name}': {exc}")
            warnings.append(f"INSERT failed for '{name}': {exc}")

    summary = {"seeded": seeded, "skipped": skipped, "warnings": warnings}
    logger.info(
        f"📊 Template seeding complete for tenant {tenant_id}: "
        f"seeded={seeded}, skipped={skipped}, warnings={len(warnings)}"
    )
    return summary
