-- ============================================================================
-- BASELINE SCHEMA — public
-- ============================================================================
-- Generated 2026-09-06 from the LIVE Supabase project (lrwzlujomukzjykafmic)
-- via the Supabase MCP, reading pg_catalog directly.
--
-- WHY THIS FILE EXISTS
-- Until now the repository could not rebuild its own database. The application
-- queried 79 tables; the .sql files in this folder created 13. The other 66 —
-- including tenants, tenant_users, messages and conversations — existed only as
-- live state in one cloud project. That meant no disaster recovery, no staging,
-- no schema review, and no way to run the product locally.
--
-- WHAT IT CONTAINS
-- The real public schema: 154 tables, 1797 columns, with the actual types,
-- defaults and NOT NULL constraints read from pg_catalog — not inferred.
-- Primary keys, foreign keys, indexes, RLS state and policies follow in
-- their own sections at the end.
--
-- NOTE ON SCOPE
-- This project's `public` schema is shared by more than Bijou. It also holds
-- an unrelated chat app (User/Conversation/Message/SearchRun), a meetings and
-- agent-ops suite (meeting_*, agent_*, action_items), the outbound prospecting
-- pipeline (bjx_*), and whatsmeow_* session tables owned by the WhatsApp
-- bridge. They are included because they are genuinely part of the schema and
-- omitting them would make this file lie about what a restore produces.
--
-- ORDER OF APPLICATION
--   0. sequences   1. tables      2. primary keys   3. unique constraints
--   4. foreign keys   5. indexes   6. functions/views/triggers   7. RLS
--
-- Sequences come FIRST because seven columns default to nextval() on them and
-- CREATE TABLE fails otherwise. That was caught by applying this file to an
-- empty database, not by reading it.
--
-- Foreign-key statements tolerate invalid_schema_name because several reference
-- auth.users, which exists in a real Supabase project but not in a bare
-- Postgres. Applying to plain Postgres therefore gives you the public schema
-- minus those links, rather than aborting.
-- Tables first with FKs deferred to a later section, so table order does not
-- matter and the file is re-runnable.
--
-- Regenerate with ops/local/devschema/dump-baseline.sh
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";


-- ─────────────────────────── SEQUENCES ────────────────────────────────────
-- Must precede the tables: seven columns default to nextval() on these, and
-- CREATE TABLE fails with `relation "..._id_seq" does not exist` otherwise.
-- Caught by applying this file to an empty database rather than by reading it.
CREATE SEQUENCE IF NOT EXISTS public.agent_activity_id_seq AS bigint START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 NO CYCLE;
CREATE SEQUENCE IF NOT EXISTS public.call_logs_id_seq AS integer START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 NO CYCLE;
CREATE SEQUENCE IF NOT EXISTS public.customer_activity_id_seq AS integer START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 NO CYCLE;
CREATE SEQUENCE IF NOT EXISTS public.follow_ups_id_seq AS bigint START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 NO CYCLE;
CREATE SEQUENCE IF NOT EXISTS public.help_ticket_seq AS bigint START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 NO CYCLE;
CREATE SEQUENCE IF NOT EXISTS public.lead_followups_id_seq AS integer START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 NO CYCLE;
CREATE SEQUENCE IF NOT EXISTS public.link_clicks_id_seq AS bigint START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 NO CYCLE;
CREATE SEQUENCE IF NOT EXISTS public.owner_devices_id_seq AS integer START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 NO CYCLE;
CREATE SEQUENCE IF NOT EXISTS public.short_links_id_seq AS bigint START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 NO CYCLE;
CREATE SEQUENCE IF NOT EXISTS public.team_activity_id_seq AS integer START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 NO CYCLE;
CREATE SEQUENCE IF NOT EXISTS public.usage_tracking_id_seq AS bigint START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 NO CYCLE;

-- ─────────────────────────────── TABLES ────────────────────────────────────

