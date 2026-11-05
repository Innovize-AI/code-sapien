# Project Saarthi — Implementation Plan
**Client**: Delhi World Public School (DWPS), Hyderabad  
**Consultant**: Pavan Kumar Vuppaladadium  
**Stack**: Python (FastAPI) + Next.js + Gemini Flash + Pinecone + Supabase + GCP + Meta WhatsApp Cloud API

---

## Part 1: Conversational Flow Design

This is the core of the agent. Every inbound WhatsApp message flows through a single pipeline that determines **who is speaking**, **what they want**, and **what to attach**.

---

### 1.1 High-Level Flow

```
Inbound WhatsApp Message
        │
        ▼
[1] Parse & Route
   ├── Voice message? → "Please resend as text"
   ├── Media/sticker? → Ignore
   └── Text message → continue
        │
        ▼
[2] Session Lookup (Supabase by phone number)
   ├── No session → NEW PARENT → Greeting + Consent Gate
   ├── status = taken_over → Counselor has control → DO NOT AUTO-REPLY
   ├── status = broadcast_sent → Dead lead replied → REACTIVATION FLOW
   └── Active session → continue
        │
        ▼
[3] Intent Classification (via Gemini)
   → Classify into one of 8 intents (see Section 1.2)
        │
        ▼
[4] Dual Pinecone Search (parallel)
   ├── knowledge namespace → RAG context
   └── resources namespace → attach relevant PDF/video
        │
        ▼
[5] Confidence Gate (80%)
   ├── >= 80% → Gemini generates response with resource attached
   └── < 80% → Fallback message + counselor alert email
        │
        ▼
[6] Lead Capture Check (woven into response)
   └── If lead incomplete → append lead capture prompt at end of response
        │
        ▼
[7] Send WhatsApp Reply
```

---

### 1.2 Parent Intent Map

Eight distinct intents Saarthi handles. Every response follows the same structure: **answer → attach resource → weave lead question if not yet captured**.

---

#### Intent 1: General Inquiry (First Contact)

**Trigger**: New parent, no CTWA referral, vague or broad opener  
Examples: "Hi", "Hello", "I want information about admissions", "Tell me about DWPS"

**Agent Action**:
1. Warm greeting personalised to DWPS
2. Brief school intro (1-2 sentences from RAG)
3. Ask what they're most interested in (fees, curriculum, transport, tour)
4. Append lead capture step 1 if not started

**Resource to Attach**:
- School Prospectus PDF (always for first contact)
- OR: Principal Welcome Video (YouTube link) if prospectus already shared

**Sample Response**:
```
Hello! Welcome to Delhi World Public School, Manneguda. 

DWPS offers Cambridge and CBSE programs from Nursery to Grade 12, with
a focus on holistic development. We're currently accepting admissions
for the 2025-26 session.

Here's our school prospectus for your reference:
[📄 DWPS School Prospectus.pdf]

What would you like to know more about — fees, curriculum, transport,
or scheduling a campus tour? 

Also, may I have your name so I can assist you better?
```

---

#### Intent 2: CTWA Arrival (Click-To-WhatsApp Ad)

**Trigger**: Meta referral object present in webhook payload  
Webhook field: `entry[0].changes[0].value.messages[0].referral`

**Agent Action**:
1. Parse `referral.body` (the pre-filled message from the ad)
2. Parse `referral.source_url` (which ad/campaign brought them)
3. Store ad attribution on Supabase lead record (`ctwa_source`, `ctwa_campaign`)
4. Send personalised opener that references the ad they clicked
5. Continue into RAG flow

**Resource to Attach**:
- Match resource to ad content:
  - "Admissions open" ad → Admission Guide PDF
  - "Cambridge curriculum" ad → Curriculum Overview PDF
  - "Transport from Hyderabad" ad → Transport/Facilities PDF

**Sample Response**:
```
Hi! Glad you reached out about DWPS admissions. Looks like you saw
our ad about [Cambridge/CBSE/Admissions] — happy to help!

[attach relevant PDF based on ad source]

What questions do you have? I can tell you about fees, the curriculum,
campus life, or help you book a tour.

Could I start with your name?
```

