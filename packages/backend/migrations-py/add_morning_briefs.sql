-- 2026-09-26: Owner morning brief (src/core/morning_brief.py, ENABLE_MORNING_BRIEF)
-- One row per (tenant, tenant-local date). The primary key IS the idempotency
-- guard: every uvicorn worker races to INSERT, exactly one wins and sends.
-- Until this is applied the claim INSERT fails and no brief is sent (feature off).
create table if not exists public.morning_briefs (
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  brief_date date not null,
  status text not null default 'claimed' check (status in ('claimed','sent','failed')),
  stats jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  sent_at timestamptz,
  primary key (tenant_id, brief_date)
);
-- Service-role only, like shared_context: RLS on, no policies.
alter table public.morning_briefs enable row level security;
comment on table public.morning_briefs is
  'Owner morning brief send ledger (idempotency per tenant per local date). Service-role only.';
