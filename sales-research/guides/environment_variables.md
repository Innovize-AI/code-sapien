# Environment Variables Reference

This document lists all environment variables required to run the `sales-research` system.

## Backend Variables (`backend/.env`)

### Core Database

- **`DATABASE_URL`**: (Required) PostgreSQL connection string.
  - Example: `postgresql+asyncpg://user:pass@localhost:5432/sales_db`
- **`ENVIRONMENT`**: (Optional) `dev` or `prod`. Defaults to `dev`.

### AI Models (LLMs)

- **`OPENAI_API_KEY`**: (Required) For general reasoning and embeddings.
- **`GOOGLE_API_KEY`** or **`GEMINI_API_KEY`**: (Required) For Gemini models used in research agents.

### Research Integrations

- **`RAPID_API_KEY`**: (Required) For LinkedIn Data (via RapidAPI).
- **`LINKEDIN_RAPID_BASE_URL`**: (Required) Base URL for the LinkedIn API.
- **`TAVILY_API_KEY`**: (Required) For general web search and company research.
- **`APOLLO_API_KEY`**: (Required) For contact enrichment (Apollo.io).

### Vector Database & Knowledge Base

- **`PINECONE_API_KEY`**: (Required) For storing and retrieving RAG embeddings.

### Authentication & User Management (Supabase)

- **`SUPABASE_URL`**: (Required) Your Supabase project URL.
- **`SUPABASE_SERVICE_ROLE_KEY`**: (Required) For admin tasks (seeding users, RLS bypass).
- **`SUPABASE_ANON_KEY`**: (Required) For client-side auth validation.

### Optional / Observability

- **`LANGCHAIN_API_KEY`**: (Optional) For LangSmith tracing.
- **`LANGCHAIN_PROJECT`**: (Optional) Project name in LangSmith.
- **`NOTION_TOKEN`**: (Optional) For Notion integration POCs.

---

## Frontend Variables (`frontend/.env.local`)

- **`NEXT_PUBLIC_API_URL`**: (Optional) The URL of your backend API.
  - Default: `http://localhost:8000`
  - Production Example: `https://api.yourdomain.com`
