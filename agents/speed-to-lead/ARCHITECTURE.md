# Speed-to-Lead — WhatsApp AI Agent Architecture

## System Overview

```mermaid
flowchart TD
    subgraph ENTRY ["Entry Points"]
        WA["WhatsApp User\nMeta Cloud API"]
        ADS["Meta Ads\nClick-to-WhatsApp (CTWA)"]
        STAFF["Staff Dashboard\nManual reply, pause AI\nbroadcast"]
    end

    ADS -->|referral payload\nattached to first message| WA
    WA -->|HMAC-SHA256 signed\nwebhook POST| FE["FastAPI Backend\nPort 8080"]
    STAFF --> FE

    FE -->|background task\nreturns 200 immediately| PIPE["pipeline.py\nOrchestration layer"]

    PIPE --> GRAPH["LangGraph\nsignal_extractor\nsupervisor\nlead_agent"]
    GRAPH --> DB[("Supabase\nPostgreSQL\nLeads, Sessions\nVisits, Logs")]
    GRAPH -->|text or document| WA_REPLY["Meta Cloud API\nWhatsApp reply"]

    style ENTRY fill:#1a2a3a,stroke:#4a8ebf,color:#fff
```

---

## Detailed LangGraph Flow

```mermaid
flowchart TD
    START([Inbound WhatsApp message]) --> PIPE

    subgraph PIPE ["pipeline.py — Orchestration (runs before and after graph)"]
        P1["1. wamid dedup\nSkip if already processed"]
        P2["2. Load lead + session from DB\nBuild LeadState"]
        P3["3. Log inbound message"]
        P4["4. ai_paused guard\nStop if staff took over"]
        P5["5. CTWA attribution\nExtract config + location\nfrom ad headline regex\n3BHK, Whitefield etc"]
        P6["6. Dead lead reactivation\nlong_term_nurture or\nbroadcast_sent → active"]
        P1 --> P2 --> P3 --> P4 --> P5 --> P6
    end

    P6 --> GRAPH

    subgraph GRAPH ["LangGraph Graph"]

        SE["signal_extractor\nClaude structured output\nExtracts from message:\n- lead_name\n- lead_type (interior or real_estate)\n- config (2BHK, 3BHK, 4BHK, Villa)\n- budget_bracket (under_5L, 5-10L etc)\n- scope (full_home, specific_room)\n- visit_date and visit_time\n- cab_pickup_address (RE only)\n- is_knowledge_question flag\n- wants_resource flag\n- education_path flag\nSaves new fields to DB immediately"]

        SE --> SUP

        SUP["supervisor\nMessage type router"]
        SUP -->|audio message| VN["voice_note\nReply: send as text please\npath_taken = voice_note"]
        SUP -->|text or image| LA

        subgraph LA_DETAIL ["lead_agent — Pre-fetch context then single Claude call"]
            CTX["Context retrieval\nis_knowledge_question?"]
            CTX -->|portfolio stage or style keywords| PORT["search_portfolio\nPinecone namespace: portfolio\ntop_k=2, threshold=0.75\nFilter: config, budget, lead_type"]
            CTX -->|no portfolio match or other query| KNOW["search_knowledge\nPinecone namespace: knowledge\ntop_k=5, threshold=0.80\nPricing, FAQs, process docs"]
            KNOW -->|score below 0.80| FALL["fallback\nPause AI\nAlert staff via email\nhandoff_to_staff = True"]
            PORT & KNOW -->|context retrieved| PROMPT["Build system prompt\nlead_agent_system()\nwith retrieved context injected\nstage + captured fields injected"]
            PROMPT --> CLAUDE["Single Claude call\nclaude-sonnet-4-6\nprompt caching ephemeral\nGenerate WhatsApp reply"]
            CLAUDE --> RG["resource_gate\nSearch resources namespace\ntop_k=1, threshold=0.70\nPace and dedup PDF/video\nattachments per session"]
        end

        LA --> CTX
    end

    GRAPH --> POST

    subgraph POST ["pipeline.py — Post-graph (persist + send)"]
        ST["advance_stage\nClaude structured output\nassesses next stage\nforward-only progression\ndiscovery → qualification\n→ portfolio_match\n→ consideration\n→ booking → conversion"]
        SEND["Send WhatsApp reply\ntext: send_text()\ndocument: send_document()\nvideo: inline URL in text\nStaging: redirect to TEST_FORWARD_NUMBER"]
        SYNC["Sync lead fields to DB\nlead_name, config, budget etc"]
        VISIT["Upsert visit if date captured\nlead_status = visit_scheduled"]
        SESS["Save session\nhistory capped at 16 entries\nturn_count incremented\nLog outbound + retrieval"]
        ST --> SEND --> SYNC --> VISIT --> SESS
    end

    POST --> END_NODE([END])
```

