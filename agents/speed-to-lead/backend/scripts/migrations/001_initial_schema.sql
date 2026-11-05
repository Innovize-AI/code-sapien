-- Speed-to-Lead — Initial Schema
-- Run via Supabase SQL editor or psql. Order matters (FK dependencies).

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. resources
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE resources (
    id            text PRIMARY KEY,   -- slug e.g. "id-brochure-2025"
    title         text NOT NULL,
    description   text,
    resource_type text NOT NULL DEFAULT 'pdf',   -- pdf | youtube | video
    url           text,
    vertical      text DEFAULT 'both',           -- interior | real_estate | both
    updated_at    timestamptz DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. leads
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE leads (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    phone               text UNIQUE NOT NULL,
    wa_name             text,
    lead_name           text,

    -- Vertical + qualification
    lead_type           text CHECK (lead_type IN ('interior', 'real_estate')),
    config              text,                   -- 2BHK | 3BHK | 4BHK | Villa
    budget_bracket      text,                   -- under_5L | 5-10L | 10-20L | 20L+
    scope               text,                   -- full_home | specific_room
    design_style        text,                   -- inferred, never asked directly
    is_qualified        boolean DEFAULT false,
    disqualified_reason text,                   -- low_budget | out_of_range

    -- CTWA attribution
    ctwa_source_id      text,
    ctwa_config         text,
    ctwa_location       text,

    -- Booking
    visit_date          date,
    visit_time_slot     text,
    cab_pickup_address  text,                   -- RE only

    -- Lifecycle
    lead_status         text DEFAULT 'new',
    ai_paused           boolean DEFAULT false,
    fallback_count      integer DEFAULT 0,
    source              text DEFAULT 'organic',

    created_at          timestamptz DEFAULT now(),
    last_active         timestamptz DEFAULT now(),
    lead_captured_at    timestamptz
);

CREATE INDEX idx_leads_phone       ON leads(phone);
CREATE INDEX idx_leads_status      ON leads(lead_status);
CREATE INDEX idx_leads_last_active ON leads(last_active);
CREATE INDEX idx_leads_lead_type   ON leads(lead_type);
CREATE INDEX idx_leads_ai_paused   ON leads(ai_paused) WHERE ai_paused = true;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. sessions
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE sessions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id         uuid REFERENCES leads(id) ON DELETE CASCADE,
    context         jsonb NOT NULL DEFAULT '{}',
    turn_count      integer DEFAULT 0,
    stage           text DEFAULT 'discovery',
    started_at      timestamptz DEFAULT now(),
    last_message_at timestamptz DEFAULT now(),
    ended_at        timestamptz
);

CREATE INDEX idx_sessions_lead_id      ON sessions(lead_id);
CREATE INDEX idx_sessions_last_message ON sessions(last_message_at);
CREATE INDEX idx_sessions_active       ON sessions(ended_at) WHERE ended_at IS NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. visits
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE visits (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id               uuid REFERENCES leads(id) ON DELETE CASCADE,
    visit_date            date NOT NULL,
    visit_time_slot       text,
    cab_pickup_address    text,                -- RE only
    status                text DEFAULT 'scheduled',  -- scheduled|rescheduled|cancelled|completed|no_show
    cancellation_reason   text,
    hesitation_code       text,               -- spouse_absent|comparing|loan_pending|price_negotiation|design_undecided|unknown
    confirmed_by_agent_at timestamptz DEFAULT now(),
    reminder_sent_at      timestamptz,
    attended              boolean,
    outcome               text,
    team_notes            text,
    updated_at            timestamptz DEFAULT now()
);

CREATE INDEX idx_visits_lead_id  ON visits(lead_id);
CREATE INDEX idx_visits_date     ON visits(visit_date);
CREATE INDEX idx_visits_attended ON visits(attended);
CREATE INDEX idx_visits_status   ON visits(status);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. conversation_logs
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE conversation_logs (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    uuid REFERENCES sessions(id) ON DELETE CASCADE,
    lead_id       uuid REFERENCES leads(id) ON DELETE CASCADE,
    direction     text NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    sender_type   text NOT NULL CHECK (sender_type IN ('lead', 'ai', 'staff')),
    message_text  text,
    media_type    text,
    path_taken    text,
    pinecone_score float,
    resource_sent text,
    turn_number   integer,
    wa_message_id text,
    created_at    timestamptz DEFAULT now()
);

