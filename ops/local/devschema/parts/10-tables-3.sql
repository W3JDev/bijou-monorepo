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
