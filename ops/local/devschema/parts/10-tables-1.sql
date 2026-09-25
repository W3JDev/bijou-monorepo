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
