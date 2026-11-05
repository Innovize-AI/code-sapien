"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { fetchFirm, fetchPlans, fetchResources, updateFirm, addResource, deleteResource, uploadKnowledgePDF, uploadResourcePDF } from "@/lib/api";
import type { Resource } from "@/lib/api";
import type { Firm, Plan } from "@/types";
import {
  ArrowLeft, Loader2, CheckCircle2, Building2, Home, Sun,
  AlertTriangle, Zap, Upload, Trash2, ExternalLink, Plus, FileText, Youtube,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ── Helpers ────────────────────────────────────────────────────────────────────

const VERTICAL_LABEL: Record<string, string> = {
  interior:    "Interior Design",
  real_estate: "Real Estate",
  solar:       "Solar",
};
const VERTICAL_ICON: Record<string, React.ElementType> = {
  interior:    Home,
  real_estate: Building2,
  solar:       Sun,
};
const VERTICAL_COLOR: Record<string, string> = {
  interior:    "var(--chart-4)",
  real_estate: "var(--chart-2)",
  solar:       "var(--chart-3)",
};

const inputCls =
  "w-full px-3.5 py-2.5 rounded-lg border border-line text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent transition";

function Field({
  label, hint, children,
}: {
  label: string; hint?: string; children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-ink/80 mb-1">{label}</label>
      {hint && <p className="text-xs text-muted mb-1.5">{hint}</p>}
      {children}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-card rounded-2xl border border-line shadow-sm p-6 space-y-5">
      <h2 className="text-sm font-semibold text-ink uppercase tracking-wide">{title}</h2>
      {children}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

interface FormState {
  name: string;
  firm_display_name: string;
  visit_cta: string;
  fallback_alert_email: string;
  wa_phone_number_id: string;
  meta_access_token: string;
  meta_webhook_verify_token: string;
  meta_app_secret: string;
  is_active: boolean;
  plan_id: string | null;
}

function firmToForm(firm: Firm): FormState {
  return {
    name:                      firm.name ?? "",
    firm_display_name:         firm.firm_display_name ?? "",
    visit_cta:                 firm.visit_cta ?? "",
    fallback_alert_email:      firm.fallback_alert_email ?? "",
    wa_phone_number_id:        firm.wa_phone_number_id ?? "",
    meta_access_token:         firm.meta_access_token ?? "",
    meta_webhook_verify_token: firm.meta_webhook_verify_token ?? "",
    meta_app_secret:           firm.meta_app_secret ?? "",
    is_active:                 firm.is_active,
    plan_id:                   firm.plan_id ?? null,
  };
}

export default function EditFirmPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();

  const { data: firm, isLoading } = useSWR<Firm>(
    `firm-${id}`,
    () => fetchFirm(id),
  );
  const { data: plans } = useSWR<Plan[]>("plans", fetchPlans);
  const { data: resources, mutate: mutateResources } = useSWR<Resource[]>(
    `resources-${id}`,
    () => fetchResources(id),
  );

  const [tab, setTab] = useState<"settings" | "knowledge" | "resources">("settings");
  const [form, setForm] = useState<FormState | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (firm && !form) setForm(firmToForm(firm));
  }, [firm, form]);

  function set(key: keyof FormState, value: string | boolean) {
    setForm(f => f ? { ...f, [key]: value } : f);
    setSaved(false);
  }

  async function save() {
    if (!form || saving) return;
    setError("");
    setSaving(true);
    try {
      await updateFirm(id, {
        name:                      form.name,
        firm_display_name:         form.firm_display_name,
        visit_cta:                 form.visit_cta || null,
        fallback_alert_email:      form.fallback_alert_email || null,
        wa_phone_number_id:        form.wa_phone_number_id || null,
        meta_access_token:         form.meta_access_token || null,
        meta_webhook_verify_token: form.meta_webhook_verify_token || null,
        meta_app_secret:           form.meta_app_secret || null,
        is_active:                 form.is_active,
        plan_id:                   form.plan_id || null,
      });
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setSaving(false);
    }
  }

  // ── Loading ──────────────────────────────────────────────────────────────────

  if (isLoading || !form) {
    return (
      <div className="p-4 sm:p-6 lg:p-8 max-w-2xl mx-auto space-y-4">
        {[0, 1, 2].map(i => (
          <div key={i} className="h-40 bg-bg animate-pulse rounded-2xl" />
        ))}
      </div>
    );
  }

  const VertIcon  = VERTICAL_ICON[firm?.vertical ?? ""] ?? Building2;
  const vertColor = VERTICAL_COLOR[firm?.vertical ?? ""] ?? "var(--muted)";

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-2xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-start gap-4">
        <button
          onClick={() => router.push("/admin/firms")}
          className="mt-1 p-1.5 rounded-lg text-muted hover:text-ink/80 hover:bg-bg transition"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ backgroundColor: `color-mix(in srgb, ${vertColor} 12%, transparent)`, border: `1.5px solid color-mix(in srgb, ${vertColor} 28%, transparent)` }}
          >
            <VertIcon className="w-5 h-5" style={{ color: vertColor }} />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-ink">{firm?.firm_display_name}</h1>
            <p className="text-xs text-muted">{VERTICAL_LABEL[firm?.vertical ?? ""] ?? firm?.vertical}</p>
          </div>
        </div>
      </div>

      {/* Tab nav */}
      <div className="flex gap-1 bg-bg p-1 rounded-xl">
        {(["settings", "knowledge", "resources"] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "flex-1 py-2 rounded-lg text-sm font-medium capitalize transition-all",
              tab === t ? "bg-card text-ink shadow-sm" : "text-muted hover:text-ink/80",
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {/* ── Settings tab ─────────────────────────────────────────────────── */}
      {tab === "settings" && <>

      {/* Status toggle */}
      <div className="bg-card rounded-2xl border border-line shadow-sm px-5 py-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-ink">Firm status</p>
          <p className="text-xs text-muted mt-0.5">Inactive firms do not receive or process WhatsApp messages</p>
        </div>
        <button
          onClick={() => set("is_active", !form.is_active)}
          className={cn(
            "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
            form.is_active ? "bg-success" : "bg-line",
          )}
        >
          <span
            className={cn(
              "inline-block h-4 w-4 rounded-full bg-card shadow transition-transform",
              form.is_active ? "translate-x-6" : "translate-x-1",
            )}
          />
        </button>
      </div>

      {/* Plan + usage */}
      <Section title="Plan">
        {/* Usage bar */}
        {firm?.plan && (
          <div className="mb-2">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-muted">Chats used this month</span>
              <span className="font-semibold text-ink/80 tabular-nums">
                {firm.monthly_chats_used} / {firm.plan.monthly_chat_cap}
              </span>
            </div>
            <div className="h-2 bg-bg rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  firm.monthly_chats_used / firm.plan.monthly_chat_cap >= 0.9
                    ? "bg-error"
                    : firm.monthly_chats_used / firm.plan.monthly_chat_cap >= 0.75
                      ? "bg-warning"
                      : "bg-success",
                )}
                style={{ width: `${Math.min(100, Math.round((firm.monthly_chats_used / firm.plan.monthly_chat_cap) * 100))}%` }}
              />
            </div>
            <p className="text-[10px] text-muted mt-1">
              Overage rate: Rs. {firm.plan.overage_per_chat}/chat above cap
            </p>
          </div>
        )}

        {/* Plan selector */}
        <div className="grid gap-2">
          {!plans ? (
            <div className="h-16 bg-bg animate-pulse rounded-xl" />
          ) : plans.map(plan => {
            const selected = form.plan_id === plan.id;
            return (
              <button
                key={plan.id}
                onClick={() => set("plan_id", plan.id)}
                className={cn(
                  "w-full text-left rounded-xl border-2 px-4 py-3 transition-all flex items-center justify-between",
                  selected
                    ? "border-accent bg-accent/5"
                    : "border-line hover:border-ink/30 hover:bg-bg",
                )}
              >
                <div className="flex items-center gap-3">
                  <Zap className={cn("w-4 h-4", selected ? "text-accent" : "text-muted")} />
                  <div>
                    <p className="text-sm font-semibold text-ink">{plan.label}</p>
                    <p className="text-xs text-muted">{plan.monthly_chat_cap} chats/month</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-semibold text-ink">Rs. {plan.price_monthly.toLocaleString("en-IN")}</span>
                  {selected && <CheckCircle2 className="w-4 h-4 text-accent" />}
                </div>
              </button>
            );
          })}
        </div>
      </Section>

      {/* Firm details */}
      <Section title="Firm details">
        <Field label="Internal name" hint="Slug identifier used in API calls, avoid changing after setup">
          <input
            className={inputCls}
            value={form.name}
            onChange={e => set("name", e.target.value)}
          />
        </Field>

        <Field label="Display name" hint="Shown to leads in conversations and in the dashboard">
          <input
            className={inputCls}
            value={form.firm_display_name}
            onChange={e => set("firm_display_name", e.target.value)}
          />
        </Field>

        <Field label="Visit CTA" hint="How the AI invites leads to visit">
          <input
            className={inputCls}
            value={form.visit_cta}
            onChange={e => set("visit_cta", e.target.value)}
          />
        </Field>

        <Field label="Fallback alert email" hint="Notified when AI cannot answer a lead's question">
          <input
            type="email"
            className={inputCls}
            value={form.fallback_alert_email}
            onChange={e => set("fallback_alert_email", e.target.value)}
          />
        </Field>
      </Section>

      {/* WhatsApp config */}
      <Section title="WhatsApp configuration">
        <p className="text-xs text-muted -mt-2">
          Find these in Meta Business Suite under WhatsApp &gt; API Setup.
        </p>

        <Field label="Phone Number ID">
          <input
            className={inputCls}
            placeholder="1234567890123456"
            value={form.wa_phone_number_id}
            onChange={e => set("wa_phone_number_id", e.target.value)}
          />
        </Field>

        <Field label="Access Token" hint="Permanent system user token, leave blank to keep current value">
          <input
            type="password"
            className={inputCls}
            placeholder={form.meta_access_token ? "••••••••••••••••" : "EAAxxxxxxxxxxxxxxxx"}
            value={form.meta_access_token}
            onChange={e => set("meta_access_token", e.target.value)}
          />
        </Field>

        <Field label="Webhook Verify Token">
          <input
            className={inputCls}
            placeholder="my-secret-verify-token"
            value={form.meta_webhook_verify_token}
            onChange={e => set("meta_webhook_verify_token", e.target.value)}
          />
        </Field>

        <Field label="App Secret" hint="Used for HMAC webhook validation, leave blank to keep current value">
          <input
            type="password"
            className={inputCls}
            placeholder={form.meta_app_secret ? "••••••••••••••••" : "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}
            value={form.meta_app_secret}
            onChange={e => set("meta_app_secret", e.target.value)}
          />
        </Field>
      </Section>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-sm text-error bg-error/10 border border-error/20 rounded-xl px-4 py-3">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Save */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => router.push("/admin/firms")}
          className="text-sm text-muted hover:text-ink transition"
        >
          Cancel
        </button>
        <button
          disabled={saving}
          onClick={save}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent text-on-accent text-sm font-medium hover:bg-accent-hover disabled:opacity-50 transition"
        >
          {saving ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</>
          ) : saved ? (
            <><CheckCircle2 className="w-4 h-4 text-success" /> Saved</>
          ) : (
            "Save changes"
          )}
        </button>
      </div>

      </> /* end settings tab */}

      {/* ── Knowledge tab ────────────────────────────────────────────────── */}
      {tab === "knowledge" && (
        <KnowledgeTab firmId={id} />
      )}

      {/* ── Resources tab ────────────────────────────────────────────────── */}
      {tab === "resources" && (
        <ResourcesTab firmId={id} resources={resources ?? []} onRefresh={() => mutateResources()} />
      )}

    </div>
  );
}

