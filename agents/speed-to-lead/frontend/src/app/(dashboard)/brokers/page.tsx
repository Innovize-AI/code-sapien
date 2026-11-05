"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  Handshake, UserPlus, Copy, Check, ScrollText, AlertTriangle, Users, CalendarCheck,
  PauseCircle, PlayCircle, SlidersHorizontal,
} from "lucide-react";
import Link from "next/link";
import { enrolBroker, fetchBrokers, fetchNumbers, setBrokerStatus } from "@/lib/api";
import { useFirm } from "@/hooks/use-firm";
import { fmtIST } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { BrokerRow, NumberRow } from "@/types";

function Stat({ icon: Icon, label, value, hint }: {
  icon: React.ElementType; label: string; value: number | string; hint?: string;
}) {
  return (
    <div className="bg-card rounded-2xl border border-line p-5">
      <div className="flex items-center gap-2 text-muted">
        <Icon className="w-4 h-4" strokeWidth={1.75} />
        <span className="label">{label}</span>
      </div>
      <p className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-ink tabular-nums">{value}</p>
      {hint && <p className="text-xs text-muted mt-1">{hint}</p>}
    </div>
  );
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [done, setDone] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 1500);
    } catch {
      /* clipboard can be blocked, the text is still visible to select */
    }
  }
  return (
    <button
      onClick={copy}
      className="inline-flex items-center gap-1.5 text-xs font-medium text-accent hover:text-accent-hover"
      title={`Copy ${label}`}
    >
      {done ? <Check className="w-3.5 h-3.5" strokeWidth={2} /> : <Copy className="w-3.5 h-3.5" strokeWidth={1.75} />}
      {done ? "Copied" : label}
    </button>
  );
}

