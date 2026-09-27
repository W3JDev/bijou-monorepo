-- 2026-09-26: Per-tenant owner identity + WhatsApp approval queue.
--
-- NOT YET APPLIED to any database (owner deferred Supabase changes). The code
-- degrades gracefully until it is: owner detection falls back to
-- OWNER_WHATSAPP_JID, and approvals keep the old ActionGuard 'blocked' result.
-- Only read when ENABLE_OWNER_APPROVALS=true.

-- Owner phones (digits, E.164 without '+') that may approve actions and are
-- treated as the owner for this tenant. Empty = no approval requests (the tool
-- stays 'blocked'); approvals are NEVER sent to the global OWNER_WHATSAPP_JID.
-- message_reasons decision rows use plain INSERT, so no unique constraint needed.
-- tenants.owner_phone (single, from signup) is intentionally NOT reused: it is
-- not guaranteed to be a WhatsApp number the owner wants approvals on.
ALTER TABLE public.tenants
  ADD COLUMN IF NOT EXISTS owner_phones text[] NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS public.pending_actions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  chat_jid text NOT NULL,
  tool text NOT NULL,
  args jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  decided_at timestamptz,
  decided_by text  -- owner phone digits, or 'system' for expiry
);

CREATE INDEX IF NOT EXISTS idx_pending_actions_tenant_status
  ON public.pending_actions (tenant_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_pending_actions_expiry
  ON public.pending_actions (expires_at) WHERE status = 'pending';

-- Service-role only (no policies), same as shared_context / message_reasons.
-- Tenant isolation is enforced in the API layer (every query filters tenant_id).
ALTER TABLE public.pending_actions ENABLE ROW LEVEL SECURITY;
