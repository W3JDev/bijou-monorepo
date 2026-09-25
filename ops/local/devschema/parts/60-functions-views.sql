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

DO $do$ BEGIN CREATE TRIGGER posthog_webhook_user_trg AFTER INSERT OR DELETE OR UPDATE ON public."User" FOR EACH ROW EXECUTE FUNCTION posthog_webhook_fire(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER prune_status_trigger AFTER INSERT ON public.agent_status FOR EACH ROW EXECUTE FUNCTION prune_agent_status(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER trg_prune_agent_status AFTER INSERT ON public.agent_status FOR EACH ROW EXECUTE FUNCTION prune_agent_status(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER trg_call_bookings_set_scheduled_date BEFORE INSERT OR UPDATE ON public.call_bookings FOR EACH ROW EXECUTE FUNCTION call_bookings_set_scheduled_date(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER campaigns_updated_at BEFORE UPDATE ON public.campaigns FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER contact_segments_updated_at BEFORE UPDATE ON public.contact_segments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER contacts_updated_at_trigger BEFORE UPDATE ON public.contacts FOR EACH ROW EXECUTE FUNCTION update_contacts_updated_at(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_device_sessions_updated_at BEFORE UPDATE ON public.device_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER email_templates_update_timestamp BEFORE UPDATE ON public.email_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER escalation_notifications_updated_at BEFORE UPDATE ON public.escalation_notifications FOR EACH ROW EXECUTE FUNCTION update_escalation_notifications_updated_at(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER escalations_updated_at_trigger BEFORE UPDATE ON public.escalations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_escalations_updated_at BEFORE UPDATE ON public.escalations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER trg_follow_ups_updated_at BEFORE UPDATE ON public.follow_ups FOR EACH ROW EXECUTE FUNCTION update_follow_ups_timestamp(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_follow_ups_updated_at BEFORE UPDATE ON public.follow_ups FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_sheets_sync_updated_at BEFORE UPDATE ON public.google_sheets_sync FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER trg_help_ticket_updated BEFORE UPDATE ON public.help_tickets FOR EACH ROW EXECUTE FUNCTION update_help_ticket_timestamp(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER industry_kb_templates_updated_at BEFORE UPDATE ON public.industry_kb_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER trg_jid_mappings_updated_at BEFORE UPDATE ON public.jid_mappings FOR EACH ROW EXECUTE FUNCTION update_jid_mappings_updated_at(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_knowledge_updated_at BEFORE UPDATE ON public.knowledge_bases FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER posthog_webhook_leads_trg AFTER INSERT OR DELETE OR UPDATE ON public.leads FOR EACH ROW EXECUTE FUNCTION posthog_webhook_fire(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON public.leads FOR EACH ROW EXECUTE FUNCTION update_leads_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER onboarding_progress_update BEFORE UPDATE ON public.onboarding_progress FOR EACH ROW EXECUTE FUNCTION update_onboarding_current_step(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER outbound_queue_updated_at BEFORE UPDATE ON public.outbound_queue FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER occ_updated_at BEFORE UPDATE ON public.outreach_campaign_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER tenant_calendars_update_timestamp BEFORE UPDATE ON public.tenant_calendars FOR EACH ROW EXECUTE FUNCTION update_updated_at(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER tenant_email_config_update_timestamp BEFORE UPDATE ON public.tenant_email_config FOR EACH ROW EXECUTE FUNCTION update_updated_at(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER tenant_kb_instances_updated_at BEFORE UPDATE ON public.tenant_kb_template_instances FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_tenant_users_updated_at BEFORE UPDATE ON public.tenant_users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_tenant_users_updated_at BEFORE UPDATE ON public.tenant_users_legacy FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER tenant_default_templates AFTER INSERT ON public.tenants FOR EACH ROW EXECUTE FUNCTION create_default_templates(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON public.tenants FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER vertical_templates_update_timestamp BEFORE UPDATE ON public.vertical_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;
DO $do$ BEGIN CREATE TRIGGER trg_web_support_ticket_updated BEFORE UPDATE ON public.web_support_tickets FOR EACH ROW EXECUTE FUNCTION update_web_support_ticket_timestamp(); EXCEPTION WHEN duplicate_object THEN NULL; END $do$;

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