**Implementation Note**: If `referral` object is absent, treat as Intent 1.

---

#### Intent 3: Admissions Process Query

**Trigger**: Parent asking about how to apply, registration, what documents needed, deadlines  
Examples: "How do I apply?", "What is the admission process?", "What documents are needed for enrollment?"

**Agent Action**:
1. Pull step-by-step admissions process from RAG (knowledge namespace)
2. Keep response structured: steps as numbered list
3. Attach Admission Guide PDF
4. Offer to book campus tour at end

**Resource to Attach**:
- Admission Guide / Process PDF (primary)
- Application Form PDF (if available)

**Sample Response**:
```
Here's how admissions work at DWPS:

1. Fill the enquiry form (or continue here on WhatsApp)
2. Campus tour — visit to meet the Principal and see the school
3. Application form submission + documents
4. Assessment (for Grade 3+): informal interaction, not an exam
5. Admission confirmation + fee payment

📋 Required documents: Birth certificate, previous school TC, report
cards, passport photos, Aadhaar copy.

I've attached our admission guide with all details:
[📄 DWPS Admission Guide.pdf]

Would you like to schedule a campus tour? It usually takes 45 minutes
and is the best way to see the school.
```

---

#### Intent 4: Fee Query

**Trigger**: Parent asking about fees, charges, costs, payment structure  
Examples: "What are the fees for Class 3?", "How much does CBSE cost?", "Are there transport charges?"

**Agent Action**:
1. **Fee Hardlock**: detect fee intent before RAG call
2. Query Supabase fee table directly (class, board, fee components)
3. Return structured breakdown: admission fee, tuition, transport, etc.
4. Bypass Gemini entirely for the numbers — only Gemini for framing the response

**Note**: Fee hardlock is in the build plan. The signed proposal does not explicitly list it as a separate deliverable but it falls under AI Agent (Deliverable 2). Treat it as part of core agent accuracy.

**Resource to Attach**:
- Fee Structure PDF (official document)
- Attach alongside the structured text response

**Sample Response**:
```
Here are the fees for [Class 3 CBSE] at DWPS for 2025-26:

Admission Fee (one-time): ₹15,000
Tuition Fee (per term): ₹22,000 × 3 terms = ₹66,000/year
Transport (from Hayathnagar, if applicable): ₹2,500/month

Annual total (excluding transport): ₹81,000

📄 Full fee structure with all classes and boards:
[📄 DWPS Fee Structure 2025-26.pdf]

Note: Transport fees vary by route. Let me know your area and I can
give you the exact transport fee.

Is there anything else you'd like to know?
```

---

#### Intent 5: Curriculum / Board Query

**Trigger**: Parent asking about CBSE vs Cambridge, subjects, teaching methodology, extracurriculars  
Examples: "Do you offer IB?", "What is Cambridge curriculum?", "Which board is better for my child?", "What subjects are taught in Grade 5?"

**Agent Action**:
1. RAG retrieves curriculum details from knowledge namespace
2. If CBSE vs Cambridge comparison asked → structured comparison table
3. Attach relevant curriculum PDF
4. If query about extracurriculars → pull from facilities/activities knowledge base

**Resource to Attach**:
- Cambridge Curriculum Overview PDF (if Cambridge query)
- CBSE Curriculum Overview PDF (if CBSE query)
- School Prospectus (if general)
- Extracurriculars brochure (if activities asked)

**Sample Response (CBSE vs Cambridge)**:
```
DWPS offers both CBSE and Cambridge (CAIE) programs. Here's a quick
comparison:

| | CBSE | Cambridge |
|---|---|---|
| Exam Board | CBSE, India | Cambridge Assessment, UK |
| Recognition | National | International |
| Assessment Style | Year-end exam | Coursework + exams |
| Best For | Engineering/Medical entrance | Abroad or holistic focus |
| Available at DWPS | Nursery–Grade 12 | Nursery–Grade 10 |

Most families at DWPS choose Cambridge for its international recognition
and project-based learning style.

📘 Here's a detailed curriculum guide:
[📄 DWPS Cambridge Program Overview.pdf]

Would you like to know the fees for a specific grade and board?
```