CREATE INDEX idx_logs_session_id ON conversation_logs(session_id);
CREATE INDEX idx_logs_lead_id    ON conversation_logs(lead_id);
CREATE INDEX idx_logs_created_at ON conversation_logs(created_at);
CREATE INDEX idx_logs_wa_msg_id  ON conversation_logs(wa_message_id)
    WHERE wa_message_id IS NOT NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. retrieval_logs
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE retrieval_logs (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id             uuid REFERENCES sessions(id) ON DELETE CASCADE,
    lead_id                uuid REFERENCES leads(id) ON DELETE CASCADE,
    turn_number            integer,
    query_original         text NOT NULL,
    knowledge_top_score    float,
    knowledge_chunks       jsonb,
    portfolio_matches      jsonb,
    confidence_gate_passed boolean,
    resource_attached      boolean DEFAULT false,
    tools_called           text[],
    pinecone_latency_ms    integer,
    claude_latency_ms      integer,
    total_latency_ms       integer,
    path_taken             text NOT NULL,
    created_at             timestamptz DEFAULT now()
);

CREATE INDEX idx_rlogs_session  ON retrieval_logs(session_id);
CREATE INDEX idx_rlogs_lead     ON retrieval_logs(lead_id);
CREATE INDEX idx_rlogs_score    ON retrieval_logs(knowledge_top_score);
CREATE INDEX idx_rlogs_path     ON retrieval_logs(path_taken);
CREATE INDEX idx_rlogs_created  ON retrieval_logs(created_at);
CREATE INDEX idx_rlogs_fallback ON retrieval_logs(created_at) WHERE path_taken = 'fallback';

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. followup_schedules
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE followup_schedules (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id       uuid REFERENCES leads(id) ON DELETE CASCADE,
    sequence      text NOT NULL,              -- pre_qualification|pre_visit|post_visit|no_show
    day           integer NOT NULL,           -- day within sequence (1, 3, 7, 14)
    template_name text NOT NULL,
    variables     jsonb DEFAULT '{}',
    scheduled_at  timestamptz NOT NULL,
    sent_at       timestamptz,
    status        text DEFAULT 'pending',     -- pending|sent|cancelled
    created_at    timestamptz DEFAULT now()
);

CREATE INDEX idx_followup_lead      ON followup_schedules(lead_id);
CREATE INDEX idx_followup_status    ON followup_schedules(status);
CREATE INDEX idx_followup_scheduled ON followup_schedules(scheduled_at) WHERE status = 'pending';

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. broadcast_campaigns + broadcast_sends
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE broadcast_campaigns (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name              text NOT NULL,
    template_name     text NOT NULL,
    template_language text DEFAULT 'en',
    target_statuses   text[],
    message_preview   text,
    scheduled_at      timestamptz,
    sent_at           timestamptz,
    total_sent        integer DEFAULT 0,
    total_delivered   integer DEFAULT 0,
    total_replied     integer DEFAULT 0,
    created_by        text,
    created_at        timestamptz DEFAULT now()
);

CREATE TABLE broadcast_sends (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id   uuid REFERENCES broadcast_campaigns(id) ON DELETE CASCADE,
    lead_id       uuid REFERENCES leads(id) ON DELETE CASCADE,
    wa_message_id text,
    status        text DEFAULT 'pending',
    error_message text,
    sent_at       timestamptz,
    delivered_at  timestamptz,
    read_at       timestamptz,
    replied_at    timestamptz,
    UNIQUE (campaign_id, lead_id)
);

CREATE INDEX idx_bc_sends_campaign ON broadcast_sends(campaign_id);
CREATE INDEX idx_bc_sends_lead     ON broadcast_sends(lead_id);
CREATE INDEX idx_bc_sends_status   ON broadcast_sends(status);

-- ─────────────────────────────────────────────────────────────────────────────
-- Row-Level Security (service role bypasses for backend writes)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE leads               ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions            ENABLE ROW LEVEL SECURITY;
ALTER TABLE visits              ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_logs   ENABLE ROW LEVEL SECURITY;
ALTER TABLE retrieval_logs      ENABLE ROW LEVEL SECURITY;
ALTER TABLE followup_schedules  ENABLE ROW LEVEL SECURITY;
ALTER TABLE resources           ENABLE ROW LEVEL SECURITY;
ALTER TABLE broadcast_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE broadcast_sends     ENABLE ROW LEVEL SECURITY;

CREATE POLICY "staff_read" ON leads               FOR SELECT TO authenticated USING (true);
CREATE POLICY "staff_read" ON sessions            FOR SELECT TO authenticated USING (true);
CREATE POLICY "staff_read" ON visits              FOR SELECT TO authenticated USING (true);
CREATE POLICY "staff_read" ON conversation_logs   FOR SELECT TO authenticated USING (true);
CREATE POLICY "staff_read" ON retrieval_logs      FOR SELECT TO authenticated USING (true);
CREATE POLICY "staff_read" ON followup_schedules  FOR SELECT TO authenticated USING (true);
CREATE POLICY "staff_read" ON resources           FOR SELECT TO authenticated USING (true);
CREATE POLICY "staff_read" ON broadcast_campaigns FOR SELECT TO authenticated USING (true);
CREATE POLICY "staff_read" ON broadcast_sends     FOR SELECT TO authenticated USING (true);
