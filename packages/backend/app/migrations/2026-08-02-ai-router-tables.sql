-- 2026-08-02-ai-router-tables.sql
-- Phase 1: AI Model Router — budget tracking + call log tables
-- All in public schema with bjx_ prefix (Supabase free-tier PostgREST constraint)

CREATE TABLE IF NOT EXISTS public.bjx_ai_budgets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider text NOT NULL,
  scope text NOT NULL CHECK (scope IN ('daily', 'hourly', 'per_task')),
  scope_key text NOT NULL,                  -- ISO date for daily, hour-of-day for hourly, task name for per_task
  limit_usd numeric NOT NULL DEFAULT 0,
  spent_usd numeric NOT NULL DEFAULT 0,
  call_count int NOT NULL DEFAULT 0,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (provider, scope, scope_key)
);

CREATE INDEX IF NOT EXISTS idx_ai_budgets_scope
  ON public.bjx_ai_budgets (provider, scope, scope_key);

CREATE TABLE IF NOT EXISTS public.bjx_ai_calls (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider text NOT NULL,
  model text NOT NULL,
  task text NOT NULL,
  tokens_in int,
  tokens_out int,
  total_tokens int,
  latency_ms int,
  cost_usd numeric,
  fallback bool DEFAULT false,
  error text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_calls_created
  ON public.bjx_ai_calls (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_calls_task
  ON public.bjx_ai_calls (task, created_at DESC);

-- Seed today's daily budgets (MYT). Update these per provider as needed.
INSERT INTO public.bjx_ai_budgets (provider, scope, scope_key, limit_usd) VALUES
  ('minimax',   'daily', to_char((now() AT TIME ZONE 'Asia/Kuala_Lumpur')::date, 'YYYY-MM-DD'), 5.00),
  ('gemini',    'daily', to_char((now() AT TIME ZONE 'Asia/Kuala_Lumpur')::date, 'YYYY-MM-DD'), 0.00),
  ('openrouter','daily', to_char((now() AT TIME ZONE 'Asia/Kuala_Lumpur')::date, 'YYYY-MM-DD'), 2.00),
  ('omniroute', 'daily', to_char((now() AT TIME ZONE 'Asia/Kuala_Lumpur')::date, 'YYYY-MM-DD'), 1.00)
ON CONFLICT (provider, scope, scope_key) DO NOTHING;