// ── Knowledge tab ──────────────────────────────────────────────────────────────

function KnowledgeTab({ firmId }: { firmId: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState("general");
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ filename: string; chunks: number } | null>(null);
  const [error, setError] = useState("");

  async function upload() {
    if (!file || uploading) return;
    setUploading(true);
    setError("");
    setResult(null);
    try {
      const res = await uploadKnowledgePDF(firmId, file, docType);
      setResult({ filename: file.name, chunks: res.chunks });
      setFile(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="bg-card rounded-2xl border border-line shadow-sm p-6 space-y-4">
        <h2 className="text-sm font-semibold text-ink uppercase tracking-wide">Upload knowledge PDF</h2>
        <p className="text-xs text-muted">
          PDFs are chunked, embedded, and stored in this firm's Pinecone knowledge namespace.
          The AI uses this to answer pricing, process, and FAQ questions.
        </p>

        <div>
          <label className="block text-sm font-medium text-ink/80 mb-1">Document type</label>
          <select
            value={docType}
            onChange={e => setDocType(e.target.value)}
            className="px-3 py-2 rounded-lg border border-line text-sm text-ink/80 focus:outline-none focus:ring-2 focus:ring-accent bg-card"
          >
            {["general", "pricing", "process", "faq", "portfolio"].map(t => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
        </div>

        <label className={cn(
          "flex flex-col items-center justify-center gap-2 border-2 border-dashed rounded-xl p-8 cursor-pointer transition-all",
          file ? "border-accent bg-accent/5" : "border-line hover:border-ink/30",
        )}>
          <input type="file" accept=".pdf" className="hidden" onChange={e => setFile(e.target.files?.[0] ?? null)} />
          <Upload className={cn("w-6 h-6", file ? "text-accent" : "text-muted")} />
          <p className="text-sm font-medium text-ink/80">{file ? file.name : "Click to select PDF"}</p>
          {file && <p className="text-xs text-muted">{(file.size / 1024).toFixed(0)} KB</p>}
        </label>

        {error && (
          <div className="flex items-center gap-2 text-sm text-error bg-error/10 border border-error/20 rounded-xl px-3 py-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" /> {error}
          </div>
        )}

        {result && (
          <div className="flex items-center gap-2 text-sm text-success bg-success/10 border border-success/30 rounded-xl px-3 py-2">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            {result.filename}, {result.chunks} chunks upserted to Pinecone
          </div>
        )}

        <button
          disabled={!file || uploading}
          onClick={upload}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent text-on-accent text-sm font-medium hover:bg-accent-hover disabled:opacity-40 transition"
        >
          {uploading ? <><Loader2 className="w-4 h-4 animate-spin" /> Uploading…</> : <><Upload className="w-4 h-4" /> Upload to Pinecone</>}
        </button>
      </div>
    </div>
  );
}

// ── Resources tab ──────────────────────────────────────────────────────────────

function ResourcesTab({ firmId, resources, onRefresh }: { firmId: string; resources: Resource[]; onRefresh: () => void }) {
  const [showAddUrl, setShowAddUrl] = useState(false);
  const [showUploadPdf, setShowUploadPdf] = useState(false);
  const [urlForm, setUrlForm] = useState({ id: "", title: "", description: "", resource_type: "youtube" as "youtube" | "pdf", url: "" });
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [pdfMeta, setPdfMeta] = useState({ title: "", description: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function addUrl() {
    if (!urlForm.title || !urlForm.url || saving) return;
    setSaving(true);
    setError("");
    try {
      await addResource(firmId, { ...urlForm, id: urlForm.id || undefined as unknown as string });
      setUrlForm({ id: "", title: "", description: "", resource_type: "youtube", url: "" });
      setShowAddUrl(false);
      onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setSaving(false);
    }
  }

  async function uploadPdf() {
    if (!pdfFile || !pdfMeta.title || saving) return;
    setSaving(true);
    setError("");
    try {
      await uploadResourcePDF(firmId, pdfFile, pdfMeta.title, pdfMeta.description);
      setPdfFile(null);
      setPdfMeta({ title: "", description: "" });
      setShowUploadPdf(false);
      onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setSaving(false);
    }
  }

  async function remove(resourceId: string) {
    await deleteResource(firmId, resourceId);
    onRefresh();
  }

  const inputCls = "w-full px-3 py-2 rounded-lg border border-line text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent transition";

  return (
    <div className="space-y-4">
      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => { setShowAddUrl(v => !v); setShowUploadPdf(false); }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-line bg-card text-sm font-medium text-ink/80 hover:border-ink/30 transition"
        >
          <Plus className="w-4 h-4" /> Add URL resource
        </button>
        <button
          onClick={() => { setShowUploadPdf(v => !v); setShowAddUrl(false); }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-line bg-card text-sm font-medium text-ink/80 hover:border-ink/30 transition"
        >
          <Upload className="w-4 h-4" /> Upload PDF
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-error bg-error/10 border border-error/20 rounded-xl px-3 py-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" /> {error}
        </div>
      )}

      {/* Add URL form */}
      {showAddUrl && (
        <div className="bg-card rounded-2xl border border-line shadow-sm p-5 space-y-3">
          <h3 className="text-sm font-semibold text-ink">Add URL resource</h3>
          <div className="flex gap-2">
            {(["youtube", "pdf"] as const).map(t => (
              <button
                key={t}
                onClick={() => setUrlForm(f => ({ ...f, resource_type: t }))}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition",
                  urlForm.resource_type === t ? "border-accent bg-accent/5 text-accent" : "border-line text-ink/70 hover:border-ink/30",
                )}
              >
                {t === "youtube" ? <Youtube className="w-3.5 h-3.5" /> : <FileText className="w-3.5 h-3.5" />}
                {t === "youtube" ? "YouTube" : "External PDF"}
              </button>
            ))}
          </div>
          <input className={inputCls} placeholder="Title" value={urlForm.title} onChange={e => setUrlForm(f => ({ ...f, title: e.target.value }))} />
          <input className={inputCls} placeholder="Description, when should the AI share this?" value={urlForm.description} onChange={e => setUrlForm(f => ({ ...f, description: e.target.value }))} />
          <input className={inputCls} placeholder={urlForm.resource_type === "youtube" ? "https://youtube.com/watch?v=..." : "https://example.com/brochure.pdf"} value={urlForm.url} onChange={e => setUrlForm(f => ({ ...f, url: e.target.value }))} />
          <div className="flex gap-2">
            <button onClick={addUrl} disabled={saving || !urlForm.title || !urlForm.url} className="px-4 py-2 rounded-xl bg-accent text-on-accent text-sm font-medium hover:bg-accent-hover disabled:opacity-40 transition">
              {saving ? "Saving…" : "Save resource"}
            </button>
            <button onClick={() => setShowAddUrl(false)} className="px-4 py-2 rounded-xl border border-line text-sm text-ink/70 hover:border-ink/30 transition">Cancel</button>
          </div>
        </div>
      )}

      {/* Upload PDF form */}
      {showUploadPdf && (
        <div className="bg-card rounded-2xl border border-line shadow-sm p-5 space-y-3">
          <h3 className="text-sm font-semibold text-ink">Upload PDF to Supabase Storage</h3>
          <input className={inputCls} placeholder="Title" value={pdfMeta.title} onChange={e => setPdfMeta(m => ({ ...m, title: e.target.value }))} />
          <input className={inputCls} placeholder="Description, when should the AI share this?" value={pdfMeta.description} onChange={e => setPdfMeta(m => ({ ...m, description: e.target.value }))} />
          <label className={cn("flex items-center gap-2 border-2 border-dashed rounded-xl p-4 cursor-pointer transition", pdfFile ? "border-accent bg-accent/5" : "border-line hover:border-ink/30")}>
            <input type="file" accept=".pdf" className="hidden" onChange={e => setPdfFile(e.target.files?.[0] ?? null)} />
            <FileText className={cn("w-5 h-5", pdfFile ? "text-accent" : "text-muted")} />
            <span className="text-sm text-ink/80">{pdfFile ? pdfFile.name : "Select PDF"}</span>
          </label>
          <div className="flex gap-2">
            <button onClick={uploadPdf} disabled={saving || !pdfFile || !pdfMeta.title} className="px-4 py-2 rounded-xl bg-accent text-on-accent text-sm font-medium hover:bg-accent-hover disabled:opacity-40 transition">
              {saving ? <><Loader2 className="w-4 h-4 animate-spin inline mr-1" />Uploading…</> : "Upload PDF"}
            </button>
            <button onClick={() => setShowUploadPdf(false)} className="px-4 py-2 rounded-xl border border-line text-sm text-ink/70 hover:border-ink/30 transition">Cancel</button>
          </div>
        </div>
      )}

      {/* Resource list */}
      {resources.length === 0 ? (
        <div className="text-center py-12 bg-card rounded-2xl border border-line">
          <FileText className="w-8 h-8 text-muted mx-auto mb-2" />
          <p className="text-muted text-sm">No resources yet</p>
          <p className="text-xs text-muted mt-1">Add PDFs or YouTube links the AI can share with leads</p>
        </div>
      ) : (
        <div className="space-y-2">
          {resources.map(r => (
            <div key={r.id} className="bg-card rounded-2xl border border-line shadow-sm px-4 py-3 flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-bg border border-line flex items-center justify-center flex-shrink-0 mt-0.5">
                {r.resource_type === "youtube" ? <Youtube className="w-4 h-4 text-error" /> : <FileText className="w-4 h-4 text-cost" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-ink truncate">{r.title}</p>
                {r.description && <p className="text-xs text-muted mt-0.5 line-clamp-2">{r.description}</p>}
                <p className="text-[10px] text-muted font-mono mt-1 truncate">{r.url}</p>
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                {r.url && (
                  <a href={r.url} target="_blank" rel="noopener noreferrer" className="p-1.5 rounded-lg text-muted hover:text-ink/80 hover:bg-bg transition">
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
                <button onClick={() => remove(r.id)} className="p-1.5 rounded-lg text-muted hover:text-error hover:bg-error/10 transition">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
