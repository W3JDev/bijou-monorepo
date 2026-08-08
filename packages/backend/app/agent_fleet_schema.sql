-- ============================================================================
-- Bijou Agent Fleet Schema (2026-07-30)
--
-- Per GROWTH-TO-50.md plan §3, builds the data layer for the 8-agent fleet:
--   SCOUT (always-on, cloud VM, cron)        -> prospects
--   SCORER (always-on, cloud VM, cron)       -> prospect_scores
--   LISTENER (always-on, cloud VM, cron)     -> listener_opportunities
--   PILLAR (content)                          -> content_drafts (pillar)
--   ATOMISER (content)                        -> content_drafts (atom)
--   PUBLISHER (content)                       -> publish_log
--   OUTREACH (human-gated, drafts only)       -> review_queue
--   FOLLOWUP (human-gated, drafts only)       -> review_queue
--
-- Lives in `bijou_agents` schema (NOT `public`) so it can't collide with
-- the existing storefront/lead-capture tables. Service-role key required
-- for all writes; anon/authenticated have no access by default.
--
-- HARD RULES (per plan §3 + §0):
--   * No scraping of personal data. Business listings only.
--   * OUTREACH/FOLLOWUP write to review_queue. A human clicks send.
--   * Never cold WhatsApp. Inbound only, always.
-- ============================================================================

create schema if not exists bijou_agents;
set search_path = bijou_agents, public;

-- ============================================================================
-- 1. prospects — businesses enumerated by SCOUT
-- ============================================================================
create table if not exists prospects (
  id uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null,

  -- Source attribution
  source text not null,            -- 'google_maps_places' | 'instagram_search' | 'facebook_pages' | 'manual_seed'
  source_id text,                  -- provider-side ID for dedup
  source_url text,                 -- canonical link to listing

  -- Business info (no PII — public listing data only)
  business_name text not null,
  vertical text,                   -- 'aesthetic_clinic' | 'dental_clinic' | 'property_agent' | 'restaurant' | 'salon'
  area text,                       -- Klang Valley sub-area: 'KLCC' | 'Mont Kiara' | 'Bangsar' | 'PJ' | etc.
  address text,
  city text default 'Kuala Lumpur',
  country text default 'Malaysia',

  -- Online presence (handles, not personal phone numbers)
  instagram_handle text,
  facebook_page_url text,
  website text,
  has_whatsapp_business boolean default false,
  has_booking_link boolean default false,

  -- Evidence of missed-enquiry pain (public indicators only)
  evidence_notes text,             -- "Posts 3+ 'DM us' CTAs unanswered" — public signal
  estimated_review_count int,

  -- Lifecycle
  status text not null default 'new',  -- 'new' | 'scored' | 'queued' | 'touched' | 'replied' | 'demoed' | 'customer' | 'rejected'
  rejection_reason text,

  -- Dedupe: (source, source_id) must be unique
  unique (source, source_id)
);
create index if not exists idx_prospects_vertical on prospects(vertical);
create index if not exists idx_prospects_area on prospects(area);
create index if not exists idx_prospects_status on prospects(status);
create index if not exists idx_prospects_created_at on prospects(created_at desc);

-- ============================================================================
-- 2. prospect_scores — output of SCORER (one row per scored prospect)
-- ============================================================================
create table if not exists prospect_scores (
  id uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  prospect_id uuid not null references prospects(id) on delete cascade,

  -- 0-100 fit score
  fit_score int not null check (fit_score between 0 and 100),

  -- Reasons (human-readable, explainable)
  appointment_driven boolean not null,  -- weight: 30
  active_whatsapp boolean not null,      -- weight: 20
  owner_reachable boolean not null,      -- weight: 20
  evidence_missed_enquiries boolean not null, -- weight: 20
  active_online_presence boolean not null,    -- weight: 10

  -- Model + version that produced the score
  model text not null,                   -- 'hermes' | 'minimax' | 'claude-haiku-4-5' | 'claude-sonnet-4-5'
  prompt_version text not null,

  -- Free-form reasoning
  reasoning text
);
create index if not exists idx_prospect_scores_prospect on prospect_scores(prospect_id);
create index if not exists idx_prospect_scores_fit on prospect_scores(fit_score desc);