---

#### Intent 6: Facilities / Campus Query

**Trigger**: Parent asking about campus, transport routes, labs, sports, hostel, canteen  
Examples: "Do you have buses from Kompally?", "Is there a swimming pool?", "What are the sports facilities?"

**Agent Action**:
1. RAG retrieves facilities info from knowledge namespace
2. For transport: return specific route info if route is mentioned
3. Offer campus tour to experience facilities in person

**Resource to Attach**:
- Campus Tour Video (YouTube link) — primary resource for this intent
- Facilities brochure PDF (if available)

**Sample Response**:
```
DWPS has excellent facilities on our Manneguda campus:

🏫 Campus: 3-acre campus with separate blocks for primary and senior
🔬 Labs: Science, Computer, and Language labs
⚽ Sports: Cricket ground, basketball court, indoor badminton
🚌 Transport: Buses run from Hayathnagar, LB Nagar, Shamshabad,
   Mehdipatnam, and surrounding areas

Here's a virtual walkthrough of the campus:
[▶️ DWPS Campus Tour — YouTube]

The best way to see it is a live visit — would you like to schedule a
30-minute campus tour this week?
```

---

#### Intent 7: Tour Booking

**Trigger**: Parent explicitly wanting to visit, book appointment, meet principal  
Examples: "Can I visit the school?", "I want to come and see", "When can I book a tour?"

**Agent Action**:
1. Confirm tour request
2. Ask for preferred date + time slot (weekdays 9am–1pm)
3. Ask for grade of interest (for routing to right counselor)
4. Store tour date in Supabase on lead record
5. Send confirmation message with what to bring

**Note**: Calendar is not integrated (out of scope). Tour date is logged only, admissions team handles actual slot confirmation.

**Resource to Attach**:
- Campus Tour Video (YouTube) — send while they wait for confirmation
- Document checklist (what to bring)

**Sample Response**:
```
Great! We'd love to have you visit DWPS. 

Campus tours are available Monday–Saturday, 9:00 AM to 1:00 PM.
Tours take about 45 minutes — you'll meet the admissions counselor
and see the campus.

What date works for you? And which grade are you planning for?

While you decide, here's a quick campus walkthrough:
[▶️ DWPS Campus Tour — YouTube]

(Please bring your child's birth certificate and last report card
for reference during the visit.)
```

---

#### Intent 8: Reactivated Dead Lead

**Trigger**: Lead status = `broadcast_sent` + incoming message received  
This means a previously cold lead has replied to our broadcast template.

**Agent Action**:
1. Detect status = `broadcast_sent` on session lookup
2. Update lead status → `reactivated` in Supabase
3. Send warm re-engagement opener that references the broadcast
4. Continue directly into RAG agent (no consent re-gate needed — they already replied)
5. Weave in lead capture if any fields still missing

**Resource to Attach**:
- School Prospectus (refresh their memory)
- OR: resource most relevant to their reply

**Sample Response**:
```
Hi [Name if captured previously]! Welcome back to DWPS. 

We're glad you're still considering us for your child's education. 
Admissions are still open for 2025-26.

Here's our latest prospectus:
[📄 DWPS School Prospectus.pdf]

What questions can I answer for you? Or would you like to schedule
a campus visit?
```

---

### 1.3 Lead Capture Flow (State Machine)

Lead capture is woven into every conversation — not a separate interrogation. The agent asks one question at a time, at the natural end of an answer.

**Fields to Capture** (in order):
1. **Name** — "May I know your name?"
2. **Child's Grade** (applying for) — "Which grade are you enquiring for?"
3. **Tour Date** (preferred) — "Would you like to schedule a campus visit? Any preferred date?"

Phone number is already known from WhatsApp — no need to ask.

**State Transitions**:
```
new
  └→ [greeting sent] → active (consent_pending in DPDP flow)
      └→ [parent replies] → active
          └→ [name captured] → lead_partial
              └→ [grade captured] → lead_partial
                  └→ [tour date captured / declined] → lead_captured
```

