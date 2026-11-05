"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { createFirm, fetchPlans } from "@/lib/api";
import type { Plan, Vertical } from "@/types";
import { Building2, Sun, Home, CheckCircle2, ArrowRight, ArrowLeft, Loader2, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Step 1: Vertical selector ──────────────────────────────────────────────────

const VERTICALS: {
  id: Vertical;
  label: string;
  sub: string;
  icon: React.ElementType;
  color: string;
  bg: string;
  bullets: string[];
}[] = [
  {
    id:    "interior",
    label: "Interior Design",
    sub:   "Home renovation & interiors",
    icon:  Home,
    color: "var(--chart-4)",
    bg:    "color-mix(in srgb, var(--chart-4) 12%, transparent)",
    bullets: ["Experience Center visit flow", "2BHK / 3BHK config capture", "Portfolio showcase", "Budget in lakhs"],
  },
  {
    id:    "real_estate",
    label: "Real Estate",
    sub:   "Property sales & site visits",
    icon:  Building2,
    color: "var(--chart-2)",
    bg:    "color-mix(in srgb, var(--chart-2) 12%, transparent)",
    bullets: ["Site visit with cab pickup", "RERA & possession date Q&A", "Payment plan handling", "Budget in lakhs/crore"],
  },
  {
    id:    "solar",
    label: "Solar",
    sub:   "Rooftop solar installation",
    icon:  Sun,
    color: "var(--chart-3)",
    bg:    "color-mix(in srgb, var(--chart-3) 12%, transparent)",
    bullets: ["Free site survey flow", "PM Surya Ghar subsidy guidance", "Monthly bill to system size calc", "Roof ownership qualification"],
  },
];

// ── Field components ───────────────────────────────────────────────────────────

function Field({
  label,
  hint,
  required,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-ink/80 mb-1">
        {label}{required && <span className="text-error ml-0.5">*</span>}
      </label>
      {hint && <p className="text-xs text-muted mb-1.5">{hint}</p>}
      {children}
    </div>
  );
}

const inputCls =
  "w-full px-3.5 py-2.5 rounded-lg border border-line text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent transition";

// ── Steps ──────────────────────────────────────────────────────────────────────

interface FormState {
  vertical: Vertical | null;
  plan_id: string | null;
  name: string;
  firm_display_name: string;
  visit_cta: string;
  fallback_alert_email: string;
  wa_phone_number_id: string;
  meta_access_token: string;
  meta_webhook_verify_token: string;
  meta_app_secret: string;
}

const INITIAL: FormState = {
  vertical:                  null,
  plan_id:                   null,
  name:                      "",
  firm_display_name:         "",
  visit_cta:                 "",
  fallback_alert_email:      "",
  wa_phone_number_id:        "",
  meta_access_token:         "",
  meta_webhook_verify_token: "",
  meta_app_secret:           "",
};

const VISIT_CTA_DEFAULT: Record<Vertical, string> = {
  interior:    "Schedule an Experience Center visit",
  real_estate: "Book a site visit",
  solar:       "Book a free site survey",
};

export default function NewFirmPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [form, setForm] = useState<FormState>(INITIAL);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const { data: plans } = useSWR<Plan[]>("plans", fetchPlans);

  function set(key: keyof FormState, value: string) {
    setForm(f => ({ ...f, [key]: value }));
  }

  function selectVertical(v: Vertical) {
    setForm(f => ({
      ...f,
      vertical: v,
      visit_cta: f.visit_cta || VISIT_CTA_DEFAULT[v],
    }));
  }

  async function submit() {
    if (!form.vertical || !form.name || !form.firm_display_name) return;
    setError("");
    setSaving(true);
    try {
      await createFirm({
        vertical:                  form.vertical,
        plan_id:                   form.plan_id || null,
        name:                      form.name,
        firm_display_name:         form.firm_display_name,
        visit_cta:                 form.visit_cta || null,
        fallback_alert_email:      form.fallback_alert_email || null,
        wa_phone_number_id:        form.wa_phone_number_id || null,
        meta_access_token:         form.meta_access_token || null,
        meta_webhook_verify_token: form.meta_webhook_verify_token || null,
        meta_app_secret:           form.meta_app_secret || null,
      } as Parameters<typeof createFirm>[0]);
      router.push("/admin/firms");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setSaving(false);
    }
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-ink">Add new firm</h1>
        <p className="text-sm text-muted mt-1">Set up a new client on Speed-to-Lead</p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-8">
        {([1, 2, 3, 4] as const).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={cn(
                "w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-all",
                step > s
                  ? "bg-success text-on-accent"
                  : step === s
                    ? "bg-accent text-on-accent"
                    : "bg-bg text-muted",
              )}
            >
              {step > s ? <CheckCircle2 className="w-4 h-4" /> : s}
            </div>
            <span className={cn("text-xs font-medium", step === s ? "text-ink" : "text-muted")}>
              {["Vertical", "Firm details", "Plan", "WhatsApp"][i]}
            </span>
            {i < 3 && <div className="w-6 h-px bg-line mx-1" />}
          </div>
        ))}
      </div>

      <div className="bg-card rounded-2xl border border-line shadow-sm p-6">

        {/* ── Step 1: Vertical ─────────────────────────────────────────────── */}
        {step === 1 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-ink mb-4">Choose a vertical</h2>
            <div className="grid gap-3">
              {VERTICALS.map(v => {
                const Icon = v.icon;
                const selected = form.vertical === v.id;
                return (
                  <button
                    key={v.id}
                    onClick={() => selectVertical(v.id)}
                    className={cn(
                      "w-full text-left rounded-xl border-2 p-4 transition-all",
                      selected
                        ? "border-accent bg-accent/5"
                        : "border-line hover:border-ink/30 hover:bg-bg",
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                        style={{ backgroundColor: v.bg, border: `1.5px solid color-mix(in srgb, ${v.color} 28%, transparent)` }}
                      >
                        <Icon className="w-5 h-5" style={{ color: v.color }} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-ink">{v.label}</p>
                          {selected && <CheckCircle2 className="w-4 h-4 text-accent" />}
                        </div>
                        <p className="text-xs text-muted mt-0.5">{v.sub}</p>
                        <ul className="mt-2 space-y-0.5">
                          {v.bullets.map(b => (
                            <li key={b} className="flex items-center gap-1.5 text-xs text-muted">
                              <span className="w-1 h-1 rounded-full bg-muted flex-shrink-0" />
                              {b}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Step 2: Firm details ─────────────────────────────────────────── */}
        {step === 2 && (
          <div className="space-y-5">
            <h2 className="text-base font-semibold text-ink mb-4">Firm details</h2>

            <Field label="Internal name" hint="Slug-style identifier, e.g. studio-luxe-interiors" required>
              <input
                className={inputCls}
                placeholder="studio-luxe-interiors"
                value={form.name}
                onChange={e => set("name", e.target.value)}
              />
            </Field>

            <Field label="Display name" hint="Shown to leads and in the dashboard, e.g. Studio Luxe" required>
              <input
                className={inputCls}
                placeholder="Studio Luxe"
                value={form.firm_display_name}
                onChange={e => set("firm_display_name", e.target.value)}
              />
            </Field>

            <Field label="Visit CTA" hint="How the AI invites leads to visit, e.g. 'Book a free site survey'">
              <input
                className={inputCls}
                placeholder={form.vertical ? VISIT_CTA_DEFAULT[form.vertical] : ""}
                value={form.visit_cta}
                onChange={e => set("visit_cta", e.target.value)}
              />
            </Field>

            <Field label="Fallback alert email" hint="Get notified when AI can't answer a question">
              <input
                type="email"
                className={inputCls}
                placeholder="team@yourfirm.com"
                value={form.fallback_alert_email}
                onChange={e => set("fallback_alert_email", e.target.value)}
              />
            </Field>
          </div>
        )}

        {/* ── Step 3: Plan selection ───────────────────────────────────────── */}
        {step === 3 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-ink mb-4">Choose a plan</h2>
            {!plans ? (
              <div className="space-y-3">
                {[0, 1, 2, 3].map(i => (
                  <div key={i} className="h-20 bg-bg animate-pulse rounded-xl" />
                ))}
              </div>
            ) : (
              <div className="grid gap-3">
                {plans.map(plan => {
                  const selected = form.plan_id === plan.id;
                  return (
                    <button
                      key={plan.id}
                      onClick={() => setForm(f => ({ ...f, plan_id: plan.id }))}
                      className={cn(
                        "w-full text-left rounded-xl border-2 p-4 transition-all",
                        selected
                          ? "border-accent bg-accent/5"
                          : "border-line hover:border-ink/30 hover:bg-bg",
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={cn(
                            "w-9 h-9 rounded-lg flex items-center justify-center",
                            selected ? "bg-accent" : "bg-bg",
                          )}>
                            <Zap className={cn("w-4 h-4", selected ? "text-accent" : "text-muted")} />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-semibold text-ink">{plan.label}</p>
                              {selected && <CheckCircle2 className="w-4 h-4 text-accent" />}
                            </div>
                            <p className="text-xs text-muted mt-0.5">{plan.monthly_chat_cap} chats/month · Rs. {plan.overage_per_chat}/chat overage</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-ink">Rs. {plan.price_monthly.toLocaleString("en-IN")}</p>
                          <p className="text-[10px] text-muted">per month ex-GST</p>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ── Step 4: WhatsApp config ──────────────────────────────────────── */}
        {step === 4 && (
          <div className="space-y-5">
            <h2 className="text-base font-semibold text-ink mb-1">WhatsApp configuration</h2>
            <p className="text-xs text-muted mb-4">
              Find these in Meta Business Suite under WhatsApp &gt; API Setup. You can add or update these later.
            </p>

            <Field label="Phone Number ID" hint="The numeric ID of the WhatsApp Business phone number">
              <input
                className={inputCls}
                placeholder="1234567890123456"
                value={form.wa_phone_number_id}
                onChange={e => set("wa_phone_number_id", e.target.value)}
              />
            </Field>

            <Field label="Access Token" hint="Permanent system user token from Meta Business Suite">
              <input
                type="password"
                className={inputCls}
                placeholder="EAAxxxxxxxxxxxxxxxx"
                value={form.meta_access_token}
                onChange={e => set("meta_access_token", e.target.value)}
              />
            </Field>

            <Field label="Webhook Verify Token" hint="The token you set when registering the webhook URL">
              <input
                className={inputCls}
                placeholder="my-secret-verify-token"
                value={form.meta_webhook_verify_token}
                onChange={e => set("meta_webhook_verify_token", e.target.value)}
              />
            </Field>

            <Field label="App Secret" hint="From your Meta app dashboard, used for HMAC webhook validation">
              <input
                type="password"
                className={inputCls}
                placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                value={form.meta_app_secret}
                onChange={e => set("meta_app_secret", e.target.value)}
              />
            </Field>

            {error && (
              <p className="text-xs text-error bg-error/10 border border-error/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
          </div>
        )}

        {/* ── Navigation ───────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between mt-8 pt-5 border-t border-line">
          {step > 1 ? (
            <button
              onClick={() => setStep(s => (s - 1) as 1 | 2 | 3 | 4)}
              className="flex items-center gap-2 text-sm text-muted hover:text-ink transition"
            >
              <ArrowLeft className="w-4 h-4" /> Back
            </button>
          ) : (
            <div />
          )}

          {step < 4 ? (
            <button
              disabled={step === 1 && !form.vertical}
              onClick={() => setStep(s => (s + 1) as 1 | 2 | 3 | 4)}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent text-on-accent text-sm font-medium hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              Continue <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              disabled={saving || !form.name || !form.firm_display_name}
              onClick={submit}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent text-on-accent text-sm font-medium hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              {saving ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Creating…</>
              ) : (
                <>Create firm <CheckCircle2 className="w-4 h-4" /></>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
