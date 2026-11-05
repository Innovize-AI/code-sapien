export type Vertical = "interior" | "real_estate" | "solar";

export interface Plan {
  id: string;
  name: string;
  label: string;
  monthly_chat_cap: number;
  price_monthly: number;
  overage_per_chat: number;
}

export interface Firm {
  id: string;
  name: string;
  firm_display_name: string;
  vertical: Vertical;
  visit_cta: string | null;
  fallback_alert_email: string | null;
  wa_phone_number_id: string | null;
  plan_id: string | null;
  plan?: Plan | null;
  monthly_chats_used: number;
  // sensitive fields omitted from list response; present on single-firm fetch
  meta_access_token?: string | null;
  meta_webhook_verify_token?: string | null;
  meta_app_secret?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Lead {
  id: string;
  firm_id: string;
  phone: string;
  wa_name: string | null;
  lead_name: string | null;
  lead_type: string | null;        // denorm from firm.vertical
  lead_status: string;
  is_qualified: boolean;
  ai_paused: boolean;
  fallback_count: number;
  ctwa_source_id: string | null;
  ctwa_location: string | null;
  broker_id?: string | null;
  project_id?: string | null;
  number_id?: string | null;
  owner_id?: string | null;
  owner_name?: string | null;
  owner_kind?: "partner" | "team" | null;
  number_label?: string | null;
  created_at: string;
  last_active: string;
  // joined from sessions
  stage?: string | null;
  turn_count?: number | null;
  last_message_at?: string | null;
  // joined from vertical profile (present on single-lead fetch)
  config?: string | null;
  budget_bracket?: string | null;
  scope?: string | null;
  design_style?: string | null;
}

export interface ConversationLog {
  id: string;
  session_id: string | null;
  lead_id: string | null;
  direction: "inbound" | "outbound";
  sender_type: "lead" | "ai" | "admin";
  message_text: string | null;
  path_taken: string | null;
  pinecone_score: number | null;
  turn_number: number | null;
  created_at: string;
}

export interface Visit {
  id: string;
  lead_id: string;
  visit_date: string;
  visit_time_slot: string | null;
  cab_pickup_address: string | null;
  hesitation_code: string | null;
  attended: boolean | null;
  outcome: string | null;
  status: "scheduled" | "rescheduled" | "cancelled" | "completed" | "no_show" | null;
  cancellation_reason: string | null;
  // joined from leads
  lead_name?: string | null;
  lead_type?: string | null;
  config?: string | null;
  phone?: string | null;
}

export interface KnowledgeChunk {
  doc_type: string;
  text: string;
  vertical?: string;
}

export interface PortfolioMatch {
  id: string;
  title: string;
  score: number;
  config?: string;
  style?: string;
  budget_bracket?: string;
}

export interface RetrievalLog {
  id: string;
  turn_number: number | null;
  query_original: string;
  knowledge_top_score: number | null;
  knowledge_chunks: KnowledgeChunk[] | null;
  portfolio_matches: PortfolioMatch[] | null;
  confidence_gate_passed: boolean | null;
  resource_candidate_id: string | null;
  resource_attached: boolean | null;
  resource_gate_fail: string | null;
  tools_called: string[] | null;
  path_taken: string;
  pinecone_latency_ms: number | null;
  claude_latency_ms: number | null;
  total_latency_ms: number | null;
  created_at: string;
}

export interface DashboardStats {
  total_messages: number;
  ai_replies: number;
  leads_captured: number;
  visits_booked: number;
  fallbacks_triggered: number;
  active_conversations: number;
  ai_paused_count: number;
  funnel: Record<string, number>;
}

// ── Channel partner registry ─────────────────────────────────────────────────

export interface Project {
  id: string;
  firm_id: string;
  name: string;
  location: string | null;
  rera_number: string | null;
  possession_date: string | null;
  starting_price: string | null;
  payment_plan: string | null;
  bank_tieups: string | null;
  validity_days: number;
  is_active: boolean;
}

export interface BrokerRow {
  id: string;
  name: string;
  company: string | null;
  phone: string;
  rera_agent_no: string | null;
  code: string;
  status: "active" | "suspended";
  kind: "partner" | "team";
  email: string | null;
  registered: number;
  conflicts: number;
  superseded: number;
  leads: number;
  visits: number;
  last_registration_at: string | null;
  created_at: string;
  link: string | null;
}

export type RegistrationStatus = "registered" | "duplicate" | "superseded" | "expired" | "rejected";

export interface Registration {
  id: string;
  reference_id: string;
  client_name: string | null;
  client_phone: string;
  client_phone_full: string;
  method: "broker_whatsapp" | "coded_link" | "form";
  status: RegistrationStatus;
  registered_at: string;
  valid_until: string | null;
  broker_id: string | null;
  broker_name: string | null;
  broker_company: string | null;
  submitted_by_phone: string | null;
  project_id: string | null;
  project_name: string | null;
  conflict_kind: "broker_vs_broker" | "broker_vs_existing_lead" | null;
  conflict_state: "open" | "resolved" | null;
  resolution_note: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  existing_lead_at: string | null;
  first: { reference_id: string; registered_at: string; broker_name: string | null } | null;
}

export interface SourceBucket {
  source: "ad" | "broker" | "organic";
  leads: number;
  visits: number;
  median_first_reply_seconds: number | null;
  visit_rate: number | null;
}

export interface SourceSplit {
  days: number;
  sources: SourceBucket[];
  open_conflicts: number;
}

export interface LeadSummary {
  empty: boolean;
  headline: string;
  intent: "hot" | "warm" | "cold";
  what_they_want: string[];
  concerns: string[];
  where_it_stands: string;
  next_action: string;
  message_count: number;
  updated_at: string;
  cached: boolean;
}

export interface NumberRow {
  id: string;
  firm_id: string;
  person_id: string | null;
  person_name: string | null;
  person_kind: "partner" | "team" | null;
  label: string;
  display_phone: string | null;
  wa_phone_number_id: string;
  has_own_token: boolean;
  is_active: boolean;
  created_at: string;
}