**Rules**:
- Never ask two lead questions at once
- Always answer the parent's question FIRST, lead question comes at the END
- If parent skips a lead question twice, mark that field `declined`, move on
- Once all fields captured, continue as a pure question-answering agent

**Supabase lead record**:
```sql
leads (
  id            uuid primary key,
  phone         text unique not null,
  name          text,
  grade         text,
  tour_date     date,
  ctwa_source   text,
  ctwa_campaign text,
  lead_status   text, -- new | partial | captured | broadcast_sent | reactivated | unresponsive | dropped_off
  ai_paused     boolean default false,
  created_at    timestamptz,
  last_active   timestamptz
)
```

---

### 1.4 Fallback & Escalation

When confidence < 80% or agent cannot answer:

**Agent says**:
```
That's a great question. Let me connect you with our admissions team
who can give you a precise answer.

Our admissions desk is available Monday–Saturday, 9:00 AM to 5:00 PM.
You can also call us at [DWPS phone number].
```

**System does**:
1. Logs fallback to Supabase (`fallback_triggered = true` on conversation log)
2. Sends email alert to admissions coordinator with: parent phone, the question asked, timestamp
3. Marks conversation in Live Takeover Console as "Needs Attention" (highlighted)
4. Counselor can then Take Over from console and reply manually

---

### 1.5 24-Hour Window Handling

WhatsApp only allows free-form messages within 24 hours of the last parent-initiated message.

**At 23 hours**:
- Cloud Scheduler fires cron every hour
- Query: `sessions where last_parent_message_at < NOW() - 23 hours AND status = active`
- Send pre-approved template: "Hi [Name], still thinking about DWPS? We're here to help. Reply to continue our conversation."
- This re-opens the 24-hour window if parent replies

**After 24 hours (no reply)**:
- Agent CANNOT send free-form messages
- Any triggered message must use an approved template
- Dead lead reactivation broadcasts also use templates (separate flow)

---

### 1.6 Resource Sharing Logic (Pinecone Resources Namespace)

Every response does a **parallel dual search**:

```python
async def get_response(query: str, session: Session) -> AgentResponse:
    # Parallel search
    knowledge_task = search_pinecone(query, namespace="knowledge")
    resource_task = search_pinecone(query, namespace="resources")
    
    knowledge_ctx, resource_hit = await asyncio.gather(
        knowledge_task, resource_task
    )
    
    # Confidence gate
    if knowledge_ctx.score < 0.80:
        return fallback_response()
    
    # Generate response
    response_text = await gemini_generate(query, knowledge_ctx)
    
    # Attach top resource if score > 0.70
    if resource_hit and resource_hit.score > 0.70:
        return AgentResponse(text=response_text, attachment=resource_hit)
    
    return AgentResponse(text=response_text)
```

**Resources namespace schema** (Pinecone metadata per chunk):
```json
{
  "type": "pdf | youtube",
  "title": "DWPS Fee Structure 2025-26",
  "url": "https://storage.googleapis.com/saarthi-docs/fee-structure.pdf",
  "topics": ["fees", "tuition", "transport", "charges"],
  "grade_level": "all | primary | secondary",
  "board": "cbse | cambridge | all"
}
```

**Resource → Intent Mapping** (for indexing):

| Resource File | Topics to Index | Attach For Intent |
|---|---|---|
| DWPS Prospectus.pdf | overview, about, general | 1, 2, 8 |
| Admission Guide.pdf | apply, process, documents, enrollment | 3 |
| Fee Structure 2025-26.pdf | fees, charges, tuition, transport | 4 |
| Cambridge Overview.pdf | cambridge, caie, curriculum, board | 5 |
| CBSE Overview.pdf | cbse, curriculum, ncert, board | 5 |
| Campus Tour (YouTube) | campus, facilities, sports, labs, visit | 6, 7 |
| Principal Welcome (YouTube) | principal, welcome, introduction | 1, 2 |
| Transport Routes.pdf | bus, transport, route, pickup, drop | 6 |

