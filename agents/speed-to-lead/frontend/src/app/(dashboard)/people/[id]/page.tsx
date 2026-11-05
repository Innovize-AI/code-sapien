"use client";

import { use, useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import {
  ArrowLeft, Phone, KeyRound, MessageSquare, Plus, PauseCircle, PlayCircle, Check, UserRound,
} from "lucide-react";
import {
  changeNumber, createPersonLogin, fetchBrokers, fetchNumbers, registerNumber,
} from "@/lib/api";
import { useFirm } from "@/hooks/use-firm";
import { cn } from "@/lib/utils";
import type { BrokerRow, NumberRow } from "@/types";

const FIELD =
  "w-full rounded-lg border border-line bg-card px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent";

function message(err: unknown, fallback: string): string {
  // The API replies "400 <reason>: /path". Show only the reason.
  return err instanceof Error ? err.message.replace(/^\d+\s+/, "").replace(/:\s*\/.*$/, "") : fallback;
}

// ── Numbers ──────────────────────────────────────────────────────────────────────

function NumbersCard({ firmId, person }: { firmId: string; person: BrokerRow }) {
  const { data: numbers, mutate } = useSWR<NumberRow[]>(
    ["numbers", firmId, person.id],
    () => fetchNumbers(firmId, person.id),
  );
  const [label, setLabel] = useState("");
  const [display, setDisplay] = useState("");
  const [waId, setWaId] = useState("");
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await registerNumber({
        firm_id: firmId, person_id: person.id, label, wa_phone_number_id: waId,
        display_phone: display || undefined, meta_access_token: token || undefined,
      });
      setLabel(""); setDisplay(""); setWaId(""); setToken("");
      await mutate();
    } catch (err) {
      setError(message(err, "Could not register the number"));
    } finally {
      setBusy(false);
    }
  }

  async function toggle(n: NumberRow) {
    setBusyId(n.id);
    try {
      await changeNumber(n.id, { is_active: !n.is_active });
      await mutate();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="bg-card rounded-2xl border border-line p-5 sm:p-6">
      <div className="flex items-center gap-2">
        <Phone className="w-4 h-4 text-accent" strokeWidth={1.75} />
        <h2 className="text-base font-semibold text-ink">WhatsApp numbers</h2>
      </div>
      <p className="text-xs text-muted mt-1 max-w-xl">
        Buyers who message one of these numbers are handled by the assistant and owned by {person.name}.
        Replies leave from the same number. Counselors still see every conversation.
      </p>

      <ul className="mt-4 divide-y divide-line border border-line rounded-xl overflow-hidden">
        {!numbers && <li className="p-4"><div className="h-10 bg-bg animate-pulse rounded-lg" /></li>}
        {numbers?.length === 0 && (
          <li className="p-4 text-sm text-muted">No numbers yet. Register one below.</li>
        )}
        {numbers?.map(n => (
          <li key={n.id} className={cn("p-4 flex items-start justify-between gap-3", !n.is_active && "opacity-60")}>
            <div className="min-w-0">
              <p className="text-sm font-medium text-ink">{n.label}</p>
              {n.display_phone && <p className="mono text-xs text-ink/80 mt-0.5">{n.display_phone}</p>}
              <p className="mono text-[11px] text-muted mt-0.5 break-all">Meta ID {n.wa_phone_number_id}</p>
              {n.has_own_token && <p className="text-[11px] text-muted mt-0.5">Uses its own access token</p>}
            </div>
            <button
              onClick={() => toggle(n)}
              disabled={busyId === n.id}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-muted hover:text-ink disabled:opacity-50 flex-shrink-0"
            >
              {n.is_active
                ? <><PauseCircle className="w-4 h-4" strokeWidth={1.75} />Pause</>
                : <><PlayCircle className="w-4 h-4" strokeWidth={1.75} />Resume</>}
            </button>
          </li>
        ))}
      </ul>

      <form onSubmit={add} className="mt-5 space-y-3">
        <p className="label">Register a number</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <input className={FIELD} placeholder="Label, for example Rahul's line" value={label} onChange={e => setLabel(e.target.value)} required />
          <input className={cn(FIELD, "mono")} placeholder="Number people dial (optional)" value={display} onChange={e => setDisplay(e.target.value)} />
          <input className={cn(FIELD, "mono")} placeholder="Phone number ID from Meta" value={waId} onChange={e => setWaId(e.target.value)} required />
          <input className={cn(FIELD, "mono")} type="password" autoComplete="off" placeholder="Access token (optional)" value={token} onChange={e => setToken(e.target.value)} />
        </div>
        <p className="text-[11px] text-muted">
          Add the number to your WhatsApp Business account in Meta first, then paste its phone number ID here.
          Leave the token empty to use the firm&apos;s token.
        </p>
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={busy}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-on-accent text-sm font-medium hover:bg-accent-hover disabled:opacity-50"
          >
            <Plus className="w-4 h-4" strokeWidth={1.75} />
            {busy ? "Registering" : "Register number"}
          </button>
          {error && <span className="text-sm text-error">{error}</span>}
        </div>
      </form>
    </section>
  );
}

