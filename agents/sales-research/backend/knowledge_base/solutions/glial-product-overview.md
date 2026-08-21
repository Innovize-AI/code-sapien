# Glial Revenue Intelligence System — Product Overview

## What Is Glial?
Glial is a private, agentic intelligence layer that transforms how sales teams identify, research, and engage high-intent prospects. It is an autonomous "Sales Brain" that tells your team **WHO** to contact, **WHEN**, and **WHY** — without hiring more analysts.

*Just as glial cells provide the essential infrastructure that allows neurons to fire and communicate, Glial provides the intelligence infrastructure that allows your sales team to act with precision and speed.*

**This is NOT lead generation. This is NOT static research.**

---

## The Problem: The "Context Gap"

| Problem | Impact |
|---------|--------|
| Bad Timing | Reaching out too early or too late because buying signals are invisible |
| No Context | Messages sound generic because reps don't know the prospect's current focus |
| Poor Follow-Through | Leads cool off because there's no system for next-best-action |
| Tool Fatigue | Reps jump between CRMs, research apps, and spreadsheets |

---

## The 4 Core Components

### 1. Command Center (Identify & Intercept)
A dedicated frontend to steer the research engine. Identifies prospects from:
- **Competitor Intercepts**: Buyers engaging with competitor posts on LinkedIn
- **Keyword Intelligence**: Public posts discussing specific pain points or budget triggers
- **Apollo Integration**: High-fidelity lead sourcing mapped to custom ICP filters
- **Autopilot Configuration**: Set once, runs 24/7 — keywords + competitor monitoring

### 2. Primary Evaluation (Instant Sifting)
Before a rep touches a lead, Glial automatically analyzes LinkedIn profiles and tags:
- ✅ **Potential Fit** — matches ICP
- 👤 **Decision Maker** — has purchasing power
- 🚫 **Competitor** — auto-filtered from outreach
- 🌐 **Website Positioning** — scrapes prospect site to distinguish partners vs. direct competitors

### 3. Deep Analysis (Decision Briefings)
Executive-grade reports delivered to Slack or CRM. Includes:
- **Why Now**: The specific trigger making outreach relevant today
- **CSO Strategic Briefing**: Synthesized intelligence from 6 specialized agents
- **Lead Score (0–100)**: Transparent scoring on 4 dimensions
- **Heat Rating (0–100)**: Urgency/timing score based on behavioral signals
- **ICP Viability Flags**: Green/red indicators against your qualification criteria
- **Buyer Journey Stage**: Awareness, Consideration, or Decision
- **Pain Points**: AI-driven analysis of the prospect's likely blockers
- **Strategic Solutions**: How Glial or AI Services maps to their specific pain
- **Multi-Variant Outreach**:
  - *The Handshake*: LinkedIn hook under 250 characters, peer-validation angle
  - *The Command*: PAS-framework email draft for executive-level engagement
- **Tactical Next Steps**: Prioritized 1-2-3 action plan for the rep

### 4. Continuous Signal Loop (Always-Monitoring)
Once an account is monitored, Glial never stops:
- Tracks new signals (emails, downloads, competitor comments, meetings)
- Re-runs analysis when context shifts
- Sends Slack updates with new "Next Steps" the moment the prospect's context changes
- Real-Time SSE feed streams live opportunities as they happen

---

## Agent Architecture

| Agent | Role | Data Sources |
|-------|------|-------------|
| **Discovery Agent** | Intercepts LinkedIn signals and keyword mentions | LinkedIn API, Web Scraping |
| **Batch Classifier** | Scores intent + sentiment for every intercepted profile | Gemini, Custom Prompts |
| **Deep Research Agent** | Builds full company + personal dossier | Tavily, Apollo, News APIs |
| **CSO Scoring Agent** | Generates Lead Score, Heat Rating, ICP Viability | Internal LLM Chain + RAG |
| **Outreach Agent** | Drafts PAS emails + LinkedIn hooks | GPT-4o/Gemini, Knowledge Base |
| **HubSpot Sync Agent** | Maps leads to CRM, triggers Lazarus Effect revivals | HubSpot API |

---

## Lead Scoring Breakdown

| Component | Weight | What It Measures |
|-----------|--------|-----------------|
| **Firmographic Fit** | 30 pts | Revenue, headcount, industry alignment to ICP |
| **Persona Match** | 30 pts | Job title, seniority, decision-making authority |
| **Behavioral Signals** | 20 pts | Posts, comments, engagement with relevant content |
| **Strategic Intent** | 20 pts | Explicit pain mentions, competitor interactions, hiring signals |

Score interpretation: < 40 = skip | 40–70 = send carefully | 70+ = priority

---

## Integrations

| Integration | Purpose | Sync Frequency |
|-------------|---------|---------------|
| **HubSpot** | CRM sync, deal revival (Lazarus Effect), contact enrichment | Every 12 hours |
| **Slack** | Real-time lead alerts with "Identify & Research" action buttons | Instant (webhook) |
| **LinkedIn** | Signal discovery via keyword + competitor monitoring | Continuous (Autopilot) |
| **Tavily** | Web research for company context and news | Per research run |
| **Apollo** | Contact enrichment and company data | Per research run |
| **OpenAI/Gemini** | LLM backbone for all AI reasoning layers | Per research run |
| **Calendly/Cal.com** | Trigger research on new meeting bookings | On event |
| **Typeform/ConvertKit** | Trigger research on form submission | On event |

---

## Why Glial Beats Static Tools

| Competitor | Their Approach | Glial Advantage |
|------------|---------------|----------------|
| Clay.com | Manual toolbox requiring expert operation | Fully-built research factory, autonomous execution |
| Apollo + ChatGPT | Manual workflows, tool fatigue, shallow analysis | Single interface, deep analysis, continuous monitoring |
| ZoomInfo / 6sense | Static dashboards, you rent data, high markup | You own infrastructure, decisions not dashboards, zero markup |
| Traditional SaaS | Per-seat licensing, vendor data lock-in | PaaS model — your keys, your data, up to 90% cost reduction |

---

## Privacy & Infrastructure Model (PaaS)
- Runs on **client infrastructure** using their own API keys
- **100% data privacy** — no data leaves their environment
- **Zero markup** on API costs (OpenAI, Apollo, Tavily)
- **Safe-mode monitoring**: External APIs only — zero risk of LinkedIn account bans

---

## Pricing

| Offering | Price |
|----------|-------|
| Initial Deployment (one-time) | $3,500 – $5,000 |
| Innovation & Growth Retainer | $1,500 – $2,000 / quarter |

**Deployment Includes**: Full infrastructure build (2–3 weeks), playbook ingestion, 1 CRM integration, 1 meeting tool integration, Slack Command App, signal mapping (5 competitors + 10 keywords).

**Retainer Includes**: Prompt optimization based on reply rates, signal expansion (new competitors/keywords), feature roadmap updates, priority support.

---

## Live Platform Stats (March 2026)

| Metric | Value |
|--------|-------|
| Total Leads Found | 87 |
| Average Lead Score | 42.1 / 100 |
| Average Heat Rating | 65 / 100 |
| Hours Saved (Research) | 43.5 hrs |
| Cost Per Lead Reduction | Up to 90% vs. traditional SaaS |