---

## Part 2: Deliverable Implementation Plan

### Deliverable 1 — Infrastructure Setup

**Goal**: All accounts live, keys in Secret Manager, health endpoint responding.

| Task | Tool | Notes |
|---|---|---|
| GCP APIs enabled | `gcloud services enable` | Cloud Run, Scheduler, Storage, Gemini, Secret Manager |
| Supabase schema | SQL migration | leads, sessions, conversation_logs, fee_data tables |
| Pinecone index | Python SDK | `text-embedding-004`, 768 dims, 2 namespaces |
| Cloud Storage bucket | GCP Console | `saarthi-docs`, uniform access, private |
| Secret Manager entries | GCP Console | All API keys stored here, never in `.env` on server |
| Meta Developer App | Meta Dev Portal | App name: `Saarthi DWPS` |
| WABA + phone number | Meta Business Suite | Register DWPS's dedicated number |
| System user token | Meta Business Suite | Never-expiring token via system user |

**Milestone 1 (Day 3)**: Webhook live + health endpoint returns `200 OK` from Cloud Run.

---

### Deliverable 2 — AI Agent (RAG + Gemini Flash)

**Architecture**:
```
Parent Message
     │
     ▼
Intent Classifier (Gemini, zero-shot, returns one of 8 intents)
     │
     ├── Fee intent? → Fee Hardlock (Supabase query, skip Gemini for numbers)
     │
     ▼
Dual Pinecone Search (knowledge + resources, parallel)
     │
     ├── knowledge score < 0.80 → Fallback flow
     │
     ▼
Gemini Flash (system prompt + retrieved context + conversation history last 5 turns)
     │
     ▼
Response Formatter (text + optional resource attachment)
     │
     ▼
Lead Capture Injector (append lead question if fields missing)
     │
     ▼
WhatsApp Message Sender
```

**System Prompt**:
```
You are Saarthi, the AI Admissions Assistant for Delhi World Public School (DWPS), 
Manneguda, Hyderabad. You speak on behalf of DWPS.

Rules:
- Answer only based on the provided context. Never invent facts, fees, or dates.
- If you don't know, say "Let me connect you with our admissions team."
- Keep responses warm, concise, and helpful. No corporate jargon.
- Respond in the same language the parent used (English or Teluglish).
- Do not mention competitor schools or make negative comparisons.
- Always end by inviting the next step (tour, question, or reply).
```

**Gemini Model**: `gemini-1.5-flash` (cost-effective, fast)  
**Embeddings Model**: `text-embedding-004` (768 dims)  
**Confidence Threshold**: 0.80 cosine similarity  

---

### Deliverable 3 — WhatsApp Cloud API Integration

**Endpoints to Build**:

```
GET  /webhook          → Meta verification (hub.challenge response)
POST /webhook          → All inbound events (messages, status updates, referrals)
POST /messages/send    → Internal: send text/template via Meta API
```

**Inbound Webhook Handler**:
```python
@router.post("/webhook")
async def handle_webhook(payload: dict):
    for entry in payload.get("entries", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            
            # Process status updates (sent, delivered, read, failed)
            if "statuses" in value:
                await handle_status_update(value["statuses"])
            
            # Process inbound messages
            if "messages" in value:
                for msg in value["messages"]:
                    await handle_inbound_message(msg, value.get("metadata"))
    
    return {"status": "ok"}
```

**Message Types to Handle**:
- `text` → Main agent flow
- `audio` → Reply: "Please resend your question as text"
- `image/video/document` → Ignore (or acknowledge receipt only)
- `interactive` → Button reply from templates

**Status Updates to Log**:
- `sent` → update `conversation_logs.delivery_status`
- `delivered` → update delivery status
- `read` → update read status
- `failed` → log failure, send email alert

