# Production Readiness & Technical Requirements
**Project**: DWPS AI & Automation Initiative  
**Objective**: Hardening the Birthday, Circular, and Admissions agents for production deployment, scale, and compliance.

---

## 1. Security & Cryptographic Controls
*   **Database Access Controls**:
    *   **Supabase Row Level Security (RLS)**: Enforce RLS on all tables. Frontend dashboard access must be protected via JWT authentication (Supabase Auth). Anonymous keys must be limited to read-only scopes.
    *   **Service Role Key Protection**: Ensure the Supabase `service_role` key is strictly kept in the backend server and never leaked to the client.
*   **Encrypted Configurations**:
    *   School credential parameters (MyClassboard administrator logins, Meta WhatsApp API Permanent Tokens) must be encrypted before database storage using **AES-256-GCM** (utilizing an encryption key stored in the server environment variables).
*   **API Protection**:
    *   Strict CORS policies (restricting backend APIs to the dashboard URL).
    *   Rate-limiting middleware (e.g., `express-rate-limit`) on public API routes and WhatsApp webhook endpoints.

---

## 2. Meta WhatsApp Cloud API Production Constraints
*   **Meta Business Manager Verification**:
    *   The school must complete Meta Business Verification to lift the initial messaging ceiling (moving from the 250 messages/day limit to 1,000, 10,000, or unlimited messages/day).
*   **Webhook Signature Validation**:
    *   The webhook receiver (`/webhooks/whatsapp`) must validate the `X-Hub-Signature-256` header using the Meta app's App Secret to ensure requests originate from Meta, preventing payload spoofing.
*   **Conversation Window Handling**:
    *   All customer-initiated threads expire in 24 hours. The Admissions bot must respect this window. If it tries to send a message outside this window, it must switch dynamically from standard text to a pre-approved template message (`Template Re-engagement`).
*   **Rate Limits and Throttling**:
    *   Meta WhatsApp API supports up to 80 messages per second (MPS). The backend must implement a queue system (e.g., BullMQ with Redis) to throttle outgoing blasts to prevent Meta rate limit rejections (HTTP 429).

---

## 3. Reliability, Queueing & Idempotent Schedulers
*   **Message Queues (Job Schedulers)**:
    *   Do not rely on in-memory timers (like `setInterval` or standard node-cron) in production. If the Node.js server restarts, scheduled sends could be missed or double-sent.
    *   **Recommendation**: Use a persistent queue manager like **BullMQ** (powered by Redis) or **Supabase pg_cron / Edge Functions** to guarantee that birthday and circular broadcasts execute exactly once (idempotent design).
*   **Delivery Status Reconciliation**:
    *   WhatsApp messages are asynchronous. Our system must process webhook events for `sent`, `delivered`, and `read`.
    *   Failed statuses (e.g. invalid phone number, template mismatch) must trigger database state updates, update dashboard statistics, and trigger email alerts for administrators.

---

## 4. LLM & RAG Engine Production Governance
*   **Guardrails and Hallucination Protection**:
    *   **System Prompt Hardening**: Instruct Gemini to reply only using retrieved context documents.
    *   **confidence Thresholds**: Reject matches with a cosine similarity below 0.70. Trigger fallback prompts (e.g. *"I am routing this request to the admissions desk"*).
    *   **Data Lookup Lock**: Do not allow the LLM to write or guess numbers, fee charts, or registration deadlines. These values must be stored in structured columns in Supabase and merged into the response template via logic.
*   **Token & Cost Limits**:
    *   Enforce a maximum input token length on user questions to prevent Denial of Service (DoS) attacks designed to drain API credits.
    *   Keep logs of input/output tokens used per message for auditing and display these metrics in the admin console.

---

## 5. Scalable Headless Browser Automation (Playwright/Puppeteer)
*   **Server Sandbox Environment**:
    *   Headless browsers require specific Linux packages. Ensure the production server has all Chromium dependencies installed (using `npx playwright install-deps`).
*   **Memory Leak Mitigation**:
    *   Playwright instances must be isolated and closed properly.
    *   **Best Practice**: Launch the browser instance, perform the MyClassboard scrape/upload action, close the browser context immediately, and implement an automatic process-kill safeguard if a browser session hangs for more than 120 seconds.
*   **Selector Fragility Fallback**:
    *   MyClassboard updates its website structure occasionally. The crawler script must check for target selector presence. If a selector is missing/changed, it must abort the sync immediately, flag the failure in the Supabase `config` table, and dispatch an email alert to the developer instead of executing corrupt form submissions.

---

## 6. Regulatory & Privacy Compliance (DPDP Act 2023)
*   **Explicit Consent Logging**:
    *   Under India's Digital Personal Data Protection Act, user consent must be explicitly collected.
    *   **Implementation**: Before the Admissions Agent starts responding, send an introductory greeting: *"Hi! To help you with admissions, we will record this conversation. Reply 'YES' to proceed."* Log this consent status with a timestamp in the database.
*   **Opt-out/Opt-in Handling**:
    *   If a parent replies "STOP" or "UNSUBSCRIBE" on WhatsApp, the backend must instantly flag their phone number in the `reminders` table as `opted_out` and block all future scheduler messages.
*   **PII Sanitization**:
    *   Personal Identifiable Information (like student names and contact numbers) must be stored in encrypted database columns where possible.

---

## 7. Observability, Metrics & Health
*   **Logging Standards**:
    *   Implement structured logging using `winston` or `pino` printing JSON formats. 
*   **Alerting**:
    *   Integrate crash and error monitoring tools (e.g. Sentry) to notify developers of unhandled backend rejections or database disconnects.
*   **Health Check Endpoint**:
    *   Expose a public GET `/health` endpoint that checks DB connectivity, Redis connection, scheduler health, and config readiness, allowing automated uptime checks.
