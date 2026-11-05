import type {
  NumberRow, BrokerRow, ConversationLog, DashboardStats, Firm, Lead, Plan, Project, Registration,
  LeadSummary, RetrievalLog, SourceSplit, Visit,
} from "@/types";

import { createClient } from "@/lib/supabase";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

// The backend decides what each signed-in person may see, so every call carries their token.
// With no session (local development with auth bypassed) the call goes out without one.
async function authHeaders(): Promise<Record<string, string>> {
  try {
    const { data } = await createClient().auth.getSession();
    const token = data.session?.access_token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

async function fail(res: Response, path: string): Promise<never> {
  let detail = "";
  try { detail = (await res.json())?.detail ?? ""; } catch { /* body was not JSON */ }
  throw new Error(`${res.status} ${detail || res.statusText}: ${path}`);
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store", headers: await authHeaders() });
  if (!res.ok) return fail(res, path);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(body),
  });
  if (!res.ok) return fail(res, path);
  return res.json() as Promise<T>;
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(body),
  });
  if (!res.ok) return fail(res, path);
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) q.set(k, String(v));
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

// ── Plans ──────────────────────────────────────────────────────────────────────

export const fetchPlans = () => get<Plan[]>("/plans");

// ── Firms ──────────────────────────────────────────────────────────────────────

export const fetchFirms = () => get<Firm[]>("/firms");

export const fetchFirm = (id: string) => get<Firm>(`/firms/${id}`);

export const createFirm = (body: Omit<Firm, "id" | "created_at" | "is_active">) =>
  post<Firm>("/firms", body);

export const updateFirm = (id: string, body: Partial<Firm>) =>
  patch<Firm>(`/firms/${id}`, body);

// ── Dashboard ──────────────────────────────────────────────────────────────────

export const fetchStats = (firmId?: string) =>
  get<DashboardStats>(`/dashboard/stats${qs({ firm_id: firmId })}`);

export const fetchVisits = (firmId?: string) =>
  get<Visit[]>(`/dashboard/visits${qs({ firm_id: firmId })}`);

export const fetchConversations = (params?: {
  firm_id?: string;
  page?: number;
  search?: string;
  stage?: string;
  ai_paused?: boolean;
  owner_id?: string;
  number_id?: string;
}) => {
  const { firm_id, page, search, stage, ai_paused, owner_id, number_id } = params ?? {};
  return get<Lead[]>(`/dashboard/conversations${qs({ firm_id, page, search, stage, ai_paused, owner_id, number_id })}`);
};

export const fetchLead = (id: string) =>
  get<Lead>(`/dashboard/lead/${id}`);

// ── Knowledge & Resources ───────────────────────────────────────────────────────

export interface Resource {
  id: string;
  firm_id: string | null;
  title: string;
  description: string | null;
  resource_type: "pdf" | "youtube" | "video";
  url: string | null;
  updated_at: string | null;
}

export const fetchResources = (firmId: string) =>
  get<Resource[]>(`/firms/${firmId}/resources`);

export const addResource = (firmId: string, body: Omit<Resource, "firm_id" | "updated_at">) =>
  post<Resource>(`/firms/${firmId}/resources`, body);

export const deleteResource = (firmId: string, resourceId: string) =>
  authHeaders().then(h => fetch(`${BASE}/firms/${firmId}/resources/${resourceId}`, { method: "DELETE", headers: h }));