**Webhook Signature Validation**:
```python
import hmac, hashlib

def verify_signature(payload_body: bytes, signature: str, app_secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        app_secret.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

### Deliverable 4 — Multilingual Layer (English / Teluglish)

**Teluglish** = Telugu words written in English script + English mixed  
Example: "Mee school lo fees entha undi?" = "How much are fees at your school?"

**Implementation**:
```python
MULTILINGUAL_SYSTEM_PROMPT = """
Detect the language of the user message:
- "english": pure English
- "teluglish": Telugu words written in Latin script, possibly mixed with English

Return JSON: {"language": "english" | "teluglish", "normalized": "<english translation>"}
"""

async def detect_and_normalize(message: str) -> tuple[str, str]:
    result = await gemini_classify(MULTILINGUAL_SYSTEM_PROMPT, message)
    return result["language"], result["normalized"]

async def translate_to_original(response: str, language: str) -> str:
    if language == "english":
        return response
    # Translate back to Teluglish style
    return await gemini_translate(response, target="teluglish")
```

**Flow**:
1. Detect language + normalize to English
2. Run RAG + Gemini in English
3. Translate response back to detected language
4. Send translated response

**Test Cases** (for Day 17):
- "CBSE ki fees entha?" → "Fees for CBSE entha undi" style response
- "Admission ela cheyali?" → Response in Teluglish
- "Transport undi Hayathnagar nundi?" → Transport info in Teluglish

---

### Deliverable 5 — Lead Capture Flow

**State Machine**:
```python
LEAD_FIELDS = ["name", "grade", "tour_date"]

async def inject_lead_question(response: str, lead: Lead) -> str:
    missing = [f for f in LEAD_FIELDS if not getattr(lead, f)]
    if not missing:
        return response  # Lead fully captured
    
    next_field = missing[0]
    question = {
        "name": "May I know your name so I can assist you better?",
        "grade": "Which grade are you enquiring for?",
        "tour_date": "Would you like to schedule a campus visit? What date suits you?"
    }[next_field]
    
    return f"{response}\n\n{question}"

async def try_capture_field(message: str, lead: Lead, session: Session):
    if not lead.name and session.awaiting_field == "name":
        lead.name = extract_name(message)
    elif not lead.grade and session.awaiting_field == "grade":
        lead.grade = extract_grade(message)
    elif not lead.tour_date and session.awaiting_field == "tour_date":
        lead.tour_date = extract_date(message)
    await supabase.update_lead(lead)
```

---

### Deliverable 6 — CTWA Referral Handler

**Webhook Referral Object** (from Meta):
```json
{
  "referral": {
    "source_url": "https://fb.me/ads/...",
    "source_type": "ad",
    "source_id": "<ad_id>",
    "headline": "DWPS Admissions Open 2025-26",
    "body": "Apply now for CBSE & Cambridge",
    "ctwa_clid": "<click_id>"
  }
}
```

**Handler**:
```python
async def handle_ctwa_referral(msg: dict, lead: Lead):
    referral = msg.get("referral")
    if not referral:
        return
    
    # Store attribution
    lead.ctwa_source = referral.get("source_id")
    lead.ctwa_headline = referral.get("headline")
    lead.ctwa_clid = referral.get("ctwa_clid")
    await supabase.update_lead(lead)
    
    # Personalize greeting based on ad content
    headline = referral.get("headline", "")
    opening = generate_ctwa_greeting(headline)
    await send_whatsapp_message(lead.phone, opening)
```

**CTWA Greeting Template**:
```
We saw you clicked our ad about [headline]. 
You've reached DWPS Admissions — I'm Saarthi, your AI guide.

[attach resource matched to ad topic]

What would you like to know?
```

---

### Deliverable 7 — Dead Lead Reactivation (1 Campaign)

**Trigger**: Manual. DWPS decides when to run the campaign (not automated on a schedule).

**Flow**:
```
[Pavan triggers reactivation script]
        │
        ▼
Filter stale leads from Supabase:
  WHERE lead_status IN ('partial', 'dropped_off')
  AND last_active < NOW() - INTERVAL '30 days'
        │
        ▼
For each lead (with 200ms delay between sends):
  1. Send Meta broadcast template to lead.phone
  2. Update lead_status → 'broadcast_sent'
  3. Log timestamp in Supabase
        │
        ▼
