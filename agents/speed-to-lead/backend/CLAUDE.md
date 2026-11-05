# Speed-to-Lead — RE/ID WhatsApp AI Agent (Backend)

WhatsApp AI agent for Real Estate and Interior Design firms.
Converts inquiries into qualified visit bookings via conversational AI.

Built with FastAPI + LangGraph + Anthropic Claude + Pinecone + Supabase.

## Project Structure

```
backend/
├── main.py                  # FastAPI app entry point + lifespan
├── config.py                # pydantic-settings (reads .env)
├── CLAUDE.md
│
├── workflow/                # LangGraph + pipeline logic
│   ├── state.py             # LeadState TypedDict + default_state()
│   ├── graph.py             # LangGraph: signal_extractor → supervisor → lead_agent
│   ├── pipeline.py          # Entry point: wamid dedup → graph → reply → persist
│   ├── supervisor.py        # Routes by message_type (audio → voice_note, else → lead_agent)
│   ├── lead_capture.py      # Stub — capture logic is in lead_agent_system prompt
│   └── stage.py             # Stage advancement: discovery→qualification→...→conversion
│
├── services/
│   ├── claude.py            # Anthropic: generate_reply, extract_signals, assess_stage, embed_query
│   ├── pinecone_svc.py      # 2 namespaces: knowledge (0.80), portfolio (0.75); resource catalogue from DB
│   ├── resource_gate.py     # Pacing + dedup gate for PDF/video attachment
│   ├── whatsapp.py          # Meta Cloud API: send_text, send_document
│   └── supabase_svc.py      # Supabase Storage only (PDF uploads)
│
├── agents/
│   ├── lead_agent.py        # Main agent: pre-fetch context → inject → single Claude call
│   ├── signal_extractor.py  # Extract: name, config, budget, lead_type, visit_date, education_path
│   ├── ctwa.py              # CTWA attribution + headline parsing (config/location)
│   └── tools.py             # _db_ctx ContextVar + threshold constants
│
├── prompts/
│   └── lead_agent_prompts.py  # lead_agent_system() + FALLBACK_MESSAGE + STAGE_ASSESSMENT_SYSTEM
│
├── db/
│   ├── database.py          # SQLAlchemy async engine + SessionLocal
│   ├── models.py            # ORM: Lead, Session, Visit, ConversationLog, RetrievalLog, FollowupSchedule
│   ├── crud.py              # All async DB operations
│   ├── schemas.py           # Pydantic response schemas for API routes
│   └── config.py            # DATABASE_URL + DB_SCHEMA derivation
│
├── routes/
│   ├── webhook.py           # Meta webhook (GET verify + POST receive + HMAC validation)
│   ├── dashboard.py         # Staff read: leads, visits, conversations, funnel stats
│   └── console.py           # Staff actions: pause AI, manual reply, broadcast
│
├── utils/
│   └── date_parser.py       # parse_visit_date: "this Saturday" / "15th" → datetime.date
│
└── scripts/
    ├── migrations/
    │   └── 001_initial_schema.sql   # Run once in Supabase SQL editor
    ├── seed_pinecone_knowledge.py   # Chunk + embed PDFs → knowledge namespace
    ├── seed_pinecone_portfolio.py   # Embed portfolio JSON → portfolio namespace
```

## Channel partner registry (real estate)

Brokers register clients from their personal WhatsApp numbers and get a time-stamped receipt. First valid
registration for a client and project wins. A later claim is stored as a duplicate and sent to a person.

| Piece | Where |
|---|---|
| Tables `projects`, `brokers`, `lead_registrations`, `leads.broker_id/project_id` | `db/models.py`, migration `alembic/versions/004_broker_registry.py` (additive, idempotent) |
| Parsing, first-claim rule, receipts, coded-link attribution, leaderboard, source split | `services/broker_registry.py` (pure helpers tested in `tests/test_broker_registry.py`) |
| Broker channel hook (enrolled numbers) and coded-link hook (`BRK-XXXX` first words) | `workflow/pipeline.py` steps 1b and 2b, mirrored in `routes/simulate.py` |
| API: `/brokers`, `/projects`, `/registrations`, `/registrations/{id}/resolve`, `/dashboard/source-split` | `routes/brokers.py` |
| Dev simulator `POST /dev/broker-message` (not served in production) | `routes/brokers.py` |
| Negotiation and unit-availability questions always go to a person | `agents/escalation.py`, used in `agents/lead_agent.py` |
| Price, RERA, possession, payment plan, loans answered from the project record | `project_facts_text` in `services/broker_registry.py` |
| Demo data (project, 4 brokers, conflicts, leads by source) | `scripts/seed_broker_demo.py --firm "Prestige Homes" [--reset]` |

A registration never makes the agent message the client. Consent comes first.

## People, their numbers, and sign-ins

A firm can register several WhatsApp numbers (`firm_numbers`, migration 006). Each is attached to one
person: a channel partner or an internal team member (`brokers.kind` = `partner` | `team`). The firm's own
main number stays on `firms.wa_phone_number_id`.