export async function uploadKnowledgePDF(firmId: string, file: File, docType: string): Promise<{ chunks: number }> {
  const form = new FormData();
  form.append("file", file);
  form.append("doc_type", docType);
  const res = await fetch(`${BASE}/firms/${firmId}/knowledge/upload`, { method: "POST", body: form, headers: await authHeaders() });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export async function uploadResourcePDF(firmId: string, file: File, title: string, description: string): Promise<Resource> {
  const form = new FormData();
  form.append("file", file);
  form.append("title", title);
  form.append("description", description);
  const res = await fetch(`${BASE}/firms/${firmId}/resources/upload`, { method: "POST", body: form, headers: await authHeaders() });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ── Console ────────────────────────────────────────────────────────────────────

export const fetchHistory = (leadId: string) =>
  get<ConversationLog[]>(`/console/lead/${leadId}/history`);

export const fetchRetrievalLogs = (leadId: string) =>
  get<RetrievalLog[]>(`/console/lead/${leadId}/retrieval`);

export const pauseAI = (leadId: string, paused: boolean) =>
  post<{ status: string }>("/console/pause", { lead_id: leadId, paused });

export const sendReply = (params: {
  lead_id: string;
  session_id: string;
  phone: string;
  message_text: string;
  admin_name?: string;
}) => post<{ status: string }>("/console/reply", params);

export const markNoShow = (leadId: string) =>
  post<{ status: string }>("/console/visit/no-show", { lead_id: leadId });

export const markAttended = (leadId: string, outcome?: string) =>
  post<{ status: string }>("/console/visit/attended", { lead_id: leadId, outcome: outcome ?? null });

// ── Channel partners and registry ───────────────────────────────────────────────

export const fetchBrokers = (firmId: string) =>
  get<BrokerRow[]>(`/brokers${qs({ firm_id: firmId })}`);

export const enrolBroker = (body: {
  firm_id: string; name: string; phone: string; company?: string; rera_agent_no?: string;
  kind?: "partner" | "team";
}) => post<{ id: string; code: string }>("/brokers", body);

export const setBrokerStatus = (id: string, status: "active" | "suspended") =>
  patch<{ id: string; status: string }>(`/brokers/${id}`, { status });

export const fetchProjects = (firmId: string) =>
  get<Project[]>(`/projects${qs({ firm_id: firmId })}`);

export const fetchRegistrations = (
  firmId: string,
  opts?: { status?: string; conflicts_only?: boolean; broker_id?: string },
) => get<Registration[]>(`/registrations${qs({ firm_id: firmId, ...opts })}`);

export const resolveRegistration = (
  id: string,
  body: { action: "keep_first" | "award_new"; note?: string; resolved_by?: string },
) => post<{ id: string; status: string }>(`/registrations/${id}/resolve`, body);

export const fetchSourceSplit = (firmId: string, days = 30) =>
  get<SourceSplit>(`/dashboard/source-split${qs({ firm_id: firmId, days })}`);

// Dev simulators (the backend does not serve these in production)
export const simulateBrokerMessage = (body: { firm_id: string; from_phone: string; text: string }) =>
  post<{ handled: boolean; reply?: string; kind?: string; reference_id?: string | null; conflict?: boolean }>(
    "/dev/broker-message", body);

export const simulateBuyerChat = (body: { firm_id: string; phone: string; message: string; wa_name?: string }) =>
  post<{ response: string | null; path_taken: string | null; stage: string }>("/dev/chat", body);

export const fetchLeadSummary = (leadId: string, refresh = false) =>
  get<LeadSummary>(`/console/lead/${leadId}/summary${qs({ refresh: refresh || undefined })}`);

// ── People's WhatsApp numbers and sign-ins ──────────────────────────────────────

export const fetchNumbers = (firmId: string, personId?: string) =>
  get<NumberRow[]>(`/numbers${qs({ firm_id: firmId, person_id: personId })}`);

export const registerNumber = (body: {
  firm_id: string; label: string; wa_phone_number_id: string; display_phone?: string;
  person_id?: string; meta_access_token?: string;
}) => post<NumberRow>("/numbers", body);

export const changeNumber = (id: string, body: {
  label?: string; display_phone?: string; is_active?: boolean; person_id?: string; detach?: boolean;
}) => patch<NumberRow>(`/numbers/${id}`, body);

export const createPersonLogin = (personId: string, body: { email: string; password: string }) =>
  post<{ id: string; email: string }>(`/people/${personId}/login`, body);
