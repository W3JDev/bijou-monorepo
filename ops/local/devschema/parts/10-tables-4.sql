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