[Lead replies] → Webhook fires
  → Detect lead_status = 'broadcast_sent'
  → Update lead_status → 'reactivated'
  → RAG agent takes over (Intent 8 flow)
        │
        ▼
[No reply in 48 hours]
  → Cloud Scheduler marks lead_status → 'unresponsive'
```

**Broadcast Template** (pre-approved by Meta, ~3 business days):
```
Template name: saarthi_reactivation_v1
Language: en_US

Body:
Hi {{1}}, it's been a while since you enquired about admissions at
Delhi World Public School. We have a few seats remaining for 2025-26.

Would you like to know more or schedule a visit? Just reply to this
message and our AI assistant will help you right away.
```

**Meta API Call** (per lead):
```python
async def send_broadcast(phone: str, name: str):
    await meta_api.post(f"/v18.0/{PHONE_NUMBER_ID}/messages", json={
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": "saarthi_reactivation_v1",
            "language": {"code": "en_US"},
            "components": [{
                "type": "body",
                "parameters": [{"type": "text", "text": name or "there"}]
            }]
        }
    })
```

---

### Deliverable 8 — Contextual Resource Sharing

Already detailed in Section 1.6. Key implementation notes:

**Resources to Index Before Launch**:
- [ ] School Prospectus PDF → namespace `resources`, topics: `overview, about, school`
- [ ] Admission Guide PDF → topics: `admissions, process, apply, documents`
- [ ] Fee Structure PDF → topics: `fees, tuition, charges, transport, cost`
- [ ] Cambridge Overview PDF → topics: `cambridge, caie, curriculum, board`
- [ ] CBSE Overview PDF → topics: `cbse, curriculum, ncert`
- [ ] Campus Tour YouTube → type: `youtube`, topics: `campus, facilities, sports, labs, visit`
- [ ] Principal Welcome YouTube → topics: `welcome, principal, introduction`
- [ ] Transport Routes PDF → topics: `bus, transport, route, pickup`

**WhatsApp Message with Attachment** (document):
```python
async def send_with_document(phone: str, text: str, doc_url: str, filename: str):
    # Send text first
    await send_text_message(phone, text)
    # Then send document
    await meta_api.post(f"/v18.0/{PHONE_NUMBER_ID}/messages", json={
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "document",
        "document": {
            "link": doc_url,
            "filename": filename
        }
    })

async def send_with_youtube(phone: str, text: str, video_url: str, video_title: str):
    # YouTube links sent as plain text (WhatsApp renders preview)
    combined = f"{text}\n\n▶️ {video_title}\n{video_url}"
    await send_text_message(phone, combined)
```

---

### Deliverable 9 — Analytics Dashboard (Next.js)

**FastAPI Endpoint**:
```
GET /dashboard/stats?from=2025-01-01&to=2025-12-31
```

**Response**:
```json
{
  "total_leads": 142,
  "leads_captured": 89,
  "tours_booked": 34,
  "ctwa_leads": 28,
  "reactivated_leads": 17,
  "total_messages": 1843,
  "ai_replies": 1701,
  "counselor_replies": 142,
  "fallbacks_triggered": 38,
  "avg_response_time_ms": 1240,
  "active_conversations": 12
}
```

**Dashboard Cards** (Next.js):
- Total Leads | Leads Captured | Conversion Rate
- CTWA Leads | Reactivated Leads
- Total Messages | AI vs Counselor split
- Fallbacks Triggered (with list on click)
- Active Conversations (link to console)

---

### Deliverable 10 — Live Takeover Console (Next.js)

**FastAPI Endpoints**:
```
GET  /conversations                    → list active conversations (phone, name, last msg, status)
GET  /conversations/{phone}            → full thread (all messages, timestamps, source)
POST /conversations/{phone}/takeover   → set ai_paused = true
POST /conversations/{phone}/reply      → send manual WhatsApp message
POST /conversations/{phone}/resume     → set ai_paused = false
```

**Console UI Flows**:
1. List view: conversations sorted by last activity, "Needs Attention" badge on fallbacks
2. Thread view: full chat history (parent messages + agent replies)
3. Take Over button → input box appears, counselor types + sends
4. Resume AI button → AI takes back over on next parent message
5. Status indicator: green (AI active) | red (taken over) | yellow (needs attention)

**AI Pause Logic** (webhook handler):
```python
session = await supabase.get_session(phone)
if session.ai_paused:
    return  # Do not auto-reply, counselor is in control