function EnrolForm({ firmId, onDone }: { firmId: string; onDone: () => void }) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [company, setCompany] = useState("");
  const [rera, setRera] = useState("");
  const [kind, setKind] = useState<"partner" | "team">("partner");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const b = await enrolBroker({
        firm_id: firmId, name, phone,
        company: company || undefined, rera_agent_no: rera || undefined, kind,
      });
      setCreated(b.code);
      setName(""); setPhone(""); setCompany(""); setRera("");
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message.replace(/^\d+ [^:]*: /, "") : "Could not enrol");
    } finally {
      setBusy(false);
    }
  }

  const field = "w-full rounded-lg border border-line bg-card px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent";
  return (
    <form onSubmit={submit} className="bg-card rounded-2xl border border-line p-5">
      <div className="flex items-center gap-2">
        <UserPlus className="w-4 h-4 text-accent" strokeWidth={1.75} />
        <h2 className="text-base font-semibold text-ink">Add a partner or team member</h2>
      </div>
      <p className="text-xs text-muted mt-1">
        Registrations are accepted only from enrolled numbers. Use the person&apos;s own mobile number. You can register WhatsApp numbers for them and give them a sign-in afterwards.
      </p>
      <div className="inline-flex rounded-lg border border-line p-0.5 bg-bg mt-4">
        {(["partner", "team"] as const).map(k => (
          <button
            key={k}
            type="button"
            onClick={() => setKind(k)}
            className={cn(
              "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
              kind === k ? "bg-card text-ink shadow-sm" : "text-muted hover:text-ink",
            )}
          >
            {k === "partner" ? "Channel partner" : "Internal team"}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mt-3">
        <input className={field} placeholder="Full name" value={name} onChange={e => setName(e.target.value)} required />
        <input className={cn(field, "mono")} placeholder="Mobile number" value={phone} onChange={e => setPhone(e.target.value)} required />
        <input className={field} placeholder="Firm (optional)" value={company} onChange={e => setCompany(e.target.value)} />
        <input className={cn(field, "mono")} placeholder="RERA agent no. (optional)" value={rera} onChange={e => setRera(e.target.value)} />
      </div>
      <div className="flex items-center gap-4 mt-4">
        <button
          type="submit"
          disabled={busy}
          className="px-4 py-2 rounded-lg bg-accent text-on-accent text-sm font-medium hover:bg-accent-hover disabled:opacity-50"
        >
          {busy ? "Adding" : kind === "team" ? "Add team member" : "Add partner"}
        </button>
        {created && (
          <span className="text-sm text-success">
            Enrolled. Their link code is <span className="mono font-medium">{created}</span>
          </span>
        )}
        {error && <span className="text-sm text-error">{error}</span>}
      </div>
    </form>
  );
}

export default function BrokersPage() {
  const { firmId, firm, loading } = useFirm();
  const { data: brokers, mutate } = useSWR<BrokerRow[]>(
    firmId ? `brokers-${firmId}` : null,
    () => fetchBrokers(firmId!),
    { refreshInterval: 30_000 },
  );
  const [busyId, setBusyId] = useState<string | null>(null);
  const { data: numbers } = useSWR<NumberRow[]>(
    firmId ? `numbers-${firmId}` : null,
    () => fetchNumbers(firmId!),
  );
  const numberCount = (numbers ?? []).reduce<Record<string, number>>((a, n) => {
    if (n.person_id && n.is_active) a[n.person_id] = (a[n.person_id] ?? 0) + 1;
    return a;
  }, {});

  async function toggle(b: BrokerRow) {
    setBusyId(b.id);
    try {
      await setBrokerStatus(b.id, b.status === "active" ? "suspended" : "active");
      await mutate();
    } finally {
      setBusyId(null);
    }
  }

  const totals = (brokers ?? []).reduce(
    (a, b) => ({
      registered: a.registered + b.registered,
      conflicts: a.conflicts + b.conflicts,
      leads: a.leads + b.leads,
      visits: a.visits + b.visits,
    }),
    { registered: 0, conflicts: 0, leads: 0, visits: 0 },
  );

  if (!loading && firm && firm.vertical !== "real_estate") {
    return (
      <div className="p-4 sm:p-6 lg:p-8 max-w-3xl mx-auto">
        <h1 className="text-2xl font-semibold text-ink">Channel partners</h1>
        <p className="text-sm text-muted mt-2">Channel partners apply to real estate firms. Switch to a real estate firm to use this page.</p>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <p className="label">Partners and team</p>
          <h1 className="text-[28px] leading-tight tracking-[-0.03em] text-ink mt-1">
            Who brings you buyers
          </h1>
          <p className="text-sm text-muted mt-1 max-w-xl">
            Each partner registers clients from their own WhatsApp number and gets a time-stamped receipt.
            The first valid registration holds the lead.
          </p>
        </div>
        <Link
          href="/registrations"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-line bg-card text-sm font-medium text-ink hover:border-ink/30"
        >
          <ScrollText className="w-4 h-4" strokeWidth={1.75} />
          Open registry
        </Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat icon={Handshake} label="Enrolled" value={brokers?.length ?? "-"} />
        <Stat icon={ScrollText} label="Registrations, 90 days" value={brokers ? totals.registered : "-"} />
        <Stat icon={Users} label="Leads via partners" value={brokers ? totals.leads : "-"} />
        <Stat icon={CalendarCheck} label="Visits from partners" value={brokers ? totals.visits : "-"} />
      </div>

      {firmId && <EnrolForm firmId={firmId} onDone={() => mutate()} />}

      <div className="bg-card rounded-2xl border border-line overflow-hidden">
        <div className="px-5 py-4 border-b border-line flex items-center justify-between">
          <h2 className="text-base font-semibold text-ink">Partners by results</h2>
          <span className="text-xs text-muted">Ranked by visits, then registrations</span>
        </div>
        {/* Phones: one card per partner */}
        <ul className="md:hidden divide-y divide-line">
          {!brokers && [0, 1].map(i => (
            <li key={i} className="p-4"><div className="h-20 bg-bg animate-pulse rounded-lg" /></li>
          ))}
          {brokers?.length === 0 && (
            <li className="p-8 text-center text-sm text-muted">No partners enrolled yet.</li>
          )}
          {brokers?.map(b => (
            <li key={b.id} className={cn("p-4 space-y-3", b.status !== "active" && "opacity-60")}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-ink">{b.name}<span className={cn(
                    "ml-2 px-1.5 py-0.5 rounded text-[10px] font-medium border align-middle",
                    b.kind === "team" ? "bg-chart-2/10 text-chart-2 border-chart-2/30" : "bg-bg text-muted border-line",
                  )}>{b.kind === "team" ? "Team" : "Partner"}</span></p>
                  <p className="text-xs text-muted">{b.company ?? "Independent"} <span className="mono">{b.phone}</span></p>
                  <Link href={`/people/${b.id}`} className="mt-1 inline-flex items-center gap-1.5 text-xs font-medium text-accent hover:text-accent-hover">
                    <SlidersHorizontal className="w-3.5 h-3.5" strokeWidth={1.75} />
                    Numbers and sign-in{(numberCount[b.id] ?? 0) > 0 ? `, ${numberCount[b.id]} number${numberCount[b.id] === 1 ? "" : "s"}` : ""}
                  </Link>
                </div>
                <button
                  onClick={() => toggle(b)}
                  disabled={busyId === b.id}
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-muted hover:text-ink disabled:opacity-50 flex-shrink-0"
                >
                  {b.status === "active"
                    ? <><PauseCircle className="w-4 h-4" strokeWidth={1.75} />Pause</>
                    : <><PlayCircle className="w-4 h-4" strokeWidth={1.75} />Resume</>}
                </button>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="mono text-sm text-ink">{b.code}</span>
                <CopyButton text={b.link ?? b.code} label={b.link ? "Copy link" : "Copy code"} />
              </div>
              <dl className="grid grid-cols-4 gap-2 text-center">
                {[["Registered", b.registered], ["Conflicts", b.conflicts], ["Leads", b.leads], ["Visits", b.visits]].map(([k, v]) => (
                  <div key={String(k)} className="rounded-lg bg-bg py-2">
                    <dd className="text-base font-semibold text-ink tabular-nums">{v}</dd>
                    <dt className="text-[10px] text-muted">{k}</dt>
                  </div>
                ))}
              </dl>
            </li>
          ))}
        </ul>
        {/* Tablet and up: table */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-line">
                <th className="label px-5 py-3 font-medium">Partner</th>
                <th className="label px-3 py-3 font-medium">Link code</th>
                <th className="label px-3 py-3 font-medium text-right">Registered</th>
                <th className="label px-3 py-3 font-medium text-right">Conflicts</th>
                <th className="label px-3 py-3 font-medium text-right">Leads</th>
                <th className="label px-3 py-3 font-medium text-right">Visits</th>
                <th className="label px-3 py-3 font-medium">Last registration</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {!brokers && [0, 1, 2].map(i => (
                <tr key={i}><td colSpan={8} className="px-5 py-3"><div className="h-8 bg-bg animate-pulse rounded-lg" /></td></tr>
              ))}
              {brokers?.length === 0 && (
                <tr><td colSpan={8} className="px-5 py-10 text-center text-muted">No partners enrolled yet.</td></tr>
              )}
              {brokers?.map(b => (
                <tr key={b.id} className={cn("border-b border-line last:border-0", b.status !== "active" && "opacity-60")}>
                  <td className="px-5 py-3">
                    <p className="font-medium text-ink">{b.name}<span className={cn(
                    "ml-2 px-1.5 py-0.5 rounded text-[10px] font-medium border align-middle",
                    b.kind === "team" ? "bg-chart-2/10 text-chart-2 border-chart-2/30" : "bg-bg text-muted border-line",
                  )}>{b.kind === "team" ? "Team" : "Partner"}</span></p>
                    <p className="text-xs text-muted">
                      {b.company ?? "Independent"} <span className="mono">· {b.phone}</span>
                    </p>
                    <Link href={`/people/${b.id}`} className="mt-1 inline-flex items-center gap-1.5 text-xs font-medium text-accent hover:text-accent-hover">
                      <SlidersHorizontal className="w-3.5 h-3.5" strokeWidth={1.75} />
                      Numbers and sign-in{(numberCount[b.id] ?? 0) > 0 ? `, ${numberCount[b.id]} number${numberCount[b.id] === 1 ? "" : "s"}` : ""}
                    </Link>
                    {b.rera_agent_no && <p className="text-[11px] text-muted mono">RERA agent {b.rera_agent_no}</p>}
                  </td>
                  <td className="px-3 py-3">
                    <p className="mono text-ink">{b.code}</p>
                    <div className="mt-0.5">
                      <CopyButton text={b.link ?? b.code} label={b.link ? "Copy link" : "Copy code"} />
                    </div>
                  </td>
                  <td className="px-3 py-3 text-right tabular-nums text-ink">{b.registered}</td>
                  <td className="px-3 py-3 text-right tabular-nums">
                    {b.conflicts > 0
                      ? <span className="inline-flex items-center gap-1 text-warning"><AlertTriangle className="w-3.5 h-3.5" strokeWidth={1.75} />{b.conflicts}</span>
                      : <span className="text-muted">0</span>}
                  </td>
                  <td className="px-3 py-3 text-right tabular-nums text-ink">{b.leads}</td>
                  <td className="px-3 py-3 text-right tabular-nums font-medium text-ink">{b.visits}</td>
                  <td className="px-3 py-3 text-xs text-muted mono">{fmtIST(b.last_registration_at)}</td>
                  <td className="px-5 py-3 text-right">
                    <button
                      onClick={() => toggle(b)}
                      disabled={busyId === b.id}
                      className="inline-flex items-center gap-1.5 text-xs font-medium text-muted hover:text-ink disabled:opacity-50"
                    >
                      {b.status === "active"
                        ? <><PauseCircle className="w-4 h-4" strokeWidth={1.75} />Pause</>
                        : <><PlayCircle className="w-4 h-4" strokeWidth={1.75} />Resume</>}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