| Piece | Where |
|---|---|
| Find the firm and the person from the number a message arrived on; pick the send credentials | `services/numbers.py`, used in `workflow/pipeline.py` step 0 |
| A lead that first arrives on a person's number is owned by that person (`leads.owner_id`, `number_id`) and credited as source | `crud.get_or_create_lead(number=...)` |
| Replies, manual replies and follow-ups leave from the number the buyer used | pipeline, `routes/console.py`, `crud.get_pending_followups_with_phones` |
| Register numbers, create a person's sign-in | `routes/people.py` (`/numbers`, `/people/{id}/login`) |
| Who is calling: asks Supabase who the token belongs to; role, firm and person come from user metadata | `services/auth.py`, `routes/guard.py` |
| Roles: `admin` and `counselor` see the whole firm. `agent` sees only leads where `owner_id` is their person | `routes/dashboard.py`, `routes/console.py` |

Agent limits are enforced on the server, not in the browser. They only hold if requests must carry a sign-in,
so production requires it by default (`REQUIRE_AUTH=1` forces it elsewhere, `0` turns it off). Local runs with no
token still work as before. Registration by a broker's WhatsApp message and coded links apply to the main
number only. Re-check everything with `python scripts/verify_numbers_and_scoping.py` (it removes what it creates).

## AI conversation summary

`GET /console/lead/{id}/summary[?refresh=true]` returns a handover summary (headline, hot/warm/cold, what the
buyer wants, concerns, where it stands, suggested next step). Built in `services/lead_summary.py` with Gemini,
cached in `lead_summaries` (migration 005), regenerated only when the message count changes. "What they want"
comes only from the buyer's own messages, never from prices the assistant quoted.

## Verticals

| Field       | Interior Design                      | Real Estate               |
|-------------|--------------------------------------|---------------------------|
| lead_type   | `interior`                           | `real_estate`             |
| visit_cta   | Experience Center visit              | Site visit (cab arranged) |
| config      | 2BHK / 3BHK / 4BHK / Villa          | same                      |
| scope       | full_home / specific_room            | n/a                       |
| extra field | —                                    | cab_pickup_address        |

## Conversation Stages

```
discovery → qualification → portfolio_match → consideration → booking → conversion
```

## Pinecone Namespaces

| Namespace   | Content                        | top_k | Threshold |
|-------------|--------------------------------|-------|-----------|
| knowledge   | Pricing, process, FAQs, docs   | 5     | 0.80      |
| portfolio   | Project metadata + image refs  | 2     | 0.75      |

## Dev Setup

```bash
# 1. Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 2. Install dependencies
cd backend
poetry install

# 3. Copy and fill env vars
cp .env.example .env

# 4. Run schema migration (Supabase SQL editor or psql)
# Run scripts/migrations/001_initial_schema.sql

# 5. Seed Pinecone
poetry run python scripts/seed_pinecone_knowledge.py --docs-dir ../docs/knowledge
poetry run python scripts/seed_pinecone_portfolio.py --projects-file ../docs/portfolio.json

# 6. Start dev server
poetry run uvicorn main:app --reload --port 8001
```

## Key Commands

| Command | Description |
|---|---|
| `poetry install` | Install all dependencies |
| `poetry run uvicorn main:app --reload` | Start dev server |
| `poetry run python scripts/seed_pinecone_knowledge.py` | Ingest knowledge docs |
| `poetry run python scripts/seed_pinecone_portfolio.py` | Ingest portfolio projects |

## Architecture Decisions

- **No DPDP gate** — RE/ID doesn't require India DPDPA consent (not a school)
- **Pre-fetch pattern** — context retrieved before LLM call (no tool-calling loops)
- **wamid deduplication** — `message_exists()` check before processing prevents duplicate replies on Meta webhook retries
- **Model: Gemini 2.5 Flash** — `services/claude.py` (the filename is historical) calls `gemini-2.5-flash` through `google-genai` for replies, signal extraction and stage assessment. Earlier notes here said Claude Sonnet 4.6; that is not what the code runs.
- **Education path** — separate prompt path for uninformed leads (bare shell, first-time)
- **CTWA auto-extract** — config + location parsed from ad headline regex on first message
- **5 qualification fields only** — config, budget_bracket, scope, lead_name, lead_type (+ design_style inferred from portfolio reaction)
- **2 Pinecone namespaces** — knowledge, portfolio (resource catalogue served from DB; LLM decides via [RESOURCE: id] tag)
- **Google text-embedding-004** — for Pinecone index compatibility

## Environment Variables

```
ANTHROPIC_API_KEY=
PINECONE_API_KEY=
DATABASE_URL=postgresql+asyncpg://...
DB_SCHEMA=public
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
META_ACCESS_TOKEN=
META_PHONE_NUMBER_ID=
META_WEBHOOK_VERIFY_TOKEN=
META_APP_SECRET=          # required in production: webhook signatures are not checked without it
META_WEBHOOK_URL=         # this service's public URL ending in /webhook, as registered in Meta
META_GRAPH_BASE_URL=https://graph.facebook.com
META_GRAPH_API_VERSION=v20.0
GOOGLE_API_KEY=           # for text-embedding-004
ENVIRONMENT=staging       # staging | production
TEST_FORWARD_NUMBER=      # staging redirect
FALLBACK_ALERT_EMAIL=
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
LANGCHAIN_API_KEY=        # optional, enables LangSmith
```
