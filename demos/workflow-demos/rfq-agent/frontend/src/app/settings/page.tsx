"use client";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Save, Loader2, CheckCircle2, Settings, Building2, Factory, ShoppingCart, Pill, Truck, Mail, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";

interface SettingsState {
  company_name: string;
  company_email: string;
  industry_vertical: string;
  confidence_threshold: number;
  amount_threshold: number;
  gst_rate: number;
  dispatch_start_hour: number;
  dispatch_end_hour: number;
  quote_validity_days: number;
  payment_terms: string;
  reviewer_email: string;
  slack_review_channel: string;
  auto_dispatch_enabled: boolean;
}

const DEFAULTS: SettingsState = {
  company_name: "InnovizeAI",
  company_email: "admin@innovizeai.com",
  industry_vertical: "manufacturing",
  confidence_threshold: 0.75,
  amount_threshold: 500000,
  gst_rate: 18,
  dispatch_start_hour: 8,
  dispatch_end_hour: 20,
  quote_validity_days: 30,
  payment_terms: "50% advance, 50% before dispatch",
  reviewer_email: "admin@innovizeai.com",
  slack_review_channel: "#rfq-review",
  auto_dispatch_enabled: true,
};

interface VerticalPreset {
  label: string;
  icon: React.ReactNode;
  description: string;
  hint: string;
  overrides: Partial<SettingsState>;
}

const VERTICALS: Record<string, VerticalPreset> = {
  manufacturing: {
    label: "Manufacturing",
    icon: <Factory size={16} />,
    description: "Material orders, BOMs, finished goods",
    hint: "Higher thresholds, longer quote validity",
    overrides: { amount_threshold: 500000, quote_validity_days: 30, confidence_threshold: 0.75, payment_terms: "50% advance, 50% before dispatch" },
  },
  construction: {
    label: "Construction",
    icon: <Building2 size={16} />,
    description: "BOQ items, plant hire, subcontractor scope",
    hint: "Short validity (prices change weekly), lower threshold",
    overrides: { amount_threshold: 50000, quote_validity_days: 3, confidence_threshold: 0.70, payment_terms: "100% advance for materials" },
  },
  trading: {
    label: "Trading / Distribution",
    icon: <ShoppingCart size={16} />,
    description: "Brand preference, MOQ, pack size",
    hint: "High volume, fast turnaround",
    overrides: { amount_threshold: 200000, quote_validity_days: 7, confidence_threshold: 0.80, payment_terms: "Net 30 days" },
  },
  pharma: {
    label: "Pharma",
    icon: <Pill size={16} />,
    description: "Batch size, expiry, regulatory codes",
    hint: "Stricter review, longer validation",
    overrides: { amount_threshold: 300000, quote_validity_days: 14, confidence_threshold: 0.85, payment_terms: "60 days credit" },
  },
  logistics: {
    label: "Logistics / Freight",
    icon: <Truck size={16} />,
    description: "Origin, destination, cargo type, weight",
    hint: "Freight quotes with route-based pricing",
    overrides: { amount_threshold: 100000, quote_validity_days: 1, confidence_threshold: 0.70, payment_terms: "Payment before dispatch" },
  },
};

interface ConnectedAccount {
  email: string;
  active: boolean;
  watch_expiry: string | null;
  connected_at: string;
}

