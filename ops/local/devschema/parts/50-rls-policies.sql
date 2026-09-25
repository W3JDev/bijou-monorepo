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
DO $$ BEGIN CREATE POLICY "Service role full access to action_items" ON public.action_items AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view accessible action items" ON public.action_items AS PERMISSIVE FOR SELECT TO authenticated USING (((assigned_to = auth.uid()) OR (department_id IN ( SELECT user_profiles.department_id
   FROM user_profiles
  WHERE (user_profiles.id = auth.uid()))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to agent_activity" ON public.agent_activity AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view activity of own agents" ON public.agent_activity AS PERMISSIVE FOR SELECT TO authenticated USING ((connection_id IN ( SELECT agent_connections.id
   FROM agent_connections
  WHERE (agent_connections.user_id = auth.uid())))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY activity_read ON public.agent_activity AS PERMISSIVE FOR SELECT TO public USING ((EXISTS ( SELECT 1
   FROM agent_connections ac
  WHERE ((ac.id = agent_activity.connection_id) AND ((ac.user_id = auth.uid()) OR (EXISTS ( SELECT 1
           FROM user_profiles
          WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = 'owner'::text))))))))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Authenticated users can insert commands" ON public.agent_commands AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((auth.uid() = issued_by)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to agent_commands" ON public.agent_commands AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view own commands" ON public.agent_commands AS PERMISSIVE FOR SELECT TO authenticated USING ((issued_by = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can delete own agent connections" ON public.agent_connections AS PERMISSIVE FOR DELETE TO authenticated USING ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can insert own agent connections" ON public.agent_connections AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can update own agent connections" ON public.agent_connections AS PERMISSIVE FOR UPDATE TO authenticated USING ((user_id = auth.uid())) WITH CHECK ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY agent_connections_select ON public.agent_connections AS PERMISSIVE FOR SELECT TO authenticated USING (((user_id = auth.uid()) OR can_view_user(auth.uid(), user_id))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY connections_delete ON public.agent_connections AS PERMISSIVE FOR DELETE TO public USING ((auth.uid() = user_id)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY connections_read ON public.agent_connections AS PERMISSIVE FOR SELECT TO public USING (((auth.uid() = user_id) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.access_level = ANY (ARRAY['executive'::text, 'director'::text, 'owner'::text]))))) OR (EXISTS ( SELECT 1
   FROM user_profiles v
  WHERE ((v.id = auth.uid()) AND (v.access_level = ANY (ARRAY['manager'::text, 'lead'::text])) AND (v.department_id = ( SELECT user_profiles.department_id
           FROM user_profiles
          WHERE (user_profiles.id = agent_connections.user_id)))))))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY connections_update ON public.agent_connections AS PERMISSIVE FOR UPDATE TO public USING ((auth.uid() = user_id)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to agent_conversations" ON public.agent_conversations AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can insert own conversations" ON public.agent_conversations AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can update own conversations" ON public.agent_conversations AS PERMISSIVE FOR UPDATE TO authenticated USING ((user_id = auth.uid())) WITH CHECK ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view own conversations" ON public.agent_conversations AS PERMISSIVE FOR SELECT TO authenticated USING ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to agent_messages" ON public.agent_messages AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can insert messages in own conversations" ON public.agent_messages AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((conversation_id IN ( SELECT agent_conversations.id
   FROM agent_conversations
  WHERE (agent_conversations.user_id = auth.uid())))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view messages in own conversations" ON public.agent_messages AS PERMISSIVE FOR SELECT TO authenticated USING ((conversation_id IN ( SELECT agent_conversations.id
   FROM agent_conversations
  WHERE (agent_conversations.user_id = auth.uid())))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to agent_status" ON public.agent_status AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view status of own agents" ON public.agent_status AS PERMISSIVE FOR SELECT TO authenticated USING ((connection_id IN ( SELECT agent_connections.id
   FROM agent_connections
  WHERE (agent_connections.user_id = auth.uid())))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY status_read ON public.agent_status AS PERMISSIVE FOR SELECT TO public USING ((EXISTS ( SELECT 1
   FROM agent_connections ac
  WHERE ((ac.id = agent_status.connection_id) AND ((ac.user_id = auth.uid()) OR (EXISTS ( SELECT 1
           FROM user_profiles
          WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = 'owner'::text))))))))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY analytics_policy ON public.analytics AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_api_keys ON public.api_keys AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY availability_overrides_tenant_isolation ON public.availability_overrides AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_blocked ON public.blocked_numbers AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY business_profiles_service_role ON public.business_profiles AS PERMISSIVE FOR ALL TO service_role USING (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY business_profiles_tenant_isolation ON public.business_profiles AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to calendar_events" ON public.calendar_events AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view own calendar events" ON public.calendar_events AS PERMISSIVE FOR SELECT TO authenticated USING (((user_id = auth.uid()) OR can_view_user(auth.uid(), user_id))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY call_availability_tenant_isolation ON public.call_availability AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY call_bookings_tenant_isolation ON public.call_bookings AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY call_settings_tenant_isolation ON public.call_settings AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY call_types_tenant_isolation ON public.call_types AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY campaign_analytics_isolation ON public.campaign_analytics AS PERMISSIVE FOR ALL TO public USING ((EXISTS ( SELECT 1
   FROM campaigns
  WHERE ((campaigns.id = campaign_analytics.campaign_id) AND (campaigns.tenant_id = (current_setting('app.tenant_id'::text, true))::uuid))))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY campaign_templates_isolation ON public.campaign_templates AS PERMISSIVE FOR ALL TO public USING ((EXISTS ( SELECT 1
   FROM campaigns
  WHERE ((campaigns.id = campaign_templates.campaign_id) AND (campaigns.tenant_id = (current_setting('app.tenant_id'::text, true))::uuid))))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY campaigns_tenant_isolation ON public.campaigns AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Authenticated users can insert checklist" ON public.checklist_state AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Authenticated users can update checklist" ON public.checklist_state AS PERMISSIVE FOR UPDATE TO authenticated USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Authenticated users can view checklist" ON public.checklist_state AS PERMISSIVE FOR SELECT TO authenticated USING (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_client_configs ON public.client_configs AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY contact_segment_members_isolation ON public.contact_segment_members AS PERMISSIVE FOR ALL TO public USING ((EXISTS ( SELECT 1
   FROM contact_segments
  WHERE ((contact_segments.id = contact_segment_members.segment_id) AND (contact_segments.tenant_id = (current_setting('app.tenant_id'::text, true))::uuid))))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY contact_segments_tenant_isolation ON public.contact_segments AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY contacts_tenant_isolation ON public.contacts AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_setting('app.tenant_id'::text, true))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY conversation_logs_tenant_isolation ON public.conversation_logs AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.current_tenant'::text))::uuid)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_policy ON public.conversations AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to daily_digests" ON public.daily_digests AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view own digests" ON public.daily_digests AS PERMISSIVE FOR SELECT TO authenticated USING ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to dashboard_views" ON public.dashboard_views AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY dashboard_views_all ON public.dashboard_views AS PERMISSIVE FOR ALL TO authenticated USING (((EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))) OR (created_by = (auth.uid())::text))) WITH CHECK (((EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))) OR (created_by = (auth.uid())::text))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY dashboard_views_select ON public.dashboard_views AS PERMISSIVE FOR SELECT TO authenticated USING (((visibility = 'org'::text) OR ((visibility = 'private'::text) AND (created_by = (auth.uid())::text)) OR ((visibility = 'department'::text) AND (department_id IN ( SELECT user_profiles.department_id
   FROM user_profiles
  WHERE (user_profiles.id = auth.uid())))))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to decisions" ON public.decisions AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view dept decisions" ON public.decisions AS PERMISSIVE FOR SELECT TO authenticated USING (((decision_maker = auth.uid()) OR (auth.uid() = ANY (stakeholders)) OR (department_id IN ( SELECT user_profiles.department_id
   FROM user_profiles
  WHERE (user_profiles.id = auth.uid()))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY departments_admin ON public.departments AS PERMISSIVE FOR ALL TO public USING ((EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.access_level = ANY (ARRAY['executive'::text, 'director'::text])))))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Allow service role full access to device_sessions" ON public.device_sessions AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to drive_documents" ON public.drive_documents AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view accessible drive docs" ON public.drive_documents AS PERMISSIVE FOR SELECT TO authenticated USING (((owner_user_id = auth.uid()) OR ((owner_user_id IS NOT NULL) AND can_view_user(auth.uid(), owner_user_id)))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to email_summaries" ON public.email_summaries AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view own emails" ON public.email_summaries AS PERMISSIVE FOR SELECT TO authenticated USING (((user_id = auth.uid()) OR can_view_user(auth.uid(), user_id))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY email_templates_select ON public.email_templates AS PERMISSIVE FOR SELECT TO public USING (((tenant_id IS NULL) OR (tenant_id = auth.uid()))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY escalations_policy ON public.escalations AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_feedback ON public.feedback AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY sheets_sync_policy ON public.google_sheets_sync AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_handover_agents ON public.handover_agents AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Tenant isolation on help_tickets" ON public.help_tickets AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY holiday_exceptions_tenant_isolation ON public.holiday_exceptions AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY jid_mappings_tenant_isolation ON public.jid_mappings AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to knowledge_base" ON public.knowledge_base AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can insert knowledge" ON public.knowledge_base AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((created_by = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view accessible knowledge" ON public.knowledge_base AS PERMISSIVE FOR SELECT TO authenticated USING (((visibility = 'public'::text) OR (created_by = auth.uid()) OR ((visibility = 'department'::text) AND (department_id IN ( SELECT user_profiles.department_id
   FROM user_profiles
  WHERE (user_profiles.id = auth.uid())))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.access_level = ANY (ARRAY['executive'::text, 'director'::text]))))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_knowledge ON public.knowledge_base AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY knowledge_policy ON public.knowledge_bases AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_knowledge_documents ON public.knowledge_documents AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Enable full access for service role" ON public.leads AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to meeting_minutes" ON public.meeting_minutes AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view dept meeting minutes" ON public.meeting_minutes AS PERMISSIVE FOR SELECT TO authenticated USING (((created_by = auth.uid()) OR (department_id IN ( SELECT user_profiles.department_id
   FROM user_profiles
  WHERE (user_profiles.id = auth.uid()))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_messages ON public.messages AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role has full access to notification_groups" ON public.notification_groups AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role has full access to notification_logs" ON public.notification_logs AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to notifications" ON public.notifications AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can update own notifications" ON public.notifications AS PERMISSIVE FOR UPDATE TO authenticated USING ((user_id = auth.uid())) WITH CHECK ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view own notifications" ON public.notifications AS PERMISSIVE FOR SELECT TO authenticated USING ((user_id = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role bypass for onboarding_sessions" ON public.onboarding_sessions AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can read own onboarding sessions" ON public.onboarding_sessions AS PERMISSIVE FOR SELECT TO authenticated USING ((email = (( SELECT users.email
   FROM auth.users
  WHERE (users.id = auth.uid())))::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY outbound_queue_tenant_isolation ON public.outbound_queue AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY occ_tenant_isolation ON public.outreach_campaign_configs AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY outreach_logs_tenant_isolation ON public.outreach_logs AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_commands ON public.owner_commands AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_owner_devices ON public.owner_devices AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_full_access_notifications ON public.owner_notifications AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)) WITH CHECK ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_isolation_personas ON public.personas AS PERMISSIVE FOR ALL TO public USING (((auth.role() = 'service_role'::text) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to projects" ON public.projects AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view dept projects" ON public.projects AS PERMISSIVE FOR SELECT TO authenticated USING (((owner_id = auth.uid()) OR (department_id IN ( SELECT user_profiles.department_id
   FROM user_profiles
  WHERE (user_profiles.id = auth.uid()))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.access_level = ANY (ARRAY['executive'::text, 'director'::text]))))))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY shared_briefs_public_read ON public.shared_briefs AS PERMISSIVE FOR SELECT TO anon USING ((is_public = true)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Authenticated users can view sheet data" ON public.sheet_data AS PERMISSIVE FOR SELECT TO authenticated USING (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to sheet_data" ON public.sheet_data AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Service role full access to tasks" ON public.tasks AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can insert tasks" ON public.tasks AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((created_by = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view accessible tasks" ON public.tasks AS PERMISSIVE FOR SELECT TO authenticated USING (((assigned_to = auth.uid()) OR (created_by = auth.uid()) OR (department_id IN ( SELECT user_profiles.department_id
   FROM user_profiles
  WHERE (user_profiles.id = auth.uid()))) OR (EXISTS ( SELECT 1
   FROM user_profiles
  WHERE ((user_profiles.id = auth.uid()) AND (user_profiles.role = ANY (ARRAY['owner'::text, 'admin'::text]))))))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Authenticated users can insert activity" ON public.team_activity AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Authenticated users can view activity" ON public.team_activity AS PERMISSIVE FOR SELECT TO authenticated USING (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_calendars_select_own ON public.tenant_calendars AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_calendars_update_own ON public.tenant_calendars AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_email_config_select_own ON public.tenant_email_config AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_email_config_update_own ON public.tenant_email_config AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_kb_instances_isolation ON public.tenant_kb_template_instances AS PERMISSIVE FOR ALL TO public USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::uuid)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_users_select_own ON public.tenant_users AS PERMISSIVE FOR SELECT TO public USING ((auth.uid() = user_id)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_tenant_users ON public.tenant_users_legacy AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_verticals_select_own ON public.tenant_verticals AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = auth.uid())); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_all_tenants ON public.tenants AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY tenant_read_own ON public.tenants AS PERMISSIVE FOR SELECT TO public USING (((auth.role() = 'service_role'::text) OR (id = (current_setting('app.current_tenant_id'::text, true))::uuid))); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can insert own profile" ON public.user_profiles AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((auth.uid() = id)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can update own profile" ON public.user_profiles AS PERMISSIVE FOR UPDATE TO authenticated USING ((auth.uid() = id)) WITH CHECK ((auth.uid() = id)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY "Users can view all profiles" ON public.user_profiles AS PERMISSIVE FOR SELECT TO authenticated USING (true); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY profiles_update ON public.user_profiles AS PERMISSIVE FOR UPDATE TO public USING ((auth.uid() = id)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_whatsapp_devices ON public.whatsapp_devices AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_mutation_macs ON public.whatsmeow_app_state_mutation_macs AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_sync_keys ON public.whatsmeow_app_state_sync_keys AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_state_version ON public.whatsmeow_app_state_version AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_chat_settings ON public.whatsmeow_chat_settings AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_contacts ON public.whatsmeow_contacts AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_whatsmeow_device ON public.whatsmeow_device AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_event_buffer ON public.whatsmeow_event_buffer AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_identity_keys ON public.whatsmeow_identity_keys AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_lid_map ON public.whatsmeow_lid_map AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_message_secrets ON public.whatsmeow_message_secrets AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_pre_keys ON public.whatsmeow_pre_keys AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_privacy_tokens ON public.whatsmeow_privacy_tokens AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_sender_keys ON public.whatsmeow_sender_keys AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_whatsmeow_sessions ON public.whatsmeow_sessions AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE POLICY service_role_only_version ON public.whatsmeow_version AS PERMISSIVE FOR ALL TO public USING ((auth.role() = 'service_role'::text)); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
