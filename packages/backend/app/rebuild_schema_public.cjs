// Drop the unused bijou_agents schema and recreate the agent tables in public
// with an agent_ prefix. This works around Supabase free-tier PostgREST not
// exposing new schemas in its config (db-schemas).
const fs = require("fs");
const path = require("path");
const { Client } = require("pg");

const envRaw = fs.readFileSync(path.join(__dirname, "..", ".env"), "utf-8");
const env = {};
for (const line of envRaw.split(/\r?\n/)) {
  const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
  if (!m) continue;
  let v = m[2].trim();
  if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
  env[m[1]] = v;
}
const url = env.SUPABASE_URL;
const pw = env.SUPABASE_DB_PASSWORD;
const m = url.match(/https?:\/\/([^.]+)\.supabase\.co/);
const connStr = `postgresql://postgres:${encodeURIComponent(pw)}@db.${m[1]}.supabase.co:5432/postgres`;

const SCHEMA = `
-- 2026-07-30: drop the original bijou_agents schema (PostgREST free-tier
-- doesn't expose it). Recreate in public with agent_ prefix so PostgREST
-- sees them out of the box.
DROP SCHEMA IF EXISTS bijou_agents CASCADE;

CREATE TABLE bjx_prospects (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamptz DEFAULT now() NOT NULL,
  updated_at timestamptz DEFAULT now() NOT NULL,
  source text NOT NULL,
  source_id text,
  source_url text,
  business_name text NOT NULL,
  vertical text,
  area text,
  address text,
  city text DEFAULT 'Kuala Lumpur',
  country text DEFAULT 'Malaysia',
  instagram_handle text,
  facebook_page_url text,
  website text,
  has_whatsapp_business boolean DEFAULT false,
  has_booking_link boolean DEFAULT false,
  evidence_notes text,
  estimated_review_count int,
  status text NOT NULL DEFAULT 'new',
  rejection_reason text,
  unique (source, source_id)
);
CREATE INDEX idx_bjx_prospects_vertical ON bjx_prospects(vertical);
CREATE INDEX idx_bjx_prospects_area ON bjx_prospects(area);
CREATE INDEX idx_bjx_prospects_status ON bjx_prospects(status);
CREATE INDEX idx_bjx_prospects_created ON bjx_prospects(created_at DESC);

CREATE TABLE bjx_prospect_scores (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamptz DEFAULT now() NOT NULL,
  prospect_id uuid NOT NULL REFERENCES bjx_prospects(id) ON DELETE CASCADE,
  fit_score int NOT NULL CHECK (fit_score BETWEEN 0 AND 100),
  appointment_driven boolean NOT NULL,
  active_whatsapp boolean NOT NULL,
  owner_reachable boolean NOT NULL,
  evidence_missed_enquiries boolean NOT NULL,
  active_online_presence boolean NOT NULL,
  model text NOT NULL,
  prompt_version text NOT NULL,
  reasoning text
);
CREATE INDEX idx_bjx_prospect_scores_prospect ON bjx_prospect_scores(prospect_id);
CREATE INDEX idx_bjx_prospect_scores_fit ON bjx_prospect_scores(fit_score DESC);

CREATE TABLE bjx_touches (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamptz DEFAULT now() NOT NULL,
  prospect_id uuid NOT NULL REFERENCES bjx_prospects(id) ON DELETE CASCADE,
  channel text NOT NULL,
  direction text NOT NULL,
  message_kind text NOT NULL,
  subject text,
  body_excerpt text,
  sent_by text NOT NULL,
  approved_by text,
  approved_at timestamptz,
  sent_at timestamptz,
  replied_at timestamptz,
  reply_kind text,
  reply_notes text
);
CREATE INDEX idx_bjx_touches_prospect ON bjx_touches(prospect_id);
CREATE INDEX idx_bjx_touches_channel ON bjx_touches(channel);
CREATE INDEX idx_bjx_touches_sent_at ON bjx_touches(sent_at DESC);

CREATE TABLE bjx_content_drafts (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamptz DEFAULT now() NOT NULL,
  updated_at timestamptz DEFAULT now() NOT NULL,
  kind text NOT NULL,
  language text NOT NULL,
  platform text,
  title text,
  body text NOT NULL,
  hashtags text[],
  media_url text,
  word_count int,
  status text NOT NULL DEFAULT 'draft',
  reviewed_by text,
  reviewed_at timestamptz,
  approved_by text,
  approved_at timestamptz,
  scheduled_for timestamptz,
  published_at timestamptz,
  pillar_id uuid REFERENCES bjx_content_drafts(id),
  model text NOT NULL,
  prompt_version text NOT NULL
);
CREATE INDEX idx_bjx_content_drafts_kind ON bjx_content_drafts(kind);
CREATE INDEX idx_bjx_content_drafts_status ON bjx_content_drafts(status);
CREATE INDEX idx_bjx_content_drafts_scheduled ON bjx_content_drafts(scheduled_for);
CREATE INDEX idx_bjx_content_drafts_pillar ON bjx_content_drafts(pillar_id);

CREATE TABLE bjx_review_queue (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamptz DEFAULT now() NOT NULL,
  item_type text NOT NULL,
  payload jsonb NOT NULL,
  source_agent text NOT NULL,
  source_prospect_id uuid REFERENCES bjx_prospects(id),
  source_pillar_id uuid REFERENCES bjx_content_drafts(id),
  source_model text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  priority int DEFAULT 50,
  approved_by text,
  approved_at timestamptz,
  rejection_reason text,
  sent_at timestamptz,
  send_error text,
  expires_at timestamptz DEFAULT (now() + interval '7 days')
);
CREATE INDEX idx_bjx_review_queue_status ON bjx_review_queue(status);
CREATE INDEX idx_bjx_review_queue_priority ON bjx_review_queue(priority DESC, created_at);
CREATE INDEX idx_bjx_review_queue_expires ON bjx_review_queue(expires_at);

CREATE TABLE bjx_listener_opportunities (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamptz DEFAULT now() NOT NULL,
  source text NOT NULL,
  source_url text NOT NULL,
  source_group text,
  post_excerpt text NOT NULL,
  post_author_handle text,
  pain_signals text[],
  match_score int CHECK (match_score BETWEEN 0 AND 100),
  status text NOT NULL DEFAULT 'new',
  queued_review_id uuid REFERENCES bjx_review_queue(id),
  unique (source, source_url)
);
CREATE INDEX idx_agent_listener_status ON bjx_listener_opportunities(status);
CREATE INDEX idx_agent_listener_match ON bjx_listener_opportunities(match_score DESC);

CREATE TABLE bjx_publish_log (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamptz DEFAULT now() NOT NULL,
  content_draft_id uuid REFERENCES bjx_content_drafts(id),
  platform text NOT NULL,
  external_id text,
  external_url text,
  scheduled_for timestamptz,
  published_at timestamptz,
  status text NOT NULL,
  error text
);
CREATE INDEX idx_bjx_publish_log_draft ON bjx_publish_log(content_draft_id);
CREATE INDEX idx_bjx_publish_log_status ON bjx_publish_log(status);

CREATE TABLE bjx_agent_runs (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamptz DEFAULT now() NOT NULL,
  finished_at timestamptz,
  agent_name text NOT NULL,
  trigger_kind text NOT NULL,
  status text NOT NULL,
  items_in int,
  items_out int,
  cost_estimate_usd numeric(10,6),
  error text,
  model text,
  prompt_version text
);
CREATE INDEX idx_bjx_agent_runs_agent ON bjx_agent_runs(agent_name);
CREATE INDEX idx_bjx_agent_runs_status ON bjx_agent_runs(status);
CREATE INDEX idx_bjx_agent_runs_created ON bjx_agent_runs(created_at DESC);

-- Seed demo row
INSERT INTO bjx_prospects (source, source_id, source_url, business_name, vertical, area, has_whatsapp_business)
VALUES ('manual_seed', 'demo-001', 'https://mybijou.xyz', 'Demo Aesthetic Clinic (Klang Valley)', 'aesthetic_clinic', 'KLCC', true)
ON CONFLICT (source, source_id) DO NOTHING;
`;

(async () => {
  const c = new Client({ connectionString: connStr, ssl: { rejectUnauthorized: false } });
  await c.connect();
  console.log(`Connected to db.${m[1]}.supabase.co`);
  try {
    await c.query(SCHEMA);
    console.log("Rebuild in `public` done.");
    // Verify
    const t = await c.query("select table_name from information_schema.tables where table_schema = 'public' and table_name like 'agent_%' order by table_name");
    console.log("bjx_ tables:", t.rows.map(r => r.table_name).join(", "));
  } catch (e) {
    console.error("Rebuild failed:", e.message);
    process.exit(1);
  }
  await c.end();
})();

