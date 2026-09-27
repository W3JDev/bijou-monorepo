"""Agreement between Jev shadow answers and what current code decided.

Reads public.message_reasons.jev_shadow (written when ENABLE_JEV_SHADOW=true;
needs migrations-py/add_message_reasons_jev_shadow.sql applied) and prints,
per decision, how often Jev agrees with the current code.

    python scripts/jev_shadow_report.py [--tenant-id UUID] [--limit 1000] [--threshold 0.5]

Comparisons (only rows where both sides have a value count):
  handover  current HandoverSystem.should_escalate  vs  Jev wants_human > threshold
  lead      current lead tier in warm/hot/qualified vs  Jev buying_intent rounds to >= 2
  tool      current tool (None = "none")            vs  Jev tool choice
"""
from __future__ import annotations

import argparse
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple

HOT_TIERS = {"warm", "hot", "qualified"}


def _val(jev: Dict[str, Any], qid: str) -> Any:
    return ((jev.get("answers") or {}).get(qid) or {}).get("value")


def pairs(record: Dict[str, Any], threshold: float = 0.5) -> Dict[str, Tuple[Any, Any]]:
    """(current, jev) per decision for one jev_shadow record; missing sides omitted."""
    jev, cur = record.get("jev") or {}, record.get("current") or {}
    out: Dict[str, Tuple[Any, Any]] = {}
    wh = _val(jev, "wants_human")
    if cur.get("handover") is not None and wh is not None:
        out["handover"] = (bool(cur["handover"]), wh > threshold)
    bi = _val(jev, "buying_intent")
    if cur.get("lead_tier") is not None and bi is not None:
        out["lead"] = (cur["lead_tier"] in HOT_TIERS, round(bi) >= 2)
    tool = _val(jev, "tool")
    if cur.get("tool") is not None and tool is not None:
        out["tool"] = (cur["tool"] or "none", tool)
    return out


def agreement(records: Iterable[Dict[str, Any]], threshold: float = 0.5) -> Dict[str, Dict[str, Any]]:
    stats: Dict[str, Dict[str, Any]] = {}
    for rec in records:
        for name, (cur, jev) in pairs(rec, threshold).items():
            s = stats.setdefault(name, {"n": 0, "agree": 0, "jev_only": 0, "current_only": 0})
            s["n"] += 1
            if cur == jev:
                s["agree"] += 1
            elif jev is True:
                s["jev_only"] += 1
            elif cur is True:
                s["current_only"] += 1
    for s in stats.values():
        s["rate"] = s["agree"] / s["n"] if s["n"] else None
    return stats


def fetch(tenant_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
    from supabase import create_client

    url = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise SystemExit("SUPABASE_URL and a service-role key must be set")
    q = (
        create_client(url, key).table("message_reasons")
        .select("jev_shadow")
        .not_.is_("jev_shadow", "null")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if tenant_id:
        q = q.eq("tenant_id", tenant_id)
    return [r["jev_shadow"] for r in (q.execute().data or []) if r.get("jev_shadow")]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--tenant-id")
    p.add_argument("--limit", type=int, default=1000)
    p.add_argument("--threshold", type=float, default=0.5, help="wants_human noul threshold")
    args = p.parse_args()

    records = fetch(args.tenant_id, args.limit)
    lat = sorted(r["jev"]["latency_ms"] for r in records if (r.get("jev") or {}).get("latency_ms") is not None)
    print(f"rows with jev_shadow: {len(records)}")
    if lat:
        print(f"jev latency ms: p50={lat[len(lat) // 2]} p95={lat[min(len(lat) - 1, int(len(lat) * 0.95))]} max={lat[-1]}")
    stats = agreement(records, args.threshold)
    for name in ("handover", "lead", "tool"):
        s = stats.get(name)
        if not s:
            print(f"{name:9s} n/a (no rows with both sides recorded)")
            continue
        print(f"{name:9s} agree {s['agree']}/{s['n']} = {s['rate']:.1%}  "
              f"(jev-only yes {s['jev_only']}, current-only yes {s['current_only']})")


if __name__ == "__main__":
    main()