// ── Sign-in ──────────────────────────────────────────────────────────────────────

function LoginCard({ person, onCreated }: { person: BrokerRow; onCreated: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createPersonLogin(person.id, { email, password });
      setDone(true);
      setPassword("");
      onCreated();
    } catch (err) {
      setError(message(err, "Could not create the sign-in"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="bg-card rounded-2xl border border-line p-5 sm:p-6">
      <div className="flex items-center gap-2">
        <KeyRound className="w-4 h-4 text-accent" strokeWidth={1.75} />
        <h2 className="text-base font-semibold text-ink">Sign-in</h2>
      </div>

      {person.email ? (
        <div className="mt-3 flex items-start gap-2 text-sm">
          <Check className="w-4 h-4 text-success mt-0.5 flex-shrink-0" strokeWidth={2} />
          <div>
            <p className="text-ink">
              {person.name} signs in with <span className="mono">{person.email}</span>.
            </p>
            <p className="text-xs text-muted mt-1">
              They see and chat on the conversations on their own numbers only.
              {done && " Share the password with them directly. It is not shown again."}
            </p>
          </div>
        </div>
      ) : (
        <form onSubmit={create} className="mt-3 space-y-3">
          <p className="text-xs text-muted max-w-xl">
            Give {person.name} an email and a password. They will see, and chat on, only the conversations
            that arrive on their own numbers.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input className={FIELD} type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required />
            <input className={FIELD} type="password" autoComplete="new-password" placeholder="Password, 8 or more characters" value={password} onChange={e => setPassword(e.target.value)} required minLength={8} />
          </div>
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={busy}
              className="px-4 py-2 rounded-lg bg-accent text-on-accent text-sm font-medium hover:bg-accent-hover disabled:opacity-50"
            >
              {busy ? "Creating" : "Create sign-in"}
            </button>
            {error && <span className="text-sm text-error">{error}</span>}
          </div>
        </form>
      )}
    </section>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────────

export default function PersonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { firmId } = useFirm();
  const { data: people, mutate } = useSWR<BrokerRow[]>(
    firmId ? `brokers-${firmId}` : null,
    () => fetchBrokers(firmId!),
  );
  const person = people?.find(p => p.id === id);

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-3xl mx-auto space-y-6">
      <Link href="/brokers" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
        <ArrowLeft className="w-4 h-4" strokeWidth={1.75} />
        Partners and team
      </Link>

      {!people ? (
        <div className="h-24 bg-bg animate-pulse rounded-2xl" />
      ) : !person ? (
        <p className="text-sm text-muted">This person was not found for the selected firm.</p>
      ) : (
        <>
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex items-start gap-3">
              <div className="w-11 h-11 rounded-full bg-accent/10 border border-line flex items-center justify-center flex-shrink-0">
                <UserRound className="w-5 h-5 text-accent" strokeWidth={1.75} />
              </div>
              <div>
                <p className="label">{person.kind === "team" ? "Internal team" : "Channel partner"}</p>
                <h1 className="text-[26px] leading-tight tracking-[-0.03em] text-ink">{person.name}</h1>
                <p className="text-sm text-muted mt-0.5">
                  {person.company ?? "Independent"} <span className="mono">· {person.phone}</span>
                </p>
                <p className="mono text-xs text-muted mt-1">Link code {person.code}</p>
              </div>
            </div>
            <Link
              href={`/conversations?owner=${person.id}`}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-line bg-card text-sm font-medium text-ink hover:border-ink/30"
            >
              <MessageSquare className="w-4 h-4" strokeWidth={1.75} />
              See their conversations
            </Link>
          </div>

          {firmId && <NumbersCard firmId={firmId} person={person} />}
          <LoginCard person={person} onCreated={() => mutate()} />
        </>
      )}
    </div>
  );
}
