"use client";

import { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import {
  ScrollText, AlertTriangle, ShieldCheck, Send, Phone, Link2, FileText, Clock, CheckCircle2,
  UserRound, Building2,
} from "lucide-react";
import {
  fetchBrokers, fetchRegistrations, resolveRegistration, simulateBrokerMessage,
  simulateBuyerChat,
} from "@/lib/api";
import { useFirm } from "@/hooks/use-firm";
import { useRole } from "@/hooks/use-role";
import { fmtIST, gapLabel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { BrokerRow, Registration, RegistrationStatus } from "@/types";

// ── Small pieces ───────────────────────────────────────────────────────────────

const STATUS_STYLE: Record<RegistrationStatus, { label: string; cls: string }> = {
  registered: { label: "Registered", cls: "bg-success/10 text-success border-success/30" },
  duplicate:  { label: "Conflict",   cls: "bg-warning/10 text-warning border-warning/30" },
  superseded: { label: "Superseded", cls: "bg-bg text-muted border-line" },
  expired:    { label: "Expired",    cls: "bg-bg text-muted border-line" },
  rejected:   { label: "Not enrolled", cls: "bg-error/10 text-error border-error/20" },
};

function StatusPill({ r }: { r: Registration }) {
  const s = STATUS_STYLE[r.status];
  const resolved = r.status === "duplicate" && r.conflict_state === "resolved";
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border", s.cls)}>
      {resolved ? "Resolved" : s.label}
    </span>
  );
}

const METHOD: Record<Registration["method"], { label: string; icon: React.ElementType }> = {
  broker_whatsapp: { label: "Partner WhatsApp", icon: Phone },
  coded_link:      { label: "Coded link", icon: Link2 },
  form:            { label: "Staff form", icon: FileText },
};

function Stamp({ iso }: { iso: string | null | undefined }) {
  return <span className="mono text-xs text-ink">{fmtIST(iso, "short")}</span>;
}

// ── Conflict card ──────────────────────────────────────────────────────────────

function ConflictCard({ r, onResolved }: { r: Registration; onResolved: () => void }) {
  const { name } = useRole();
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<"keep_first" | "award_new" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const firstAt = r.first?.registered_at ?? r.existing_lead_at;
  const firstWho = r.first
    ? r.first.broker_name ?? "Partner"
    : "Developer's own enquiry (ads or direct)";

  async function act(action: "keep_first" | "award_new") {
    setBusy(action);
    setError(null);
    try {
      await resolveRegistration(r.id, { action, note: note || undefined, resolved_by: name || undefined });
      onResolved();
    } catch {
      setError("Could not save the decision");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="bg-card rounded-2xl border border-warning/40 overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-line bg-warning/10">
        <AlertTriangle className="w-4 h-4 text-warning" strokeWidth={1.75} />
        <p className="text-sm font-medium text-ink">
          {r.client_name ?? "Client"} <span className="mono text-muted">({r.client_phone})</span>
          {r.project_name && <span className="text-muted"> for {r.project_name}</span>}
        </p>
        <span className="ml-auto label">
          {r.conflict_kind === "broker_vs_existing_lead" ? "Partner vs existing enquiry" : "Partner vs partner"}
        </span>
      </div>

      <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-line">
        <div className="p-5">
          <p className="label">First claim</p>
          <p className="mt-2 flex items-center gap-2 text-sm font-medium text-ink">
            {r.first ? <UserRound className="w-4 h-4 text-accent" strokeWidth={1.75} /> : <Building2 className="w-4 h-4 text-accent" strokeWidth={1.75} />}
            {firstWho}
          </p>
          <p className="mt-1"><Stamp iso={firstAt} /></p>
          {r.first && <p className="mono text-xs text-muted mt-1">{r.first.reference_id}</p>}
        </div>
        <div className="p-5">
          <p className="label">Later attempt</p>
          <p className="mt-2 flex items-center gap-2 text-sm font-medium text-ink">
            <UserRound className="w-4 h-4 text-muted" strokeWidth={1.75} />
            {r.broker_name ?? "Unknown"}
            {r.broker_company && <span className="text-xs text-muted font-normal">{r.broker_company}</span>}
          </p>
          <p className="mt-1 flex items-center gap-2">
            <Stamp iso={r.registered_at} />
            {firstAt && <span className="text-xs text-muted">{gapLabel(firstAt, r.registered_at)}</span>}
          </p>
          <p className="mono text-xs text-muted mt-1">{r.reference_id}</p>
        </div>
      </div>

      <div className="px-5 py-4 border-t border-line flex flex-wrap items-center gap-3">
        <input
          value={note}
          onChange={e => setNote(e.target.value)}
          placeholder="Note for the record (optional)"
          className="flex-1 min-w-[220px] rounded-lg border border-line bg-card px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent"
        />
        <button
          onClick={() => act("keep_first")}
          disabled={busy !== null}
          className="px-4 py-2 rounded-lg bg-accent text-on-accent text-sm font-medium hover:bg-accent-hover disabled:opacity-50"
        >
          {busy === "keep_first" ? "Saving" : "Keep first claim"}
        </button>
        <button
          onClick={() => act("award_new")}
          disabled={busy !== null}
          className="px-4 py-2 rounded-lg border border-line bg-card text-sm font-medium text-ink hover:border-ink/30 disabled:opacity-50"
        >
          {busy === "award_new" ? "Saving" : "Award to later attempt"}
        </button>
        {error && <span className="text-sm text-error">{error}</span>}
      </div>
    </div>
  );
}

// ── Desk simulator ─────────────────────────────────────────────────────────────

interface Bubble { side: "out" | "in"; text: string; meta?: string }

function DeskSimulator({ firmId, brokers, onActivity }: {
  firmId: string; brokers: BrokerRow[]; onActivity: () => void;
}) {
  const [mode, setMode] = useState<"broker" | "buyer">("broker");
  const [brokerId, setBrokerId] = useState<string>("");
  const [text, setText] = useState("REG Vikram Singh 9100000031 Skyline");
  const [thread, setThread] = useState<Bubble[]>([]);
  const [busy, setBusy] = useState(false);
  const [buyerPhone] = useState(() => "91900000" + String(Math.floor(1000 + Math.random() * 9000)));
  const [buyerCode, setBuyerCode] = useState("");
  const [buyerStarted, setBuyerStarted] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const active = brokers.filter(b => b.status === "active");
  useEffect(() => {
    if (!brokerId && active.length > 0) setBrokerId(active[0].id);
    if (!buyerCode && active.length > 0) setBuyerCode(active[0].code);
  }, [active, brokerId, buyerCode]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [thread]);

  const broker = brokers.find(b => b.id === brokerId);

  function switchMode(m: "broker" | "buyer") {
    setMode(m);
    setThread([]);
    setBuyerStarted(false);
    setText(m === "broker" ? "REG Vikram Singh 9100000031 Skyline" : "Hi, what is the price and the RERA number?");
  }

  async function send() {
    const msg = text.trim();
    if (!msg || busy) return;
    setBusy(true);
    try {
      if (mode === "broker") {
        if (!broker) return;
        setThread(t => [...t, { side: "out", text: msg, meta: `${broker.name}, ${broker.phone}` }]);
        const res = await simulateBrokerMessage({
          firm_id: firmId, from_phone: "91" + broker.phone.replace(/\D/g, "").slice(-10), text: msg,
        });
        setThread(t => [...t, { side: "in", text: res.reply ?? "No broker reply. This would go to the buyer flow.", meta: res.kind }]);
      } else {
        const full = buyerStarted ? msg : `${buyerCode} ${msg}`;
        setThread(t => [...t, { side: "out", text: full, meta: `Buyer ${buyerPhone.slice(-10)}` }]);
        setBuyerStarted(true);
        const res = await simulateBuyerChat({ firm_id: firmId, phone: buyerPhone, message: full, wa_name: "Demo Buyer" });
        setThread(t => [...t, { side: "in", text: res.response ?? "", meta: res.path_taken ?? undefined }]);
      }
      setText("");
      onActivity();
    } catch {
      setThread(t => [...t, { side: "in", text: "The simulator could not reach the backend.", meta: "error" }]);
    } finally {
      setBusy(false);
    }
  }

  const presets = mode === "broker"
    ? [
        ["New client", "REG Vikram Singh 9100000031 Skyline"],
        ["Same client, another partner", "REG Vikram Singh 9100000031"],
        ["Check status", "STATUS REG-"],
      ]
    : [
        ["Price and RERA", "Hi, what is the price and the RERA number?"],
        ["Possession and loans", "When is possession and which banks give loans?"],
        ["Ask for a discount", "Can I get a discount on the 3BHK?"],
        ["Ask about a unit", "Is a 3BHK on the 12th floor available?"],
      ];

  return (
    <div className="bg-card rounded-2xl border border-line overflow-hidden flex flex-col">
      <div className="px-5 py-4 border-b border-line">
        <h2 className="text-base font-semibold text-ink">Desk simulator</h2>
        <p className="text-xs text-muted mt-0.5">Run the scenes live. Nothing is sent to WhatsApp.</p>
        <div className="mt-3 inline-flex rounded-lg border border-line p-0.5 bg-bg">
          {(["broker", "buyer"] as const).map(m => (
            <button
              key={m}
              onClick={() => switchMode(m)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                mode === m ? "bg-card text-ink shadow-sm" : "text-muted hover:text-ink",
              )}
            >
              {m === "broker" ? "Partner registers" : "Buyer taps partner link"}
            </button>
          ))}
        </div>
      </div>

      <div className="px-5 pt-4 space-y-3">
        {mode === "broker" ? (
          <label className="block">
            <span className="label">Sending from</span>
            <select
              value={brokerId}
              onChange={e => setBrokerId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-line bg-card px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent"
            >
              {active.map(b => <option key={b.id} value={b.id}>{b.name}, {b.phone}</option>)}
            </select>
          </label>
        ) : (
          <label className="block">
            <span className="label">Link used by the buyer</span>
            <select
              value={buyerCode}
              disabled={buyerStarted}
              onChange={e => setBuyerCode(e.target.value)}
              className="mt-1 w-full rounded-lg border border-line bg-card px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-60"
            >
              {active.map(b => <option key={b.id} value={b.code}>{b.name}, {b.code}</option>)}
            </select>
          </label>
        )}
        <div className="flex flex-wrap gap-1.5">
          {presets.map(([label, value]) => (
            <button
              key={label}
              onClick={() => setText(value)}
              className="px-2.5 py-1 rounded-full border border-line text-xs text-ink/70 hover:border-ink/30 hover:text-ink"
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="mx-5 mt-4 rounded-xl bg-bg border border-line p-3 h-72 overflow-y-auto space-y-2">
        {thread.length === 0 && (
          <p className="text-xs text-muted text-center pt-24">Pick a scene above and press send.</p>
        )}
        {thread.map((b, i) => (
          <div key={i} className={cn("flex", b.side === "out" ? "justify-end" : "justify-start")}>
            <div className={cn(
              "max-w-[88%] rounded-xl px-3 py-2 text-[13px] leading-snug whitespace-pre-wrap border",
              b.side === "out" ? "bg-accent/10 border-accent/20 text-ink" : "bg-card border-line text-ink",
            )}>
              {b.text}
              {b.meta && <p className="mono text-[10px] text-muted mt-1">{b.meta}</p>}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={e => { e.preventDefault(); send(); }}
        className="p-5 flex gap-2"
      >
        <input
          value={text}
          onChange={e => setText(e.target.value)}
          className="flex-1 rounded-lg border border-line bg-card px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent"
          placeholder="Type a message"
        />
        <button
          type="submit"
          disabled={busy || !text.trim()}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-on-accent text-sm font-medium hover:bg-accent-hover disabled:opacity-50"
        >
          <Send className="w-4 h-4" strokeWidth={1.75} />
          {busy ? "Sending" : "Send"}
        </button>
      </form>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

const FILTERS = [
  { id: "all", label: "All" },
  { id: "conflicts", label: "Conflicts" },
  { id: "registered", label: "Registered" },
] as const;

export default function RegistryPage() {
  const { firmId, firm, loading } = useFirm();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");

  const { data: regs, mutate: mutateRegs } = useSWR<Registration[]>(
    firmId ? `regs-${firmId}` : null,
    () => fetchRegistrations(firmId!),
    { refreshInterval: 20_000 },
  );
  const { data: brokers, mutate: mutateBrokers } = useSWR<BrokerRow[]>(
    firmId ? `brokers-${firmId}` : null,
    () => fetchBrokers(firmId!),
  );

  const refresh = () => { mutateRegs(); mutateBrokers(); };

  if (!loading && firm && firm.vertical !== "real_estate") {
    return (
      <div className="p-4 sm:p-6 lg:p-8 max-w-3xl mx-auto">
        <h1 className="text-2xl font-semibold text-ink">Registry</h1>
        <p className="text-sm text-muted mt-2">The registry applies to real estate firms. Switch to a real estate firm to use this page.</p>
      </div>
    );
  }

  const open = (regs ?? []).filter(r => r.status === "duplicate" && r.conflict_state === "open");
  const rows = (regs ?? []).filter(r => {
    if (filter === "conflicts") return r.conflict_state != null;
    if (filter === "registered") return r.status === "registered";
    return true;
  });

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <p className="label">Registry</p>
        <h1 className="text-[28px] leading-tight tracking-[-0.03em] text-ink mt-1">
          Every client registration, time-stamped
        </h1>
        <p className="text-sm text-muted mt-1 max-w-2xl">
          The first valid registration for a client and project holds the lead. A later claim is recorded,
          never overwritten, and comes here for a person to decide.
        </p>
      </div>

      <div className="grid xl:grid-cols-[1fr_380px] gap-6 items-start">
        <div className="space-y-6 min-w-0">
          {/* Open conflicts */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <h2 className="text-base font-semibold text-ink">Needs a decision</h2>
              {open.length > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-warning/10 text-warning text-xs font-medium border border-warning/30">
                  {open.length} open
                </span>
              )}
            </div>
            {!regs ? (
              <div className="h-40 bg-bg animate-pulse rounded-2xl" />
            ) : open.length === 0 ? (
              <div className="bg-card rounded-2xl border border-line p-6 flex items-center gap-3 text-sm text-muted">
                <ShieldCheck className="w-5 h-5 text-success" strokeWidth={1.75} />
                No open conflicts. Every registration has a clear first claim.
              </div>
            ) : (
              <div className="space-y-4">
                {open.map(r => <ConflictCard key={r.id} r={r} onResolved={refresh} />)}
              </div>
            )}
          </section>

          {/* Ledger */}
          <section className="bg-card rounded-2xl border border-line overflow-hidden">
            <div className="px-5 py-4 border-b border-line flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <ScrollText className="w-4 h-4 text-accent" strokeWidth={1.75} />
                <h2 className="text-base font-semibold text-ink">Ledger</h2>
              </div>
              <div className="inline-flex rounded-lg border border-line p-0.5 bg-bg">
                {FILTERS.map(f => (
                  <button
                    key={f.id}
                    onClick={() => setFilter(f.id)}
                    className={cn(
                      "px-3 py-1 rounded-md text-xs font-medium transition-colors",
                      filter === f.id ? "bg-card text-ink shadow-sm" : "text-muted hover:text-ink",
                    )}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>
            {/* Phones: one card per registration */}
            <ul className="md:hidden divide-y divide-line">
              {!regs && [0, 1, 2].map(i => (
                <li key={i} className="p-4"><div className="h-16 bg-bg animate-pulse rounded-lg" /></li>
              ))}
              {regs && rows.length === 0 && (
                <li className="p-8 text-center text-sm text-muted">Nothing to show for this filter.</li>
              )}
              {rows.map(r => {
                const M = METHOD[r.method];
                return (
                  <li key={r.id} className="p-4 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="mono text-xs text-ink">{r.reference_id}</span>
                      <StatusPill r={r} />
                    </div>
                    <p className="text-sm font-medium text-ink">
                      {r.client_name ?? "-"} <span className="mono text-xs text-muted font-normal">{r.client_phone}</span>
                    </p>
                    <p className="text-xs text-muted">
                      {r.broker_name ?? "Unknown number"}{r.project_name ? `, ${r.project_name}` : ""}
                    </p>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
                      <Stamp iso={r.registered_at} />
                      <span className="text-muted">Valid until <span className="mono">{fmtIST(r.valid_until, "date")}</span></span>
                      <span className="inline-flex items-center gap-1.5 text-ink/70">
                        <M.icon className="w-3.5 h-3.5" strokeWidth={1.75} />{M.label}
                      </span>
                    </div>
                    {r.status === "duplicate" && r.conflict_state === "resolved" && r.resolution_note && (
                      <p className="text-[11px] text-muted flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-success" strokeWidth={1.75} />{r.resolution_note}
                      </p>
                    )}
                  </li>
                );
              })}
            </ul>
            {/* Tablet and up: table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left border-b border-line">
                    <th className="label px-5 py-3 font-medium">Reference</th>
                    <th className="label px-3 py-3 font-medium">Client</th>
                    <th className="label px-3 py-3 font-medium">Partner</th>
                    <th className="label px-3 py-3 font-medium">Registered</th>
                    <th className="label px-3 py-3 font-medium">Valid until</th>
                    <th className="label px-3 py-3 font-medium">Via</th>
                    <th className="label px-5 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {!regs && [0, 1, 2, 3].map(i => (
                    <tr key={i}><td colSpan={7} className="px-5 py-3"><div className="h-8 bg-bg animate-pulse rounded-lg" /></td></tr>
                  ))}
                  {regs && rows.length === 0 && (
                    <tr><td colSpan={7} className="px-5 py-10 text-center text-muted">Nothing to show for this filter.</td></tr>
                  )}
                  {rows.map(r => {
                    const M = METHOD[r.method];
                    return (
                      <tr key={r.id} className="border-b border-line last:border-0 hover:bg-bg/60">
                        <td className="px-5 py-3 mono text-xs text-ink">{r.reference_id}</td>
                        <td className="px-3 py-3">
                          <p className="text-ink">{r.client_name ?? "-"}</p>
                          <p className="mono text-[11px] text-muted">{r.client_phone}</p>
                        </td>
                        <td className="px-3 py-3">
                          <p className="text-ink">{r.broker_name ?? <span className="text-error">Unknown number</span>}</p>
                          <p className="text-[11px] text-muted">{r.project_name ?? ""}</p>
                        </td>
                        <td className="px-3 py-3"><Stamp iso={r.registered_at} /></td>
                        <td className="px-3 py-3 text-xs text-muted mono">{fmtIST(r.valid_until, "date")}</td>
                        <td className="px-3 py-3">
                          <span className="inline-flex items-center gap-1.5 text-xs text-ink/70">
                            <M.icon className="w-3.5 h-3.5" strokeWidth={1.75} />{M.label}
                          </span>
                        </td>
                        <td className="px-5 py-3">
                          <StatusPill r={r} />
                          {r.status === "duplicate" && r.conflict_state === "resolved" && r.resolution_note && (
                            <p className="text-[11px] text-muted mt-1 flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3 text-success" strokeWidth={1.75} />{r.resolution_note}
                            </p>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="px-5 py-3 border-t border-line flex items-center gap-1.5 text-xs text-muted">
              <Clock className="w-3.5 h-3.5" strokeWidth={1.75} />
              All times in IST. Registrations are valid for the project&apos;s set period.
            </div>
          </section>
        </div>

        {firmId && (
          <DeskSimulator firmId={firmId} brokers={brokers ?? []} onActivity={refresh} />
        )}
      </div>
    </div>
  );
}
