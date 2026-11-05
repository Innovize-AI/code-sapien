# Project Saarthi — Supabase Database Schema
**Single authoritative reference for all tables. All other documents defer to this file.**

---

## Table of Contents

1. [leads](#1-leads)
2. [visits](#2-visits)
3. [sessions](#3-sessions)
4. [conversation_logs](#4-conversation_logs)
5. [retrieval_logs](#5-retrieval_logs)
6. [fee_data](#6-fee_data)
7. [transport_data](#7-transport_data)
8. [documents](#8-documents)
9. [broadcast_campaigns](#9-broadcast_campaigns)
10. [broadcast_sends](#10-broadcast_sends)

---

## 1. leads

Core record for every parent who contacts DWPS via WhatsApp. One row per phone number.

```sql
CREATE TABLE leads (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    phone                 text UNIQUE NOT NULL,          -- E.164 format: +919XXXXXXXXX

    -- Identity
    wa_name               text,                          -- WhatsApp display name (from webhook)
    parent_name           text,                          -- Confirmed name from conversation

    -- Interest signals (updated throughout conversation)
    grade                 text,                          -- 'LKG', 'Class 3', 'Grade 10', etc.
    board_preference      text,                          -- 'cbse' | 'cambridge' | NULL (undecided)
    transport_area        text,                          -- 'Hayathnagar', 'Kompally', etc.
    child_current_school  text,                          -- Current school (switching families)
    primary_concern       text,                          -- 'fees' | 'curriculum' | 'distance' | 'facilities' | 'culture'

    -- Attribution
    source                text DEFAULT 'organic',        -- 'organic' | 'ctwa' | 'referral' | 'reactivation'
    ctwa_source_id        text,                          -- Meta ad source_id from CTWA referral payload
    ctwa_headline         text,                          -- Ad headline parent clicked
    ctwa_clid             text,                          -- Click ID for Meta attribution

    -- Lifecycle
    lead_status           text DEFAULT 'new',
        -- 'new'           → first message received
        -- 'engaged'       → 2+ turns, signals captured
        -- 'visit_booked'  → visit date confirmed
        -- 'visit_attended'→ physically came to campus
        -- 'enrolled'      → admission taken
        -- 'cold'          → 14+ days no reply
        -- 'dead'          → explicitly said not interested / enrolled elsewhere

    -- Call preference (when parent declines visit)
    call_requested        boolean DEFAULT false,
    call_preferred_time   text,                          -- 'morning' | 'afternoon' | 'evening' | free text

    -- DPDP Consent (India Digital Personal Data Protection Act 2023)
    -- No lead fields (name, grade, area) are stored until consent_given = true
    consent_pending       boolean DEFAULT false,         -- Consent message sent, waiting for reply
    consent_given         boolean DEFAULT false,         -- Parent explicitly said YES
    consent_given_at      timestamptz,                   -- Timestamp of consent
    consent_declined      boolean DEFAULT false,         -- Parent said STOP/NO — never contact again

    -- Operations
    ai_paused             boolean DEFAULT false,         -- Counselor has taken over; AI stays silent
    fallback_count        integer DEFAULT 0,             -- How many times confidence < 0.80 fallback triggered
    broadcast_sent        boolean DEFAULT false,         -- Dead lead reactivation broadcast sent

    -- Timestamps
    created_at            timestamptz DEFAULT now(),
    last_active           timestamptz DEFAULT now(),     -- Updated on every inbound message
    lead_captured_at      timestamptz                    -- When name + grade both known (qualified lead)
);

-- Indexes
CREATE INDEX idx_leads_phone        ON leads(phone);
CREATE INDEX idx_leads_status       ON leads(lead_status);
CREATE INDEX idx_leads_last_active  ON leads(last_active);
CREATE INDEX idx_leads_source       ON leads(source);
CREATE INDEX idx_leads_ai_paused    ON leads(ai_paused) WHERE ai_paused = true;
```

**Status transition flow:**
```
new → engaged → visit_booked → visit_attended → enrolled
                             ↘ cold → (reactivation) → re-engaged
                                    → dead
```

---

## 2. visits

One row per booked campus visit. A lead can have multiple visits (reschedules create a new row).

```sql
CREATE TABLE visits (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id               uuid REFERENCES leads(id) ON DELETE CASCADE,

    -- Booking details (captured during conversation)
    visit_date            date NOT NULL,
    time_slot             text,                          -- 'morning (9-11am)' | 'afternoon (12-2pm)'
    grade                 text,                          -- Grade of interest at time of booking
    board_preference      text,                          -- 'cbse' | 'cambridge' | NULL

    -- Context for counselor prep
    child_current_school  text,
    primary_concern       text,                          -- What the parent cares most about
    parent_name           text,                          -- Denormalized from leads for quick counselor access

    -- Agent tracking
    confirmed_by_agent_at timestamptz DEFAULT now(),
    reminder_sent_at      timestamptz,                   -- Populated when D-1 reminder template sent

    -- Post-visit outcome (filled by DWPS team)
    attended              boolean,                       -- NULL = scheduled, true/false = outcome known
    outcome               text,
        -- 'enrolled'     → admission taken same day
        -- 'follow_up'    → interested, needs time
        -- 'not_fit'      → not the right school for them
        -- 'no_show'      → didn't come without cancelling
    counselor_name        text,                          -- Who handled the visit
    team_notes            text,                          -- Free-form notes from counselor

    updated_at            timestamptz DEFAULT now()
);

-- Indexes
CREATE INDEX idx_visits_lead_id    ON visits(lead_id);
CREATE INDEX idx_visits_date       ON visits(visit_date);
CREATE INDEX idx_visits_attended   ON visits(attended);
```

---

## 3. sessions

One row per WhatsApp conversation session. A new session starts when a lead messages after 24 hours of silence.

```sql
CREATE TABLE sessions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id         uuid REFERENCES leads(id) ON DELETE CASCADE,

    -- State snapshot (serialized SessionContext dataclass)
    context         jsonb NOT NULL DEFAULT '{}',
        -- Fields: name, grade_interest, board_preference, area, primary_concern,
        --         stage, turn_count, topics_covered, resources_shared,
        --         lead_name_captured, lead_grade_captured, lead_tour_date_captured,
        --         ai_paused, reactivated, ctwa_source

    -- Session metadata
    turn_count      integer DEFAULT 0,
    stage           text DEFAULT 'discovery',
        -- 'discovery' | 'exploration' | 'consideration' | 'intent' | 'conversion'

    -- Timestamps
    started_at      timestamptz DEFAULT now(),
    last_message_at timestamptz DEFAULT now(),
    ended_at        timestamptz                          -- NULL = session still active
);

-- Indexes
CREATE INDEX idx_sessions_lead_id        ON sessions(lead_id);
CREATE INDEX idx_sessions_last_message   ON sessions(last_message_at);
CREATE INDEX idx_sessions_stage          ON sessions(stage);
```

**Active session lookup:**
```sql
-- Get current open session for a phone number
SELECT s.*
FROM sessions s
JOIN leads l ON l.id = s.lead_id
WHERE l.phone = $1
  AND s.ended_at IS NULL
ORDER BY s.started_at DESC
LIMIT 1;
```

---

## 4. conversation_logs

Append-only log of every message exchanged. Never update rows — only insert.

```sql
CREATE TABLE conversation_logs (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      uuid REFERENCES sessions(id) ON DELETE CASCADE,
    lead_id         uuid REFERENCES leads(id) ON DELETE CASCADE,

    -- Message content
    direction       text NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    message_text    text,                               -- Raw text of the message
    media_type      text,                               -- NULL | 'image' | 'document' | 'audio'
    media_url       text,                               -- If inbound media was received

    -- Routing metadata (what happened when processing this message)
    path_taken      text,
        -- 'fee_hardlock'      → Supabase direct query
        -- 'is_answering'      → session context update, no Pinecone
        -- 'conversational'    → Gemini reply, no Pinecone
        -- 'rag'               → Pinecone knowledge search + Gemini
        -- 'fallback'          → confidence < 0.80 fallback
        -- 'live_counselor'    → ai_paused, sent by human
    pinecone_score  float,                              -- Top knowledge chunk score (NULL if no RAG)
    resource_sent   text,                               -- Resource ID attached, if any (e.g. 'fee-structure-pdf')

    -- Turn metadata
    turn_number     integer,                            -- Turn within this session
    wa_message_id   text,                               -- Meta message ID (for dedup and status tracking)
    wa_status       text,                               -- 'sent' | 'delivered' | 'read' | 'failed'

    created_at      timestamptz DEFAULT now()
);

-- Indexes
CREATE INDEX idx_logs_session_id  ON conversation_logs(session_id);
CREATE INDEX idx_logs_lead_id     ON conversation_logs(lead_id);
CREATE INDEX idx_logs_created_at  ON conversation_logs(created_at);
CREATE INDEX idx_logs_wa_msg_id   ON conversation_logs(wa_message_id) WHERE wa_message_id IS NOT NULL;
```

---

## 5. retrieval_logs

Append-only observability log for every RAG path invocation. Feeds the admin dashboard (KB gap analysis, fallback rate, retrieval quality trend). Never update rows — only insert.

```sql
CREATE TABLE retrieval_logs (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              uuid REFERENCES sessions(id) ON DELETE CASCADE,
    lead_id                 uuid REFERENCES leads(id) ON DELETE CASCADE,
    turn_number             integer,

    -- Query (what went into Pinecone)
    query_original          text NOT NULL,          -- raw parent message
    query_rewritten         text,                   -- NULL if no rewrite
    query_rewrite_type      text,
        -- 'none' | 'cheap_expansion' | 'full_gemini_rewrite'

    -- Knowledge namespace results
    knowledge_top_score     float,                  -- top chunk cosine score (NULL for non-RAG paths)
    knowledge_chunks        jsonb,
        -- [{text, score, source, doc_type}] top 5 chunks returned
    confidence_gate_passed  boolean,                -- score >= 0.80

    -- Resources namespace results
    resource_top_score      float,
    resource_candidate_id   text,                   -- which resource matched (e.g. 'fee-structure-pdf')
    resource_attached       boolean DEFAULT false,  -- did it actually get sent?
    resource_gate_fail      text,
        -- NULL if attached or no candidate
        -- 'score_low' | 'already_sent' | 'parent_answering'
        -- | 'consecutive_turn' | 'session_cap'

    -- Latency (milliseconds)
    embed_latency_ms        integer,
    pinecone_latency_ms     integer,
    gemini_latency_ms       integer,
    total_latency_ms        integer,

    -- Routing
    path_taken              text NOT NULL,
        -- 'fee_hardlock' | 'is_answering' | 'conversational' | 'rag' | 'fallback'

    created_at              timestamptz DEFAULT now()
);

CREATE INDEX idx_rlogs_session   ON retrieval_logs(session_id);
CREATE INDEX idx_rlogs_lead      ON retrieval_logs(lead_id);
CREATE INDEX idx_rlogs_score     ON retrieval_logs(knowledge_top_score);
CREATE INDEX idx_rlogs_path      ON retrieval_logs(path_taken);
CREATE INDEX idx_rlogs_created   ON retrieval_logs(created_at);
CREATE INDEX idx_rlogs_fallback  ON retrieval_logs(created_at)
    WHERE path_taken = 'fallback';           -- fast fallback-only queries for dashboard
```

**Key dashboard queries this table powers:**
- Fallback rate % (knowledge base gap indicator)
- Top unanswered questions (what to add to KB next)
- Average retrieval score trend over time (KB quality health)
- Resource attachment breakdown by resource ID
- Query rewrite rate and its effect on score

---

## 6. fee_data

Structured fee table. Bypasses RAG entirely — fetched with a direct Supabase query for any fee question.

```sql
CREATE TABLE fee_data (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    class_name       text NOT NULL,                     -- 'LKG', 'UKG', 'Class 1' … 'Class 10'
    board            text NOT NULL CHECK (board IN ('cbse', 'cambridge')),
    tuition_per_term integer,                           -- In INR
    terms_per_year   integer,                           -- Typically 3 for CBSE, 4 for Cambridge
    admission_fee    integer,                           -- One-time, first year only
    annual_tuition   integer GENERATED ALWAYS AS (tuition_per_term * terms_per_year) STORED,
    updated_at       timestamptz DEFAULT now(),

    UNIQUE (class_name, board)
);

-- Example rows
-- INSERT INTO fee_data (class_name, board, tuition_per_term, terms_per_year, admission_fee)
-- VALUES
--   ('Class 3', 'cbse',      18000, 3, 15000),
--   ('Class 3', 'cambridge', 22000, 4, 20000);
```

---

## 7. transport_data

Transport fee lookup by area. Part of the fee hardlock — fetched alongside fee_data when area is known.

```sql
CREATE TABLE transport_data (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    area            text NOT NULL,                      -- 'Hayathnagar', 'Kompally', 'LB Nagar'
    route_name      text,                               -- 'Route A — Hayathnagar via ORR'
    pickup_time     text,                               -- '7:15 AM'
    fee_per_month   integer,                            -- In INR
    annual_fee      integer GENERATED ALWAYS AS (fee_per_month * 10) STORED,  -- 10-month academic year
    updated_at      timestamptz DEFAULT now(),

    UNIQUE (area)
);
```

**Combined fee + transport query:**
```python
async def handle_fee_query(grade: str, board: str, area: str | None) -> str:
    fee = await supabase.table("fee_data").select("*")
              .eq("class_name", grade).eq("board", board).single().execute()
    transport = None
    if area:
        transport = await supabase.table("transport_data").select("*")
                        .eq("area", area).single().execute()

    lines = [
        f"{grade} {board.upper()} fees (2026-27):",
        f"Tuition: ₹{fee.tuition_per_term:,}/term × {fee.terms_per_year} = ₹{fee.annual_tuition:,}/year",
        f"Admission fee (first year only): ₹{fee.admission_fee:,}"
    ]
    if transport:
        lines += [
            f"Transport from {area}: ₹{transport.fee_per_month:,}/month",
            f"Year 1 total: ₹{fee.annual_tuition + fee.admission_fee + transport.annual_fee:,}",
            f"Year 2+ total: ₹{fee.annual_tuition + transport.annual_fee:,}/year"
        ]
    return "\n".join(lines)
```

---

## 8. documents

Registry of every ingested document — both knowledge chunks in Pinecone and resources sent via WhatsApp. Pinecone holds the vectors; this table holds the canonical metadata.

```sql
CREATE TABLE documents (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pinecone_id     text UNIQUE,                        -- Vector ID prefix (e.g. 'fee-structure-chunk')
    title           text NOT NULL,
    doc_type        text NOT NULL,
        -- 'fee_structure' | 'admission_guide' | 'prospectus' | 'curriculum'
        -- | 'faq' | 'magazine' | 'academic_calendar' | 'campus_tour' | 'welcome_video'
    file_type       text NOT NULL CHECK (file_type IN ('pdf', 'youtube', 'excel', 'docx')),
    storage_url     text,                               -- GCS URL for PDFs; YouTube URL for videos
    pinecone_namespaces text[],                         -- Which namespaces this doc is indexed in
        -- '{knowledge}' | '{resources}' | '{knowledge,resources}'
    topics          text[],                             -- Topic tags used for resource search
    trigger_intents text[],                             -- Intent names that should trigger attaching this doc
    ingested_at     timestamptz DEFAULT now(),
    last_updated    timestamptz DEFAULT now(),
    notes           text                                -- E.g. "image-based PDF, OCR pending"
);
```

**Example rows:**
```sql
INSERT INTO documents (title, doc_type, file_type, storage_url, pinecone_namespaces, topics, trigger_intents, notes) VALUES
(
    'DWPS Fee Structure 2026-27', 'fee_structure', 'pdf',
    'https://storage.googleapis.com/saarthi-docs/fee-structure-2026.pdf',
    ARRAY['resources'],
    ARRAY['fees', 'tuition', 'transport', 'charges', 'cost', 'how much'],
    ARRAY['fee_query', 'transport_query'],
    'Fee answers come from Supabase hardlock. PDF shared as attachment only.'
),
(
    'Darpan — DWPS School Magazine', 'magazine', 'pdf',
    'https://storage.googleapis.com/saarthi-docs/darpan-magazine.pdf',
    ARRAY['resources'],
    ARRAY['school life', 'events', 'achievements', 'extracurricular', 'activities', 'clubs', 'sports'],
    ARRAY['culture_query', 'activities_query', 'achievements_query'],
    'Image-based CorelDRAW PDF. OCR via Gemini Vision planned for Week 3+. Resources namespace only until then.'
);
```

---

## 9. broadcast_campaigns

One row per dead-lead reactivation campaign. Used for template message blasts to cold/dead leads.

```sql
CREATE TABLE broadcast_campaigns (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL,                      -- 'July 2026 Admissions Open Reminder'
    template_name   text NOT NULL,                      -- Meta-approved template ID
    template_language text DEFAULT 'en',
    target_statuses text[],                             -- Which lead statuses to target, e.g. '{cold,dead}'
    message_preview text,                               -- Human-readable summary of the template
    scheduled_at    timestamptz,                        -- When to send (NULL = send now)
    sent_at         timestamptz,                        -- Populated when dispatch finishes
    total_sent      integer DEFAULT 0,
    total_delivered integer DEFAULT 0,
    total_replied   integer DEFAULT 0,
    created_by      text,                               -- Staff member who triggered it
    created_at      timestamptz DEFAULT now()
);
```

---

## 10. broadcast_sends

Per-lead delivery tracking for each campaign. One row per (campaign × lead).

```sql
CREATE TABLE broadcast_sends (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     uuid REFERENCES broadcast_campaigns(id) ON DELETE CASCADE,
    lead_id         uuid REFERENCES leads(id) ON DELETE CASCADE,

    wa_message_id   text,                               -- Meta message ID returned on send
    status          text DEFAULT 'pending',
        -- 'pending' | 'sent' | 'delivered' | 'read' | 'replied' | 'failed'
    error_message   text,                               -- If status = 'failed'
    sent_at         timestamptz,
    delivered_at    timestamptz,
    read_at         timestamptz,
    replied_at      timestamptz,

    UNIQUE (campaign_id, lead_id)
);

-- Indexes
CREATE INDEX idx_bc_sends_campaign ON broadcast_sends(campaign_id);
CREATE INDEX idx_bc_sends_lead     ON broadcast_sends(lead_id);
CREATE INDEX idx_bc_sends_status   ON broadcast_sends(status);
```

---

## Row-Level Security (RLS)

Enable RLS on all tables. Service role key (used by the Python backend) bypasses RLS. Dashboard uses authenticated JWT.

```sql
-- Enable RLS
ALTER TABLE leads               ENABLE ROW LEVEL SECURITY;
ALTER TABLE visits              ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions            ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_logs   ENABLE ROW LEVEL SECURITY;
ALTER TABLE fee_data            ENABLE ROW LEVEL SECURITY;
ALTER TABLE transport_data      ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents           ENABLE ROW LEVEL SECURITY;
ALTER TABLE broadcast_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE broadcast_sends     ENABLE ROW LEVEL SECURITY;

-- Dashboard staff can read everything; backend service role bypasses RLS
CREATE POLICY "Authenticated staff read all" ON leads
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated staff read all" ON visits
    FOR SELECT TO authenticated USING (true);

-- All writes go through service role (Python backend) — no insert/update policies needed for dashboard
```

---

## Migration Order

Run in this order on a fresh Supabase project:

```
1.  fee_data
2.  transport_data
3.  documents
4.  leads
5.  sessions
6.  visits
7.  conversation_logs
8.  retrieval_logs
9.  broadcast_campaigns
10. broadcast_sends
```

`leads` must exist before `sessions`, `visits`, `conversation_logs`, `retrieval_logs`, and `broadcast_sends`.  
`sessions` must exist before `conversation_logs` and `retrieval_logs`.  
`broadcast_campaigns` must exist before `broadcast_sends`.

---

*DB Schema | Project Saarthi | Pavan Kumar Vuppaladadium × DWPS | July 2026*