---

## Conversation Stages

```mermaid
flowchart LR
    D["discovery\nWho are you, what do you need"]
    Q["qualification\nconfig, budget, scope captured"]
    PM["portfolio_match\nShow relevant past projects"]
    C["consideration\nSharing resources, PDFs, videos"]
    B["booking\nCollect visit date and time"]
    CV["conversion\nVisit confirmed, cab if RE"]

    D --> Q --> PM --> C --> B --> CV

    NOTE["Stage advances forward only\nClaude assess_stage call after every turn\nHard-wire: booking → conversion\nwhen visit_date_captured = True"]
```

---

## Pinecone Knowledge Base

```mermaid
flowchart TD
    subgraph SEED ["Ingestion (one-time scripts)"]
        S1["seed_pinecone_knowledge.py\nPDFs: pricing, process, FAQs\ndoc_type metadata tagged"]
        S2["seed_pinecone_portfolio.py\nProject JSON: config, style\nlocation, budget, image_urls"]
        S3["seed_pinecone_resources.py\nPDF and video metadata\ntitle, url, vertical"]
    end

    subgraph PC ["Pinecone Index\nEmbedding: Google text-embedding-004"]
        NS1["namespace: knowledge\ntop_k=5, threshold=0.80\nPricing, FAQs, process docs\nTechnical questions"]
        NS2["namespace: portfolio\ntop_k=2, threshold=0.75\nPast project metadata\nFiltered by config and budget"]
        NS3["namespace: resources\ntop_k=1, threshold=0.70\nPDF brochures and videos\nPaced by resource_gate"]
    end

    S1 --> NS1
    S2 --> NS2
    S3 --> NS3

    NS1 & NS2 & NS3 -->|pre-fetch before Claude call| LA["lead_agent\nsingle Claude call\nwith context injected"]
```

---

## CTWA (Click-to-WhatsApp) Attribution

```mermaid
flowchart LR
    AD["Meta Ad\ne.g. headline: 3BHK in Whitefield"] -->|user taps| WA["WhatsApp message\nwith referral payload"]
    WA -->|first message only| CTWA["ctwa.py\nExtract config via regex\nExtract location via regex\nStore: ctwa_source_id\nctwa_config = 3BHK\nctwa_location = Whitefield"]
    CTWA -->|pre-fills state| LA["lead_agent\nskips asking config and location\nalready knows from ad"]
```

---

## Staff Dashboard and Controls

```mermaid
flowchart TD
    subgraph DASH ["Staff Routes"]
        D1["GET /dashboard/leads\nAll leads with status and scores"]
        D2["GET /dashboard/visits\nUpcoming visit bookings"]
        D3["GET /dashboard/conversations\nFull message history per lead"]
        D4["GET /dashboard/funnel\nConversion funnel stats"]
    end

    subgraph CON ["Console Actions"]
        C1["POST /console/pause\nSet ai_paused = True\nAI stops auto-replying"]
        C2["POST /console/resume\nSet ai_paused = False\nAI resumes"]
        C3["POST /console/reply\nManual message from staff\nLogged as staff direction"]
        C4["POST /console/broadcast\nBulk message to lead list"]
    end

    FALL["Fallback alert email\nSMTP via Gmail\nWhen Pinecone score below threshold\nAI auto-pauses for that lead"]

    FALL -.->|staff gets email| CON
```