-- ============================================================================
-- 3. touches — every outreach attempt (approved sends only)
-- ============================================================================
create table if not exists touches (
  id uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  prospect_id uuid not null references prospects(id) on delete cascade,

  channel text not null,                  -- 'email' | 'instagram_dm' | 'linkedin' | 'whatsapp_inbound_only'
  direction text not null,                -- 'outbound' (we sent) | 'inbound' (they replied)
  message_kind text not null,             -- 'first_touch' | 'followup_1' | 'followup_2' | 'reply'

  -- The actual content (anonymized: no passwords, no api keys, no internal notes)
  subject text,
  body_excerpt text,                      -- first 500 chars, not full body

  -- Who/when
  sent_by text not null,                  -- 'founder' | 'agent_outreach_draft_approved'
  approved_by text,                       -- founder email for traceability
  approved_at timestamp with time zone,
  sent_at timestamp with time zone,

  -- Response tracking
  replied_at timestamp with time zone,
  reply_kind text,                        -- 'interested' | 'not_now' | 'unsubscribe' | 'question'
  reply_notes text
);
create index if not exists idx_touches_prospect on touches(prospect_id);
create index if not exists idx_touches_channel on touches(channel);
create index if not exists idx_touches_sent_at on touches(sent_at desc);

-- ============================================================================
-- 4. content_drafts — output of PILLAR + ATOMISER (one row per draft asset)
-- ============================================================================
create table if not exists content_drafts (
  id uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null,

  kind text not null,                     -- 'pillar_longform' | 'social_post' | 'reel_script' | 'email' | 'whatsapp_broadcast'
  language text not null,                 -- 'en' | 'ms' | 'manglish' | 'zh' | 'ta'
  platform text,                          -- 'facebook' | 'instagram' | 'linkedin' | 'tiktok' | 'email' | 'whatsapp' | 'blog'

  title text,
  body text not null,
  hashtags text[],
  media_url text,                         -- optional media asset (CDN URL after publish)
  word_count int,

  -- Pipeline state
  status text not null default 'draft',   -- 'draft' | 'reviewed' | 'approved' | 'scheduled' | 'published' | 'rejected'
  reviewed_by text,
  reviewed_at timestamp with time zone,
  approved_by text,
  approved_at timestamp with time zone,
  scheduled_for timestamp with time zone,
  published_at timestamp with time zone,

  -- Trace
  pillar_id uuid references content_drafts(id),  -- for atoms: the pillar they were derived from
  model text not null,                    -- which model wrote it
  prompt_version text not null
);
create index if not exists idx_content_drafts_kind on content_drafts(kind);
create index if not exists idx_content_drafts_status on content_drafts(status);
create index if not exists idx_content_drafts_scheduled on content_drafts(scheduled_for);
create index if not exists idx_content_drafts_pillar on content_drafts(pillar_id);

-- ============================================================================
-- 5. review_queue — HUMAN-GATED. Nothing reaches a prospect without approval.
--    This is the canonical safety layer for the plan §3 hard rule.
-- ============================================================================
create table if not exists review_queue (
  id uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,

  -- What the agent produced
  item_type text not null,                -- 'outreach_dm' | 'outreach_email' | 'followup' | 'whatsapp_broadcast' | 'pubsub_post'
  payload jsonb not null,                 -- the actual content + recipient (anon-ready)

  -- Trace
  source_agent text not null,             -- 'scout' | 'outreach' | 'followup' | 'pillar' | 'atomiser'
  source_prospect_id uuid references prospects(id),
  source_pillar_id uuid references content_drafts(id),
  source_model text not null,

  -- Approval state — human clicks Approve to send
  status text not null default 'pending', -- 'pending' | 'approved' | 'rejected' | 'sent' | 'failed' | 'expired'
  priority int default 50,                -- 0-100, higher = more urgent

  approved_by text,
  approved_at timestamp with time zone,
  rejection_reason text,
  sent_at timestamp with time zone,
  send_error text,

  -- Expire stale drafts after 7 days
  expires_at timestamp with time zone default (timezone('utc'::text, now()) + interval '7 days')
);
create index if not exists idx_review_queue_status on review_queue(status);
create index if not exists idx_review_queue_priority on review_queue(priority desc, created_at);
create index if not exists idx_review_queue_expires on review_queue(expires_at);

