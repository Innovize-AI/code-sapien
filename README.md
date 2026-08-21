# Code Sapien — InnovizeAI Operating System (AIOS)

The central monorepo for all InnovizeAI code, agents, products, client projects, and business intelligence.

---

## Structure

```
code-sapien/
│
├── agents/                  Autonomous AI systems (each deployed independently)
│   ├── sales-research/      Lead intelligence platform (Glial)
│   ├── inbox-manager/       Email triage and management agent
│   ├── content-generation/  Multi-agent SEO content pipeline
│   ├── lead-generator/      Lead generation scripts
│   ├── speed-to-lead/       Admissions WhatsApp AI (Project Saarthi)
│   ├── google-drive-slack/  Google Drive + Slack integration bot
│   ├── invoice-extractor/   OCR invoice extraction
│   ├── upwork-proposals/    Upwork proposal automation
│   └── whatsapp-reminders/  WhatsApp notification system
│
├── products/                InnovizeAI-owned full-stack products
│   ├── creator-studio/      Content production hub (video gen + LinkedIn gen)
│   │   └── video-generator/ AI video generation pipeline
│   ├── svayam-crm/          Internal CRM
│   └── mission-control/     Ops dashboard
│
├── demos/                   Client-facing prototypes and POCs
│   ├── cmdb/                CMDB / ServiceNow integration demo
│   ├── mock-ui/             UI shells for demos
│   ├── searcheasy/          AI SEO landing page
│   ├── workflow-demos/      Invoice + RFQ workflow walkthroughs
│   └── quick-commerce/      Blinkit portal automation demo
│
├── research/                Experimental and reference code
│   ├── crosslingual-coreference/
│   └── references/          External demos, third-party examples, archived experiments
│
├── ui/                      Frontend surfaces
│   ├── marketing-site/      InnovizeAI public website
│   ├── shared-components/   Shared React components
│   └── explainer-video/     Explainer video frontend
│
├── clients/                 Per-client workspaces
│   ├── _template/           Copy this for every new client
│   ├── dwps/                DWPS — Saarthi admissions + voice agent
│   ├── rave/                Rave — Privacy-safe inbox manager
│   ├── project-inspired/    Project Inspired — Reporting tools
│   ├── cheryl/              Cheryl — Automation project
│   └── partners/            Partner projects (Greyson, Cyber-Uplink, Jonpaul)
│
├── core/                    Shared internal Python package (sapien-core)
│   ├── llm/                 Claude, OpenAI, Gemini clients
│   ├── db/                  Supabase, Postgres helpers
│   ├── messaging/           Slack, WhatsApp, email senders
│   └── auth/                Shared auth patterns
│
├── integrations/            Third-party connectors
│   ├── hubspot/
│   ├── apollo/
│   ├── linkedin/
│   ├── gmail/
│   └── slack/
│
├── prompts/                 Version-controlled prompt registry
├── evals/                   Agent evaluation and benchmarks
├── templates/               Boilerplates for new agents, products, clients
│
├── ops/                     Infrastructure, CI/CD, tooling
│   ├── docker/              Docker configs
│   ├── tools/               Standalone utility scripts
│   └── workflows/           Deployment SOPs
│
└── workspace/               Business layer — files on disk, NOT git tracked
    ├── knowledge/           Case studies, playbooks, GTM docs, industry research
    ├── marketing/           Decks, offers, content, cold email, SOPs
    ├── accounts/            Finance, hiring, legal
    ├── pipeline/            Prospects, proposals, active clients, closed deals
    └── brand/               Logos, colors, typography, guidelines
```

---

## Key Rules

- **Each project deploys independently** — no cross-project imports
- **`core/` and `integrations/`** provide shared interfaces, never credentials
- **Credentials** live in each project's `.env` (gitignored)
- **Client code** is in `clients/<name>/code/` — client docs and knowledge are gitignored
- **`workspace/`** is gitignored — business docs live on disk, not in version control
- **Client projects** with their own git remotes manage their own history independently

---

## Adding a New Client

```bash
cp -r clients/_template clients/<client-name>
cd clients/<client-name>
# add their code, docs, credentials
```

## Adding a New Agent

```bash
mkdir agents/<agent-name>
# copy pyproject.toml template from templates/new-agent/
# add .env.example with required keys
# add Dockerfile with build context at repo root
```