---

## Deployment

```mermaid
flowchart TD
    subgraph INFRA ["Infrastructure"]
        FE["FastAPI\nCloud Run\nPort 8080\nDocker multi-stage build"]
        DB["Supabase\nPostgreSQL\nRow-level security\nStorage for PDFs"]
        PC["Pinecone\nVector store\n3 namespaces per vertical"]
        META["Meta Cloud API\nWhatsApp Business\nHMAC-SHA256 webhook security"]
    end

    subgraph ENV ["Environments"]
        STG["Staging\nTEST_FORWARD_NUMBER set\nAll replies redirect to test number\nno real leads get AI replies"]
        PROD["Production\nFull traffic\nReal lead replies"]
    end

    subgraph SECRETS ["Environment Variables"]
        SEC["ANTHROPIC_API_KEY\nPINECONE_API_KEY\nGOOGLE_API_KEY (embedding)\nDATABASE_URL\nSUPABASE_URL and SERVICE_KEY\nMETA_ACCESS_TOKEN\nMETA_PHONE_NUMBER_ID\nMETA_APP_SECRET\nMETA_WEBHOOK_VERIFY_TOKEN\nSMTP credentials (fallback alerts)\nLANGCHAIN_API_KEY (optional LangSmith)"]
    end

    FE --> DB & PC & META
    SEC -.-> FE

    style INFRA fill:#1a2a3a,stroke:#4a8ebf,color:#fff
    style ENV fill:#2a2a1a,stroke:#f39c12,color:#fff
    style SECRETS fill:#1a3a2a,stroke:#2ecc71,color:#fff
```

**Deployment notes:**

| Config | Value |
|--------|-------|
| **Runtime** | Python 3.11, Poetry, Docker multi-stage build |
| **Server** | Uvicorn on port 8080 |
| **DB migrations** | `alembic upgrade head` runs on container startup |
| **Staging safety** | `TEST_FORWARD_NUMBER` redirects all outbound replies away from real leads |
| **Webhook security** | HMAC-SHA256 signature validation on every Meta POST |
| **Deduplication** | `wamid` check before processing prevents double-replies on Meta retries |
| **Observability** | LangSmith (optional via LANGCHAIN_API_KEY), latency fields in LeadState |
| **Embedding model** | Google text-embedding-004 (matches DWPS Pinecone index) |

---

## Component Summary

| Component | Tech | Role |
|-----------|------|------|
| **Orchestration** | LangGraph StateGraph | signal_extractor → supervisor → lead_agent |
| **LLM** | Anthropic Claude claude-sonnet-4-6 | Reply generation, signal extraction, stage assessment |
| **Prompt caching** | Anthropic cache_control: ephemeral | System prompt cached to cut latency and cost |
| **Vector store** | Pinecone (3 namespaces) | Knowledge, portfolio, resources retrieval |
| **Embeddings** | Google text-embedding-004 | Query and document embedding |
| **Database** | Supabase (PostgreSQL) | Leads, sessions, visits, conversation logs, retrieval logs |
| **WhatsApp** | Meta Cloud API | Inbound webhook + outbound text and document sends |
| **CTWA** | Meta referral payload | Ad config and location auto-extracted on first message |
| **Stage machine** | Claude structured output | Forward-only stage progression per turn |
| **Resource gate** | resource_gate.py | Paces PDF and video attachments, deduplicates per session |
| **Fallback** | SMTP email alert | Auto-pauses AI and alerts staff when confidence is too low |
| **Verticals** | Interior Design and Real Estate | Same graph, lead_type field controls prompts and routing |
