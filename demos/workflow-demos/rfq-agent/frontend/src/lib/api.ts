import type {
  RFQListResponse,
  RFQDetail,
  StatsResponse,
  UploadResponse,
  EmailSummary,
  EmailDetail,
} from "./types";

const BASE = "/api";

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + url, { cache: "no-store", ...init });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  stats: () => req<StatsResponse>("/rfq/stats"),

  list: (params?: { status?: string; page?: number; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.page) q.set("page", String(params.page));
    if (params?.limit) q.set("limit", String(params.limit));
    return req<RFQListResponse>(`/rfq?${q}`);
  },

  detail: (rfqId: string) => req<RFQDetail>(`/rfq/${rfqId}`),

  uploadFile: (file: File, sender: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("sender", sender);
    return req<UploadResponse>("/rfq/upload", { method: "POST", body: form });
  },

  submitText: (rawText: string, sender: string, subject?: string) =>
    req<UploadResponse>("/rfq/text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: rawText, sender, subject }),
    }),

  approve: (rfqId: string) =>
    req<{ rfq_id: string; status: string; email_sent: boolean }>(`/rfq/${rfqId}/approve`, { method: "POST" }),

  reject: (rfqId: string) =>
    req<{ rfq_id: string; status: string }>(`/rfq/${rfqId}/reject`, { method: "POST" }),

  pdfUrl: (rfqId: string) => `${BASE}/rfq/${rfqId}/pdf`,

  getTrace: (rfqId: string) =>
    req<{ steps: Array<{ node: string; label: string; detail: string; status: string }> }>(`/rfq/${rfqId}/trace`),

  getStatus: (rfqId: string) =>
    req<{ status: string }>(`/rfq/${rfqId}/status`),

  listEmails: (limit = 25) => req<{ emails: EmailSummary[]; total: number }>(`/emails?limit=${limit}`),

  getEmail: (emailId: string) => req<EmailDetail>(`/emails/${emailId}`),

  processEmail: (emailId: string) =>
    req<{ rfq_id: string; status: string }>(`/emails/${emailId}/process`, { method: "POST" }),

  getSettings: () => req<Record<string, unknown>>("/settings"),

  updateSettings: (body: Record<string, unknown>) =>
    req<Record<string, unknown>>("/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  listConnectedAccounts: () =>
    req<{ accounts: { email: string; active: boolean; watch_expiry: string | null; connected_at: string }[] }>("/auth/accounts"),

  disconnectAccount: (email: string) =>
    req<{ status: string; email: string }>(`/auth/accounts/${encodeURIComponent(email)}`, { method: "DELETE" }),
};