function SettingsPage() {
  const [form, setForm] = useState<SettingsState>(DEFAULTS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [presetApplied, setPresetApplied] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [disconnecting, setDisconnecting] = useState<string | null>(null);
  const [justConnected, setJustConnected] = useState<string | null>(null);
  const searchParams = useSearchParams();

  useEffect(() => {
    api.getSettings()
      .then(data => setForm({ ...DEFAULTS, ...(data as Partial<SettingsState>) }))
      .catch(() => {})
      .finally(() => setLoading(false));
    loadAccounts();
    const connected = searchParams.get("connected");
    if (connected) {
      setJustConnected(connected);
      setTimeout(() => setJustConnected(null), 5000);
    }
  }, []);

  const loadAccounts = () => {
    api.listConnectedAccounts()
      .then(data => setAccounts(data.accounts))
      .catch(() => {});
  };

  const disconnect = async (email: string) => {
    setDisconnecting(email);
    try {
      await api.disconnectAccount(email);
      setAccounts(prev => prev.filter(a => a.email !== email));
    } finally {
      setDisconnecting(null);
    }
  };

  const set = (key: keyof SettingsState, val: unknown) =>
    setForm(prev => ({ ...prev, [key]: val }));

  const applyVertical = (key: string) => {
    const preset = VERTICALS[key];
    if (!preset) return;
    setForm(prev => ({ ...prev, industry_vertical: key, ...preset.overrides }));
    setPresetApplied(preset.label);
    setTimeout(() => setPresetApplied(null), 3000);
  };

  const save = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await api.updateSettings(form as unknown as Record<string, unknown>);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-slate-400 gap-3">
      <Loader2 size={20} className="animate-spin" /> Loading settings…
    </div>
  );

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Settings</h1>
          <p className="text-slate-500 text-sm mt-0.5">Configure your RFQ Agent</p>
        </div>
        <button onClick={save} disabled={saving}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white text-sm font-medium px-5 py-2.5 rounded-xl transition-colors">
          {saving ? <Loader2 size={15} className="animate-spin" /> : saved ? <CheckCircle2 size={15} /> : <Save size={15} />}
          {saved ? "Saved!" : "Save Changes"}
        </button>
      </div>

      <div className="space-y-5">

        {/* Industry Vertical */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-50">
            <div className="flex items-center gap-2">
              <span className="text-slate-400"><Building2 size={15} /></span>
              <h2 className="font-semibold text-slate-800 text-sm">Industry Vertical</h2>
            </div>
            {presetApplied && (
              <span className="flex items-center gap-1.5 text-xs text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full">
                <CheckCircle2 size={12} /> {presetApplied} preset applied
              </span>
            )}
          </div>
          <div className="px-6 py-5">
            <p className="text-xs text-slate-500 mb-4">Select your industry to auto-apply the right defaults for quote validity, approval thresholds, and payment terms.</p>
            <div className="grid grid-cols-5 gap-3">
              {Object.entries(VERTICALS).map(([key, v]) => (
                <button key={key} onClick={() => applyVertical(key)}
                  className={`flex flex-col items-center gap-2 p-3 rounded-xl border text-center transition-all ${
                    form.industry_vertical === key
                      ? "border-indigo-400 bg-indigo-50 text-indigo-700"
                      : "border-slate-200 text-slate-600 hover:border-indigo-200 hover:bg-slate-50"
                  }`}>
                  <span className={form.industry_vertical === key ? "text-indigo-600" : "text-slate-400"}>{v.icon}</span>
                  <span className="text-xs font-semibold leading-tight">{v.label}</span>
                  <span className="text-[10px] text-slate-400 leading-tight">{v.description}</span>
                </button>
              ))}
            </div>
            {form.industry_vertical && VERTICALS[form.industry_vertical] && (
              <p className="mt-3 text-xs text-slate-400 bg-slate-50 rounded-lg px-3 py-2">
                <span className="font-medium text-slate-500">Note:</span> {VERTICALS[form.industry_vertical].hint}
              </p>
            )}
          </div>
        </div>

        {/* Company */}
        <Section title="Company" icon={<Settings size={15} />}>
          <Field label="Company Name">
            <input value={form.company_name} onChange={e => set("company_name", e.target.value)} className={input} />
          </Field>
          <Field label="Company Email">
            <input type="email" value={form.company_email} onChange={e => set("company_email", e.target.value)} className={input} />
          </Field>
          <Field label="Reviewer Email" hint="Who gets notified when a quote needs review">
            <input type="email" value={form.reviewer_email} onChange={e => set("reviewer_email", e.target.value)} className={input} />
          </Field>
        </Section>

        {/* Automation rules */}
        <Section title="Automation Rules" icon={<Settings size={15} />}>
          <Field label="Auto-Dispatch" hint="Automatically send quotes without human approval">
            <label className="flex items-center gap-2 cursor-pointer">
              <div onClick={() => set("auto_dispatch_enabled", !form.auto_dispatch_enabled)}
                className={`w-10 h-6 rounded-full transition-colors relative ${form.auto_dispatch_enabled ? "bg-emerald-500" : "bg-slate-300"}`}>
                <span className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-all ${form.auto_dispatch_enabled ? "left-5" : "left-1"}`} />
              </div>
              <span className="text-sm text-slate-600">{form.auto_dispatch_enabled ? "Enabled" : "Disabled"}</span>
            </label>
          </Field>
          <Field label="Confidence Threshold" hint="Below this, RFQ goes to review (0–1)">
            <div className="flex items-center gap-3">
              <input type="range" min="0.5" max="0.99" step="0.01" value={form.confidence_threshold}
                onChange={e => set("confidence_threshold", parseFloat(e.target.value))} className="flex-1" />
              <span className="text-sm font-semibold text-slate-800 w-12 text-right">{Math.round(form.confidence_threshold * 100)}%</span>
            </div>
          </Field>
          <Field label="Amount Threshold (₹)" hint="Orders above this always go to review">
            <input type="number" value={form.amount_threshold} onChange={e => set("amount_threshold", parseFloat(e.target.value))}
              className={input} />
          </Field>
          <Field label="Dispatch Hours" hint="Only auto-dispatch between these hours">
            <div className="flex items-center gap-2">
              <input type="number" min="0" max="23" value={form.dispatch_start_hour}
                onChange={e => set("dispatch_start_hour", parseInt(e.target.value))} className={`${input} w-20`} />
              <span className="text-slate-400">to</span>
              <input type="number" min="0" max="23" value={form.dispatch_end_hour}
                onChange={e => set("dispatch_end_hour", parseInt(e.target.value))} className={`${input} w-20`} />
            </div>
          </Field>
        </Section>

        {/* Quote settings */}
        <Section title="Quote Settings" icon={<Settings size={15} />}>
          <Field label="GST Rate (%)" >
            <input type="number" min="0" max="28" value={form.gst_rate}
              onChange={e => set("gst_rate", parseFloat(e.target.value))} className={`${input} w-24`} />
          </Field>
          <Field label="Quote Validity (days)">
            <input type="number" min="1" max="90" value={form.quote_validity_days}
              onChange={e => set("quote_validity_days", parseInt(e.target.value))} className={`${input} w-24`} />
          </Field>
          <Field label="Payment Terms">
            <input value={form.payment_terms} onChange={e => set("payment_terms", e.target.value)} className={input} />
          </Field>
        </Section>

        {/* Notifications */}
        <Section title="Notifications" icon={<Settings size={15} />}>
          <Field label="Slack Review Channel">
            <input value={form.slack_review_channel} onChange={e => set("slack_review_channel", e.target.value)} className={input} placeholder="#rfq-review" />
          </Field>
        </Section>

        {/* Connected Gmail Accounts */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-50">
            <div className="flex items-center gap-2">
              <span className="text-slate-400"><Mail size={15} /></span>
              <h2 className="font-semibold text-slate-800 text-sm">Connected Gmail Accounts</h2>
            </div>
            <a
              href="/api/auth/gmail"
              className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
            >
              <Plus size={13} /> Connect Account
            </a>
          </div>
          <div className="px-6 py-5">
            {justConnected && (
              <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-lg px-4 py-2.5 mb-4">
                <CheckCircle2 size={15} /> <span><strong>{justConnected}</strong> connected successfully</span>
              </div>
            )}
            {accounts.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-4">
                No accounts connected. Click <strong>Connect Account</strong> to add a Gmail inbox to monitor.
              </p>
            ) : (
              <div className="space-y-2">
                {accounts.map(account => (
                  <div key={account.email} className="flex items-center justify-between py-3 px-4 bg-slate-50 rounded-xl">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 text-xs font-bold">
                        {account.email[0].toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-slate-800">{account.email}</p>
                        <p className="text-xs text-slate-400">
                          {account.watch_expiry
                            ? `Watch expires ${new Date(account.watch_expiry).toLocaleDateString()}`
                            : "Polling mode (no push watch)"}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${account.active ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-400"}`}>
                        {account.active ? "Active" : "Inactive"}
                      </span>
                      <button
                        onClick={() => disconnect(account.email)}
                        disabled={disconnecting === account.email}
                        className="text-slate-400 hover:text-red-500 transition-colors disabled:opacity-40"
                        title="Disconnect"
                      >
                        {disconnecting === account.email
                          ? <Loader2 size={15} className="animate-spin" />
                          : <Trash2 size={15} />}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

const input = "w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-white";

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
      <div className="flex items-center gap-2 px-6 py-4 border-b border-slate-50">
        <span className="text-slate-400">{icon}</span>
        <h2 className="font-semibold text-slate-800 text-sm">{title}</h2>
      </div>
      <div className="px-6 py-5 space-y-5">{children}</div>
    </div>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-4 items-start">
      <div className="pt-2">
        <p className="text-sm font-medium text-slate-700">{label}</p>
        {hint && <p className="text-xs text-slate-400 mt-0.5">{hint}</p>}
      </div>
      <div className="col-span-2">{children}</div>
    </div>
  );
}

export default function SettingsPageWrapper() {
  return (
    <Suspense>
      <SettingsPage />
    </Suspense>
  );
}