```

---

### Deliverable 11 — Staff SOP Document

Delivered as PDF at go-live. Sections:
1. How to use the Live Takeover Console (screenshots)
2. When to take over (fallback alerts, sensitive topics)
3. How to resume AI after counselor reply
4. How to upload new documents (for knowledge base)
5. What happens during dead lead reactivation (who triggers, what to watch)
6. Escalation path if agent goes down (Pavan contact + Cloud Run health check URL)
7. How to add new WhatsApp phone numbers to the system

---

## Part 3: Technical Stack Decisions

| Layer | Choice | Reason |
|---|---|---|
| Backend | FastAPI (Python) | Async, lightweight, fast for WebSocket/webhooks |
| Frontend | Next.js | Dashboard + Console in one app, easy Cloud Run deploy |
| AI | Gemini 1.5 Flash | Free tier sufficient for Phase 1, low latency |
| Embeddings | text-embedding-004 | 768 dims, free in Gemini API, no OpenAI dependency |
| Vector DB | Pinecone | Managed, two namespaces (knowledge + resources) |
| Operational DB | Supabase (PostgreSQL) | Leads, sessions, logs, fee data |
| Infra | GCP Cloud Run | Serverless, scales to zero, no idle cost |
| Scheduling | Cloud Scheduler | 23-hour follow-up, 48-hour no-reply, daily health check |
| File Storage | Cloud Storage | Documents uploaded by DWPS, private, signed URLs |
| Secrets | Secret Manager | All API keys, never in code or env files |
| Monitoring | Cloud Logging + email alerts | Fallback triggers, failed messages |

---

## Part 4: Document Knowledge Base Setup (Day 6)

Documents to collect from DWPS before Day 6:
- [ ] School Prospectus (any format → convert to PDF)
- [ ] Fee Structure 2025-26 (PDF or Excel)
- [ ] Admission Process Guide (PDF or Word)
- [ ] FAQ document from Admissions Coordinator (any format)
- [ ] Cambridge Programme overview (if available)
- [ ] CBSE curriculum overview (if available)
- [ ] Transport routes and fees by area (if available)

YouTube links to collect:
- [ ] Campus Tour video URL
- [ ] Principal Welcome video URL (if exists)

**Ingestion Pipeline**:
```
PDF → PyMuPDF → text extraction → chunking (500 tokens, 50 overlap)
     → Gemini embeddings (text-embedding-004) → Pinecone (knowledge namespace)

YouTube URL → store metadata only → Pinecone (resources namespace, no embedding needed)
```

---

## Part 5: Testing Plan (Week 4)

### English Test Suite (50 queries)
- 10 admissions process questions
- 10 fee questions (various grades + boards)
- 10 curriculum/board questions
- 10 facilities/transport questions
- 5 tour booking requests
- 5 edge cases (off-topic, rude, competitor mention)

### Teluglish Test Suite (15 queries)
- 5 fee questions in Teluglish
- 5 admissions questions in Teluglish
- 5 mixed English-Telugu

### CTWA Simulation
- Craft test webhook payload with referral object
- Verify attribution stored, personalized response sent

### Dead Lead Reactivation Test
- Create 3 test leads with status `dropped_off`
- Run reactivation script
- Verify template sent, status updated
- Reply from test number → verify RAG takes over

### Live Takeover Console Test
- Trigger fallback → verify "Needs Attention" badge appears
- Counselor clicks Take Over → types reply → verify sent on WhatsApp
- Counselor clicks Resume AI → parent sends message → verify AI responds

---

*Project Saarthi Implementation Plan | Pavan Kumar Vuppaladadium × DWPS | July 2026*
