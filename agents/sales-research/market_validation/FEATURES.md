# Sales Research Project Features & Strategy

## 1. Core Features (The "Glial" Engine)

**Goal:** Find high-quality potential customers from multiple data sources.

### Lead Discovery & Acquisition
*   **Multi-Source Search**:
    *   **Tavily (X-Ray Search)**: Uses advanced Google Dorks to find LinkedIn profiles matching specific **Industry**, **Job Title**, and **Location** criteria without needing a paid LinkedIn API.
    *   **Apollo.io Integration**: Direct integration with Apollo's structured people database for more granular filtering (requires API key).
    *   **LinkedIn Keyword Monitoring**: Monitors specific keywords in LinkedIn posts to identify leads discussing relevant topics (e.g., "Hiring SDRs", "Cold email problems").
*   **Competitor Intercept ("The Cobalt Strategy")**:
    *   **Monitor Competitors**: Analyzes LinkedIn posts from defined competitors.
    *   **Lead Extraction**: Identifies users who engage (comment/like) with competitor content.
    *   **AI Classification**: Automatically classifies these users into:
        *   **Is Fit**: Matches ICP.
        *   **Decision Maker**: Has purchasing power.
        *   **Competitor**: Is an employee of a competitor (to exclude).
        *   **Intent/Sentiment**: Analyzes the sentiment of their comment (e.g., dissatisfied with competitor).

### Deep Research & Analysis
**Goal:** deeply understand a prospect before outreach.

*   **Automated Profile Analysis**:
    *   Takes a LinkedIn URL or Website.
    *   Scrapes and analyzes the profile to generate a **Research Report**.
*   **Scoring & Qualification**:
    *   **Lead Score**: auto-calculated score (0-100) based on fit.
    *   **High Potential Flag**: Automatically flags leads with score > 70.
*   **Draft Generation**:
    *   **Outreach drafts**: Generates personalized cold outreach messages based on the research.
    *   **Intent Emails**: Drafts emails tailored to specific intents identified (e.g., "Saw you hiring").

### Knowledge Base & RAG
**Goal:** Ground the AI in specific business context and strategy.

*   **Vector Database (Pinecone)**: Stores proprietary documents to customize AI responses.
*   **Namespaces**:
    *   **Playbooks**: Strategic sales frameworks.
    *   **Solutions**: Technical product details.
    *   **Case Studies**: Social proof and ROI data.
*   **Strategic Pivot Configuration**: Allows configuring a "Hero Product" that the agents should prioritize selling, linking it to specific target roles and documents.

### Operational Dashboard
**Goal:** Central view of sales intelligence operations.

*   **Metrics**: Displays Total Leads Found, Average Lead Score, High Potential Leads count, and Estimated Time Saved.
*   **Activity Feed**: Real-time log of background activities (e.g., "Discovered 5 new leads from Competitor X").
*   **History**: Searchable history of all generated research reports.

### Integrations & Infrastructure
**Goal:** Connect with other tools and automate workflows.

*   **Slack**: Notifications for high-potential leads or critical events.
*   **ConvertKit (Kit)**: Integration to fetch forms, likely for syncing leads to email nurture sequences.
*   **Webhooks**: API endpoints to trigger actions from external systems.
*   **Background Jobs**: Async processing for long-running tasks like bulk classification and research.

---

## 2. Strategic Context (Innovize AI)

This project is part of a **dual-engine business strategy** designed to validate and scale "Innovize AI".

### Engine A: Glial Revenue Intelligence (The "Wedge")
*   **Role:** Productized sales intelligence infrastructure.
*   **Value Prop:** Infrastructure-as-a-Service (IaaS). You own the engine, pay raw API costs.
*   **Sales Function:** Trust builder and "Trojan Horse" to get inside client operations.

### Engine B: AI Transformation Services (The "Premium")
*   **Role:** High-value custom AI consulting ($20k-$50k+) for SMEs and Agencies.
*   **Offerings:** Document Intelligence, Workflow Automation, Compliance AI.
*   **Sales Function:** Profit maximizer sold via cross-sell to happy Glial users.

### The Cross-Sell Playbook
1.  **Deploy Glial (Weeks 1-2):** Deliver quick wins.
2.  **Listen (Weeks 3-4):** Identify manual "grunt work" during weekly check-ins.
3.  **Casual Mention (Week 5):** "By the way, we also automate [X]..."
4.  **Free Assessment (Week 6):** Deliver a 1-page tailored proposal for high-ticket service.

### Go-To-Market (GTM)
*   **ICP:** B2B SaaS Founders & VP Sales (Seed - Series B).
*   **Channels:**
    *   **Dogfooding:** Using Glial to find leads for Glial.
    *   **Partner Network:** Agencies/consultants referring deals for commission.
    *   **Content:** Playbook-style LinkedIn content (Problem -> Solution -> Automate).