-- ── 10-tables-1 ──
CREATE TABLE IF NOT EXISTS public."Conversation" (
  id text DEFAULT (gen_random_uuid())::text NOT NULL,
  "userId" text NOT NULL,
  title text,
  slug text,
  "createdAt" timestamp with time zone DEFAULT now(),
  "updatedAt" timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public."Message" (
  id text DEFAULT (gen_random_uuid())::text NOT NULL,
  "conversationId" text NOT NULL,
  role text NOT NULL,
  content text NOT NULL,
  "createdAt" timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public."SearchRun" (
  id text DEFAULT (gen_random_uuid())::text NOT NULL,
  "conversationId" text NOT NULL,
  "normalizedQuery" text NOT NULL,
  "originalQuery" text NOT NULL,
  "sourcesJson" jsonb NOT NULL,
  "answerText" text,
  "followupsJson" jsonb,
  "createdAt" timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public."User" (
  id text DEFAULT (gen_random_uuid())::text NOT NULL,
  email text NOT NULL,
  name text NOT NULL,
  provider text NOT NULL,
  "supabaseId" text NOT NULL,
  "createdAt" timestamp with time zone DEFAULT now(),
  "updatedAt" timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.action_items (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  meeting_id uuid,
  owner_id uuid,
  owner_name text NOT NULL,
  description text NOT NULL,
  deadline date,
  priority text DEFAULT 'medium'::text,
  status text DEFAULT 'open'::text,
  done_definition text,
  blocker_description text,
  reminder_sent boolean DEFAULT false,
  reminder_count integer DEFAULT 0,
  completed_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  assigned_to uuid,
  department_id uuid,
  source_type text,
  source_id text,
  extracted_by text,
  task_id uuid,
  due_date date
);

CREATE TABLE IF NOT EXISTS public.admin_audit_log (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  actor_id uuid,
  actor_email text,
  actor_type text DEFAULT 'admin'::text NOT NULL,
  action text NOT NULL,
  target_type text,
  target_id text,
  metadata jsonb DEFAULT '{}'::jsonb,
  ip inet,
  user_agent text,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.agent_activity (
  id bigint DEFAULT nextval('agent_activity_id_seq'::regclass) NOT NULL,
  connection_id uuid NOT NULL,
  event_type text NOT NULL,
  title text,
  description text,
  severity text DEFAULT 'info'::text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.agent_commands (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  agent_id text NOT NULL,
  command text NOT NULL,
  payload jsonb DEFAULT '{}'::jsonb,
  status text DEFAULT 'pending'::text NOT NULL,
  issued_by uuid,
  result jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  completed_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS public.agent_connections (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  user_id uuid NOT NULL,
  name text NOT NULL,
  agent_type text NOT NULL,
  endpoint_url text NOT NULL,
  auth_type text DEFAULT 'basic'::text,
  auth_credentials text,
  is_active boolean DEFAULT true,
  poll_interval_seconds integer DEFAULT 300,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.agent_conversations (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  user_id uuid NOT NULL,
  agent_id text NOT NULL,
  title text,
  status text DEFAULT 'active'::text NOT NULL,
  department_id uuid,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.agent_messages (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  conversation_id uuid NOT NULL,
  sender_type text NOT NULL,
  sender_id text NOT NULL,
  agent_id text,
  content text NOT NULL,
  content_type text DEFAULT 'text'::text NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.agent_runs (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  session_id text,
  task_description text,
  model text,
  provider text,
  input_tokens integer,
  output_tokens integer,
  cost_usd numeric(10,8),
  duration_seconds numeric(8,2),
  category text,
  outcome text,
  output_summary text,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.agent_status (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  connection_id uuid NOT NULL,
  status text DEFAULT 'unknown'::text,
  response_time_ms integer,
  details jsonb DEFAULT '{}'::jsonb,
  plugins jsonb DEFAULT '[]'::jsonb,
  devices jsonb DEFAULT '[]'::jsonb,
  metrics jsonb DEFAULT '{}'::jsonb,
  error_message text,
  checked_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.agent_trajectory (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  chat_jid text NOT NULL,
  step_no integer NOT NULL,
  thought text,
  tool text,
  args jsonb,
  result jsonb,
  ts timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.analytics (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  date date NOT NULL,
  total_messages integer DEFAULT 0,
  ai_responses integer DEFAULT 0,
  escalations integer DEFAULT 0,
  avg_response_time_ms integer,
  avg_confidence_score real,
  language_breakdown jsonb DEFAULT '{}'::jsonb,
  emotion_breakdown jsonb DEFAULT '{}'::jsonb,
  api_calls integer DEFAULT 0,
  estimated_cost_usd real DEFAULT 0,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.api_keys (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  key_name text NOT NULL,
  key_hash text NOT NULL,
  scopes text[] DEFAULT ARRAY['read'::text, 'write'::text],
  rate_limit_per_hour integer DEFAULT 1000,
  is_active boolean DEFAULT true,
  last_used_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  expires_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS public.audit_log (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  actor_id uuid,
  actor_email text,
  actor_type text NOT NULL,
  action text NOT NULL,
  target_type text,
  target_id text,
  metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
  ip text,
  user_agent text,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.availability_overrides (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  date date NOT NULL,
  start_time time without time zone,
  end_time time without time zone,
  is_available boolean DEFAULT false,
  reason text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.bjx_agent_runs (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  finished_at timestamp with time zone,
  agent_name text NOT NULL,
  trigger_kind text NOT NULL,
  status text NOT NULL,
  items_in integer,
  items_out integer,
  cost_estimate_usd numeric(10,6),
  error text,
  model text,
  prompt_version text
);

CREATE TABLE IF NOT EXISTS public.bjx_content_drafts (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  kind text NOT NULL,
  language text NOT NULL,
  platform text,
  title text,
  body text NOT NULL,
  hashtags text[],
  media_url text,
  word_count integer,
  status text DEFAULT 'draft'::text NOT NULL,
  reviewed_by text,
  reviewed_at timestamp with time zone,
  approved_by text,
  approved_at timestamp with time zone,
  scheduled_for timestamp with time zone,
  published_at timestamp with time zone,
  pillar_id uuid,
  model text NOT NULL,
  prompt_version text NOT NULL
);

CREATE TABLE IF NOT EXISTS public.bjx_listener_opportunities (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  source text NOT NULL,
  source_url text NOT NULL,
  source_group text,
  post_excerpt text NOT NULL,
  post_author_handle text,
  pain_signals text[],
  match_score integer,
  status text DEFAULT 'new'::text NOT NULL,
  queued_review_id uuid
);

CREATE TABLE IF NOT EXISTS public.bjx_prospect_scores (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  prospect_id uuid NOT NULL,
  fit_score integer NOT NULL,
  appointment_driven boolean NOT NULL,
  active_whatsapp boolean NOT NULL,
  owner_reachable boolean NOT NULL,
  evidence_missed_enquiries boolean NOT NULL,
  active_online_presence boolean NOT NULL,
  model text NOT NULL,
  prompt_version text NOT NULL,
  reasoning text
);

CREATE TABLE IF NOT EXISTS public.bjx_prospects (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  source text NOT NULL,
  source_id text,
  source_url text,
  business_name text NOT NULL,
  vertical text,
  area text,
  address text,
  city text DEFAULT 'Kuala Lumpur'::text,
  country text DEFAULT 'Malaysia'::text,
  instagram_handle text,
  facebook_page_url text,
  website text,
  has_whatsapp_business boolean DEFAULT false,
  has_booking_link boolean DEFAULT false,
  evidence_notes text,
  estimated_review_count integer,
  status text DEFAULT 'new'::text NOT NULL,
  rejection_reason text
);

CREATE TABLE IF NOT EXISTS public.bjx_publish_log (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  content_draft_id uuid,
  platform text NOT NULL,
  external_id text,
  external_url text,
  scheduled_for timestamp with time zone,
  published_at timestamp with time zone,
  status text NOT NULL,
  error text
);

CREATE TABLE IF NOT EXISTS public.bjx_review_queue (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  item_type text NOT NULL,
  payload jsonb NOT NULL,
  source_agent text NOT NULL,
  source_prospect_id uuid,
  source_pillar_id uuid,
  source_model text NOT NULL,
  status text DEFAULT 'pending'::text NOT NULL,
  priority integer DEFAULT 50,
  approved_by text,
  approved_at timestamp with time zone,
  rejection_reason text,
  sent_at timestamp with time zone,
  send_error text,
  expires_at timestamp with time zone DEFAULT (now() + '7 days'::interval)
);

CREATE TABLE IF NOT EXISTS public.bjx_touches (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  prospect_id uuid NOT NULL,
  channel text NOT NULL,
  direction text NOT NULL,
  message_kind text NOT NULL,
  subject text,
  body_excerpt text,
  sent_by text NOT NULL,
  approved_by text,
  approved_at timestamp with time zone,
  sent_at timestamp with time zone,
  replied_at timestamp with time zone,
  reply_kind text,
  reply_notes text
);

CREATE TABLE IF NOT EXISTS public.blocked_numbers (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid,
  customer_jid text NOT NULL,
  phone_number text NOT NULL,
  reason text DEFAULT 'owner_block'::text NOT NULL,
  block_type text DEFAULT 'permanent'::text,
  expires_at timestamp with time zone,
  blocked_by text NOT NULL,
  blocked_at timestamp with time zone DEFAULT now(),
  unblocked_at timestamp with time zone,
  unblocked_by text,
  owner_instruction text,
  is_active boolean DEFAULT true,
  notes text
);

CREATE TABLE IF NOT EXISTS public.business_profiles (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  business_name text,
  owner_name text,
  handover_contacts jsonb DEFAULT '[]'::jsonb,
  business_hours text,
  notes text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  business_type text
);

CREATE TABLE IF NOT EXISTS public.calendar_events (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  user_id uuid NOT NULL,
  google_event_id text NOT NULL,
  title text,
  description text,
  start_time timestamp with time zone,
  end_time timestamp with time zone,
  attendees jsonb DEFAULT '[]'::jsonb,
  location text,
  meet_link text,
  recurrence text,
  ai_meeting_prep text,
  ai_suggested_agenda jsonb DEFAULT '[]'::jsonb,
  synced_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.call_availability (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  day_of_week integer NOT NULL,
  start_time time without time zone NOT NULL,
  end_time time without time zone NOT NULL,
  timezone text DEFAULT 'Asia/Kuala_Lumpur'::text,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.call_bookings (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  customer_jid text NOT NULL,
  customer_name text,
  customer_phone text,
  scheduled_time timestamp with time zone NOT NULL,
  scheduled_date date,
  duration_minutes integer DEFAULT 30,
  call_type text DEFAULT 'consultation'::text,
  status text DEFAULT 'scheduled'::text,
  notes text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  reminder_sent boolean DEFAULT false,
  confirmation_sent boolean DEFAULT false
);

CREATE TABLE IF NOT EXISTS public.call_logs (
  id integer DEFAULT nextval('call_logs_id_seq'::regclass) NOT NULL,
  ts timestamp with time zone DEFAULT now(),
  source text,
  caller_name text,
  caller_email text,
  verified_name text,
  verified_email text,
  staff_matched integer,
  email_mismatch boolean,
  ticket_key text,
  ticket_summary text,
  ticket_reporter text,
  ticket_creator text,
  error text,
  raw_request jsonb
);

CREATE TABLE IF NOT EXISTS public.call_settings (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  timezone text DEFAULT 'Asia/Kuala_Lumpur'::text,
  buffer_minutes integer DEFAULT 15,
  max_calls_per_day integer DEFAULT 8,
  max_calls_per_hour integer DEFAULT 2,
  advance_booking_days integer DEFAULT 30,
  allow_same_day_booking boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.call_types (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  name text NOT NULL,
  duration_minutes integer DEFAULT 30,
  description text,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.campaign_analytics (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  campaign_id uuid NOT NULL,
  date date NOT NULL,
  messages_queued integer DEFAULT 0,
  messages_sent integer DEFAULT 0,
  messages_delivered integer DEFAULT 0,
  messages_failed integer DEFAULT 0,
  messages_read integer DEFAULT 0,
  replies_received integer DEFAULT 0,
  opt_outs integer DEFAULT 0,
  conversions integer DEFAULT 0,
  avg_delivery_time_ms integer,
  failure_rate numeric(5,4),
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.campaign_templates (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  campaign_id uuid NOT NULL,
  template_id uuid NOT NULL,
  sequence_step integer DEFAULT 1 NOT NULL,
  step_name text,
  delay_days integer DEFAULT 0,
  delay_hours integer DEFAULT 0,
  is_active boolean DEFAULT true
);

CREATE TABLE IF NOT EXISTS public.campaigns (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  name text NOT NULL,
  description text,
  campaign_type text DEFAULT 'outreach'::text NOT NULL,
  target_segment_id uuid,
  target_criteria jsonb DEFAULT '{}'::jsonb,
  status text DEFAULT 'draft'::text NOT NULL,
  scheduled_start_at timestamp with time zone,
  scheduled_end_at timestamp with time zone,
  timezone text DEFAULT 'Asia/Kuala_Lumpur'::text,
  daily_limit integer DEFAULT 50,
  send_window_start time without time zone DEFAULT '09:00:00'::time without time zone,
  send_window_end time without time zone DEFAULT '18:00:00'::time without time zone,
  min_delay_seconds integer DEFAULT 120,
  max_delay_seconds integer DEFAULT 300,
  sequence_type text DEFAULT 'single'::text,
  follow_up_days integer[] DEFAULT '{}'::integer[],
  stop_on_reply boolean DEFAULT true,
  total_recipients integer DEFAULT 0,
  sent_count integer DEFAULT 0,
  delivered_count integer DEFAULT 0,
  failed_count integer DEFAULT 0,
  reply_count integer DEFAULT 0,
  conversion_count integer DEFAULT 0,
  started_at timestamp with time zone,
  completed_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  created_by uuid,
  settings jsonb DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS public.chats (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  jid text NOT NULL,
  name text,
  last_message_at timestamp with time zone,
  unread_count integer DEFAULT 0,
  is_group boolean DEFAULT false,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.checklist_state (
  id text NOT NULL,
  checked boolean DEFAULT false,
  checked_by text,
  checked_at timestamp with time zone DEFAULT now(),
  section text,
  batch integer
);

CREATE TABLE IF NOT EXISTS public.client_configs (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  client_type text NOT NULL,
  manglish_level text DEFAULT 'medium'::text,
  tone text DEFAULT 'professional'::text,
  enabled_tools text[] DEFAULT '{}'::text[],
  system_prompt_vars jsonb DEFAULT '{}'::jsonb,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  escalation_timeout_minutes integer DEFAULT 30
);

-- ── 10-tables-2 ──
CREATE TABLE IF NOT EXISTS public.command_center_state (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  state_key text NOT NULL,
  state_value jsonb NOT NULL,
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.contact_segment_members (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  segment_id uuid NOT NULL,
  contact_id uuid NOT NULL,
  added_at timestamp with time zone DEFAULT now() NOT NULL,
  added_via text DEFAULT 'manual'::text
);

CREATE TABLE IF NOT EXISTS public.contact_segments (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  name text NOT NULL,
  description text,
  segment_type text DEFAULT 'static'::text NOT NULL,
  filter_criteria jsonb DEFAULT '{}'::jsonb,
  contact_count integer DEFAULT 0,
  last_calculated_at timestamp with time zone,
  source text DEFAULT 'manual'::text,
  source_file text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.contacts (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id text NOT NULL,
  jid text NOT NULL,
  phone text,
  name text,
  tag text DEFAULT 'lead'::text,
  source text DEFAULT 'whatsapp'::text,
  status text DEFAULT 'active'::text,
  notes text,
  property_interest text,
  first_message_at timestamp with time zone,
  last_message_at timestamp with time zone,
  message_count integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  last_outreach_at timestamp with time zone,
  outreach_count integer DEFAULT 0,
  last_reply_at timestamp with time zone,
  reply_count integer DEFAULT 0,
  opted_out_at timestamp with time zone,
  opted_out_reason text,
  lead_temperature text DEFAULT 'cold'::text,
  campaign_config_id uuid,
  industry_type text,
  sub_type text,
  country text DEFAULT 'MY'::text,
  language_pref text DEFAULT 'auto'::text,
  business_size text,
  estimated_revenue text,
  whatsapp_active text DEFAULT 'unknown'::text,
  online_presence text DEFAULT 'unknown'::text,
  pain_point_hint text,
  competitor_used text,
  persona text DEFAULT 'direct'::text,
  priority text DEFAULT 'normal'::text,
  custom_note text,
  do_not_contact boolean DEFAULT false,
  max_followups integer DEFAULT 3,
  interest_score integer DEFAULT 0,
  qualification_signals_hit jsonb DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS public.conversation_logs (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  chat_jid text NOT NULL,
  event_type text NOT NULL,
  tool_name text,
  success boolean DEFAULT true,
  error_message text,
  metadata jsonb,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.conversations (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  chat_jid text NOT NULL,
  message_id text,
  message_content text NOT NULL,
  sender text,
  is_from_me boolean DEFAULT false,
  detected_language text,
  detected_emotion text,
  formality_level text,
  confidence_score real,
  ai_response text,
  response_strategy text,
  processing_time_ms integer,
  "timestamp" timestamp with time zone DEFAULT now(),
  created_at timestamp with time zone DEFAULT now(),
  customer_jid text,
  linked_chat_jids text[] DEFAULT '{}'::text[],
  contact_name text,
  profile_pic_url text
);

CREATE TABLE IF NOT EXISTS public.conversion_events (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  event_type text NOT NULL,
  customer_jid text NOT NULL,
  customer_name text,
  customer_phone text,
  conversion_value numeric(10,2),
  conversion_metadata jsonb DEFAULT '{}'::jsonb,
  source text,
  conversation_id uuid,
  converted_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.customer_activity (
  id integer DEFAULT nextval('customer_activity_id_seq'::regclass) NOT NULL,
  tenant_id text NOT NULL,
  customer_jid text NOT NULL,
  last_message_at timestamp without time zone NOT NULL,
  message_count integer DEFAULT 1,
  updated_at timestamp without time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.customer_memory (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  chat_jid text NOT NULL,
  key_facts jsonb DEFAULT '{}'::jsonb NOT NULL,
  summary text DEFAULT ''::text NOT NULL,
  embedding vector(768),
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.daily_digests (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  user_id uuid NOT NULL,
  digest_date date NOT NULL,
  type text NOT NULL,
  content jsonb DEFAULT '{}'::jsonb,
  delivered_via text[] DEFAULT '{}'::text[],
  delivered_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.dashboard_views (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  name text NOT NULL,
  description text,
  view_type text NOT NULL,
  config jsonb DEFAULT '{}'::jsonb,
  created_by text NOT NULL,
  department_id uuid,
  visibility text DEFAULT 'private'::text NOT NULL,
  pinned boolean DEFAULT false NOT NULL,
  sort_order integer DEFAULT 0 NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.data_request_deletions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  phone_normalized text NOT NULL,
  email text NOT NULL,
  request_id text NOT NULL,
  row_count_at_request integer DEFAULT 0 NOT NULL,
  grace_until timestamp with time zone NOT NULL,
  status text DEFAULT 'pending'::text NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.decisions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  title text NOT NULL,
  description text,
  department_id uuid,
  status text DEFAULT 'proposed'::text NOT NULL,
  decision_maker uuid,
  stakeholders uuid[] DEFAULT '{}'::uuid[],
  options jsonb DEFAULT '[]'::jsonb,
  chosen_option text,
  rationale text,
  ai_analysis text,
  deadline date,
  decided_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.departments (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  name text NOT NULL,
  parent_id uuid,
  level integer DEFAULT 0,
  description text,
  icon text,
  sort_order integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.device_sessions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid,
  device_id text NOT NULL,
  whatsapp_jid text,
  status text NOT NULL,
  qr_code_url text,
  qr_expires_at timestamp with time zone,
  connected_at timestamp with time zone,
  last_seen timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  bridge_url text
);

CREATE TABLE IF NOT EXISTS public.drive_documents (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  google_file_id text NOT NULL,
  name text,
  mime_type text,
  owner_email text,
  owner_user_id uuid,
  shared_with text[] DEFAULT '{}'::text[],
  web_view_link text,
  content_text text,
  last_modified_at timestamp with time zone,
  synced_at timestamp with time zone DEFAULT now() NOT NULL,
  content_embedding vector(1536)
);

CREATE TABLE IF NOT EXISTS public.email_summaries (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  user_id uuid NOT NULL,
  gmail_message_id text NOT NULL,
  gmail_thread_id text,
  subject text,
  sender text,
  recipients text[] DEFAULT '{}'::text[],
  snippet text,
  labels text[] DEFAULT '{}'::text[],
  ai_summary text,
  ai_action_items jsonb DEFAULT '[]'::jsonb,
  ai_urgency text,
  ai_topics text[] DEFAULT '{}'::text[],
  received_at timestamp with time zone,
  synced_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.email_templates (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid,
  template_type text NOT NULL,
  subject text NOT NULL,
  body_html text NOT NULL,
  body_text text,
  variables jsonb,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.email_verification_tokens (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  email text NOT NULL,
  token text NOT NULL,
  expires_at timestamp without time zone NOT NULL,
  verified_at timestamp without time zone,
  resent_count integer DEFAULT 0,
  created_at timestamp without time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.escalation_actions (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  escalation_id uuid NOT NULL,
  tenant_id uuid NOT NULL,
  action_type text NOT NULL,
  performed_by text NOT NULL,
  action_data jsonb,
  notes text,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.escalation_notifications (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  escalation_id uuid NOT NULL,
  channel text NOT NULL,
  recipient text NOT NULL,
  status text NOT NULL,
  error_message text,
  retry_count integer DEFAULT 0,
  sent_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.escalations (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  chat_jid text NOT NULL,
  reason text,
  status text DEFAULT 'pending'::text,
  priority text DEFAULT 'normal'::text,
  assigned_to text,
  assigned_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  resolved_at timestamp with time zone,
  resolution_notes text,
  sla_deadline timestamp with time zone,
  customer_context jsonb,
  metadata jsonb DEFAULT '{}'::jsonb,
  assigned_agent_id uuid,
  updated_at timestamp with time zone DEFAULT now(),
  escalation_timeout_minutes integer DEFAULT 30,
  escalation_triggered_at timestamp with time zone,
  warning_sent boolean DEFAULT false,
  warning_sent_at timestamp with time zone,
  reason_type text,
  escalation_type text DEFAULT 'general'::text,
  confidence_score real,
  trigger_keywords jsonb DEFAULT '[]'::jsonb,
  conversation_context jsonb,
  notification_channels jsonb DEFAULT '[]'::jsonb,
  notification_sent_at timestamp with time zone,
  auto_resume boolean DEFAULT true,
  resumed_at timestamp with time zone,
  customer_satisfaction_score integer
);

CREATE TABLE IF NOT EXISTS public.extracted_items (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  raw_event_id uuid,
  item_type text NOT NULL,
  title text NOT NULL,
  body text,
  assignee text,
  due_date date,
  priority text,
  status text DEFAULT 'pending'::text,
  source_meeting text,
  tags text[],
  metadata jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.feedback (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid,
  customer_jid text NOT NULL,
  conversation_id uuid,
  chat_jid text NOT NULL,
  rating integer,
  comment text,
  feedback_type text DEFAULT 'rating'::text,
  sentiment text,
  keywords text[],
  auto_categorized boolean DEFAULT false,
  follow_up_needed boolean DEFAULT false,
  follow_up_completed boolean DEFAULT false,
  admin_response text,
  responded_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.follow_ups (
  id bigint DEFAULT nextval('follow_ups_id_seq'::regclass) NOT NULL,
  tenant_id uuid,
  chat_jid text NOT NULL,
  lead_status text NOT NULL,
  scheduled_at timestamp with time zone NOT NULL,
  status text DEFAULT 'pending'::text,
  message_sent_at timestamp with time zone,
  notes text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.google_sheets_sync (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  spreadsheet_id text NOT NULL,
  spreadsheet_url text,
  sheet_name text DEFAULT 'Messages'::text,
  sync_enabled boolean DEFAULT true,
  sync_interval_minutes integer DEFAULT 5,
  last_sync_at timestamp with time zone,
  last_sync_status text,
  last_sync_error text,
  column_mapping jsonb DEFAULT '{"sender": "B", "message": "C", "response": "D", "timestamp": "A"}'::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.handover_agents (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  agent_name text NOT NULL,
  agent_email text,
  agent_whatsapp text,
  agent_role text DEFAULT 'Support Agent'::text,
  is_active boolean DEFAULT true,
  priority_level integer DEFAULT 1,
  working_hours jsonb,
  skills jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.help_tickets (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  ticket_number text NOT NULL,
  group_jid text NOT NULL,
  sender_jid text NOT NULL,
  sender_name text,
  message text NOT NULL,
  status text DEFAULT 'open'::text NOT NULL,
  priority text DEFAULT 'normal'::text NOT NULL,
  escalated_at timestamp with time zone,
  closed_at timestamp with time zone,
  resolved_by text,
  notes text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.holiday_exceptions (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  date date NOT NULL,
  title text,
  description text,
  is_recurring boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.inbox_copilot_events (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  kind text NOT NULL,
  event_id text NOT NULL,
  chat_jid text NOT NULL,
  suggestion_id text,
  suggestion_ids jsonb,
  draft_reply text,
  last_customer_message text,
  conversation_age_minutes integer,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.industry_kb_templates (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  vertical text NOT NULL,
  sub_vertical text,
  template_name text NOT NULL,
  description text,
  language text DEFAULT 'en_manglish'::text NOT NULL,
  variables jsonb DEFAULT '[]'::jsonb NOT NULL,
  faq_template jsonb DEFAULT '[]'::jsonb NOT NULL,
  qualification_questions jsonb DEFAULT '[]'::jsonb NOT NULL,
  escalation_triggers jsonb DEFAULT '[]'::jsonb NOT NULL,
  greeting_template text,
  after_hours_template text,
  is_active boolean DEFAULT true,
  sort_order integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.jid_mappings (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  lid_jid text NOT NULL,
  phone_jid text,
  display_name text,
  source text DEFAULT 'manual'::text,
  last_seen_at timestamp with time zone DEFAULT now(),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.knowledge_base (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid,
  title text NOT NULL,
  source_type text NOT NULL,
  source_url text,
  content text NOT NULL,
  content_type text DEFAULT 'text/plain'::text,
  file_size integer,
  chunks jsonb DEFAULT '[]'::jsonb,
  total_chunks integer DEFAULT 0,
  keywords text[],
  topics text[],
  language text DEFAULT 'auto'::text,
  embedding_model text,
  embedding_stored boolean DEFAULT false,
  times_referenced integer DEFAULT 0,
  last_referenced_at timestamp with time zone,
  is_active boolean DEFAULT true,
  processing_status text DEFAULT 'ready'::text,
  processing_error text,
  uploaded_by text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  source_id text,
  content_embedding vector(1536),
  department_id uuid,
  visibility text DEFAULT 'department'::text,
  created_by uuid,
  metadata jsonb DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS public.knowledge_bases (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  source_type text NOT NULL,
  source_url text,
  title text NOT NULL,
  content text NOT NULL,
  content_hash text,
  embedding vector(1536),
  category text,
  tags text[],
  language text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  last_synced_at timestamp with time zone,
  is_active boolean DEFAULT true,
  chunks jsonb DEFAULT '[]'::jsonb,
  chunk_count integer DEFAULT 0,
  processing_status text DEFAULT 'pending'::text,
  last_processed_at timestamp with time zone,
  file_hash text,
  file_size_kb real,
  mime_type text,
  error_message text
);

CREATE TABLE IF NOT EXISTS public.knowledge_chunks (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  knowledge_base_id uuid NOT NULL,
  tenant_id uuid NOT NULL,
  chunk_text text NOT NULL,
  chunk_index integer NOT NULL,
  chunk_size integer,
  embedding vector(1536),
  section_title text,
  page_number integer,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.knowledge_doc_versions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  document_id uuid NOT NULL,
  tenant_id uuid NOT NULL,
  version_number integer NOT NULL,
  filename text,
  content text,
  metadata jsonb DEFAULT '{}'::jsonb,
  changed_by text DEFAULT 'dashboard'::text,
  change_summary text,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.knowledge_documents (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  filename text NOT NULL,
  file_type text,
  file_url text,
  file_size_kb integer,
  content_extracted text,
  uploaded_at timestamp without time zone DEFAULT now(),
  uploaded_by text,
  metadata jsonb DEFAULT '{}'::jsonb,
  status text DEFAULT 'uploaded'::text,
  file_size_bytes integer,
  upload_url text,
  extracted_text text,
  chunk_count integer DEFAULT 0,
  processed_at timestamp with time zone,
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.knowledge_sync_jobs (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  knowledge_base_id uuid NOT NULL,
  tenant_id uuid NOT NULL,
  sync_type text NOT NULL,
  status text DEFAULT 'pending'::text,
  previous_hash text,
  current_hash text,
  changes_detected boolean DEFAULT false,
  started_at timestamp with time zone DEFAULT now(),
  completed_at timestamp with time zone,
  duration_ms integer,
  error_message text,
  chunks_created integer DEFAULT 0,
  chunks_updated integer DEFAULT 0,
  chunks_deleted integer DEFAULT 0
);

CREATE TABLE IF NOT EXISTS public.lead_followups (
  id integer DEFAULT nextval('lead_followups_id_seq'::regclass) NOT NULL,
  tenant_id text NOT NULL,
  customer_jid text NOT NULL,
  initial_contact_at timestamp without time zone NOT NULL,
  followup_count integer DEFAULT 0,
  last_followup_at timestamp without time zone,
  next_followup_at timestamp without time zone,
  status text DEFAULT 'active'::text,
  created_at timestamp without time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.leads (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
  updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
  name text NOT NULL,
  email text NOT NULL,
  phone text,
  company text,
  industry text,
  source text DEFAULT 'website'::text NOT NULL,
  utm_source text,
  utm_medium text,
  utm_campaign text,
  referrer text,
  status text DEFAULT 'new'::text NOT NULL,
  lead_score integer DEFAULT 0,
  notes text,
  marketing_consent boolean DEFAULT false,
  pdpa_consent boolean DEFAULT true,
  ip_address inet,
  user_agent text,
  device_type text,
  location_country text,
  location_city text,
  email_sent_at timestamp with time zone,
  email_opened_at timestamp with time zone,
  email_clicked_at timestamp with time zone
);

-- ── 10-tables-3 ──
CREATE TABLE IF NOT EXISTS public.link_clicks (
  id bigint NOT NULL,
  link_id bigint,
  ip_address text,
  user_agent text,
  referer text,
  country text,
  device_type text,
  clicked_at timestamp with time zone DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.llm_usage (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  ts timestamp with time zone NOT NULL,
  alias text NOT NULL,
  provider text NOT NULL,
  model text NOT NULL,
  cost_usd numeric(12,6) DEFAULT 0 NOT NULL,
  latency_ms integer DEFAULT 0 NOT NULL,
  prompt_tokens integer DEFAULT 0 NOT NULL,
  completion_tokens integer DEFAULT 0 NOT NULL,
  fallback_reason text,
  error_class text,
  tenant_id uuid
);

CREATE TABLE IF NOT EXISTS public.media_library (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid,
  original_name character varying(255) NOT NULL,
  stored_filename character varying(255) NOT NULL,
  file_type character varying(50) NOT NULL,
  mime_type character varying(100),
  file_url text NOT NULL,
  file_size integer,
  description text,
  tags text[] DEFAULT ARRAY[]::text[],
  send_count integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.meeting_blockers (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  meeting_id uuid,
  action_item_id uuid,
  description text NOT NULL,
  blocked_person text,
  resolver text,
  status text DEFAULT 'open'::text,
  resolved_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.meeting_decisions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  meeting_id uuid,
  description text NOT NULL,
  decided_by text,
  effective_date date,
  category text DEFAULT 'process'::text,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.meeting_followups (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  meeting_id uuid,
  action_item_id uuid,
  followup_type text NOT NULL,
  channel text,
  recipient text,
  content text,
  status text DEFAULT 'pending'::text,
  requires_approval boolean DEFAULT false,
  sent_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.meeting_minutes (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  calendar_event_id uuid,
  title text NOT NULL,
  attendees jsonb DEFAULT '[]'::jsonb,
  summary text,
  key_decisions jsonb DEFAULT '[]'::jsonb,
  action_items_extracted jsonb DEFAULT '[]'::jsonb,
  department_id uuid,
  created_by uuid,
  ai_generated boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.meetings (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  title text NOT NULL,
  meeting_date date DEFAULT CURRENT_DATE NOT NULL,
  meeting_type text DEFAULT 'sync'::text,
  transcript text,
  summary text,
  attendees uuid[] DEFAULT '{}'::uuid[],
  recap_sent boolean DEFAULT false,
  recap_sent_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.message_reasons (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  message_id text NOT NULL,
  chat_jid text NOT NULL,
  channel text DEFAULT 'whatsapp'::text NOT NULL,
  retrieved_docs jsonb DEFAULT '[]'::jsonb NOT NULL,
  tool_calls jsonb DEFAULT '[]'::jsonb NOT NULL,
  model text,
  confidence numeric,
  alternatives jsonb DEFAULT '[]'::jsonb NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.message_templates (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  template_name text NOT NULL,
  template_content text NOT NULL,
  category text,
  variables jsonb DEFAULT '[]'::jsonb,
  usage_count integer DEFAULT 0,
  last_used_at timestamp with time zone,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  trigger_mode character varying(50) DEFAULT 'manual_only'::character varying,
  trigger_keywords text[] DEFAULT ARRAY[]::text[],
  source character varying(50) DEFAULT 'custom'::character varying
);

CREATE TABLE IF NOT EXISTS public.messages (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid,
  chat_jid text NOT NULL,
  role text NOT NULL,
  content text NOT NULL,
  "timestamp" timestamp with time zone DEFAULT now(),
  message_id text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  customer_phone character varying(50),
  customer_name character varying(100),
  device_jid text,
  phone_jid text,
  chat_type text DEFAULT 'individual'::text NOT NULL,
  is_system_event boolean DEFAULT false NOT NULL,
  conversation_key text,
  media_url text,
  media_type text,
  media_mime text
);

CREATE TABLE IF NOT EXISTS public.notification_groups (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  group_type text NOT NULL,
  group_jid text NOT NULL,
  group_name text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  is_active boolean DEFAULT true
);

CREATE TABLE IF NOT EXISTS public.notification_logs (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  group_type text NOT NULL,
  group_jid text NOT NULL,
  customer_jid text,
  customer_phone text,
  customer_name text,
  notification_type text NOT NULL,
  message_preview text,
  sent_at timestamp with time zone DEFAULT now(),
  metadata jsonb
);

CREATE TABLE IF NOT EXISTS public.notifications (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  user_id uuid NOT NULL,
  type text NOT NULL,
  title text NOT NULL,
  body text,
  link text,
  channels text[] DEFAULT '{dashboard}'::text[],
  read boolean DEFAULT false NOT NULL,
  delivered jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.onboarding_progress (
  tenant_id uuid NOT NULL,
  step_payment_completed boolean DEFAULT false,
  step_details_completed boolean DEFAULT false,
  step_whatsapp_completed boolean DEFAULT false,
  step_knowledge_completed boolean DEFAULT false,
  step_agents_completed boolean DEFAULT false,
  step_payment_at timestamp with time zone,
  step_details_at timestamp with time zone,
  step_whatsapp_at timestamp with time zone,
  step_knowledge_at timestamp with time zone,
  step_agents_at timestamp with time zone,
  current_step text DEFAULT 'payment'::text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.onboarding_sessions (
  token text NOT NULL,
  tenant_id uuid,
  email text NOT NULL,
  status text DEFAULT 'pending_whatsapp'::text,
  created_at timestamp with time zone DEFAULT now(),
  expires_at timestamp with time zone NOT NULL,
  completed_at timestamp with time zone,
  metadata jsonb DEFAULT '{}'::jsonb,
  ip_address text,
  user_agent text
);

CREATE TABLE IF NOT EXISTS public.outbound_queue (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  campaign_id uuid,
  contact_id uuid,
  recipient_jid text NOT NULL,
  recipient_name text,
  recipient_phone text,
  message_content text NOT NULL,
  message_template_id uuid,
  variables_used jsonb DEFAULT '{}'::jsonb,
  sequence_step integer DEFAULT 1,
  sequence_order integer DEFAULT 0,
  scheduled_at timestamp with time zone NOT NULL,
  send_after timestamp with time zone,
  status text DEFAULT 'pending'::text NOT NULL,
  sent_at timestamp with time zone,
  delivered_at timestamp with time zone,
  read_at timestamp with time zone,
  failed_at timestamp with time zone,
  retry_count integer DEFAULT 0,
  max_retries integer DEFAULT 3,
  error_message text,
  error_code text,
  replied_at timestamp with time zone,
  reply_content text,
  wa_message_id text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.outreach_campaign_configs (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  campaign_id text NOT NULL,
  name text NOT NULL,
  industry_type text NOT NULL,
  sub_type text,
  meta jsonb DEFAULT '{}'::jsonb NOT NULL,
  industry_config jsonb DEFAULT '{}'::jsonb NOT NULL,
  qualification_config jsonb DEFAULT '{}'::jsonb NOT NULL,
  sequence_config jsonb DEFAULT '{}'::jsonb NOT NULL,
  persona_config jsonb DEFAULT '{}'::jsonb NOT NULL,
  reveal_config jsonb DEFAULT '{}'::jsonb NOT NULL,
  escalation_config jsonb DEFAULT '{}'::jsonb NOT NULL,
  is_active boolean DEFAULT true NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.outreach_consent_log (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  contact_id uuid NOT NULL,
  consent_type text NOT NULL,
  consent_text text,
  channel text NOT NULL,
  source text DEFAULT 'manual'::text NOT NULL,
  ip_address inet,
  user_agent text,
  granted_at timestamp with time zone DEFAULT now() NOT NULL,
  expires_at timestamp with time zone,
  revoked_at timestamp with time zone,
  revoked_reason text,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.outreach_logs (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  campaign_id uuid,
  queue_id uuid,
  log_type text NOT NULL,
  log_message text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.owner_commands (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid,
  command_type text NOT NULL,
  raw_command text NOT NULL,
  parsed_params jsonb DEFAULT '{}'::jsonb,
  executed_at timestamp with time zone DEFAULT now(),
  success boolean DEFAULT true,
  error_message text,
  owner_jid text NOT NULL,
  chat_jid text NOT NULL,
  result_summary text,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.owner_devices (
  id integer DEFAULT nextval('owner_devices_id_seq'::regclass) NOT NULL,
  device_jid text NOT NULL,
  owner_jid text NOT NULL,
  registered_at timestamp with time zone DEFAULT now(),
  notes text
);

CREATE TABLE IF NOT EXISTS public.owner_notifications (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid,
  notification_type text NOT NULL,
  message text NOT NULL,
  chat_jid text NOT NULL,
  customer_name text,
  sent_at timestamp with time zone DEFAULT now(),
  delivered boolean DEFAULT false,
  delivery_error text,
  created_at timestamp with time zone DEFAULT now(),
  owner_jid text
);

CREATE TABLE IF NOT EXISTS public.payment_transactions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  stripe_payment_intent_id text,
  stripe_invoice_id text,
  stripe_charge_id text,
  amount_cents integer NOT NULL,
  currency text DEFAULT 'usd'::text,
  status text NOT NULL,
  plan_name text,
  billing_period text,
  description text,
  receipt_url text,
  invoice_pdf text,
  created_at timestamp without time zone DEFAULT now(),
  paid_at timestamp without time zone,
  failed_at timestamp without time zone,
  failure_code text,
  failure_message text
);

CREATE TABLE IF NOT EXISTS public.personas (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid,
  persona_key text,
  display_name text,
  industry text,
  system_prompt text NOT NULL,
  greeting_template text,
  tone text DEFAULT 'professional'::text,
  language_preference text DEFAULT 'auto'::text,
  knows_creator boolean DEFAULT true,
  can_roleplay boolean DEFAULT true,
  auto_demo_mode boolean DEFAULT false,
  templates jsonb DEFAULT '{}'::jsonb,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  created_by text,
  name text,
  role text,
  introduction text,
  specialties jsonb DEFAULT '[]'::jsonb,
  qualification_questions jsonb DEFAULT '[]'::jsonb,
  upsell_bijou boolean DEFAULT false,
  mention_w3j boolean DEFAULT true,
  type text
);

CREATE TABLE IF NOT EXISTS public.platform_admins (
  user_id uuid NOT NULL,
  email text NOT NULL,
  role text DEFAULT 'admin'::text NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  created_by uuid,
  notes text
);

CREATE TABLE IF NOT EXISTS public.projects (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  name text NOT NULL,
  description text,
  department_id uuid,
  owner_id uuid,
  status text DEFAULT 'active'::text NOT NULL,
  priority text DEFAULT 'medium'::text NOT NULL,
  start_date date,
  target_date date,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.proposals (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  extracted_item_id uuid,
  title text NOT NULL,
  proposal_type text,
  content jsonb NOT NULL,
  agent_reasoning text,
  status text DEFAULT 'pending_approval'::text,
  approved_at timestamp with time zone,
  executed_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.raw_events (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  source text NOT NULL,
  source_id text,
  raw_content jsonb NOT NULL,
  processed boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.response_coordinator_state (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  chat_jid text NOT NULL,
  state jsonb DEFAULT '{}'::jsonb NOT NULL,
  last_activity_at timestamp with time zone DEFAULT now() NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.scheduled_messages (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  schedule_name text NOT NULL,
  cron_expression text NOT NULL,
  timezone text DEFAULT 'Asia/Kuala_Lumpur'::text,
  template_id uuid,
  recipients jsonb,
  message_content text,
  is_active boolean DEFAULT true,
  next_run_at timestamp with time zone,
  last_run_at timestamp with time zone,
  run_count integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  status text DEFAULT 'pending'::text,
  scheduled_time timestamp with time zone,
  sent_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS public.shared_briefs (
  token text NOT NULL,
  title text NOT NULL,
  project_name text,
  period text,
  health text DEFAULT 'On Track'::text,
  content text,
  action_items jsonb DEFAULT '[]'::jsonb,
  decision_count integer DEFAULT 0,
  blocker_count integer DEFAULT 0,
  attendee_count integer DEFAULT 0,
  author_name text,
  is_public boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  source_id text
);

CREATE TABLE IF NOT EXISTS public.shared_context (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  customer_phone text NOT NULL,
  channel text NOT NULL,
  thread_id text NOT NULL,
  role text NOT NULL,
  content text NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.sheet_data (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  google_sheet_id text NOT NULL,
  sheet_name text NOT NULL,
  range text NOT NULL,
  data jsonb DEFAULT '{}'::jsonb,
  synced_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.short_links (
  id bigint NOT NULL,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
  slug text NOT NULL,
  destination_url text NOT NULL,
  owner_email text,
  click_count integer DEFAULT 0
);

CREATE TABLE IF NOT EXISTS public.silence_rules (
  tenant_id text NOT NULL,
  silence_days integer NOT NULL,
  message_template text NOT NULL,
  enabled boolean DEFAULT true,
  last_check timestamp without time zone,
  created_at timestamp without time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.subscription_plans (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  plan_code text NOT NULL,
  plan_name text NOT NULL,
  description text,
  price_monthly_cents integer,
  price_yearly_cents integer,
  currency text DEFAULT 'myr'::text,
  stripe_price_id_monthly text,
  stripe_price_id_yearly text,
  max_contacts integer,
  max_messages_per_month integer,
  ai_model text DEFAULT 'gemini-2.0-flash-exp'::text,
  support_level text DEFAULT 'email'::text,
  custom_branding boolean DEFAULT false,
  is_active boolean DEFAULT true,
  display_order integer DEFAULT 0,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.system_metrics (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  metric_name text NOT NULL,
  metric_value double precision NOT NULL,
  labels jsonb DEFAULT '{}'::jsonb,
  recorded_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.tasks (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  project_id uuid,
  title text NOT NULL,
  description text,
  assigned_to uuid,
  assigned_agent text,
  created_by uuid,
  department_id uuid,
  status text DEFAULT 'todo'::text NOT NULL,
  priority text DEFAULT 'medium'::text NOT NULL,
  due_date date,
  estimated_hours double precision,
  actual_hours double precision,
  source_type text,
  source_id text,
  tags text[] DEFAULT '{}'::text[],
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  completed_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS public.team_activity (
  id integer DEFAULT nextval('team_activity_id_seq'::regclass) NOT NULL,
  user_name text NOT NULL,
  item_id text NOT NULL,
  action text DEFAULT 'check'::text,
  created_at timestamp with time zone DEFAULT now(),
  user_id uuid
);

-- ── 10-tables-4 ──
CREATE TABLE IF NOT EXISTS public.team_members (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  name text NOT NULL,
  email text,
  preferred_channel text DEFAULT 'email'::text,
  avg_response_latency_hours numeric DEFAULT 0,
  eta_accuracy_pct numeric DEFAULT 100,
  completion_rate_pct numeric DEFAULT 100,
  total_tasks_assigned integer DEFAULT 0,
  total_tasks_completed integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.tenant_action_policy (
  tenant_id uuid NOT NULL,
  tool_name text NOT NULL,
  mode text DEFAULT 'confirm'::text NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.tenant_calendars (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  provider text DEFAULT 'cal.com'::text NOT NULL,
  cal_username text,
  cal_api_key text,
  default_event_type_id integer,
  send_confirmation_email boolean DEFAULT true,
  confirmation_email_template_id uuid,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  is_oauth_connected boolean DEFAULT false,
  oauth_access_token text,
  oauth_refresh_token text,
  oauth_expiry timestamp with time zone,
  oauth_scope text,
  oauth_user_email text,
  oauth_user_id text
);

CREATE TABLE IF NOT EXISTS public.tenant_email_config (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  smtp_host text NOT NULL,
  smtp_port integer DEFAULT 587 NOT NULL,
  smtp_user text NOT NULL,
  smtp_pass text NOT NULL,
  smtp_use_tls boolean DEFAULT true,
  from_email text NOT NULL,
  from_name text NOT NULL,
  reply_to_email text,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.tenant_integrations (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  integration_id text NOT NULL,
  connection_id text NOT NULL,
  status text DEFAULT 'connected'::text,
  connected_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.tenant_kb_template_instances (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  template_id uuid NOT NULL,
  filled_variables jsonb DEFAULT '{}'::jsonb NOT NULL,
  completion_pct integer DEFAULT 0,
  is_complete boolean DEFAULT false,
  is_applied boolean DEFAULT false,
  kb_entry_ids uuid[] DEFAULT '{}'::uuid[],
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.tenant_metrics (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  metric_name text NOT NULL,
  metric_value double precision NOT NULL,
  labels jsonb DEFAULT '{}'::jsonb,
  recorded_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.tenant_setup_progress (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  step_email_verify integer DEFAULT 0,
  step_whatsapp_connect integer DEFAULT 0,
  step_knowledge_upload integer DEFAULT 0,
  step_business_hours integer DEFAULT 0,
  step_custom_responses integer DEFAULT 0,
  step_test_conversation integer DEFAULT 0,
  started_at timestamp without time zone DEFAULT now(),
  completed_at timestamp without time zone,
  last_updated_at timestamp without time zone DEFAULT now(),
  completion_percentage integer DEFAULT 0,
  current_step text DEFAULT 'email_verify'::text
);

CREATE TABLE IF NOT EXISTS public.tenant_users (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  tenant_id uuid NOT NULL,
  user_id uuid NOT NULL,
  role text DEFAULT 'owner'::text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.tenant_users_legacy (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  email text NOT NULL,
  role text DEFAULT 'owner'::text,
  is_main_contact boolean DEFAULT false,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.tenant_verticals (
  tenant_id uuid NOT NULL,
  vertical_id text NOT NULL,
  enabled boolean DEFAULT true,
  custom_overrides jsonb,
  assigned_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.tenants (
  id uuid DEFAULT uuid_generate_v4() NOT NULL,
  name text NOT NULL,
  slug text NOT NULL,
  whatsapp_jid text,
  owner_email text,
  owner_phone text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  is_active boolean DEFAULT true,
  plan_tier text DEFAULT 'free'::text,
  monthly_message_limit integer DEFAULT 100,
  settings jsonb DEFAULT '{}'::jsonb,
  whatsapp_number text,
  subscription_tier text DEFAULT 'freemium'::text,
  status text DEFAULT 'active'::text,
  telegram_username text,
  email text,
  business_name text,
  phone text,
  plan text DEFAULT 'basic'::text,
  signup_token text,
  onboarding_completed boolean DEFAULT false,
  whatsapp_connected_at timestamp without time zone,
  created_by text DEFAULT 'jewel-owner'::text,
  testing_mode boolean DEFAULT false,
  test_numbers jsonb DEFAULT '[]'::jsonb,
  ignore_numbers jsonb DEFAULT '[]'::jsonb,
  private_numbers jsonb DEFAULT '[]'::jsonb,
  handover_primary text,
  handover_secondary jsonb DEFAULT '[]'::jsonb,
  handover_enabled boolean DEFAULT true,
  business_hours jsonb DEFAULT '{"enabled": true, "schedule": {"friday": {"end": "18:00", "start": "09:00", "enabled": false}, "monday": {"end": "18:00", "start": "09:00", "enabled": true}, "sunday": {"end": "18:00", "start": "09:00", "enabled": true}, "tuesday": {"end": "18:00", "start": "09:00", "enabled": true}, "saturday": {"end": "18:00", "start": "09:00", "enabled": true}, "thursday": {"end": "18:00", "start": "09:00", "enabled": true}, "wednesday": {"end": "18:00", "start": "09:00", "enabled": true}}, "timezone": "Asia/Kuala_Lumpur", "out_of_hours_message": "Thank you for your message. Our business hours are Monday-Thursday and Saturday-Sunday, 9 AM - 6 PM. We will respond during our next business hours."}'::jsonb,
  auto_reply_enabled boolean DEFAULT true,
  welcome_message text,
  google_access_token text,
  google_refresh_token text,
  google_token_expires_at timestamp with time zone,
  profile_picture_url text,
  whatsapp_connected boolean DEFAULT false,
  device_id text,
  session_active boolean DEFAULT false,
  session_connected_at timestamp with time zone,
  last_seen timestamp with time zone,
  trial_ends_at timestamp with time zone,
  onboarding_completed_at timestamp with time zone,
  onboarding_step text DEFAULT 'payment'::text,
  payment_method text,
  manglish_mode boolean DEFAULT false,
  stripe_customer_id text,
  daily_outreach_limit integer DEFAULT 100,
  outreach_enabled boolean DEFAULT false,
  outreach_start_time time without time zone DEFAULT '09:00:00'::time without time zone,
  outreach_end_time time without time zone DEFAULT '18:00:00'::time without time zone,
  outreach_timezone text DEFAULT 'Asia/Kuala_Lumpur'::text,
  outreach_cooldown_hours integer DEFAULT 72,
  email_verified boolean DEFAULT false,
  email_verification_token text,
  email_verified_at timestamp without time zone,
  trial_start_date timestamp without time zone,
  trial_end_date timestamp without time zone,
  trial_days integer DEFAULT 14,
  is_trial boolean DEFAULT true,
  stripe_subscription_id text,
  subscription_status text DEFAULT 'trial'::text,
  subscription_start_date timestamp without time zone,
  current_period_end timestamp without time zone,
  onboarding_checklist jsonb DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS public.trial_notifications (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  notification_type text NOT NULL,
  sent_at timestamp without time zone DEFAULT now(),
  email_sent boolean DEFAULT false,
  whatsapp_sent boolean DEFAULT false,
  metadata jsonb DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS public.usage_tracking (
  id bigint DEFAULT nextval('usage_tracking_id_seq'::regclass) NOT NULL,
  tenant_id uuid NOT NULL,
  message_count integer DEFAULT 0,
  tool_call_count integer DEFAULT 0,
  customer_jid text,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.user_profiles (
  id uuid NOT NULL,
  display_name text NOT NULL,
  email text,
  avatar_url text,
  role text DEFAULT 'member'::text,
  preferences jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  department_id uuid,
  manager_id uuid,
  access_level text DEFAULT 'member'::text,
  title text,
  google_avatar text
);

CREATE TABLE IF NOT EXISTS public.vertical_templates (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  vertical_id text NOT NULL,
  vertical_name text NOT NULL,
  domain_prompt text NOT NULL,
  progressive_profiling_fields jsonb,
  escalation_triggers text[],
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.wa_learning_jobs (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid,
  import_type character varying(50) NOT NULL,
  status character varying(50) DEFAULT 'processing'::character varying,
  raw_message_count integer DEFAULT 0,
  qa_pairs_extracted integer DEFAULT 0,
  faq_count integer DEFAULT 0,
  tone_detected character varying(100),
  suggested_system_prompt text,
  suggested_templates jsonb DEFAULT '[]'::jsonb,
  error_message text,
  file_url text,
  created_at timestamp with time zone DEFAULT now(),
  completed_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS public.web_support_tickets (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  ticket_number text NOT NULL,
  submitter_name text NOT NULL,
  submitter_email text NOT NULL,
  issue_type text DEFAULT 'other'::text NOT NULL,
  message text NOT NULL,
  status text DEFAULT 'open'::text NOT NULL,
  tenant_id uuid,
  notes text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.whatsapp_devices (
  tenant_id uuid NOT NULL,
  device_id text NOT NULL,
  device_name character varying(100),
  phone_number character varying(50),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  whatsapp_jid text
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_app_state_mutation_macs (
  jid text NOT NULL,
  name text NOT NULL,
  version bigint NOT NULL,
  index_mac bytea NOT NULL,
  value_mac bytea NOT NULL
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_app_state_sync_keys (
  jid text NOT NULL,
  key_id bytea NOT NULL,
  key_data bytea NOT NULL,
  "timestamp" bigint NOT NULL,
  fingerprint bytea NOT NULL
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_app_state_version (
  jid text NOT NULL,
  name text NOT NULL,
  version bigint NOT NULL,
  hash bytea NOT NULL
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_chat_settings (
  our_jid text NOT NULL,
  chat_jid text NOT NULL,
  muted_until bigint DEFAULT 0 NOT NULL,
  pinned boolean DEFAULT false NOT NULL,
  archived boolean DEFAULT false NOT NULL
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_contacts (
  our_jid text NOT NULL,
  their_jid text NOT NULL,
  first_name text,
  full_name text,
  push_name text,
  business_name text,
  redacted_phone text
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_device (
  jid text NOT NULL,
  lid text,
  facebook_uuid uuid,
  registration_id bigint NOT NULL,
  noise_key bytea NOT NULL,
  identity_key bytea NOT NULL,
  signed_pre_key bytea NOT NULL,
  signed_pre_key_id integer NOT NULL,
  signed_pre_key_sig bytea NOT NULL,
  adv_key bytea NOT NULL,
  adv_details bytea NOT NULL,
  adv_account_sig bytea NOT NULL,
  adv_account_sig_key bytea NOT NULL,
  adv_device_sig bytea NOT NULL,
  platform text DEFAULT ''::text NOT NULL,
  business_name text DEFAULT ''::text NOT NULL,
  push_name text DEFAULT ''::text NOT NULL,
  lid_migration_ts bigint DEFAULT 0 NOT NULL
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_event_buffer (
  our_jid text NOT NULL,
  ciphertext_hash bytea NOT NULL,
  plaintext bytea,
  server_timestamp bigint NOT NULL,
  insert_timestamp bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_identity_keys (
  our_jid text NOT NULL,
  their_id text NOT NULL,
  identity bytea NOT NULL
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_lid_map (
  lid text NOT NULL,
  pn text NOT NULL
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_message_secrets (
  our_jid text NOT NULL,
  chat_jid text NOT NULL,
  sender_jid text NOT NULL,
  message_id text NOT NULL,
  key bytea NOT NULL
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_pre_keys (
  jid text NOT NULL,
  key_id integer NOT NULL,
  key bytea NOT NULL,
  uploaded boolean NOT NULL
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_privacy_tokens (
  our_jid text NOT NULL,
  their_jid text NOT NULL,
  token bytea NOT NULL,
  "timestamp" bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_sender_keys (
  our_jid text NOT NULL,
  chat_id text NOT NULL,
  sender_id text NOT NULL,
  sender_key bytea NOT NULL
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_sessions (
  our_jid text NOT NULL,
  their_id text NOT NULL,
  session bytea
);

CREATE TABLE IF NOT EXISTS public.whatsmeow_version (
  version integer,
  compat integer
);


-- ─────────────── PRIMARY KEYS + UNIQUE CONSTRAINTS ────────────────
DO $$ BEGIN ALTER TABLE public."Conversation" ADD CONSTRAINT "Conversation_pkey" PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public."Message" ADD CONSTRAINT "Message_pkey" PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public."SearchRun" ADD CONSTRAINT "SearchRun_pkey" PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public."User" ADD CONSTRAINT "User_email_key" UNIQUE (email); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public."User" ADD CONSTRAINT "User_pkey" PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public."User" ADD CONSTRAINT "User_supabaseId_key" UNIQUE ("supabaseId"); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.action_items ADD CONSTRAINT action_items_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.admin_audit_log ADD CONSTRAINT admin_audit_log_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_activity ADD CONSTRAINT agent_activity_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_commands ADD CONSTRAINT agent_commands_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_connections ADD CONSTRAINT agent_connections_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_conversations ADD CONSTRAINT agent_conversations_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_messages ADD CONSTRAINT agent_messages_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_runs ADD CONSTRAINT agent_runs_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_status ADD CONSTRAINT agent_status_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_trajectory ADD CONSTRAINT agent_trajectory_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.analytics ADD CONSTRAINT analytics_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.analytics ADD CONSTRAINT unique_tenant_date UNIQUE (tenant_id, date); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.api_keys ADD CONSTRAINT api_keys_key_hash_key UNIQUE (key_hash); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.api_keys ADD CONSTRAINT api_keys_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.audit_log ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.availability_overrides ADD CONSTRAINT availability_overrides_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.availability_overrides ADD CONSTRAINT unique_availability_override UNIQUE (tenant_id, date); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_agent_runs ADD CONSTRAINT bjx_agent_runs_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_content_drafts ADD CONSTRAINT bjx_content_drafts_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_listener_opportunities ADD CONSTRAINT bjx_listener_opportunities_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_listener_opportunities ADD CONSTRAINT bjx_listener_opportunities_source_source_url_key UNIQUE (source, source_url); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_prospect_scores ADD CONSTRAINT bjx_prospect_scores_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_prospects ADD CONSTRAINT bjx_prospects_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_prospects ADD CONSTRAINT bjx_prospects_source_source_id_key UNIQUE (source, source_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_publish_log ADD CONSTRAINT bjx_publish_log_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_review_queue ADD CONSTRAINT bjx_review_queue_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_touches ADD CONSTRAINT bjx_touches_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.blocked_numbers ADD CONSTRAINT blocked_numbers_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.blocked_numbers ADD CONSTRAINT blocked_numbers_tenant_id_customer_jid_key UNIQUE (tenant_id, customer_jid); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.business_profiles ADD CONSTRAINT business_profiles_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.business_profiles ADD CONSTRAINT unique_tenant_profile UNIQUE (tenant_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.calendar_events ADD CONSTRAINT calendar_events_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.calendar_events ADD CONSTRAINT calendar_events_user_id_google_event_id_key UNIQUE (user_id, google_event_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_availability ADD CONSTRAINT call_availability_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_availability ADD CONSTRAINT unique_availability_slot UNIQUE (tenant_id, day_of_week, start_time); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_bookings ADD CONSTRAINT call_bookings_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_logs ADD CONSTRAINT call_logs_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_settings ADD CONSTRAINT call_settings_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_settings ADD CONSTRAINT call_settings_tenant_id_key UNIQUE (tenant_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_types ADD CONSTRAINT call_types_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_types ADD CONSTRAINT unique_call_type_name UNIQUE (tenant_id, name); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.campaign_analytics ADD CONSTRAINT campaign_analytics_campaign_id_date_key UNIQUE (campaign_id, date); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.campaign_analytics ADD CONSTRAINT campaign_analytics_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.campaign_templates ADD CONSTRAINT campaign_templates_campaign_id_sequence_step_key UNIQUE (campaign_id, sequence_step); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.campaign_templates ADD CONSTRAINT campaign_templates_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.campaigns ADD CONSTRAINT campaigns_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.chats ADD CONSTRAINT chats_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.checklist_state ADD CONSTRAINT checklist_state_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.client_configs ADD CONSTRAINT client_configs_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.client_configs ADD CONSTRAINT client_configs_tenant_id_key UNIQUE (tenant_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.command_center_state ADD CONSTRAINT command_center_state_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.command_center_state ADD CONSTRAINT command_center_state_state_key_key UNIQUE (state_key); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.contact_segment_members ADD CONSTRAINT contact_segment_members_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.contact_segment_members ADD CONSTRAINT contact_segment_members_segment_id_contact_id_key UNIQUE (segment_id, contact_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.contact_segments ADD CONSTRAINT contact_segments_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.contact_segments ADD CONSTRAINT contact_segments_tenant_id_name_key UNIQUE (tenant_id, name); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.contacts ADD CONSTRAINT contacts_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.contacts ADD CONSTRAINT contacts_tenant_jid_unique UNIQUE (tenant_id, jid); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.conversation_logs ADD CONSTRAINT conversation_logs_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.conversations ADD CONSTRAINT conversations_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.conversion_events ADD CONSTRAINT conversion_events_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.customer_activity ADD CONSTRAINT customer_activity_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.customer_activity ADD CONSTRAINT customer_activity_tenant_id_customer_jid_key UNIQUE (tenant_id, customer_jid); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.customer_memory ADD CONSTRAINT customer_memory_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.customer_memory ADD CONSTRAINT customer_memory_tenant_id_chat_jid_key UNIQUE (tenant_id, chat_jid); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.daily_digests ADD CONSTRAINT daily_digests_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.daily_digests ADD CONSTRAINT daily_digests_user_id_digest_date_type_key UNIQUE (user_id, digest_date, type); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.dashboard_views ADD CONSTRAINT dashboard_views_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.data_request_deletions ADD CONSTRAINT data_request_deletions_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.decisions ADD CONSTRAINT decisions_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.departments ADD CONSTRAINT departments_name_key UNIQUE (name); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.departments ADD CONSTRAINT departments_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.device_sessions ADD CONSTRAINT device_sessions_device_id_key UNIQUE (device_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.device_sessions ADD CONSTRAINT device_sessions_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.drive_documents ADD CONSTRAINT drive_documents_google_file_id_key UNIQUE (google_file_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.drive_documents ADD CONSTRAINT drive_documents_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.email_summaries ADD CONSTRAINT email_summaries_gmail_message_id_key UNIQUE (gmail_message_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.email_summaries ADD CONSTRAINT email_summaries_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.email_templates ADD CONSTRAINT email_templates_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.email_templates ADD CONSTRAINT email_templates_tenant_type_unique UNIQUE (tenant_id, template_type); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.email_verification_tokens ADD CONSTRAINT email_verification_tokens_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.email_verification_tokens ADD CONSTRAINT email_verification_tokens_token_key UNIQUE (token); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalation_actions ADD CONSTRAINT escalation_actions_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalation_notifications ADD CONSTRAINT escalation_notifications_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalations ADD CONSTRAINT escalations_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.extracted_items ADD CONSTRAINT extracted_items_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.feedback ADD CONSTRAINT feedback_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.follow_ups ADD CONSTRAINT follow_ups_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.google_sheets_sync ADD CONSTRAINT google_sheets_sync_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.google_sheets_sync ADD CONSTRAINT unique_tenant_spreadsheet UNIQUE (tenant_id, spreadsheet_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.handover_agents ADD CONSTRAINT handover_agents_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.help_tickets ADD CONSTRAINT help_tickets_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.holiday_exceptions ADD CONSTRAINT holiday_exceptions_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.holiday_exceptions ADD CONSTRAINT unique_holiday_per_tenant UNIQUE (tenant_id, date); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.inbox_copilot_events ADD CONSTRAINT inbox_copilot_events_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.industry_kb_templates ADD CONSTRAINT industry_kb_templates_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.industry_kb_templates ADD CONSTRAINT industry_kb_templates_vertical_sub_vertical_language_key UNIQUE (vertical, sub_vertical, language); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.jid_mappings ADD CONSTRAINT jid_mappings_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.jid_mappings ADD CONSTRAINT uq_jid_mappings_tenant_lid UNIQUE (tenant_id, lid_jid); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_base ADD CONSTRAINT knowledge_base_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_bases ADD CONSTRAINT knowledge_bases_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_chunks ADD CONSTRAINT knowledge_chunks_knowledge_base_id_chunk_index_key UNIQUE (knowledge_base_id, chunk_index); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_chunks ADD CONSTRAINT knowledge_chunks_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_doc_versions ADD CONSTRAINT knowledge_doc_versions_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_documents ADD CONSTRAINT knowledge_documents_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_sync_jobs ADD CONSTRAINT knowledge_sync_jobs_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.lead_followups ADD CONSTRAINT lead_followups_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.leads ADD CONSTRAINT leads_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.link_clicks ADD CONSTRAINT link_clicks_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.llm_usage ADD CONSTRAINT llm_usage_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.media_library ADD CONSTRAINT media_library_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_blockers ADD CONSTRAINT meeting_blockers_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_decisions ADD CONSTRAINT meeting_decisions_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_followups ADD CONSTRAINT meeting_followups_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_minutes ADD CONSTRAINT meeting_minutes_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meetings ADD CONSTRAINT meetings_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.message_reasons ADD CONSTRAINT message_reasons_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.message_templates ADD CONSTRAINT message_templates_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.message_templates ADD CONSTRAINT unique_template_per_tenant_source UNIQUE (tenant_id, template_name, source); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.messages ADD CONSTRAINT messages_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.notification_groups ADD CONSTRAINT notification_groups_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.notification_groups ADD CONSTRAINT notification_groups_tenant_id_group_type_key UNIQUE (tenant_id, group_type); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.notification_logs ADD CONSTRAINT notification_logs_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.notifications ADD CONSTRAINT notifications_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.onboarding_progress ADD CONSTRAINT onboarding_progress_pkey PRIMARY KEY (tenant_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.onboarding_sessions ADD CONSTRAINT onboarding_sessions_pkey PRIMARY KEY (token); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outbound_queue ADD CONSTRAINT outbound_queue_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outreach_campaign_configs ADD CONSTRAINT outreach_campaign_configs_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outreach_campaign_configs ADD CONSTRAINT outreach_campaign_configs_tenant_id_campaign_id_key UNIQUE (tenant_id, campaign_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outreach_consent_log ADD CONSTRAINT outreach_consent_log_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outreach_logs ADD CONSTRAINT outreach_logs_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.owner_commands ADD CONSTRAINT owner_commands_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.owner_devices ADD CONSTRAINT owner_devices_device_jid_key UNIQUE (device_jid); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.owner_devices ADD CONSTRAINT owner_devices_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.owner_notifications ADD CONSTRAINT owner_notifications_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.payment_transactions ADD CONSTRAINT payment_transactions_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.personas ADD CONSTRAINT personas_persona_key_key UNIQUE (persona_key); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.personas ADD CONSTRAINT personas_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.platform_admins ADD CONSTRAINT platform_admins_pkey PRIMARY KEY (user_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.projects ADD CONSTRAINT projects_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.proposals ADD CONSTRAINT proposals_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.raw_events ADD CONSTRAINT raw_events_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.response_coordinator_state ADD CONSTRAINT response_coordinator_state_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.response_coordinator_state ADD CONSTRAINT response_coordinator_state_tenant_id_chat_jid_key UNIQUE (tenant_id, chat_jid); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.scheduled_messages ADD CONSTRAINT scheduled_messages_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.shared_briefs ADD CONSTRAINT shared_briefs_pkey PRIMARY KEY (token); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.shared_context ADD CONSTRAINT shared_context_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.sheet_data ADD CONSTRAINT sheet_data_google_sheet_id_sheet_name_range_key UNIQUE (google_sheet_id, sheet_name, range); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.sheet_data ADD CONSTRAINT sheet_data_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.short_links ADD CONSTRAINT short_links_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.short_links ADD CONSTRAINT short_links_slug_key UNIQUE (slug); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.silence_rules ADD CONSTRAINT silence_rules_pkey PRIMARY KEY (tenant_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.subscription_plans ADD CONSTRAINT subscription_plans_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.subscription_plans ADD CONSTRAINT subscription_plans_plan_code_key UNIQUE (plan_code); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.system_metrics ADD CONSTRAINT system_metrics_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tasks ADD CONSTRAINT tasks_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.team_activity ADD CONSTRAINT team_activity_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.team_members ADD CONSTRAINT team_members_email_key UNIQUE (email); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.team_members ADD CONSTRAINT team_members_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_action_policy ADD CONSTRAINT tenant_action_policy_pkey PRIMARY KEY (tenant_id, tool_name); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_calendars ADD CONSTRAINT tenant_calendars_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_calendars ADD CONSTRAINT tenant_calendars_tenant_id_provider_key UNIQUE (tenant_id, provider); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_email_config ADD CONSTRAINT tenant_email_config_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_email_config ADD CONSTRAINT tenant_email_config_tenant_id_key UNIQUE (tenant_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_integrations ADD CONSTRAINT tenant_integrations_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_integrations ADD CONSTRAINT tenant_integrations_tenant_id_integration_id_key UNIQUE (tenant_id, integration_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_kb_template_instances ADD CONSTRAINT tenant_kb_template_instances_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_kb_template_instances ADD CONSTRAINT tenant_kb_template_instances_tenant_id_template_id_key UNIQUE (tenant_id, template_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_metrics ADD CONSTRAINT tenant_metrics_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_setup_progress ADD CONSTRAINT tenant_setup_progress_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_setup_progress ADD CONSTRAINT tenant_setup_progress_tenant_id_key UNIQUE (tenant_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_users ADD CONSTRAINT tenant_users_pkey1 PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_users ADD CONSTRAINT tenant_users_tenant_id_user_id_key UNIQUE (tenant_id, user_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_users_legacy ADD CONSTRAINT tenant_users_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_users_legacy ADD CONSTRAINT tenant_users_tenant_id_email_key UNIQUE (tenant_id, email); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_verticals ADD CONSTRAINT tenant_verticals_pkey PRIMARY KEY (tenant_id, vertical_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenants ADD CONSTRAINT tenants_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenants ADD CONSTRAINT tenants_signup_token_key UNIQUE (signup_token); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenants ADD CONSTRAINT tenants_slug_key UNIQUE (slug); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenants ADD CONSTRAINT tenants_telegram_username_key UNIQUE (telegram_username); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenants ADD CONSTRAINT tenants_whatsapp_number_unique UNIQUE (whatsapp_number); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.trial_notifications ADD CONSTRAINT trial_notifications_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.trial_notifications ADD CONSTRAINT unique_notification UNIQUE (tenant_id, notification_type); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.usage_tracking ADD CONSTRAINT usage_tracking_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.user_profiles ADD CONSTRAINT user_profiles_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.vertical_templates ADD CONSTRAINT vertical_templates_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.vertical_templates ADD CONSTRAINT vertical_templates_vertical_id_key UNIQUE (vertical_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.wa_learning_jobs ADD CONSTRAINT wa_learning_jobs_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.web_support_tickets ADD CONSTRAINT web_support_tickets_pkey PRIMARY KEY (id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsapp_devices ADD CONSTRAINT uq_whatsapp_devices_tenant UNIQUE (tenant_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsapp_devices ADD CONSTRAINT whatsapp_devices_pkey PRIMARY KEY (tenant_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_app_state_mutation_macs ADD CONSTRAINT whatsmeow_app_state_mutation_macs_pkey PRIMARY KEY (jid, name, version, index_mac); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_app_state_sync_keys ADD CONSTRAINT whatsmeow_app_state_sync_keys_pkey PRIMARY KEY (jid, key_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_app_state_version ADD CONSTRAINT whatsmeow_app_state_version_pkey PRIMARY KEY (jid, name); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_chat_settings ADD CONSTRAINT whatsmeow_chat_settings_pkey PRIMARY KEY (our_jid, chat_jid); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_contacts ADD CONSTRAINT whatsmeow_contacts_pkey PRIMARY KEY (our_jid, their_jid); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_device ADD CONSTRAINT whatsmeow_device_pkey PRIMARY KEY (jid); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_event_buffer ADD CONSTRAINT whatsmeow_event_buffer_pkey PRIMARY KEY (our_jid, ciphertext_hash); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_identity_keys ADD CONSTRAINT whatsmeow_identity_keys_pkey PRIMARY KEY (our_jid, their_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_lid_map ADD CONSTRAINT whatsmeow_lid_map_pkey PRIMARY KEY (lid); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_lid_map ADD CONSTRAINT whatsmeow_lid_map_pn_key UNIQUE (pn); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_message_secrets ADD CONSTRAINT whatsmeow_message_secrets_pkey PRIMARY KEY (our_jid, chat_jid, sender_jid, message_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_pre_keys ADD CONSTRAINT whatsmeow_pre_keys_pkey PRIMARY KEY (jid, key_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_privacy_tokens ADD CONSTRAINT whatsmeow_privacy_tokens_pkey PRIMARY KEY (our_jid, their_jid); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_sender_keys ADD CONSTRAINT whatsmeow_sender_keys_pkey PRIMARY KEY (our_jid, chat_id, sender_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_sessions ADD CONSTRAINT whatsmeow_sessions_pkey PRIMARY KEY (our_jid, their_id); EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL; END $$;


-- ─────────────── FOREIGN KEYS + CHECK CONSTRAINTS ─────────────────
-- 30-foreign-keys.sql
-- FOREIGN KEY and CHECK constraints for schema "public", extracted from the live Supabase project.
-- 260 constraints. Each wrapped in a DO block so a missing referenced table does not abort the file.

DO $$ BEGIN ALTER TABLE public."Conversation" ADD CONSTRAINT "Conversation_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public."Message" ADD CONSTRAINT "Message_conversationId_fkey" FOREIGN KEY ("conversationId") REFERENCES "Conversation"(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public."SearchRun" ADD CONSTRAINT "SearchRun_conversationId_fkey" FOREIGN KEY ("conversationId") REFERENCES "Conversation"(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.action_items ADD CONSTRAINT action_items_assigned_to_fkey FOREIGN KEY (assigned_to) REFERENCES auth.users(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.action_items ADD CONSTRAINT action_items_department_id_fkey FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.action_items ADD CONSTRAINT action_items_meeting_id_fkey FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.action_items ADD CONSTRAINT action_items_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES team_members(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.action_items ADD CONSTRAINT action_items_priority_check CHECK ((priority = ANY (ARRAY['critical'::text, 'high'::text, 'medium'::text, 'low'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.action_items ADD CONSTRAINT action_items_status_check CHECK ((status = ANY (ARRAY['open'::text, 'in_progress'::text, 'blocked'::text, 'done'::text, 'cancelled'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.action_items ADD CONSTRAINT action_items_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_activity ADD CONSTRAINT agent_activity_connection_id_fkey FOREIGN KEY (connection_id) REFERENCES agent_connections(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_activity ADD CONSTRAINT agent_activity_event_type_check CHECK ((event_type = ANY (ARRAY['message'::text, 'task'::text, 'error'::text, 'restart'::text, 'deploy'::text, 'health_check'::text, 'custom'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_activity ADD CONSTRAINT agent_activity_severity_check CHECK ((severity = ANY (ARRAY['info'::text, 'warning'::text, 'error'::text, 'critical'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_commands ADD CONSTRAINT agent_commands_issued_by_fkey FOREIGN KEY (issued_by) REFERENCES auth.users(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_commands ADD CONSTRAINT agent_commands_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'acknowledged'::text, 'executing'::text, 'completed'::text, 'failed'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_connections ADD CONSTRAINT agent_connections_agent_type_check CHECK ((agent_type = ANY (ARRAY['openclaw'::text, 'hermes'::text, 'claude_code'::text, 'hyperagent'::text, 'custom'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_connections ADD CONSTRAINT agent_connections_auth_type_check CHECK ((auth_type = ANY (ARRAY['basic'::text, 'bearer'::text, 'api_key'::text, 'none'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_connections ADD CONSTRAINT agent_connections_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_conversations ADD CONSTRAINT agent_conversations_department_id_fkey FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_conversations ADD CONSTRAINT agent_conversations_status_check CHECK ((status = ANY (ARRAY['active'::text, 'archived'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_conversations ADD CONSTRAINT agent_conversations_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_messages ADD CONSTRAINT agent_messages_content_type_check CHECK ((content_type = ANY (ARRAY['text'::text, 'markdown'::text, 'json'::text, 'ui_component'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_messages ADD CONSTRAINT agent_messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES agent_conversations(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_messages ADD CONSTRAINT agent_messages_sender_type_check CHECK ((sender_type = ANY (ARRAY['user'::text, 'agent'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_status ADD CONSTRAINT agent_status_connection_id_fkey FOREIGN KEY (connection_id) REFERENCES agent_connections(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_status ADD CONSTRAINT agent_status_status_check CHECK ((status = ANY (ARRAY['online'::text, 'offline'::text, 'degraded'::text, 'error'::text, 'unknown'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.agent_trajectory ADD CONSTRAINT agent_trajectory_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.analytics ADD CONSTRAINT analytics_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.api_keys ADD CONSTRAINT api_keys_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.api_keys ADD CONSTRAINT valid_scopes CHECK ((scopes <@ ARRAY['read'::text, 'write'::text, 'admin'::text])); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.audit_log ADD CONSTRAINT audit_log_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES auth.users(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.audit_log ADD CONSTRAINT audit_log_actor_type_check CHECK ((actor_type = ANY (ARRAY['platform_admin'::text, 'service'::text, 'mcp'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.availability_overrides ADD CONSTRAINT valid_override_time_range CHECK ((((start_time IS NULL) AND (end_time IS NULL)) OR ((start_time IS NOT NULL) AND (end_time IS NOT NULL) AND (end_time > start_time)))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_content_drafts ADD CONSTRAINT bjx_content_drafts_pillar_id_fkey FOREIGN KEY (pillar_id) REFERENCES bjx_content_drafts(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_listener_opportunities ADD CONSTRAINT bjx_listener_opportunities_match_score_check CHECK (((match_score >= 0) AND (match_score <= 100))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_listener_opportunities ADD CONSTRAINT bjx_listener_opportunities_queued_review_id_fkey FOREIGN KEY (queued_review_id) REFERENCES bjx_review_queue(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_prospect_scores ADD CONSTRAINT bjx_prospect_scores_fit_score_check CHECK (((fit_score >= 0) AND (fit_score <= 100))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_prospect_scores ADD CONSTRAINT bjx_prospect_scores_prospect_id_fkey FOREIGN KEY (prospect_id) REFERENCES bjx_prospects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_publish_log ADD CONSTRAINT bjx_publish_log_content_draft_id_fkey FOREIGN KEY (content_draft_id) REFERENCES bjx_content_drafts(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_review_queue ADD CONSTRAINT bjx_review_queue_source_pillar_id_fkey FOREIGN KEY (source_pillar_id) REFERENCES bjx_content_drafts(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_review_queue ADD CONSTRAINT bjx_review_queue_source_prospect_id_fkey FOREIGN KEY (source_prospect_id) REFERENCES bjx_prospects(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.bjx_touches ADD CONSTRAINT bjx_touches_prospect_id_fkey FOREIGN KEY (prospect_id) REFERENCES bjx_prospects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.blocked_numbers ADD CONSTRAINT blocked_numbers_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.business_profiles ADD CONSTRAINT business_profiles_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.calendar_events ADD CONSTRAINT calendar_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_availability ADD CONSTRAINT valid_day_of_week CHECK (((day_of_week >= 0) AND (day_of_week <= 6))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_availability ADD CONSTRAINT valid_time_range CHECK ((end_time > start_time)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_bookings ADD CONSTRAINT valid_call_status CHECK ((status = ANY (ARRAY['scheduled'::text, 'confirmed'::text, 'cancelled'::text, 'completed'::text, 'no_show'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_bookings ADD CONSTRAINT valid_duration CHECK (((duration_minutes > 0) AND (duration_minutes <= 480))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_settings ADD CONSTRAINT valid_advance_booking_days CHECK (((advance_booking_days >= 0) AND (advance_booking_days <= 365))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_settings ADD CONSTRAINT valid_buffer_minutes CHECK (((buffer_minutes >= 0) AND (buffer_minutes <= 60))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_settings ADD CONSTRAINT valid_max_calls_per_day CHECK (((max_calls_per_day > 0) AND (max_calls_per_day <= 24))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_settings ADD CONSTRAINT valid_max_calls_per_hour CHECK (((max_calls_per_hour > 0) AND (max_calls_per_hour <= 6))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.call_types ADD CONSTRAINT valid_call_type_duration CHECK (((duration_minutes > 0) AND (duration_minutes <= 480))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.campaign_analytics ADD CONSTRAINT campaign_analytics_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.campaign_templates ADD CONSTRAINT campaign_templates_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.campaign_templates ADD CONSTRAINT campaign_templates_template_id_fkey FOREIGN KEY (template_id) REFERENCES message_templates(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.campaigns ADD CONSTRAINT campaigns_campaign_type_check CHECK ((campaign_type = ANY (ARRAY['outreach'::text, 'nurture'::text, 'reactivation'::text, 'event'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.campaigns ADD CONSTRAINT campaigns_sequence_type_check CHECK ((sequence_type = ANY (ARRAY['single'::text, 'drip'::text, 'smart'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.campaigns ADD CONSTRAINT campaigns_status_check CHECK ((status = ANY (ARRAY['draft'::text, 'scheduled'::text, 'running'::text, 'paused'::text, 'completed'::text, 'cancelled'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.campaigns ADD CONSTRAINT campaigns_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.client_configs ADD CONSTRAINT client_configs_client_type_check CHECK ((client_type = ANY (ARRAY['gaming'::text, 'ecommerce'::text, 'support'::text, 'general'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.client_configs ADD CONSTRAINT client_configs_manglish_level_check CHECK ((manglish_level = ANY (ARRAY['none'::text, 'light'::text, 'medium'::text, 'heavy'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.client_configs ADD CONSTRAINT client_configs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.client_configs ADD CONSTRAINT client_configs_tone_check CHECK ((tone = ANY (ARRAY['professional'::text, 'casual'::text, 'hype'::text, 'friendly'::text, 'formal'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.contact_segment_members ADD CONSTRAINT contact_segment_members_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.contact_segment_members ADD CONSTRAINT contact_segment_members_segment_id_fkey FOREIGN KEY (segment_id) REFERENCES contact_segments(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.contact_segments ADD CONSTRAINT contact_segments_segment_type_check CHECK ((segment_type = ANY (ARRAY['static'::text, 'dynamic'::text, 'imported'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.contact_segments ADD CONSTRAINT contact_segments_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.contacts ADD CONSTRAINT contacts_campaign_config_id_fkey FOREIGN KEY (campaign_config_id) REFERENCES outreach_campaign_configs(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.contacts ADD CONSTRAINT contacts_lead_temperature_check CHECK ((lead_temperature = ANY (ARRAY['cold'::text, 'warm'::text, 'hot'::text, 'converted'::text, 'lost'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.conversation_logs ADD CONSTRAINT conversation_logs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.conversations ADD CONSTRAINT conversations_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.conversations ADD CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.conversion_events ADD CONSTRAINT conversion_events_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES conversations(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.conversion_events ADD CONSTRAINT conversion_events_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.conversion_events ADD CONSTRAINT valid_event_type CHECK ((event_type = ANY (ARRAY['lead_captured'::text, 'appointment_booked'::text, 'payment_received'::text, 'form_submitted'::text, 'trial_started'::text, 'subscription_purchased'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.customer_memory ADD CONSTRAINT customer_memory_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.daily_digests ADD CONSTRAINT daily_digests_type_check CHECK ((type = ANY (ARRAY['morning_brief'::text, 'eod_report'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.daily_digests ADD CONSTRAINT daily_digests_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.dashboard_views ADD CONSTRAINT dashboard_views_department_id_fkey FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.dashboard_views ADD CONSTRAINT dashboard_views_view_type_check CHECK ((view_type = ANY (ARRAY['table'::text, 'chart'::text, 'kanban'::text, 'timeline'::text, 'document'::text, 'chat'::text, 'form'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.dashboard_views ADD CONSTRAINT dashboard_views_visibility_check CHECK ((visibility = ANY (ARRAY['private'::text, 'department'::text, 'org'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.data_request_deletions ADD CONSTRAINT data_request_deletions_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'processing'::text, 'done'::text, 'cancelled'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.decisions ADD CONSTRAINT decisions_decision_maker_fkey FOREIGN KEY (decision_maker) REFERENCES auth.users(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.decisions ADD CONSTRAINT decisions_department_id_fkey FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.decisions ADD CONSTRAINT decisions_status_check CHECK ((status = ANY (ARRAY['proposed'::text, 'discussing'::text, 'decided'::text, 'implemented'::text, 'revisited'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.departments ADD CONSTRAINT departments_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES departments(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.device_sessions ADD CONSTRAINT device_sessions_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'active'::text, 'disconnected'::text, 'expired'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.device_sessions ADD CONSTRAINT device_sessions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.drive_documents ADD CONSTRAINT drive_documents_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES auth.users(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.email_summaries ADD CONSTRAINT email_summaries_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.email_templates ADD CONSTRAINT email_templates_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.email_verification_tokens ADD CONSTRAINT email_verification_tokens_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.email_verification_tokens ADD CONSTRAINT valid_resent_count CHECK ((resent_count <= 5)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalation_actions ADD CONSTRAINT escalation_actions_escalation_id_fkey FOREIGN KEY (escalation_id) REFERENCES escalations(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalation_actions ADD CONSTRAINT escalation_actions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalation_notifications ADD CONSTRAINT escalation_notifications_channel_check CHECK ((channel = ANY (ARRAY['email'::text, 'sms'::text, 'whatsapp'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalation_notifications ADD CONSTRAINT escalation_notifications_escalation_id_fkey FOREIGN KEY (escalation_id) REFERENCES escalations(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalation_notifications ADD CONSTRAINT escalation_notifications_status_check CHECK ((status = ANY (ARRAY['sent'::text, 'failed'::text, 'pending'::text, 'retrying'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalation_notifications ADD CONSTRAINT escalation_notifications_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalations ADD CONSTRAINT escalations_assigned_agent_id_fkey FOREIGN KEY (assigned_agent_id) REFERENCES handover_agents(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalations ADD CONSTRAINT escalations_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalations ADD CONSTRAINT valid_escalation_timeout CHECK (((escalation_timeout_minutes > 0) OR (escalation_timeout_minutes IS NULL))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalations ADD CONSTRAINT valid_priority CHECK ((priority = ANY (ARRAY['low'::text, 'normal'::text, 'high'::text, 'urgent'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalations ADD CONSTRAINT valid_satisfaction_score CHECK (((customer_satisfaction_score IS NULL) OR ((customer_satisfaction_score >= 1) AND (customer_satisfaction_score <= 5)))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalations ADD CONSTRAINT valid_status CHECK ((status = ANY (ARRAY['pending'::text, 'in_progress'::text, 'resolved'::text, 'cancelled'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.escalations ADD CONSTRAINT warning_consistency CHECK ((((warning_sent = true) AND (warning_sent_at IS NOT NULL)) OR ((warning_sent = false) AND (warning_sent_at IS NULL)))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.extracted_items ADD CONSTRAINT extracted_items_raw_event_id_fkey FOREIGN KEY (raw_event_id) REFERENCES raw_events(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.feedback ADD CONSTRAINT feedback_rating_check CHECK (((rating >= 1) AND (rating <= 5))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.feedback ADD CONSTRAINT feedback_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.follow_ups ADD CONSTRAINT follow_ups_lead_status_check CHECK ((lead_status = ANY (ARRAY['cold'::text, 'warm'::text, 'hot'::text, 'qualified'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.follow_ups ADD CONSTRAINT follow_ups_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'sent'::text, 'failed'::text, 'cancelled'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.follow_ups ADD CONSTRAINT follow_ups_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.google_sheets_sync ADD CONSTRAINT google_sheets_sync_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.handover_agents ADD CONSTRAINT handover_agents_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.help_tickets ADD CONSTRAINT help_tickets_priority_check CHECK ((priority = ANY (ARRAY['normal'::text, 'high'::text, 'urgent'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.help_tickets ADD CONSTRAINT help_tickets_status_check CHECK ((status = ANY (ARRAY['open'::text, 'in_progress'::text, 'escalated'::text, 'closed'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.help_tickets ADD CONSTRAINT help_tickets_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.inbox_copilot_events ADD CONSTRAINT inbox_copilot_events_kind_check CHECK ((kind = ANY (ARRAY['suggest'::text, 'accept'::text, 'edit'::text, 'dismiss'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.inbox_copilot_events ADD CONSTRAINT inbox_copilot_events_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.jid_mappings ADD CONSTRAINT jid_mappings_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_base ADD CONSTRAINT knowledge_base_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_base ADD CONSTRAINT knowledge_base_department_id_fkey FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_base ADD CONSTRAINT knowledge_base_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_base ADD CONSTRAINT knowledge_base_visibility_check CHECK ((visibility = ANY (ARRAY['public'::text, 'department'::text, 'private'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_bases ADD CONSTRAINT knowledge_bases_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_bases ADD CONSTRAINT valid_source_type CHECK ((source_type = ANY (ARRAY['google_sheets'::text, 'file_upload'::text, 'manual'::text, 'web_scrape'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_chunks ADD CONSTRAINT knowledge_chunks_knowledge_base_id_fkey FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_chunks ADD CONSTRAINT knowledge_chunks_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_documents ADD CONSTRAINT knowledge_documents_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_documents ADD CONSTRAINT valid_doc_status CHECK ((status = ANY (ARRAY['uploaded'::text, 'processing'::text, 'completed'::text, 'failed'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_sync_jobs ADD CONSTRAINT knowledge_sync_jobs_knowledge_base_id_fkey FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_sync_jobs ADD CONSTRAINT knowledge_sync_jobs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.knowledge_sync_jobs ADD CONSTRAINT valid_sync_status CHECK ((status = ANY (ARRAY['pending'::text, 'running'::text, 'completed'::text, 'failed'::text, 'cancelled'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.leads ADD CONSTRAINT valid_email CHECK ((email ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$'::text)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.leads ADD CONSTRAINT valid_source CHECK ((source = ANY (ARRAY['hero_form'::text, 'cal_booking'::text, 'waitlist'::text, 'whatsapp_cta'::text, 'website'::text, 'referral'::text, 'final_cta_direct'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.leads ADD CONSTRAINT valid_status CHECK ((status = ANY (ARRAY['new'::text, 'contacted'::text, 'qualified'::text, 'customer'::text, 'lost'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.link_clicks ADD CONSTRAINT link_clicks_link_id_fkey FOREIGN KEY (link_id) REFERENCES short_links(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.media_library ADD CONSTRAINT media_library_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_blockers ADD CONSTRAINT meeting_blockers_action_item_id_fkey FOREIGN KEY (action_item_id) REFERENCES action_items(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_blockers ADD CONSTRAINT meeting_blockers_meeting_id_fkey FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_blockers ADD CONSTRAINT meeting_blockers_status_check CHECK ((status = ANY (ARRAY['open'::text, 'escalated'::text, 'resolved'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_decisions ADD CONSTRAINT meeting_decisions_category_check CHECK ((category = ANY (ARRAY['process'::text, 'technical'::text, 'product'::text, 'team'::text, 'financial'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_decisions ADD CONSTRAINT meeting_decisions_meeting_id_fkey FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_followups ADD CONSTRAINT meeting_followups_action_item_id_fkey FOREIGN KEY (action_item_id) REFERENCES action_items(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_followups ADD CONSTRAINT meeting_followups_followup_type_check CHECK ((followup_type = ANY (ARRAY['recap_email'::text, 'calendar_event'::text, 'dm_owner'::text, 'team_post'::text, 'escalation'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_followups ADD CONSTRAINT meeting_followups_meeting_id_fkey FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_followups ADD CONSTRAINT meeting_followups_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'sent'::text, 'failed'::text, 'needs_approval'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_minutes ADD CONSTRAINT meeting_minutes_calendar_event_id_fkey FOREIGN KEY (calendar_event_id) REFERENCES calendar_events(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_minutes ADD CONSTRAINT meeting_minutes_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meeting_minutes ADD CONSTRAINT meeting_minutes_department_id_fkey FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.meetings ADD CONSTRAINT meetings_meeting_type_check CHECK ((meeting_type = ANY (ARRAY['sync'::text, 'standup'::text, 'sprint_review'::text, 'retro'::text, 'planning'::text, 'ad_hoc'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.message_reasons ADD CONSTRAINT message_reasons_channel_check CHECK ((channel = ANY (ARRAY['whatsapp'::text, 'telegram'::text, 'voice'::text, 'sms'::text, 'email'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.message_reasons ADD CONSTRAINT message_reasons_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.message_templates ADD CONSTRAINT message_templates_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.messages ADD CONSTRAINT messages_role_check CHECK ((role = ANY (ARRAY['user'::text, 'assistant'::text, 'system'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.messages ADD CONSTRAINT messages_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.notification_groups ADD CONSTRAINT notification_groups_group_type_check CHECK ((group_type = ANY (ARRAY['escalation_queue'::text, 'hot_leads'::text, 'customer_updates'::text, 'help_tickets'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.notification_groups ADD CONSTRAINT notification_groups_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.notification_logs ADD CONSTRAINT notification_logs_notification_type_check CHECK ((notification_type = ANY (ARRAY['escalation'::text, 'hot_lead'::text, 'new_customer'::text, 'acknowledgment'::text, 'update'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.notification_logs ADD CONSTRAINT notification_logs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.notifications ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.onboarding_progress ADD CONSTRAINT onboarding_progress_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.onboarding_sessions ADD CONSTRAINT onboarding_sessions_status_check CHECK ((status = ANY (ARRAY['pending_whatsapp'::text, 'whatsapp_connected'::text, 'completed'::text, 'expired'::text, 'cancelled'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.onboarding_sessions ADD CONSTRAINT onboarding_sessions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outbound_queue ADD CONSTRAINT outbound_queue_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outbound_queue ADD CONSTRAINT outbound_queue_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outbound_queue ADD CONSTRAINT outbound_queue_message_template_id_fkey FOREIGN KEY (message_template_id) REFERENCES message_templates(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outbound_queue ADD CONSTRAINT outbound_queue_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'scheduled'::text, 'sending'::text, 'sent'::text, 'delivered'::text, 'read'::text, 'failed'::text, 'cancelled'::text, 'blocked'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outbound_queue ADD CONSTRAINT outbound_queue_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outreach_campaign_configs ADD CONSTRAINT outreach_campaign_configs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outreach_consent_log ADD CONSTRAINT outreach_consent_log_channel_check CHECK ((channel = ANY (ARRAY['web_form'::text, 'whatsapp'::text, 'sms'::text, 'email'::text, 'in_person'::text, 'api'::text, 'imported'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outreach_consent_log ADD CONSTRAINT outreach_consent_log_consent_type_check CHECK ((consent_type = ANY (ARRAY['opt_in'::text, 'opt_out'::text, 'transactional'::text, 'imported_legacy'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outreach_consent_log ADD CONSTRAINT outreach_consent_log_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outreach_consent_log ADD CONSTRAINT outreach_consent_log_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outreach_logs ADD CONSTRAINT outreach_logs_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outreach_logs ADD CONSTRAINT outreach_logs_log_type_check CHECK ((log_type = ANY (ARRAY['campaign_start'::text, 'campaign_pause'::text, 'campaign_complete'::text, 'message_queued'::text, 'message_sent'::text, 'message_delivered'::text, 'message_failed'::text, 'reply_received'::text, 'contact_blocked'::text, 'rate_limit_hit'::text, 'error'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outreach_logs ADD CONSTRAINT outreach_logs_queue_id_fkey FOREIGN KEY (queue_id) REFERENCES outbound_queue(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.outreach_logs ADD CONSTRAINT outreach_logs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.owner_commands ADD CONSTRAINT owner_commands_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.owner_notifications ADD CONSTRAINT owner_notifications_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.payment_transactions ADD CONSTRAINT payment_transactions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.personas ADD CONSTRAINT personas_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.platform_admins ADD CONSTRAINT platform_admins_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.platform_admins ADD CONSTRAINT platform_admins_role_check CHECK ((role = ANY (ARRAY['admin'::text, 'superadmin'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.platform_admins ADD CONSTRAINT platform_admins_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.projects ADD CONSTRAINT projects_department_id_fkey FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.projects ADD CONSTRAINT projects_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES auth.users(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.projects ADD CONSTRAINT projects_priority_check CHECK ((priority = ANY (ARRAY['low'::text, 'medium'::text, 'high'::text, 'critical'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.projects ADD CONSTRAINT projects_status_check CHECK ((status = ANY (ARRAY['active'::text, 'paused'::text, 'completed'::text, 'archived'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.proposals ADD CONSTRAINT proposals_extracted_item_id_fkey FOREIGN KEY (extracted_item_id) REFERENCES extracted_items(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.scheduled_messages ADD CONSTRAINT scheduled_messages_template_id_fkey FOREIGN KEY (template_id) REFERENCES message_templates(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.scheduled_messages ADD CONSTRAINT scheduled_messages_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.shared_context ADD CONSTRAINT shared_context_channel_check CHECK ((channel = ANY (ARRAY['whatsapp'::text, 'telegram'::text, 'voice'::text, 'sms'::text, 'email'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.shared_context ADD CONSTRAINT shared_context_role_check CHECK ((role = ANY (ARRAY['user'::text, 'assistant'::text, 'system'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.shared_context ADD CONSTRAINT shared_context_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tasks ADD CONSTRAINT tasks_assigned_to_fkey FOREIGN KEY (assigned_to) REFERENCES auth.users(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tasks ADD CONSTRAINT tasks_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tasks ADD CONSTRAINT tasks_department_id_fkey FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tasks ADD CONSTRAINT tasks_priority_check CHECK ((priority = ANY (ARRAY['low'::text, 'medium'::text, 'high'::text, 'critical'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tasks ADD CONSTRAINT tasks_project_id_fkey FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tasks ADD CONSTRAINT tasks_status_check CHECK ((status = ANY (ARRAY['todo'::text, 'in_progress'::text, 'blocked'::text, 'review'::text, 'done'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.team_activity ADD CONSTRAINT team_activity_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.team_members ADD CONSTRAINT team_members_preferred_channel_check CHECK ((preferred_channel = ANY (ARRAY['email'::text, 'slack'::text, 'gchat'::text, 'whatsapp'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_action_policy ADD CONSTRAINT tenant_action_policy_mode_check CHECK ((mode = ANY (ARRAY['allow'::text, 'confirm'::text, 'deny'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_action_policy ADD CONSTRAINT tenant_action_policy_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_calendars ADD CONSTRAINT tenant_calendars_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_email_config ADD CONSTRAINT tenant_email_config_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_kb_template_instances ADD CONSTRAINT tenant_kb_template_instances_template_id_fkey FOREIGN KEY (template_id) REFERENCES industry_kb_templates(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_kb_template_instances ADD CONSTRAINT tenant_kb_template_instances_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_setup_progress ADD CONSTRAINT tenant_setup_progress_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_users ADD CONSTRAINT tenant_users_tenant_id_fkey1 FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_users ADD CONSTRAINT tenant_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_users_legacy ADD CONSTRAINT tenant_users_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_verticals ADD CONSTRAINT tenant_verticals_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenant_verticals ADD CONSTRAINT tenant_verticals_vertical_id_fkey FOREIGN KEY (vertical_id) REFERENCES vertical_templates(vertical_id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenants ADD CONSTRAINT tenants_status_check CHECK ((status = ANY (ARRAY['active'::text, 'suspended'::text, 'cancelled'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenants ADD CONSTRAINT tenants_subscription_tier_check CHECK ((subscription_tier = ANY (ARRAY['freemium'::text, 'starter'::text, 'pro'::text, 'enterprise'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.tenants ADD CONSTRAINT valid_plan_tier CHECK ((plan_tier = ANY (ARRAY['free'::text, 'pro'::text, 'enterprise'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.trial_notifications ADD CONSTRAINT trial_notifications_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.usage_tracking ADD CONSTRAINT usage_tracking_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.user_profiles ADD CONSTRAINT user_profiles_access_level_check CHECK ((access_level = ANY (ARRAY['executive'::text, 'director'::text, 'manager'::text, 'lead'::text, 'member'::text, 'viewer'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.user_profiles ADD CONSTRAINT user_profiles_department_id_fkey FOREIGN KEY (department_id) REFERENCES departments(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.user_profiles ADD CONSTRAINT user_profiles_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.user_profiles ADD CONSTRAINT user_profiles_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES user_profiles(id); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.user_profiles ADD CONSTRAINT user_profiles_role_check CHECK ((role = ANY (ARRAY['owner'::text, 'admin'::text, 'member'::text, 'viewer'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.wa_learning_jobs ADD CONSTRAINT wa_learning_jobs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.web_support_tickets ADD CONSTRAINT web_support_tickets_issue_type_check CHECK ((issue_type = ANY (ARRAY['connection'::text, 'ai_response'::text, 'billing'::text, 'setup'::text, 'feature'::text, 'other'::text, 'chat-escalation'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.web_support_tickets ADD CONSTRAINT web_support_tickets_status_check CHECK ((status = ANY (ARRAY['open'::text, 'in_progress'::text, 'closed'::text]))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.web_support_tickets ADD CONSTRAINT web_support_tickets_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsapp_devices ADD CONSTRAINT fk_whatsapp_devices_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsapp_devices ADD CONSTRAINT whatsapp_devices_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_app_state_mutation_macs ADD CONSTRAINT whatsmeow_app_state_mutation_macs_index_mac_check CHECK ((length(index_mac) = 32)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_app_state_mutation_macs ADD CONSTRAINT whatsmeow_app_state_mutation_macs_jid_name_fkey FOREIGN KEY (jid, name) REFERENCES whatsmeow_app_state_version(jid, name) ON UPDATE CASCADE ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_app_state_mutation_macs ADD CONSTRAINT whatsmeow_app_state_mutation_macs_value_mac_check CHECK ((length(value_mac) = 32)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_app_state_sync_keys ADD CONSTRAINT whatsmeow_app_state_sync_keys_jid_fkey FOREIGN KEY (jid) REFERENCES whatsmeow_device(jid) ON UPDATE CASCADE ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_app_state_version ADD CONSTRAINT whatsmeow_app_state_version_hash_check CHECK ((length(hash) = 128)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_app_state_version ADD CONSTRAINT whatsmeow_app_state_version_jid_fkey FOREIGN KEY (jid) REFERENCES whatsmeow_device(jid) ON UPDATE CASCADE ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_chat_settings ADD CONSTRAINT whatsmeow_chat_settings_our_jid_fkey FOREIGN KEY (our_jid) REFERENCES whatsmeow_device(jid) ON UPDATE CASCADE ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_contacts ADD CONSTRAINT whatsmeow_contacts_our_jid_fkey FOREIGN KEY (our_jid) REFERENCES whatsmeow_device(jid) ON UPDATE CASCADE ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_device ADD CONSTRAINT whatsmeow_device_adv_account_sig_check CHECK ((length(adv_account_sig) = 64)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_device ADD CONSTRAINT whatsmeow_device_adv_account_sig_key_check CHECK ((length(adv_account_sig_key) = 32)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_device ADD CONSTRAINT whatsmeow_device_adv_device_sig_check CHECK ((length(adv_device_sig) = 64)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_device ADD CONSTRAINT whatsmeow_device_identity_key_check CHECK ((length(identity_key) = 32)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_device ADD CONSTRAINT whatsmeow_device_noise_key_check CHECK ((length(noise_key) = 32)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_device ADD CONSTRAINT whatsmeow_device_registration_id_check CHECK (((registration_id >= 0) AND (registration_id < '4294967296'::bigint))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_device ADD CONSTRAINT whatsmeow_device_signed_pre_key_check CHECK ((length(signed_pre_key) = 32)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_device ADD CONSTRAINT whatsmeow_device_signed_pre_key_id_check CHECK (((signed_pre_key_id >= 0) AND (signed_pre_key_id < 16777216))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_device ADD CONSTRAINT whatsmeow_device_signed_pre_key_sig_check CHECK ((length(signed_pre_key_sig) = 64)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_event_buffer ADD CONSTRAINT whatsmeow_event_buffer_ciphertext_hash_check CHECK ((length(ciphertext_hash) = 32)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_event_buffer ADD CONSTRAINT whatsmeow_event_buffer_our_jid_fkey FOREIGN KEY (our_jid) REFERENCES whatsmeow_device(jid) ON UPDATE CASCADE ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_identity_keys ADD CONSTRAINT whatsmeow_identity_keys_identity_check CHECK ((length(identity) = 32)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_identity_keys ADD CONSTRAINT whatsmeow_identity_keys_our_jid_fkey FOREIGN KEY (our_jid) REFERENCES whatsmeow_device(jid) ON UPDATE CASCADE ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_message_secrets ADD CONSTRAINT whatsmeow_message_secrets_our_jid_fkey FOREIGN KEY (our_jid) REFERENCES whatsmeow_device(jid) ON UPDATE CASCADE ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_pre_keys ADD CONSTRAINT whatsmeow_pre_keys_jid_fkey FOREIGN KEY (jid) REFERENCES whatsmeow_device(jid) ON UPDATE CASCADE ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_pre_keys ADD CONSTRAINT whatsmeow_pre_keys_key_check CHECK ((length(key) = 32)); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_pre_keys ADD CONSTRAINT whatsmeow_pre_keys_key_id_check CHECK (((key_id >= 0) AND (key_id < 16777216))); EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_sender_keys ADD CONSTRAINT whatsmeow_sender_keys_our_jid_fkey FOREIGN KEY (our_jid) REFERENCES whatsmeow_device(jid) ON UPDATE CASCADE ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE public.whatsmeow_sessions ADD CONSTRAINT whatsmeow_sessions_our_jid_fkey FOREIGN KEY (our_jid) REFERENCES whatsmeow_device(jid) ON UPDATE CASCADE ON DELETE CASCADE; EXCEPTION WHEN duplicate_object OR duplicate_table OR undefined_table OR invalid_schema_name OR undefined_column THEN NULL; END $$;


-- ──────────────────────────── INDEXES ─────────────────────────────
CREATE INDEX IF NOT EXISTS idx_action_items_deadline ON public.action_items USING btree (deadline);
CREATE INDEX IF NOT EXISTS idx_action_items_owner ON public.action_items USING btree (owner_id);
CREATE INDEX IF NOT EXISTS idx_action_items_status ON public.action_items USING btree (status);
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_action ON public.admin_audit_log USING btree (action);
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_actor_id ON public.admin_audit_log USING btree (actor_id);
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_created_at ON public.admin_audit_log USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_activity_connection ON public.agent_activity USING btree (connection_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_activity_event_type ON public.agent_activity USING btree (event_type);
CREATE INDEX IF NOT EXISTS idx_agent_activity_severity ON public.agent_activity USING btree (severity);
CREATE INDEX IF NOT EXISTS idx_agent_activity_type ON public.agent_activity USING btree (event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_commands_agent_status ON public.agent_commands USING btree (agent_id, status);
CREATE INDEX IF NOT EXISTS idx_agent_commands_created_at ON public.agent_commands USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_commands_issued_by ON public.agent_commands USING btree (issued_by);
CREATE INDEX IF NOT EXISTS idx_agent_connections_agent_type ON public.agent_connections USING btree (agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_connections_user ON public.agent_connections USING btree (user_id);
CREATE INDEX IF NOT EXISTS idx_agent_conversations_agent_id ON public.agent_conversations USING btree (agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_conversations_status ON public.agent_conversations USING btree (status);
CREATE INDEX IF NOT EXISTS idx_agent_conversations_user_id ON public.agent_conversations USING btree (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_messages_agent_id ON public.agent_messages USING btree (agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_conversation_created ON public.agent_messages USING btree (conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_runs_created ON public.agent_runs USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_status_connection ON public.agent_status USING btree (connection_id, checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_trajectory_tenant_chat ON public.agent_trajectory USING btree (tenant_id, chat_jid, ts);
CREATE INDEX IF NOT EXISTS idx_analytics_date ON public.analytics USING btree (date DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_tenant ON public.analytics USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON public.api_keys USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON public.audit_log USING btree (action, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON public.audit_log USING btree (actor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON public.audit_log USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_target ON public.audit_log USING btree (target_type, target_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_availability_overrides_date ON public.availability_overrides USING btree (date);
CREATE INDEX IF NOT EXISTS idx_availability_overrides_tenant_id ON public.availability_overrides USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_bjx_agent_runs_agent ON public.bjx_agent_runs USING btree (agent_name);
CREATE INDEX IF NOT EXISTS idx_bjx_agent_runs_created ON public.bjx_agent_runs USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bjx_agent_runs_status ON public.bjx_agent_runs USING btree (status);
CREATE INDEX IF NOT EXISTS idx_bjx_content_drafts_kind ON public.bjx_content_drafts USING btree (kind);
CREATE INDEX IF NOT EXISTS idx_bjx_content_drafts_pillar ON public.bjx_content_drafts USING btree (pillar_id);
CREATE INDEX IF NOT EXISTS idx_bjx_content_drafts_scheduled ON public.bjx_content_drafts USING btree (scheduled_for);
CREATE INDEX IF NOT EXISTS idx_bjx_content_drafts_status ON public.bjx_content_drafts USING btree (status);
CREATE INDEX IF NOT EXISTS idx_agent_listener_match ON public.bjx_listener_opportunities USING btree (match_score DESC);
CREATE INDEX IF NOT EXISTS idx_agent_listener_status ON public.bjx_listener_opportunities USING btree (status);
CREATE INDEX IF NOT EXISTS idx_bjx_prospect_scores_fit ON public.bjx_prospect_scores USING btree (fit_score DESC);
CREATE INDEX IF NOT EXISTS idx_bjx_prospect_scores_prospect ON public.bjx_prospect_scores USING btree (prospect_id);
CREATE INDEX IF NOT EXISTS idx_bjx_prospects_area ON public.bjx_prospects USING btree (area);
CREATE INDEX IF NOT EXISTS idx_bjx_prospects_created ON public.bjx_prospects USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bjx_prospects_status ON public.bjx_prospects USING btree (status);
CREATE INDEX IF NOT EXISTS idx_bjx_prospects_vertical ON public.bjx_prospects USING btree (vertical);
CREATE INDEX IF NOT EXISTS idx_bjx_publish_log_draft ON public.bjx_publish_log USING btree (content_draft_id);
CREATE INDEX IF NOT EXISTS idx_bjx_publish_log_status ON public.bjx_publish_log USING btree (status);
CREATE INDEX IF NOT EXISTS idx_bjx_review_queue_expires ON public.bjx_review_queue USING btree (expires_at);
CREATE INDEX IF NOT EXISTS idx_bjx_review_queue_priority ON public.bjx_review_queue USING btree (priority DESC, created_at);
CREATE INDEX IF NOT EXISTS idx_bjx_review_queue_status ON public.bjx_review_queue USING btree (status);
CREATE INDEX IF NOT EXISTS idx_bjx_touches_channel ON public.bjx_touches USING btree (channel);
CREATE INDEX IF NOT EXISTS idx_bjx_touches_prospect ON public.bjx_touches USING btree (prospect_id);
CREATE INDEX IF NOT EXISTS idx_bjx_touches_sent_at ON public.bjx_touches USING btree (sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_blocked_active ON public.blocked_numbers USING btree (is_active);
CREATE INDEX IF NOT EXISTS idx_blocked_expires ON public.blocked_numbers USING btree (expires_at) WHERE (expires_at IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_blocked_jid ON public.blocked_numbers USING btree (customer_jid) WHERE (is_active = true);
CREATE INDEX IF NOT EXISTS idx_blocked_tenant ON public.blocked_numbers USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_start_time ON public.calendar_events USING btree (start_time);
CREATE INDEX IF NOT EXISTS idx_calendar_events_user_id ON public.calendar_events USING btree (user_id, start_time);
CREATE INDEX IF NOT EXISTS idx_call_availability_active ON public.call_availability USING btree (is_active);
CREATE INDEX IF NOT EXISTS idx_call_availability_day ON public.call_availability USING btree (day_of_week);
CREATE INDEX IF NOT EXISTS idx_call_availability_tenant_id ON public.call_availability USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_call_bookings_customer_jid ON public.call_bookings USING btree (customer_jid);
CREATE INDEX IF NOT EXISTS idx_call_bookings_scheduled_date ON public.call_bookings USING btree (scheduled_date);
CREATE INDEX IF NOT EXISTS idx_call_bookings_scheduled_time ON public.call_bookings USING btree (scheduled_time);
CREATE INDEX IF NOT EXISTS idx_call_bookings_status ON public.call_bookings USING btree (status);
CREATE INDEX IF NOT EXISTS idx_call_bookings_tenant_date ON public.call_bookings USING btree (tenant_id, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_call_bookings_tenant_id ON public.call_bookings USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_call_types_active ON public.call_types USING btree (is_active);
CREATE INDEX IF NOT EXISTS idx_call_types_tenant_id ON public.call_types USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_campaign_analytics_date ON public.campaign_analytics USING btree (campaign_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_campaigns_scheduled_start ON public.campaigns USING btree (scheduled_start_at) WHERE (status = 'scheduled'::text);
CREATE INDEX IF NOT EXISTS idx_campaigns_tenant_status ON public.campaigns USING btree (tenant_id, status) WHERE (status = ANY (ARRAY['scheduled'::text, 'running'::text]));
CREATE INDEX IF NOT EXISTS idx_chats_jid ON public.chats USING btree (jid);
CREATE INDEX IF NOT EXISTS idx_chats_last_message ON public.chats USING btree (last_message_at DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_chats_tenant_id ON public.chats USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_segment_members_contact ON public.contact_segment_members USING btree (contact_id);
CREATE INDEX IF NOT EXISTS idx_segment_members_segment ON public.contact_segment_members USING btree (segment_id);
CREATE INDEX IF NOT EXISTS idx_contact_segments_tenant ON public.contact_segments USING btree (tenant_id, segment_type);
CREATE INDEX IF NOT EXISTS idx_contacts_campaign_config ON public.contacts USING btree (campaign_config_id) WHERE (campaign_config_id IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_contacts_do_not_contact ON public.contacts USING btree (tenant_id, do_not_contact) WHERE (do_not_contact = true);
CREATE INDEX IF NOT EXISTS idx_contacts_industry_type ON public.contacts USING btree (tenant_id, industry_type) WHERE (industry_type IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_contacts_interest_score ON public.contacts USING btree (tenant_id, interest_score DESC) WHERE (interest_score > 0);
CREATE INDEX IF NOT EXISTS idx_contacts_outreach ON public.contacts USING btree (tenant_id, last_outreach_at) WHERE (last_outreach_at IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_contacts_tenant_last_msg ON public.contacts USING btree (tenant_id, last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_contacts_tenant_status ON public.contacts USING btree (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_contacts_tenant_tag ON public.contacts USING btree (tenant_id, tag);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_chat ON public.conversation_logs USING btree (chat_jid);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_created_at ON public.conversation_logs USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_event_type ON public.conversation_logs USING btree (event_type);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_failures ON public.conversation_logs USING btree (tenant_id, success) WHERE (success = false);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_tenant ON public.conversation_logs USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_chat_jid ON public.conversations USING btree (chat_jid);
CREATE INDEX IF NOT EXISTS idx_conversations_contact_name ON public.conversations USING btree (contact_name);
CREATE INDEX IF NOT EXISTS idx_conversations_customer ON public.conversations USING btree (customer_jid);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant ON public.conversations USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_chat ON public.conversations USING btree (tenant_id, chat_jid);
CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON public.conversations USING btree ("timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_conversion_events_date ON public.conversion_events USING btree (converted_at);
CREATE INDEX IF NOT EXISTS idx_conversion_events_tenant ON public.conversion_events USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversion_events_type ON public.conversion_events USING btree (event_type);
CREATE INDEX IF NOT EXISTS idx_customer_activity_last_message ON public.customer_activity USING btree (last_message_at);
CREATE INDEX IF NOT EXISTS idx_customer_activity_tenant ON public.customer_activity USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_views_created_by ON public.dashboard_views USING btree (created_by);
CREATE INDEX IF NOT EXISTS idx_dashboard_views_dept_visibility ON public.dashboard_views USING btree (department_id, visibility);
CREATE INDEX IF NOT EXISTS idx_dashboard_views_pinned ON public.dashboard_views USING btree (pinned) WHERE (pinned = true);
CREATE UNIQUE INDEX IF NOT EXISTS idx_data_request_deletions_phone ON public.data_request_deletions USING btree (phone_normalized);
CREATE INDEX IF NOT EXISTS idx_data_request_deletions_status_grace ON public.data_request_deletions USING btree (status, grace_until);
CREATE INDEX IF NOT EXISTS idx_departments_parent ON public.departments USING btree (parent_id);
CREATE INDEX IF NOT EXISTS idx_device_sessions_device_id ON public.device_sessions USING btree (device_id);
CREATE INDEX IF NOT EXISTS idx_device_sessions_status ON public.device_sessions USING btree (status);
CREATE INDEX IF NOT EXISTS idx_device_sessions_tenant_id ON public.device_sessions USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_drive_documents_mime_type ON public.drive_documents USING btree (mime_type);
CREATE INDEX IF NOT EXISTS idx_drive_documents_owner_user_id ON public.drive_documents USING btree (owner_user_id);
CREATE INDEX IF NOT EXISTS idx_email_summaries_ai_urgency ON public.email_summaries USING btree (ai_urgency);
CREATE INDEX IF NOT EXISTS idx_email_summaries_thread_id ON public.email_summaries USING btree (gmail_thread_id);
CREATE INDEX IF NOT EXISTS idx_email_summaries_user_id ON public.email_summaries USING btree (user_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_templates_tenant_type ON public.email_templates USING btree (tenant_id, template_type) WHERE (is_active = true);
CREATE INDEX IF NOT EXISTS idx_email_tokens_expires ON public.email_verification_tokens USING btree (expires_at);
CREATE INDEX IF NOT EXISTS idx_email_tokens_tenant ON public.email_verification_tokens USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_escalation_actions_created ON public.escalation_actions USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_escalation_actions_escalation ON public.escalation_actions USING btree (escalation_id);
CREATE INDEX IF NOT EXISTS idx_escalation_actions_type ON public.escalation_actions USING btree (action_type);
CREATE INDEX IF NOT EXISTS idx_escalation_notifications_created ON public.escalation_notifications USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_escalation_notifications_escalation ON public.escalation_notifications USING btree (escalation_id);
CREATE INDEX IF NOT EXISTS idx_escalation_notifications_status ON public.escalation_notifications USING btree (status);
CREATE INDEX IF NOT EXISTS idx_escalation_notifications_tenant ON public.escalation_notifications USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_escalations_agent_status ON public.escalations USING btree (assigned_agent_id, status) WHERE (assigned_agent_id IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_escalations_assigned_agent ON public.escalations USING btree (assigned_agent_id);
CREATE INDEX IF NOT EXISTS idx_escalations_chat ON public.escalations USING btree (chat_jid);
CREATE INDEX IF NOT EXISTS idx_escalations_priority ON public.escalations USING btree (priority, created_at);
CREATE INDEX IF NOT EXISTS idx_escalations_reason_type ON public.escalations USING btree (reason_type);
CREATE INDEX IF NOT EXISTS idx_escalations_sla ON public.escalations USING btree (sla_deadline) WHERE (status = ANY (ARRAY['pending'::text, 'claimed'::text]));
CREATE INDEX IF NOT EXISTS idx_escalations_status ON public.escalations USING btree (status);
CREATE INDEX IF NOT EXISTS idx_escalations_status_sla ON public.escalations USING btree (status, sla_deadline) WHERE ((status = ANY (ARRAY['pending'::text, 'in_progress'::text])) AND (sla_deadline IS NOT NULL));
CREATE INDEX IF NOT EXISTS idx_escalations_tenant ON public.escalations USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_escalations_tenant_chat ON public.escalations USING btree (tenant_id, chat_jid);
CREATE INDEX IF NOT EXISTS idx_escalations_tenant_status ON public.escalations USING btree (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_escalations_timeout_candidates ON public.escalations USING btree (tenant_id, status, escalation_triggered_at) WHERE (status = ANY (ARRAY['pending'::text, 'in_progress'::text]));
CREATE INDEX IF NOT EXISTS idx_escalations_updated_at ON public.escalations USING btree (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_escalations_warning_candidates ON public.escalations USING btree (tenant_id, status, warning_sent, escalation_triggered_at) WHERE ((status = ANY (ARRAY['pending'::text, 'in_progress'::text])) AND (warning_sent = false));
CREATE INDEX IF NOT EXISTS idx_extracted_items_status ON public.extracted_items USING btree (status);
CREATE INDEX IF NOT EXISTS idx_extracted_items_type ON public.extracted_items USING btree (item_type);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON public.feedback USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_customer ON public.feedback USING btree (customer_jid);
CREATE INDEX IF NOT EXISTS idx_feedback_follow_up ON public.feedback USING btree (follow_up_needed) WHERE (follow_up_needed = true);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON public.feedback USING btree (rating);
CREATE INDEX IF NOT EXISTS idx_feedback_sentiment ON public.feedback USING btree (sentiment);
CREATE INDEX IF NOT EXISTS idx_feedback_tenant ON public.feedback USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_follow_ups_chat ON public.follow_ups USING btree (chat_jid, status);
CREATE INDEX IF NOT EXISTS idx_follow_ups_pending ON public.follow_ups USING btree (status, scheduled_at) WHERE (status = 'pending'::text);
CREATE INDEX IF NOT EXISTS idx_follow_ups_scheduled ON public.follow_ups USING btree (scheduled_at) WHERE (status = 'pending'::text);
CREATE INDEX IF NOT EXISTS idx_follow_ups_status ON public.follow_ups USING btree (status, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_follow_ups_tenant ON public.follow_ups USING btree (tenant_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_follow_ups_unique_pending ON public.follow_ups USING btree (tenant_id, chat_jid) WHERE (status = 'pending'::text);
CREATE INDEX IF NOT EXISTS idx_sheets_sync_enabled ON public.google_sheets_sync USING btree (sync_enabled);
CREATE INDEX IF NOT EXISTS idx_sheets_sync_tenant ON public.google_sheets_sync USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_handover_agents_active ON public.handover_agents USING btree (tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_handover_agents_is_active ON public.handover_agents USING btree (is_active);
CREATE INDEX IF NOT EXISTS idx_handover_agents_priority ON public.handover_agents USING btree (priority_level);
CREATE INDEX IF NOT EXISTS idx_handover_agents_tenant_id ON public.handover_agents USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_help_tickets_group_jid ON public.help_tickets USING btree (group_jid, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_help_tickets_tenant_status ON public.help_tickets USING btree (tenant_id, status, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_help_ticket_number ON public.help_tickets USING btree (tenant_id, ticket_number);
CREATE INDEX IF NOT EXISTS idx_holiday_exceptions_date ON public.holiday_exceptions USING btree (date);
CREATE INDEX IF NOT EXISTS idx_holiday_exceptions_tenant_id ON public.holiday_exceptions USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_inbox_copilot_events_event ON public.inbox_copilot_events USING btree (event_id);
CREATE INDEX IF NOT EXISTS idx_inbox_copilot_events_tenant ON public.inbox_copilot_events USING btree (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jid_mappings_phone_jid ON public.jid_mappings USING btree (tenant_id, phone_jid);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_tenant_id ON public.knowledge_base USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_content_fts ON public.knowledge_base USING gin (to_tsvector('english'::regconfig, content));
CREATE INDEX IF NOT EXISTS idx_knowledge_created ON public.knowledge_base USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_keywords ON public.knowledge_base USING gin (keywords);
CREATE INDEX IF NOT EXISTS idx_knowledge_status ON public.knowledge_base USING btree (processing_status);
CREATE INDEX IF NOT EXISTS idx_knowledge_topics ON public.knowledge_base USING gin (topics);
CREATE INDEX IF NOT EXISTS idx_knowledge_active ON public.knowledge_bases USING btree (is_active);
CREATE INDEX IF NOT EXISTS idx_knowledge_bases_tenant ON public.knowledge_bases USING btree (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON public.knowledge_bases USING btree (category);
CREATE INDEX IF NOT EXISTS idx_knowledge_tenant ON public.knowledge_bases USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding ON public.knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists='100');
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_kb ON public.knowledge_chunks USING btree (knowledge_base_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_tenant ON public.knowledge_chunks USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_kdv_document_id ON public.knowledge_doc_versions USING btree (document_id, version_number DESC);
CREATE INDEX IF NOT EXISTS idx_kdv_tenant_id ON public.knowledge_doc_versions USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_status ON public.knowledge_documents USING btree (status);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_tenant_id ON public.knowledge_documents USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_uploaded_at ON public.knowledge_documents USING btree (tenant_id, uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_sync_jobs_kb ON public.knowledge_sync_jobs USING btree (knowledge_base_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_sync_jobs_status ON public.knowledge_sync_jobs USING btree (status);
CREATE INDEX IF NOT EXISTS idx_knowledge_sync_jobs_tenant ON public.knowledge_sync_jobs USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_lead_followups_next ON public.lead_followups USING btree (next_followup_at);
CREATE INDEX IF NOT EXISTS idx_lead_followups_tenant ON public.lead_followups USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON public.leads USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_email ON public.leads USING btree (email);
CREATE INDEX IF NOT EXISTS idx_leads_lead_score ON public.leads USING btree (lead_score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_source ON public.leads USING btree (source);
CREATE INDEX IF NOT EXISTS idx_leads_status ON public.leads USING btree (status);
CREATE INDEX IF NOT EXISTS idx_leads_updated_at ON public.leads USING btree (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_media_tenant ON public.media_library USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_meeting_blockers_status ON public.meeting_blockers USING btree (status);
CREATE INDEX IF NOT EXISTS idx_meetings_date ON public.meetings USING btree (meeting_date);
CREATE INDEX IF NOT EXISTS idx_message_reasons_chat ON public.message_reasons USING btree (tenant_id, chat_jid, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_message_reasons_lookup ON public.message_reasons USING btree (tenant_id, message_id);
CREATE INDEX IF NOT EXISTS idx_message_templates_active ON public.message_templates USING btree (is_active);
CREATE INDEX IF NOT EXISTS idx_message_templates_tenant ON public.message_templates USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_templates_trigger_mode ON public.message_templates USING btree (tenant_id, trigger_mode);
CREATE INDEX IF NOT EXISTS idx_messages_chat_jid ON public.messages USING btree (chat_jid);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_key ON public.messages USING btree (conversation_key) WHERE (conversation_key IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_messages_customer_name ON public.messages USING btree (customer_name);
CREATE INDEX IF NOT EXISTS idx_messages_customer_phone ON public.messages USING btree (customer_phone);
CREATE INDEX IF NOT EXISTS idx_messages_device_jid ON public.messages USING btree (device_jid) WHERE (device_jid IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_messages_system_event ON public.messages USING btree (tenant_id, is_system_event) WHERE (is_system_event = false);
CREATE INDEX IF NOT EXISTS idx_messages_tenant_chat ON public.messages USING btree (tenant_id, chat_jid);
CREATE INDEX IF NOT EXISTS idx_messages_tenant_id ON public.messages USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_messages_tenant_id_created ON public.messages USING btree (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON public.messages USING btree ("timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_notification_groups_group_type ON public.notification_groups USING btree (group_type);
CREATE INDEX IF NOT EXISTS idx_notification_groups_tenant_id ON public.notification_groups USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_notification_logs_customer_jid ON public.notification_logs USING btree (customer_jid);
CREATE INDEX IF NOT EXISTS idx_notification_logs_sent_at ON public.notification_logs USING btree (sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_logs_tenant_id ON public.notification_logs USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON public.notifications USING btree (user_id, read, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_onboarding_progress_current_step ON public.onboarding_progress USING btree (current_step);
CREATE INDEX IF NOT EXISTS idx_onboarding_created ON public.onboarding_sessions USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_onboarding_email ON public.onboarding_sessions USING btree (email);
CREATE INDEX IF NOT EXISTS idx_onboarding_expires ON public.onboarding_sessions USING btree (expires_at);
CREATE INDEX IF NOT EXISTS idx_onboarding_status ON public.onboarding_sessions USING btree (status);
CREATE INDEX IF NOT EXISTS idx_onboarding_tenant ON public.onboarding_sessions USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_onboarding_token ON public.onboarding_sessions USING btree (token) WHERE (status <> 'completed'::text);
CREATE INDEX IF NOT EXISTS idx_outbound_queue_campaign ON public.outbound_queue USING btree (campaign_id, status);
CREATE INDEX IF NOT EXISTS idx_outbound_queue_contact ON public.outbound_queue USING btree (contact_id, campaign_id) WHERE (replied_at IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_outbound_queue_daily_check ON public.outbound_queue USING btree (tenant_id, sent_at);
CREATE INDEX IF NOT EXISTS idx_outbound_queue_pending ON public.outbound_queue USING btree (tenant_id, status, scheduled_at) WHERE (status = ANY (ARRAY['pending'::text, 'scheduled'::text]));
CREATE INDEX IF NOT EXISTS idx_occ_active ON public.outreach_campaign_configs USING btree (tenant_id, is_active) WHERE (is_active = true);
CREATE INDEX IF NOT EXISTS idx_occ_industry ON public.outreach_campaign_configs USING btree (industry_type);
CREATE INDEX IF NOT EXISTS idx_occ_tenant ON public.outreach_campaign_configs USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_outreach_consent_active ON public.outreach_consent_log USING btree (tenant_id, contact_id) WHERE (revoked_at IS NULL);
CREATE INDEX IF NOT EXISTS idx_outreach_consent_contact ON public.outreach_consent_log USING btree (tenant_id, contact_id, revoked_at);
CREATE INDEX IF NOT EXISTS idx_outreach_logs_tenant ON public.outreach_logs USING btree (tenant_id, log_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_owner_commands_created ON public.owner_commands USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_owner_commands_owner ON public.owner_commands USING btree (owner_jid);
CREATE INDEX IF NOT EXISTS idx_owner_commands_tenant ON public.owner_commands USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_owner_commands_type ON public.owner_commands USING btree (command_type);
CREATE INDEX IF NOT EXISTS idx_owner_notifications_chat ON public.owner_notifications USING btree (chat_jid);
CREATE INDEX IF NOT EXISTS idx_owner_notifications_sent_at ON public.owner_notifications USING btree (sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_owner_notifications_tenant ON public.owner_notifications USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON public.payment_transactions USING btree (status);
CREATE INDEX IF NOT EXISTS idx_payments_stripe_intent ON public.payment_transactions USING btree (stripe_payment_intent_id);
CREATE INDEX IF NOT EXISTS idx_payments_tenant ON public.payment_transactions USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_personas_active ON public.personas USING btree (is_active) WHERE (is_active = true);
CREATE INDEX IF NOT EXISTS idx_personas_tenant ON public.personas USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_projects_department_id ON public.projects USING btree (department_id);
CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON public.projects USING btree (owner_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON public.projects USING btree (status);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON public.proposals USING btree (status);
CREATE INDEX IF NOT EXISTS idx_raw_events_processed ON public.raw_events USING btree (processed);
CREATE INDEX IF NOT EXISTS idx_raw_events_source ON public.raw_events USING btree (source);
CREATE INDEX IF NOT EXISTS idx_response_coord_activity ON public.response_coordinator_state USING btree (last_activity_at);
CREATE INDEX IF NOT EXISTS idx_response_coord_tenant ON public.response_coordinator_state USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_messages_active_nextrun ON public.scheduled_messages USING btree (is_active, next_run_at) WHERE (is_active = true);
CREATE INDEX IF NOT EXISTS idx_scheduled_messages_next_run ON public.scheduled_messages USING btree (next_run_at) WHERE (is_active = true);
CREATE INDEX IF NOT EXISTS idx_scheduled_messages_status_time ON public.scheduled_messages USING btree (status, scheduled_time) WHERE (status = 'pending'::text);
CREATE INDEX IF NOT EXISTS idx_scheduled_messages_tenant ON public.scheduled_messages USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_shared_briefs_created_at ON public.shared_briefs USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_shared_context_lookup ON public.shared_context USING btree (tenant_id, customer_phone, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_shared_context_thread ON public.shared_context USING btree (tenant_id, thread_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sheet_data_sheet_id ON public.sheet_data USING btree (google_sheet_id);
CREATE INDEX IF NOT EXISTS idx_system_metrics_name_time ON public.system_metrics USING btree (metric_name, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON public.tasks USING btree (assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON public.tasks USING btree (project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON public.tasks USING btree (status);
CREATE INDEX IF NOT EXISTS idx_tenant_calendars_tenant_id ON public.tenant_calendars USING btree (tenant_id) WHERE (is_active = true);
CREATE INDEX IF NOT EXISTS idx_tenant_email_config_tenant_id ON public.tenant_email_config USING btree (tenant_id) WHERE (is_active = true);
CREATE INDEX IF NOT EXISTS idx_tenant_integrations_tenant_id ON public.tenant_integrations USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_kb_instances_tenant ON public.tenant_kb_template_instances USING btree (tenant_id, is_complete);
CREATE INDEX IF NOT EXISTS idx_tenant_metrics_name ON public.tenant_metrics USING btree (metric_name);
CREATE INDEX IF NOT EXISTS idx_tenant_metrics_tenant_time ON public.tenant_metrics USING btree (tenant_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_tenant_users_tenant_id ON public.tenant_users USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_users_user_id ON public.tenant_users USING btree (user_id);
CREATE INDEX IF NOT EXISTS idx_tenant_users_email ON public.tenant_users_legacy USING btree (email);
CREATE INDEX IF NOT EXISTS idx_tenant_users_main_contact ON public.tenant_users_legacy USING btree (tenant_id, is_main_contact) WHERE (is_main_contact = true);
CREATE INDEX IF NOT EXISTS idx_tenant_verticals_tenant_id ON public.tenant_verticals USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenants_auto_reply ON public.tenants USING btree (auto_reply_enabled) WHERE (auto_reply_enabled = true);
CREATE INDEX IF NOT EXISTS idx_tenants_device_id ON public.tenants USING btree (device_id);
CREATE INDEX IF NOT EXISTS idx_tenants_email ON public.tenants USING btree (email);
CREATE INDEX IF NOT EXISTS idx_tenants_email_token ON public.tenants USING btree (email_verification_token);
CREATE INDEX IF NOT EXISTS idx_tenants_handover_primary ON public.tenants USING btree (handover_primary) WHERE (handover_primary IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON public.tenants USING btree (status);
CREATE INDEX IF NOT EXISTS idx_tenants_stripe_customer_id ON public.tenants USING btree (stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_tenants_stripe_subscription ON public.tenants USING btree (stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_tenants_testing_mode ON public.tenants USING btree (testing_mode) WHERE (testing_mode = true);
CREATE INDEX IF NOT EXISTS idx_tenants_tier ON public.tenants USING btree (subscription_tier);
CREATE INDEX IF NOT EXISTS idx_tenants_whatsapp_jid ON public.tenants USING btree (whatsapp_jid);
CREATE INDEX IF NOT EXISTS idx_trial_notif_tenant ON public.trial_notifications USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_trial_notif_type ON public.trial_notifications USING btree (notification_type);
CREATE INDEX IF NOT EXISTS idx_usage_created ON public.usage_tracking USING btree (created_at);
CREATE INDEX IF NOT EXISTS idx_usage_customer ON public.usage_tracking USING btree (customer_jid);
CREATE INDEX IF NOT EXISTS idx_usage_tenant_date ON public.usage_tracking USING btree (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_profiles_dept ON public.user_profiles USING btree (department_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON public.user_profiles USING btree (email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_manager ON public.user_profiles USING btree (manager_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_role ON public.user_profiles USING btree (role);
CREATE INDEX IF NOT EXISTS idx_web_support_tickets_email ON public.web_support_tickets USING btree (submitter_email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_web_support_tickets_status ON public.web_support_tickets USING btree (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_whatsapp_devices_device_id ON public.whatsapp_devices USING btree (device_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_devices_tenant ON public.whatsapp_devices USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_devices_whatsapp_jid ON public.whatsapp_devices USING btree (whatsapp_jid);


-- ─────────────── FUNCTIONS, VIEWS, TRIGGERS ───────────────────────
-- 60-functions-views.sql
-- Extracted from the live Supabase project (public schema), read-only from pg_catalog.
-- Contents: 32 functions, 3 views, 33 triggers.
-- NOTE: public.posthog_webhook_fire() contained a hardcoded X-Internal-Token in
-- production. It has been replaced below with the placeholder
-- '<POSTHOG_BRIDGE_INTERNAL_TOKEN>' so no live secret is committed to the repo.
-- NOTE: 19 of the 32 functions are SECURITY DEFINER. In the public schema these are
-- callable by anon/authenticated by default and bypass RLS. See the audit note at the
-- end of this file.

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION public.calculate_campaign_stats(p_campaign_id uuid)
 RETURNS TABLE(total_recipients bigint, sent_count bigint, delivered_count bigint, failed_count bigint, reply_count bigint)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) as total_recipients,
        COUNT(*) FILTER (WHERE status IN ('sent', 'delivered', 'read')) as sent_count,
        COUNT(*) FILTER (WHERE status IN ('delivered', 'read')) as delivered_count,
        COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
        COUNT(*) FILTER (WHERE replied_at IS NOT NULL) as reply_count
    FROM outbound_queue
    WHERE campaign_id = p_campaign_id;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.calculate_lead_score(lead_data leads)
 RETURNS integer
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
  score int := 0;
BEGIN
  -- Base score for complete profile
  IF lead_data.name IS NOT NULL AND lead_data.email IS NOT NULL THEN
    score := score + 10;
  END IF;

  -- Phone number adds significant value
  IF lead_data.phone IS NOT NULL AND length(lead_data.phone) > 8 THEN
    score := score + 15;
  END IF;

  -- Company information shows business intent
  IF lead_data.company IS NOT NULL AND length(lead_data.company) > 2 THEN
    score := score + 20;
  END IF;

  -- Industry context helps with qualification
  IF lead_data.industry IS NOT NULL THEN
    score := score + 10;
  END IF;

  -- Email engagement tracking
  IF lead_data.email_opened_at IS NOT NULL THEN
    score := score + 25;
  END IF;

  IF lead_data.email_clicked_at IS NOT NULL THEN
    score := score + 35;
  END IF;

  -- Marketing consent shows higher intent
  IF lead_data.marketing_consent = true THEN
    score := score + 15;
  END IF;

  -- Source-based scoring (Malaysian market behavior)
  CASE lead_data.source
    WHEN 'cal_booking' THEN score := score + 50;      -- Booked demo = highest intent
    WHEN 'whatsapp_cta' THEN score := score + 40;     -- Direct WhatsApp = high intent
    WHEN 'final_cta_direct' THEN score := score + 35; -- Bottom CTA = high intent
    WHEN 'hero_form' THEN score := score + 30;        -- Main form = medium-high intent
    WHEN 'waitlist' THEN score := score + 20;         -- Email signup = medium intent
    ELSE score := score + 10;                          -- Other sources = baseline
  END CASE;

  RETURN score;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.call_bookings_set_scheduled_date()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
  -- Set scheduled_date from scheduled_time on INSERT/UPDATE
  IF (TG_OP = 'INSERT') THEN
    NEW.scheduled_date := (NEW.scheduled_time)::date;
    RETURN NEW;
  ELSIF (TG_OP = 'UPDATE') THEN
    -- Update scheduled_date if scheduled_time changed
    IF (NEW.scheduled_time IS DISTINCT FROM OLD.scheduled_time) THEN
      NEW.scheduled_date := (NEW.scheduled_time)::date;
    END IF;
    RETURN NEW;
  END IF;
  RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.can_view_user(viewer_id uuid, target_id uuid)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
    v_role TEXT; v_access TEXT; v_dept UUID; t_dept UUID;
BEGIN
    IF viewer_id = target_id THEN RETURN true; END IF;
    SELECT role, access_level, department_id
      INTO v_role, v_access, v_dept
      FROM user_profiles WHERE id = viewer_id;
    SELECT department_id INTO t_dept
      FROM user_profiles WHERE id = target_id;
    IF v_role IN ('owner', 'admin') THEN RETURN true; END IF;
    IF v_access IN ('executive', 'director') THEN RETURN true; END IF;
    IF v_access IN ('manager', 'lead') AND v_dept IS NOT NULL AND v_dept = t_dept THEN RETURN true; END IF;
    IF v_dept IS NOT NULL AND v_dept = t_dept THEN RETURN true; END IF;
    RETURN false;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.cleanup_expired_onboarding_sessions(days_old integer DEFAULT 30)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM onboarding_sessions
    WHERE status = 'expired'
    AND expires_at < NOW() - (days_old || ' days')::interval;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN deleted_count;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.cleanup_expired_onboarding_sessions()
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
BEGIN
  DELETE FROM onboarding_sessions
  WHERE status = 'pending'
    AND created_at < NOW() - INTERVAL '1 hour';
END;
$function$
;

CREATE OR REPLACE FUNCTION public.cleanup_expired_qr_sessions()
 RETURNS TABLE(deleted_count integer)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
  affected_rows integer;
BEGIN
  DELETE FROM device_sessions
  WHERE status = 'pending'
    AND (qr_expires_at < now() OR created_at < now() - INTERVAL '1 hour');
  GET DIAGNOSTICS affected_rows = ROW_COUNT;
  RETURN QUERY SELECT affected_rows;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.count_monthly_conversations(p_tenant_id uuid, p_month_start timestamp without time zone)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN (
        SELECT COUNT(DISTINCT conversation_id)
        FROM messages
        WHERE tenant_id = p_tenant_id
          AND created_at >= p_month_start
          AND created_at < p_month_start + INTERVAL '1 month'
    );
END;
$function$
;

CREATE OR REPLACE FUNCTION public.create_default_templates()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    -- Greeting template
    INSERT INTO message_templates (tenant_id, template_name, template_content, category)
    VALUES (
        NEW.id,
        'Welcome Message',
        'Hi {customer_name}! 👋 Welcome to {business_name}. How can I help you today?',
        'greeting'
    )
    ON CONFLICT DO NOTHING;

    -- Business hours template
    INSERT INTO message_templates (tenant_id, template_name, template_content, category)
    VALUES (
        NEW.id,
        'Business Hours',
        'Our business hours are Monday-Friday, 9 AM - 6 PM (Malaysia Time). We''ll respond during these hours.',
        'faq'
    )
    ON CONFLICT DO NOTHING;

    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.current_tenant_id()
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    -- First try JWT claims (for authenticated users)
    RETURN (current_setting('request.jwt.claims', true)::json->>'tenant_id')::UUID;
EXCEPTION
    WHEN OTHERS THEN
        -- Fallback to app-level context (set by service role)
        RETURN current_setting('app.current_tenant_id', true)::UUID;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.expire_old_onboarding_sessions()
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
BEGIN
  UPDATE onboarding_sessions
  SET status = 'expired'
  WHERE status = 'pending'
    AND created_at < NOW() - INTERVAL '1 hour';
END;
$function$
;

CREATE OR REPLACE FUNCTION public.get_contact_last_campaign(p_contact_id uuid)
 RETURNS TABLE(campaign_id uuid, campaign_name text, last_message_at timestamp with time zone, replied boolean)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.name,
        MAX(oq.sent_at) as last_message_at,
        BOOL_OR(oq.replied_at IS NOT NULL) as replied
    FROM campaigns c
    JOIN outbound_queue oq ON oq.campaign_id = c.id
    WHERE oq.contact_id = p_contact_id
    GROUP BY c.id, c.name
    ORDER BY MAX(oq.sent_at) DESC
    LIMIT 1;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.get_conversation_threads(p_tenant_id uuid, p_chat_jid text DEFAULT NULL::text, p_limit integer DEFAULT 50, p_offset integer DEFAULT 0)
 RETURNS TABLE(chat_jid text, conversation_key text, device_jid text, message_count bigint, last_message_at timestamp with time zone, last_role text, last_content text, customer_phone text, customer_name text)
 LANGUAGE sql
 STABLE
 SET search_path TO 'public', 'pg_temp'
AS $function$
    SELECT
        m.chat_jid,
        m.conversation_key,
        m.device_jid,
        COUNT(*)                                          AS message_count,
        MAX(m.created_at)                                AS last_message_at,
        -- Role and content of the most recent message in the thread
        (
            SELECT m2.role
            FROM   messages m2
            WHERE  m2.tenant_id = p_tenant_id
              AND  m2.chat_jid  = m.chat_jid
              AND  (p_chat_jid IS NULL OR m2.chat_jid = p_chat_jid)
            ORDER  BY m2.created_at DESC
            LIMIT  1
        )                                                AS last_role,
        LEFT(
            (
                SELECT m3.content
                FROM   messages m3
                WHERE  m3.tenant_id = p_tenant_id
                  AND  m3.chat_jid  = m.chat_jid
                  AND  (p_chat_jid IS NULL OR m3.chat_jid = p_chat_jid)
                ORDER  BY m3.created_at DESC
                LIMIT  1
            ),
            120
        )                                                AS last_content,
        MAX(m.customer_phone)                            AS customer_phone,
        MAX(m.customer_name)                             AS customer_name
    FROM messages m
    WHERE m.tenant_id       = p_tenant_id
      AND m.is_system_event = FALSE
      AND (p_chat_jid IS NULL OR m.chat_jid = p_chat_jid)
    GROUP BY m.chat_jid, m.conversation_key, m.device_jid
    ORDER BY last_message_at DESC
    LIMIT  p_limit
    OFFSET p_offset;
$function$
;

CREATE OR REPLACE FUNCTION public.get_tenant_daily_sent_count(p_tenant_id uuid)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM outbound_queue
        WHERE tenant_id = p_tenant_id
        AND status IN ('sent', 'delivered', 'read')
        AND sent_at >= CURRENT_DATE
    );
END;
$function$
;

CREATE OR REPLACE FUNCTION public.handle_new_user()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
BEGIN
    INSERT INTO public.user_profiles (id, display_name, email, avatar_url)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data ->> 'full_name', NEW.raw_user_meta_data ->> 'name', ''),
        COALESCE(NEW.email, ''),
        COALESCE(NEW.raw_user_meta_data ->> 'avatar_url', '')
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.increment_click_count(row_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
  UPDATE public.short_links
  SET click_count = click_count + 1
  WHERE id = row_id;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.increment_contact_message(p_tenant_id text, p_jid text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    UPDATE contacts
    SET
        message_count   = message_count + 1,
        last_message_at = NOW(),
        updated_at      = NOW()
    WHERE tenant_id = p_tenant_id
      AND jid       = p_jid;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.is_service_role()
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN current_setting('request.jwt.claims', true)::json->>'role' = 'service_role';
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.posthog_webhook_fire()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'extensions'
AS $function$
  DECLARE
    payload jsonb;
    target_table text := TG_TABLE_NAME;
    op text := lower(TG_OP);
    safe_record jsonb;
    safe_old jsonb;
  BEGIN
    -- Build a minimal, non-sensitive payload.
    safe_record := case when TG_OP = 'DELETE' then null else to_jsonb(NEW) end;
    safe_old    := case when TG_OP = 'DELETE' then to_jsonb(OLD) when TG_OP = 'UPDATE' then to_jsonb(OLD) else null end;

    -- Strip password / secret columns if present
    safe_record := safe_record - 'password' - 'password_hash' - 'encrypted_password';
    safe_old    := safe_old    - 'password' - 'password_hash' - 'encrypted_password';

    payload := jsonb_build_object(
      'type',       op,
      'table',      target_table,
      'record',     safe_record,
      'old_record', safe_old,
      'schema',     TG_TABLE_SCHEMA,
      'at',         to_char(now() at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')
    );

    -- Fire and forget. pg_net queues the request and returns immediately,
    -- so the user-facing INSERT/UPDATE is not blocked on the network.
    -- Signature (pg_net 0.19+): http_post(url, body jsonb, params jsonb, headers jsonb, timeout int) -> bigint
    PERFORM net.http_post(
      url     := 'https://bijou-landing.vercel.app/api/posthog-bridge',
      body    := payload,
      params  := '{}'::jsonb,
      headers := jsonb_build_object(
        'Content-Type',     'application/json',
        'X-Internal-Token', '<POSTHOG_BRIDGE_INTERNAL_TOKEN>'
      ),
      timeout_milliseconds := 5000
    );

    RETURN coalesce(NEW, OLD);
  END;
  $function$
;

CREATE OR REPLACE FUNCTION public.prune_agent_status()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
BEGIN
    DELETE FROM agent_status
    WHERE id IN (
        SELECT id FROM agent_status
        WHERE connection_id = NEW.connection_id
        ORDER BY checked_at DESC
        OFFSET 50
    );
    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.rls_auto_enable()
 RETURNS event_trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog'
AS $function$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN
    SELECT *
    FROM pg_event_trigger_ddl_commands()
    WHERE command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      AND object_type IN ('table','partitioned table')
  LOOP
     IF cmd.schema_name IS NOT NULL AND cmd.schema_name IN ('public') AND cmd.schema_name NOT IN ('pg_catalog','information_schema') AND cmd.schema_name NOT LIKE 'pg_toast%' AND cmd.schema_name NOT LIKE 'pg_temp%' THEN
      BEGIN
        EXECUTE format('alter table if exists %s enable row level security', cmd.object_identity);
        RAISE LOG 'rls_auto_enable: enabled RLS on %', cmd.object_identity;
      EXCEPTION
        WHEN OTHERS THEN
          RAISE LOG 'rls_auto_enable: failed to enable RLS on %', cmd.object_identity;
      END;
     ELSE
        RAISE LOG 'rls_auto_enable: skip % (either system schema or not in enforced list: %.)', cmd.object_identity, cmd.schema_name;
     END IF;
  END LOOP;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.search_knowledge(query_embedding vector, query_text text DEFAULT ''::text, match_threshold double precision DEFAULT 0.7, match_count integer DEFAULT 10, filter_department uuid DEFAULT NULL::uuid)
 RETURNS TABLE(id uuid, title text, content text, source_type text, similarity double precision)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
BEGIN
    RETURN QUERY
    SELECT kb.id, kb.title, kb.content, kb.source_type,
        (1 - (kb.content_embedding <=> query_embedding))::FLOAT AS similarity
    FROM knowledge_base kb
    WHERE kb.content_embedding IS NOT NULL
        AND (1 - (kb.content_embedding <=> query_embedding)) > match_threshold
        AND (filter_department IS NULL OR kb.department_id = filter_department OR kb.visibility = 'public')
    ORDER BY kb.content_embedding <=> query_embedding
    LIMIT match_count;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.update_contacts_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.update_escalation_notifications_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.update_follow_ups_timestamp()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    NEW.updated_at = now
();
RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.update_help_ticket_timestamp()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    NEW.updated_at = now
();
RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.update_jid_mappings_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.update_leads_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
  NEW.updated_at = timezone('utc'::text, now());
  RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.update_onboarding_current_step()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    -- Auto-update current_step based on completion flags
    IF NEW.step_agents_completed THEN
        NEW.current_step := 'completed';
    ELSIF NEW.step_knowledge_completed THEN
        NEW.current_step := 'agents';
    ELSIF NEW.step_whatsapp_completed THEN
        NEW.current_step := 'knowledge';
    ELSIF NEW.step_details_completed THEN
        NEW.current_step := 'whatsapp';
    ELSIF NEW.step_payment_completed THEN
        NEW.current_step := 'details';
    END IF;

    NEW.updated_at := NOW();
    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.update_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.update_web_support_ticket_timestamp()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$function$
;

-- ============================================================================
-- VIEWS
-- ============================================================================
-- None of the three live views were defined WITH (security_invoker), so none is
-- set here either.

CREATE OR REPLACE VIEW public.active_conversations AS  SELECT tenant_id,
    chat_jid,
    max("timestamp") AS last_message_at,
    count(*) AS message_count
   FROM conversations
  WHERE ("timestamp" > (now() - '24:00:00'::interval))
  GROUP BY tenant_id, chat_jid;

CREATE OR REPLACE VIEW public.daily_message_volume AS  SELECT tenant_id,
    date("timestamp") AS date,
    count(*) AS total_messages,
    count(
        CASE
            WHEN is_from_me THEN 1
            ELSE NULL::integer
        END) AS outgoing,
    count(
        CASE
            WHEN (NOT is_from_me) THEN 1
            ELSE NULL::integer
        END) AS incoming
   FROM conversations
  GROUP BY tenant_id, (date("timestamp"));

CREATE OR REPLACE VIEW public.escalation_summary AS  SELECT tenant_id,
    status,
    count(*) AS count,
    avg((EXTRACT(epoch FROM (resolved_at - created_at)) / (60)::numeric)) AS avg_resolution_time_minutes
   FROM escalations
  WHERE (created_at > (now() - '30 days'::interval))
  GROUP BY tenant_id, status;

-- ============================================================================
-- TRIGGERS
-- ============================================================================
-- CREATE TRIGGER has no IF NOT EXISTS, so each is wrapped in a DO block that
-- swallows duplicate_object.

DO $do$ BEGIN CREATE TRIGGER posthog_webhook_user_trg AFTER INSERT OR DELETE OR UPDATE ON public."User" FOR EACH ROW EXECUTE FUNCTION posthog_webhook_fire(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER prune_status_trigger AFTER INSERT ON public.agent_status FOR EACH ROW EXECUTE FUNCTION prune_agent_status(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER trg_prune_agent_status AFTER INSERT ON public.agent_status FOR EACH ROW EXECUTE FUNCTION prune_agent_status(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER trg_call_bookings_set_scheduled_date BEFORE INSERT OR UPDATE ON public.call_bookings FOR EACH ROW EXECUTE FUNCTION call_bookings_set_scheduled_date(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER campaigns_updated_at BEFORE UPDATE ON public.campaigns FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER contact_segments_updated_at BEFORE UPDATE ON public.contact_segments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER contacts_updated_at_trigger BEFORE UPDATE ON public.contacts FOR EACH ROW EXECUTE FUNCTION update_contacts_updated_at(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_device_sessions_updated_at BEFORE UPDATE ON public.device_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER email_templates_update_timestamp BEFORE UPDATE ON public.email_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER escalation_notifications_updated_at BEFORE UPDATE ON public.escalation_notifications FOR EACH ROW EXECUTE FUNCTION update_escalation_notifications_updated_at(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER escalations_updated_at_trigger BEFORE UPDATE ON public.escalations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_escalations_updated_at BEFORE UPDATE ON public.escalations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER trg_follow_ups_updated_at BEFORE UPDATE ON public.follow_ups FOR EACH ROW EXECUTE FUNCTION update_follow_ups_timestamp(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_follow_ups_updated_at BEFORE UPDATE ON public.follow_ups FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_sheets_sync_updated_at BEFORE UPDATE ON public.google_sheets_sync FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER trg_help_ticket_updated BEFORE UPDATE ON public.help_tickets FOR EACH ROW EXECUTE FUNCTION update_help_ticket_timestamp(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER industry_kb_templates_updated_at BEFORE UPDATE ON public.industry_kb_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER trg_jid_mappings_updated_at BEFORE UPDATE ON public.jid_mappings FOR EACH ROW EXECUTE FUNCTION update_jid_mappings_updated_at(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_knowledge_updated_at BEFORE UPDATE ON public.knowledge_bases FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER posthog_webhook_leads_trg AFTER INSERT OR DELETE OR UPDATE ON public.leads FOR EACH ROW EXECUTE FUNCTION posthog_webhook_fire(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON public.leads FOR EACH ROW EXECUTE FUNCTION update_leads_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER onboarding_progress_update BEFORE UPDATE ON public.onboarding_progress FOR EACH ROW EXECUTE FUNCTION update_onboarding_current_step(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER outbound_queue_updated_at BEFORE UPDATE ON public.outbound_queue FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER occ_updated_at BEFORE UPDATE ON public.outreach_campaign_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER tenant_calendars_update_timestamp BEFORE UPDATE ON public.tenant_calendars FOR EACH ROW EXECUTE FUNCTION update_updated_at(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER tenant_email_config_update_timestamp BEFORE UPDATE ON public.tenant_email_config FOR EACH ROW EXECUTE FUNCTION update_updated_at(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER tenant_kb_instances_updated_at BEFORE UPDATE ON public.tenant_kb_template_instances FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_tenant_users_updated_at BEFORE UPDATE ON public.tenant_users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_tenant_users_updated_at BEFORE UPDATE ON public.tenant_users_legacy FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER tenant_default_templates AFTER INSERT ON public.tenants FOR EACH ROW EXECUTE FUNCTION create_default_templates(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON public.tenants FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER vertical_templates_update_timestamp BEFORE UPDATE ON public.vertical_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER trg_web_support_ticket_updated BEFORE UPDATE ON public.web_support_tickets FOR EACH ROW EXECUTE FUNCTION update_web_support_ticket_timestamp(); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $do$;

-- ============================================================================
-- AUDIT NOTE: SECURITY DEFINER functions in public (19 of 32)
-- ============================================================================
-- calculate_campaign_stats, call_bookings_set_scheduled_date, can_view_user,
-- cleanup_expired_onboarding_sessions() and (integer), cleanup_expired_qr_sessions,
-- count_monthly_conversations, current_tenant_id, expire_old_onboarding_sessions,
-- get_contact_last_campaign, get_tenant_daily_sent_count, handle_new_user,
-- increment_click_count, increment_contact_message, is_service_role,
-- posthog_webhook_fire, prune_agent_status, rls_auto_enable, search_knowledge
-- ============================================================================


-- ────────────────────── RLS + POLICIES ────────────────────────────
ALTER TABLE public."Conversation" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."Message" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."SearchRun" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."User" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.action_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_trajectory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.availability_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bjx_agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bjx_content_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bjx_listener_opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bjx_prospect_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bjx_prospects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bjx_publish_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bjx_review_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bjx_touches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.blocked_numbers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.business_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.call_availability ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.call_bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.call_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.call_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.call_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.checklist_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.command_center_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contact_segment_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contact_segments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversion_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customer_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customer_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_digests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dashboard_views ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.data_request_deletions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.device_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.drive_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.email_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.email_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.email_verification_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.escalation_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.escalation_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.escalations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.extracted_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.follow_ups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.google_sheets_sync ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.handover_agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.help_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.holiday_exceptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inbox_copilot_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.industry_kb_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jid_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_base ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_bases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_doc_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_sync_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lead_followups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.link_clicks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.llm_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.media_library ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meeting_blockers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meeting_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meeting_followups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meeting_minutes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meetings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.message_reasons ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.message_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.onboarding_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.onboarding_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outbound_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outreach_campaign_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outreach_consent_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outreach_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.owner_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.owner_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.owner_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.personas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.platform_admins ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.raw_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.response_coordinator_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scheduled_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shared_briefs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shared_context ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sheet_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.short_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.silence_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscription_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.team_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_action_policy ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_calendars ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_email_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_kb_template_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_setup_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_users_legacy ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_verticals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trial_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vertical_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wa_learning_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.web_support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsapp_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_app_state_mutation_macs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_app_state_sync_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_app_state_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_chat_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_device ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_event_buffer ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_identity_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_lid_map ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_message_secrets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_pre_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_privacy_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_sender_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsmeow_version ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN CREATE POLICY "Service role full access to action_items" ON public.action_items AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view accessible action items" ON public.action_items AS PERMISSIVE FOR SELECT TO authenticated USING (((assigned_to = auth.uid()) OR (department_id IN ( SELECT user_profiles.department_id
   FROM user_profiles
  WHERE (user_profiles.id = auth.uid()))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to agent_activity" ON public.agent_activity AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view activity of own agents" ON public.agent_activity AS PERMISSIVE FOR SELECT TO authenticated USING ((connection_id IN ( SELECT agent_connections.id
   FROM agent_connections
  WHERE (agent_connections.user_id = auth.uid())))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY activity_read ON public.agent_activity AS PERMISSIVE FOR SELECT TO public USING ((EXISTS ( SELECT 1
   FROM agent_connections ac
  WHERE ((ac.id = agent_activity.connection_id) AND ((ac.user_id = auth.uid()) OR (EXISTS ( SELECT 1
           FROM user_profiles
          WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = 'owner'::text))))))))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Authenticated users can insert commands" ON public.agent_commands AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((auth.uid() = issued_by)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to agent_commands" ON public.agent_commands AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view own commands" ON public.agent_commands AS PERMISSIVE FOR SELECT TO authenticated USING ((issued_by = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can delete own agent connections" ON public.agent_connections AS PERMISSIVE FOR DELETE TO authenticated USING ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can insert own agent connections" ON public.agent_connections AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can update own agent connections" ON public.agent_connections AS PERMISSIVE FOR UPDATE TO authenticated USING ((user_id = auth.uid())) WITH CHECK ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY agent_connections_select ON public.agent_connections AS PERMISSIVE FOR SELECT TO authenticated USING (((user_id = auth.uid()) OR can_view_user(auth.uid(), user_id))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY connections_delete ON public.agent_connections AS PERMISSIVE FOR DELETE TO public USING ((auth.uid() = user_id)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY connections_read ON public.agent_connections AS PERMISSIVE FOR SELECT TO public USING (((auth.uid() = user_id) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.access_level = ANY (ARRAY['executive'::text, 'director'::text, 'owner'::text]))))) OR (EXISTS ( SELECT 1
   FROM user_profiles v
  WHERE ((v.id = auth.uid()) AND (v.access_level = ANY (ARRAY['manager'::text, 'lead'::text])) AND (v.department_id = ( SELECT user_profiles.department_id
           FROM user_profiles
          WHERE (user_profiles.id = agent_connections.user_id)))))))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY connections_update ON public.agent_connections AS PERMISSIVE FOR UPDATE TO public USING ((auth.uid() = user_id)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to agent_conversations" ON public.agent_conversations AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can insert own conversations" ON public.agent_conversations AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can update own conversations" ON public.agent_conversations AS PERMISSIVE FOR UPDATE TO authenticated USING ((user_id = auth.uid())) WITH CHECK ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view own conversations" ON public.agent_conversations AS PERMISSIVE FOR SELECT TO authenticated USING ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to agent_messages" ON public.agent_messages AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can insert messages in own conversations" ON public.agent_messages AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((conversation_id IN ( SELECT agent_conversations.id
   FROM agent_conversations
  WHERE (agent_conversations.user_id = auth.uid())))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view messages in own conversations" ON public.agent_messages AS PERMISSIVE FOR SELECT TO authenticated USING ((conversation_id IN ( SELECT agent_conversations.id
   FROM agent_conversations
  WHERE (agent_conversations.user_id = auth.uid())))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to agent_status" ON public.agent_status AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view status of own agents" ON public.agent_status AS PERMISSIVE FOR SELECT TO authenticated USING ((connection_id IN ( SELECT agent_connections.id
   FROM agent_connections
  WHERE (agent_connections.user_id = auth.uid())))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY status_read ON public.agent_status AS PERMISSIVE FOR SELECT TO public USING ((EXISTS ( SELECT 1
   FROM agent_connections ac
  WHERE ((ac.id = agent_status.connection_id) AND ((ac.user_id = auth.uid()) OR (EXISTS ( SELECT 1
           FROM user_profiles
          WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = 'owner'::text))))))))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY analytics_policy ON public.analytics AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_api_keys ON public.api_keys AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY availability_overrides_tenant_isolation ON public.availability_overrides AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_blocked ON public.blocked_numbers AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY business_profiles_service_role ON public.business_profiles AS PERMISSIVE FOR ALL TO service_role USING (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY business_profiles_tenant_isolation ON public.business_profiles AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to calendar_events" ON public.calendar_events AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view own calendar events" ON public.calendar_events AS PERMISSIVE FOR SELECT TO authenticated USING (((user_id = auth.uid()) OR can_view_user(auth.uid(), user_id))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY call_availability_tenant_isolation ON public.call_availability AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY call_bookings_tenant_isolation ON public.call_bookings AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY call_settings_tenant_isolation ON public.call_settings AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY call_types_tenant_isolation ON public.call_types AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY campaign_analytics_isolation ON public.campaign_analytics AS PERMISSIVE FOR ALL TO public USING ((EXISTS ( SELECT 1
   FROM campaigns
  WHERE ((campaigns.id = campaign_analytics.campaign_id) AND (campaigns.tenant_id = (current_setting('app.tenant_id'::text, true))::uuid))))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY campaign_templates_isolation ON public.campaign_templates AS PERMISSIVE FOR ALL TO public USING ((EXISTS ( SELECT 1
   FROM campaigns
  WHERE ((campaigns.id = campaign_templates.campaign_id) AND (campaigns.tenant_id = (current_setting('app.tenant_id'::text, true))::uuid))))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY campaigns_tenant_isolation ON public.campaigns AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Authenticated users can insert checklist" ON public.checklist_state AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Authenticated users can update checklist" ON public.checklist_state AS PERMISSIVE FOR UPDATE TO authenticated USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Authenticated users can view checklist" ON public.checklist_state AS PERMISSIVE FOR SELECT TO authenticated USING (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_client_configs ON public.client_configs AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY contact_segment_members_isolation ON public.contact_segment_members AS PERMISSIVE FOR ALL TO public USING ((EXISTS ( SELECT 1
   FROM contact_segments
  WHERE ((contact_segments.id = contact_segment_members.segment_id) AND (contact_segments.tenant_id = (current_setting('app.tenant_id'::text, true))::uuid))))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY contact_segments_tenant_isolation ON public.contact_segments AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY contacts_tenant_isolation ON public.contacts AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_setting('app.tenant_id'::text, true))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY conversation_logs_tenant_isolation ON public.conversation_logs AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.current_tenant'::text))::uuid)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_policy ON public.conversations AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to daily_digests" ON public.daily_digests AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view own digests" ON public.daily_digests AS PERMISSIVE FOR SELECT TO authenticated USING ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to dashboard_views" ON public.dashboard_views AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY dashboard_views_all ON public.dashboard_views AS PERMISSIVE FOR ALL TO authenticated USING (((EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))) OR (created_by = (auth.uid())::text))) WITH CHECK (((EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))) OR (created_by = (auth.uid())::text))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY dashboard_views_select ON public.dashboard_views AS PERMISSIVE FOR SELECT TO authenticated USING (((visibility = 'org'::text) OR ((visibility = 'private'::text) AND (created_by = (auth.uid())::text)) OR ((visibility = 'department'::text) AND (department_id IN ( SELECT user_profiles.department_id
   FROM user_profiles
  WHERE (user_profiles.id = auth.uid())))))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to decisions" ON public.decisions AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view dept decisions" ON public.decisions AS PERMISSIVE FOR SELECT TO authenticated USING (((decision_maker = auth.uid()) OR (auth.uid() = ANY (stakeholders)) OR (department_id IN ( SELECT user_profiles.department_id
   FROM user_profiles
  WHERE (user_profiles.id = auth.uid()))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY departments_admin ON public.departments AS PERMISSIVE FOR ALL TO public USING ((EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.access_level = ANY (ARRAY['executive'::text, 'director'::text])))))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Allow service role full access to device_sessions" ON public.device_sessions AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to drive_documents" ON public.drive_documents AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view accessible drive docs" ON public.drive_documents AS PERMISSIVE FOR SELECT TO authenticated USING (((owner_user_id = auth.uid()) OR ((owner_user_id IS NOT NULL) AND can_view_user(auth.uid(), owner_user_id)))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to email_summaries" ON public.email_summaries AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view own emails" ON public.email_summaries AS PERMISSIVE FOR SELECT TO authenticated USING (((user_id = auth.uid()) OR can_view_user(auth.uid(), user_id))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY email_templates_select ON public.email_templates AS PERMISSIVE FOR SELECT TO public USING (((tenant_id IS NULL) OR (tenant_id = auth.uid()))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY escalations_policy ON public.escalations AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_feedback ON public.feedback AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY sheets_sync_policy ON public.google_sheets_sync AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_handover_agents ON public.handover_agents AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Tenant isolation on help_tickets" ON public.help_tickets AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY holiday_exceptions_tenant_isolation ON public.holiday_exceptions AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY jid_mappings_tenant_isolation ON public.jid_mappings AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to knowledge_base" ON public.knowledge_base AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can insert knowledge" ON public.knowledge_base AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((created_by = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view accessible knowledge" ON public.knowledge_base AS PERMISSIVE FOR SELECT TO authenticated USING (((visibility = 'public'::text) OR (created_by = auth.uid()) OR ((visibility = 'department'::text) AND (department_id IN ( SELECT user_profiles.department_id
   FROM user_profiles
  WHERE (user_profiles.id = auth.uid())))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.access_level = ANY (ARRAY['executive'::text, 'director'::text]))))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_knowledge ON public.knowledge_base AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY knowledge_policy ON public.knowledge_bases AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_knowledge_documents ON public.knowledge_documents AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Enable full access for service role" ON public.leads AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to meeting_minutes" ON public.meeting_minutes AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view dept meeting minutes" ON public.meeting_minutes AS PERMISSIVE FOR SELECT TO authenticated USING (((created_by = auth.uid()) OR (department_id IN ( SELECT user_profiles.department_id
   FROM user_profiles
  WHERE (user_profiles.id = auth.uid()))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_messages ON public.messages AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role has full access to notification_groups" ON public.notification_groups AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role has full access to notification_logs" ON public.notification_logs AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to notifications" ON public.notifications AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can update own notifications" ON public.notifications AS PERMISSIVE FOR UPDATE TO authenticated USING ((user_id = auth.uid())) WITH CHECK ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view own notifications" ON public.notifications AS PERMISSIVE FOR SELECT TO authenticated USING ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role bypass for onboarding_sessions" ON public.onboarding_sessions AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can read own onboarding sessions" ON public.onboarding_sessions AS PERMISSIVE FOR SELECT TO authenticated USING ((email = (( SELECT users.email
   FROM auth.users
  WHERE (users.id = auth.uid())))::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY outbound_queue_tenant_isolation ON public.outbound_queue AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY occ_tenant_isolation ON public.outreach_campaign_configs AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY outreach_logs_tenant_isolation ON public.outreach_logs AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_commands ON public.owner_commands AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_owner_devices ON public.owner_devices AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_full_access_notifications ON public.owner_notifications AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)) WITH CHECK ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_personas ON public.personas AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to projects" ON public.projects AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view dept projects" ON public.projects AS PERMISSIVE FOR SELECT TO authenticated USING (((owner_id = auth.uid()) OR (department_id IN ( SELECT user_profiles.department_id
   FROM user_profiles
  WHERE (user_profiles.id = auth.uid()))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.access_level = ANY (ARRAY['executive'::text, 'director'::text]))))))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY shared_briefs_public_read ON public.shared_briefs AS PERMISSIVE FOR SELECT TO anon USING ((is_public = true)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Authenticated users can view sheet data" ON public.sheet_data AS PERMISSIVE FOR SELECT TO authenticated USING (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to sheet_data" ON public.sheet_data AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to tasks" ON public.tasks AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can insert tasks" ON public.tasks AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((created_by = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view accessible tasks" ON public.tasks AS PERMISSIVE FOR SELECT TO authenticated USING (((assigned_to = auth.uid()) OR (created_by = auth.uid()) OR (department_id IN ( SELECT user_profiles.department_id
   FROM user_profiles
  WHERE (user_profiles.id = auth.uid()))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Authenticated users can insert activity" ON public.team_activity AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Authenticated users can view activity" ON public.team_activity AS PERMISSIVE FOR SELECT TO authenticated USING (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_calendars_select_own ON public.tenant_calendars AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_calendars_update_own ON public.tenant_calendars AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_email_config_select_own ON public.tenant_email_config AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_email_config_update_own ON public.tenant_email_config AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_kb_instances_isolation ON public.tenant_kb_template_instances AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_users_select_own ON public.tenant_users AS PERMISSIVE FOR SELECT TO public USING ((auth.uid() = user_id)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_tenant_users ON public.tenant_users_legacy AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_verticals_select_own ON public.tenant_verticals AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = auth.uid())); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_all_tenants ON public.tenants AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_read_own ON public.tenants AS PERMISSIVE FOR SELECT TO public USING (((auth.role() = 'service_role'::text) OR (id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can insert own profile" ON public.user_profiles AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((auth.uid() = id)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can update own profile" ON public.user_profiles AS PERMISSIVE FOR UPDATE TO authenticated USING ((auth.uid() = id)) WITH CHECK ((auth.uid() = id)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view all profiles" ON public.user_profiles AS PERMISSIVE FOR SELECT TO authenticated USING (true); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY profiles_update ON public.user_profiles AS PERMISSIVE FOR UPDATE TO public USING ((auth.uid() = id)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_whatsapp_devices ON public.whatsapp_devices AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_mutation_macs ON public.whatsmeow_app_state_mutation_macs AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_sync_keys ON public.whatsmeow_app_state_sync_keys AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_state_version ON public.whatsmeow_app_state_version AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_chat_settings ON public.whatsmeow_chat_settings AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_contacts ON public.whatsmeow_contacts AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_whatsmeow_device ON public.whatsmeow_device AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_event_buffer ON public.whatsmeow_event_buffer AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_identity_keys ON public.whatsmeow_identity_keys AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_lid_map ON public.whatsmeow_lid_map AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_message_secrets ON public.whatsmeow_message_secrets AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_pre_keys ON public.whatsmeow_pre_keys AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_privacy_tokens ON public.whatsmeow_privacy_tokens AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_sender_keys ON public.whatsmeow_sender_keys AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_whatsmeow_sessions ON public.whatsmeow_sessions AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_version ON public.whatsmeow_version AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object OR invalid_schema_name OR undefined_function OR undefined_table OR undefined_column THEN NULL; END $$;