-- ============================================================================
-- 6. listener_opportunities — real-time opportunities from LISTENER
-- ============================================================================
create table if not exists listener_opportunities (
  id uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,

  source text not null,                   -- 'facebook_group' | 'r_malaysia' | 'lowyat' | 'twitter_my'
  source_url text not null,
  source_group text,                      -- group/subreddit name

  -- The post content (no PII; just the public post text)
  post_excerpt text not null,
  post_author_handle text,                -- public handle, NOT personal phone/email

  -- Pain signals detected
  pain_signals text[],                    -- ['missed_messages', 'front_desk_overload', 'booking_gaps']
  match_score int check (match_score between 0 and 100),

  -- Action
  status text not null default 'new',     -- 'new' | 'queued' | 'replied' | 'dismissed'
  queued_review_id uuid references review_queue(id),

  -- Dedup
  unique (source, source_url)
);
create index if not exists idx_listener_status on listener_opportunities(status);
create index if not exists idx_listener_match on listener_opportunities(match_score desc);

-- ============================================================================
-- 7. publish_log — every content publish (after human approval)
-- ============================================================================
create table if not exists publish_log (
  id uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,

  content_draft_id uuid references content_drafts(id),
  platform text not null,
  external_id text,                       -- platform-side post ID
  external_url text,
  scheduled_for timestamp with time zone,
  published_at timestamp with time zone,
  status text not null,                   -- 'scheduled' | 'published' | 'failed'
  error text
);
create index if not exists idx_publish_log_draft on publish_log(content_draft_id);
create index if not exists idx_publish_log_status on publish_log(status);

-- ============================================================================
-- 8. agent_runs — observability for every agent invocation
-- ============================================================================
create table if not exists agent_runs (
  id uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  finished_at timestamp with time zone,

  agent_name text not null,               -- 'scout' | 'scorer' | 'listener' | 'pillar' | 'atomiser' | 'publisher' | 'outreach' | 'followup'
  trigger_kind text not null,             -- 'cron' | 'manual' | 'event'
  status text not null,                   -- 'running' | 'ok' | 'error' | 'rate_limited'

  -- Counts
  items_in int,                           -- inputs (e.g. businesses to score)
  items_out int,                          -- outputs (e.g. prospects scored)
  cost_estimate_usd numeric(10,6),        -- LLM cost
  error text,

  model text,
  prompt_version text
);
create index if not exists idx_agent_runs_agent on agent_runs(agent_name);
create index if not exists idx_agent_runs_status on agent_runs(status);
create index if not exists idx_agent_runs_created on agent_runs(created_at desc);

-- ============================================================================
-- Row Level Security — service role only (no public access by default)
-- ============================================================================
alter table prospects enable row level security;
alter table prospect_scores enable row level security;
alter table touches enable row level security;
alter table content_drafts enable row level security;
alter table review_queue enable row level security;
alter table listener_opportunities enable row level security;
alter table publish_log enable row level security;
alter table agent_runs enable row level security;

-- Explicit no-public-access policies (deny all for anon/authenticated)
-- Service role bypasses RLS, so all reads/writes via API must use the service key.
-- The storefront OUTREACH review-queue UI authenticates the founder via the
-- existing /api/auth flow and uses service key server-side.
do $$
declare
  t text;
begin
  for t in
    select unnest(array[
      'prospects','prospect_scores','touches','content_drafts',
      'review_queue','listener_opportunities','publish_log','agent_runs'
    ])
  loop
    execute format('drop policy if exists %I_anon_all on bijou_agents.%I', t, t);
    execute format('create policy %I_anon_all on bijou_agents.%I for all to anon, authenticated using (false) with check (false)', t, t);
  end loop;
end $$;

-- ============================================================================
-- Seed a single demo prospect to prove the schema works (DELETE before prod)
-- ============================================================================
insert into prospects (source, source_id, source_url, business_name, vertical, area, city, has_whatsapp_business)
values (
  'manual_seed', 'demo-001', 'https://mybijou.xyz',
  'Demo Aesthetic Clinic (Klang Valley)',
  'aesthetic_clinic', 'KLCC', 'Kuala Lumpur', true
)
on conflict (source, source_id) do nothing;
