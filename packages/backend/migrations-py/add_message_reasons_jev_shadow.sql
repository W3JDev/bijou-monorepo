-- 2026-09-26: TypeSafe Jev shadow mode (ENABLE_JEV_SHADOW, default off).
--
-- Stores Jev's routing answers (intent, tool, wants_human, legal_threat,
-- opt_out, ack_only, injection, frustration, buying_intent — values,
-- probabilities, confidence, latency) next to what the current code decided
-- for the same turn (handover, lead tier, tool). Log only; nothing reads this
-- to change behaviour. scripts/jev_shadow_report.py computes agreement.
--
-- Shape: {"jev": {"model", "latency_ms", "answers": {...}},
--         "current": {"lead_tier", "lead_handover", "handover", "tool"}}
--
-- Until this is applied, the shadow write fails and is logged at debug level;
-- replies are unaffected. NOT yet applied to any database.
alter table public.message_reasons
  add column if not exists jev_shadow jsonb;

create index if not exists idx_message_reasons_jev_shadow
  on public.message_reasons (created_at desc)
  where jev_shadow is not null;
