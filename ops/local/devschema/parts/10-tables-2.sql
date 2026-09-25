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
