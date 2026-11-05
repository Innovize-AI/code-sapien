"use client";

import { use, useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { format, formatDistanceToNow } from "date-fns";
import {
  ArrowLeft, Bot, PauseCircle, PlayCircle,
  Send, Loader2, User, Phone, Home,
  Wallet, ChevronDown, ChevronUp,
  Search, Zap, FileText, Info, LayoutGrid,
  Sparkles, RefreshCw, MessageSquare, ClipboardList, Handshake, Target, AlertCircle,
  UserRound, Activity, ScrollText, ExternalLink,
} from "lucide-react";
import { fetchBrokers, fetchRegistrations, fetchHistory, fetchLead, fetchLeadSummary, fetchRetrievalLogs, pauseAI, sendReply } from "@/lib/api";
import { StageBadge, StatusBadge } from "@/components/stage-badge";
import { displayName, initials, cn } from "@/lib/utils";
import { fmtIST } from "@/lib/format";
import type { BrokerRow, ConversationLog, KnowledgeChunk, Lead, LeadSummary, PortfolioMatch, Registration, RetrievalLog } from "@/types";

// How a reply was produced. Every value the backend can set has a plain name here.
const PATH_LABELS: Record<string, { label: string; color: string; hint: string }> = {
  knowledge:      { label: "Knowledge base", color: "bg-cost/10 text-cost",         hint: "Answered from a search of the knowledge base" },
  portfolio:      { label: "Past projects",  color: "bg-chart-4/10 text-chart-4",   hint: "Answered from matching past projects" },
  project_facts:  { label: "Project facts",  color: "bg-accent/10 text-accent",     hint: "Answered from the project record: price, RERA, possession, payment plan, loans" },
  conversational: { label: "Chat",           color: "bg-bg text-muted",             hint: "No lookup needed: small talk, a follow-up, or a request for material" },
  escalation:     { label: "Escalated",      color: "bg-warning/10 text-warning",   hint: "Discount or unit availability: sent to a person and the AI paused" },
  fallback:       { label: "Fallback",       color: "bg-error/10 text-error",       hint: "The search was not confident enough, so the AI handed over and paused" },
  voice_note:     { label: "Voice note",     color: "bg-warning/10 text-warning",   hint: "The buyer sent audio, which the AI cannot read" },
  admin_manual:   { label: "Staff reply",    color: "bg-success/10 text-success",   hint: "Written by a person" },
};

function PathTag({ path }: { path: string | null }) {
  if (!path) return null;
  const cfg = PATH_LABELS[path] ?? {
    label: path.replace(/_/g, " ").replace(/^\w/, c => c.toUpperCase()), color: "bg-bg text-muted", hint: path,
  };
  return (
    <span title={cfg.hint} className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded", cfg.color)}>
      {cfg.label}
    </span>
  );
}

// ── Retrieval detail panel ────────────────────────────────────────────────────

function ChunkCard({ chunk, index }: { chunk: KnowledgeChunk; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const shortText = chunk.text.length > 120 ? chunk.text.slice(0, 120) + "…" : chunk.text;
  return (
    <div className="rounded-lg border border-line bg-cost/10 p-2.5 text-xs">
      <div className="flex items-center justify-between mb-1">
        <span className="inline-flex items-center gap-1 font-medium text-cost">
          <span className="bg-cost/20 text-cost px-1 py-0.5 rounded text-[10px]">{chunk.doc_type}</span>
          {chunk.vertical && <span className="text-cost text-[10px]">{chunk.vertical}</span>}
          chunk {index + 1}
        </span>
        {chunk.text.length > 120 && (
          <button onClick={() => setExpanded(e => !e)} className="text-cost hover:text-cost">
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        )}
      </div>
      <p className="text-ink/70 text-[10px] leading-relaxed whitespace-pre-wrap">
        {expanded ? chunk.text : shortText}
      </p>
    </div>
  );
}

function PortfolioCard({ match }: { match: PortfolioMatch }) {
  return (
    <div className="rounded-lg border border-line bg-chart-4/10 p-2.5 text-xs">
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium text-chart-4 truncate">{match.title}</span>
        <span className={cn(
          "font-mono font-semibold text-[10px] ml-2 flex-shrink-0",
          match.score >= 0.75 ? "text-success" : "text-warning",
        )}>
          {match.score.toFixed(3)}
        </span>
      </div>
      <div className="flex gap-2 text-[10px] text-chart-4">
        {match.config && <span>{match.config}</span>}
        {match.style && <span>· {match.style}</span>}
        {match.budget_bracket && <span>· {match.budget_bracket}</span>}
      </div>
    </div>
  );
}

function RetrievalDetail({ log }: { log: RetrievalLog }) {
  const [open, setOpen] = useState(false);
  const showDetails = ["knowledge", "portfolio", "fallback"].includes(log.path_taken);
  if (!showDetails) return null;

  return (
    <div className="mt-1.5">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1 text-[10px] text-muted hover:text-ink/70 transition"
      >
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {open ? "Hide" : "Show"} retrieval details
      </button>

      {open && (
        <div className="mt-2 rounded-xl border border-line bg-card p-3 space-y-3 shadow-sm text-xs">

          {/* Query */}
          <div>
            <div className="flex items-center gap-1.5 mb-1 text-muted font-medium">
              <Search className="w-3 h-3" /> Query
            </div>
            <p className="text-ink/80 bg-bg rounded-lg px-2.5 py-1.5 font-mono text-[10px]">
              {log.query_original}
            </p>
          </div>

          {/* Confidence */}
          {log.knowledge_top_score != null && (
            <div className="flex items-center gap-3">
              <div>
                <p className="text-[10px] text-muted mb-0.5">Confidence</p>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-20 bg-bg rounded-full overflow-hidden">
                    <div
                      className={cn("h-full rounded-full", log.knowledge_top_score >= 0.8 ? "bg-success" : "bg-error")}
                      style={{ width: `${Math.min(log.knowledge_top_score * 100, 100)}%` }}
                    />
                  </div>
                  <span className={cn("font-mono font-semibold text-[10px]", log.knowledge_top_score >= 0.8 ? "text-success" : "text-error")}>
                    {log.knowledge_top_score.toFixed(3)}
                  </span>
                </div>
              </div>
              {log.confidence_gate_passed === false && (
                <span className="text-[10px] text-error bg-error/10 border border-error/40 px-1.5 py-0.5 rounded">
                  gate failed
                </span>
              )}
              {log.resource_gate_fail && (
                <span className="text-[10px] text-warning bg-warning/10 border border-warning/30 px-1.5 py-0.5 rounded">
                  resource: {log.resource_gate_fail}
                </span>
              )}
            </div>
          )}

          {/* Portfolio matches */}
          {log.portfolio_matches && log.portfolio_matches.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-1.5 text-muted font-medium">
                <LayoutGrid className="w-3 h-3" /> Portfolio matches
              </div>
              <div className="space-y-1.5">
                {log.portfolio_matches.map((m) => (
                  <PortfolioCard key={m.id} match={m} />
                ))}
              </div>
            </div>
          )}

          {/* Knowledge chunks */}
          {log.knowledge_chunks && log.knowledge_chunks.length > 0 && (
            <div>
              <p className="text-[10px] text-muted mb-1.5">
                {log.knowledge_chunks.length} chunk{log.knowledge_chunks.length !== 1 ? "s" : ""} retrieved
              </p>
              <div className="space-y-1.5">
                {log.knowledge_chunks.map((chunk, i) => (
                  <ChunkCard key={i} chunk={chunk} index={i} />
                ))}
              </div>
            </div>
          )}

          {/* Resource selected */}
          {log.resource_candidate_id && (
            <div className="rounded-lg border border-success/30 bg-success/10 p-2.5">
              <div className="flex items-center gap-1.5 mb-1 text-success font-medium">
                <FileText className="w-3 h-3" />
                <span>Resource selected</span>
                <span className="font-mono text-[10px] bg-success/10 text-success px-1.5 py-0.5 rounded ml-1">
                  {log.resource_candidate_id}
                </span>
                {log.resource_attached ? (
                  <span className="text-[10px] text-success ml-auto">✓ attached</span>
                ) : (
                  <span className="text-[10px] text-warning ml-auto">blocked</span>
                )}
              </div>
            </div>
          )}

          {/* Latency */}
          {(log.pinecone_latency_ms != null || log.claude_latency_ms != null || log.total_latency_ms != null) && (
            <div className="flex items-center gap-3 pt-1 border-t border-line">
              <Zap className="w-3 h-3 text-muted" />
              {log.pinecone_latency_ms != null && (
                <span className="text-[10px] text-muted">pinecone <b className="text-ink/70">{log.pinecone_latency_ms}ms</b></span>
              )}
              {log.claude_latency_ms != null && (
                <span className="text-[10px] text-muted">llm <b className="text-ink/70">{log.claude_latency_ms}ms</b></span>
              )}
              {log.total_latency_ms != null && (
                <span className="text-[10px] text-muted">total <b className="text-ink/70">{log.total_latency_ms}ms</b></span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Attachment sent with a reply ──────────────────────────────────────────────

function AttachmentCard({ resource }: { resource: NonNullable<ConversationLog["resource"]> }) {
  const isVideo = resource.type === "youtube" || resource.type === "video";
  const Icon = isVideo ? PlayCircle : FileText;
  const body = (
    <>
      <div className="w-9 h-9 rounded-lg bg-accent/10 text-accent flex items-center justify-center flex-shrink-0">
        <Icon className="w-4 h-4" strokeWidth={1.75} />
      </div>
      <div className="min-w-0 text-left">
        <p className="text-sm font-medium text-ink truncate">{resource.title.replace(/\s[—–]\s/g, ": ")}</p>
        <p className="text-[11px] text-muted">
          {isVideo ? "Video link" : "PDF document"} sent with this reply
        </p>
      </div>
      {resource.url && <ExternalLink className="w-3.5 h-3.5 text-muted flex-shrink-0" strokeWidth={1.75} />}
    </>
  );
  const cls = "mt-1.5 flex items-center gap-3 rounded-xl border border-line bg-card px-3 py-2 max-w-full";
  return resource.url ? (
    <a href={resource.url} target="_blank" rel="noopener noreferrer" className={cn(cls, "hover:border-ink/30")}>
      {body}
    </a>
  ) : (
    <div className={cls}>{body}</div>
  );
}

// ── Message bubble ────────────────────────────────────────────────────────────

function MessageBubble({ msg, retrieval }: { msg: ConversationLog; retrieval?: RetrievalLog }) {
  const time = format(new Date(msg.created_at), "h:mm a");

  if (msg.sender_type === "lead") {
    return (
      <div className="flex items-end gap-2 max-w-[70%]">
        <div className="w-7 h-7 rounded-full bg-line flex items-center justify-center flex-shrink-0 mb-1">
          <User className="w-3.5 h-3.5 text-ink/70" />
        </div>
        <div>
          <div className="bg-card border border-line rounded-2xl rounded-bl-sm px-4 py-2.5 shadow-sm">
            <p className="text-sm text-ink whitespace-pre-wrap">{msg.message_text}</p>
          </div>
          <p className="text-[10px] text-muted mt-1 ml-1">{time}</p>
        </div>
      </div>
    );
  }

  if (msg.sender_type === "ai") {
    return (
      <div className="flex flex-col items-end max-w-[75%] ml-auto">
        <div className="bg-accent rounded-2xl rounded-br-sm px-4 py-2.5 shadow-sm">
          <p className="text-sm text-on-accent whitespace-pre-wrap">{msg.message_text}</p>
        </div>
        {msg.resource && <AttachmentCard resource={msg.resource} />}
        <div className="flex items-center gap-1.5 mt-1 mr-1">
          {msg.path_taken && <PathTag path={msg.path_taken} />}
          {msg.resource && (
            <span
              title={`${msg.resource.title.replace(/\s[—–]\s/g, ": ")} was sent with this reply`}
              className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-accent/10 text-accent"
            >
              Resource sent
            </span>
          )}
          {msg.pinecone_score != null && (
            <span className="text-[10px] text-muted">conf {msg.pinecone_score.toFixed(2)}</span>
          )}
          <p className="text-[10px] text-muted">{time}</p>
          <Bot className="w-3 h-3 text-muted" />
        </div>
        {retrieval && <RetrievalDetail log={retrieval} />}
      </div>
    );
  }

  // admin
  return (
    <div className="flex flex-col items-end max-w-[70%] ml-auto">
      <div className="bg-success rounded-2xl rounded-br-sm px-4 py-2.5 shadow-sm">
        <p className="text-sm text-on-accent whitespace-pre-wrap">{msg.message_text}</p>
      </div>
      <div className="flex items-center gap-1.5 mt-1 mr-1">
        <PathTag path="admin_manual" />
        <p className="text-[10px] text-muted">{time}</p>
      </div>
    </div>
  );
}

// ── Lead info + controls ──────────────────────────────────────────────────────

const BUDGET_LABELS: Record<string, string> = {
  under_5L: "Under 5L",
  "5-10L":  "5–10L",
  "10-20L": "10–20L",
  "20L+":   "20L+",
  // real estate
  under_50L: "Under 50L",
  "50L-1Cr": "50L to 1 Cr",
  "1Cr-2Cr": "1 to 2 Cr",
  "2Cr+":    "2 Cr and above",
  // solar, monthly bill
  under_2k: "Under 2k",
  "2k-5k":  "2k to 5k",
  "5k-10k": "5k to 10k",
  "10k+":   "10k and above",
};

const VERTICAL_LABELS: Record<string, string> = {
  interior:    "Interior Design",
  real_estate: "Real Estate",
};

function LeadInfoPanel({ lead, onPauseToggle }: { lead: Lead; onPauseToggle: (p: boolean) => void }) {
  const [toggling, setToggling] = useState(false);

  async function toggle() {
    setToggling(true);
    try {
      await pauseAI(lead.id, !lead.ai_paused);
      onPauseToggle(!lead.ai_paused);
    } finally {
      setToggling(false);
    }
  }

  const infoRows = [
    { icon: Phone,      label: "Phone",    value: lead.phone },
    { icon: Home,       label: "Config",   value: lead.config ?? "-" },
    { icon: Wallet,     label: "Budget",   value: lead.budget_bracket ? (BUDGET_LABELS[lead.budget_bracket] ?? lead.budget_bracket) : "-" },
    { icon: LayoutGrid, label: "Vertical", value: lead.lead_type ? (VERTICAL_LABELS[lead.lead_type] ?? lead.lead_type) : "-" },
  ];

  return (
    <div className="space-y-4">
      <div className="bg-card rounded-2xl border border-line p-5 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-full bg-accent text-on-accent flex items-center justify-center font-semibold text-sm flex-shrink-0">
            {initials(lead.lead_name, lead.phone)}
          </div>
          <div>
            <p className="font-semibold text-ink">{displayName(lead)}</p>
            <StatusBadge status={lead.lead_status} />
          </div>
        </div>

        <div className="space-y-2.5">
          {infoRows.map(({ icon: Icon, label, value }) => (
            <div key={label} className="flex items-start gap-2.5">
              <Icon className="w-3.5 h-3.5 text-muted mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[10px] text-muted uppercase tracking-wide font-medium">{label}</p>
                <p className="text-sm text-ink/80">{value}</p>
              </div>
            </div>
          ))}
          {lead.scope && (
            <div className="flex items-start gap-2.5">
              <Info className="w-3.5 h-3.5 text-muted mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[10px] text-muted uppercase tracking-wide font-medium">Scope</p>
                <p className="text-sm text-ink/80 capitalize">{lead.scope.replace(/_/g, " ")}</p>
              </div>
            </div>
          )}
          {lead.design_style && (
            <div className="flex items-start gap-2.5">
              <Info className="w-3.5 h-3.5 text-muted mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[10px] text-muted uppercase tracking-wide font-medium">Style</p>
                <p className="text-sm text-ink/80 capitalize">{lead.design_style}</p>
              </div>
            </div>
          )}
        </div>

        <div className="mt-4 pt-4 border-t border-line flex items-center justify-between">
          <div>
            <p className="text-[10px] text-muted uppercase tracking-wide mb-1">Stage</p>
            <StageBadge stage={lead.stage} />
          </div>
          <div className="text-right">
            <p className="text-[10px] text-muted uppercase tracking-wide">Turns</p>
            <p className="text-lg font-semibold text-ink tabular-nums">{lead.turn_count ?? 0}</p>
          </div>
        </div>
        <p className="text-[10px] text-muted mt-3">
          Last active {formatDistanceToNow(new Date(lead.last_active), { addSuffix: true })}
        </p>
      </div>

      {/* AI control */}
      <div className="bg-card rounded-2xl border border-line p-5 shadow-sm">
        <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-3">AI Control</p>
        <div className={cn(
          "flex items-center gap-2 p-3 rounded-xl mb-4 text-sm font-medium",
          lead.ai_paused
            ? "bg-warning/10 text-warning border border-warning/30"
            : "bg-success/10 text-success border border-success/30",
        )}>
          {lead.ai_paused
            ? <><PauseCircle className="w-4 h-4" /> AI paused, you&apos;re in control</>
            : <><Bot className="w-4 h-4" /> AI is handling this conversation</>}
        </div>
        {lead.ai_paused ? (
          <button onClick={toggle} disabled={toggling} className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-success text-on-accent text-sm font-semibold hover:bg-success disabled:opacity-60 transition">
            {toggling ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}
            Resume AI
          </button>
        ) : (
          <button onClick={toggle} disabled={toggling} className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-warning text-on-accent text-sm font-semibold hover:opacity-90 disabled:opacity-60 transition">
            {toggling ? <Loader2 className="w-4 h-4 animate-spin" /> : <PauseCircle className="w-4 h-4" />}
            Take Over
          </button>
        )}
      </div>
    </div>
  );
}

function ReplyBox({ lead, sessionId, onSent }: { lead: Lead; sessionId: string | null; onSent: () => void }) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  async function send() {
    if (!text.trim() || !sessionId || !lead.ai_paused) return;
    setError("");
    setSending(true);
    try {
      await sendReply({ lead_id: lead.id, session_id: sessionId, phone: lead.phone, message_text: text.trim(), admin_name: "Staff" });
      setText("");
      onSent();
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="bg-card rounded-2xl border border-line p-5 shadow-sm">
      <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-3">Send Manual Reply</p>
      {!lead.ai_paused && (
        <p className="text-xs text-warning bg-warning/10 border border-warning/30 rounded-lg px-3 py-2 mb-3">
          Pause AI first to send a manual reply.
        </p>
      )}
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={!lead.ai_paused || sending}
        onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send(); }}
        rows={4}
        placeholder={lead.ai_paused ? "Type your message… (Ctrl+Enter to send)" : "Pause AI to reply manually"}
        className="w-full resize-none rounded-xl border border-line px-3.5 py-2.5 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/20 disabled:bg-bg disabled:cursor-not-allowed transition"
      />
      {error && <p className="text-xs text-error mt-2">{error}</p>}
      <button
        onClick={send}
        disabled={!text.trim() || !lead.ai_paused || sending}
        className="mt-3 w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-accent text-on-accent text-sm font-semibold hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition"
      >
        {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        {sending ? "Sending…" : "Send via WhatsApp"}
      </button>
    </div>
  );
}

// ── AI summary ────────────────────────────────────────────────────────────────

const INTENT: Record<LeadSummary["intent"], { label: string; cls: string }> = {
  hot:  { label: "Hot",  cls: "bg-accent/10 text-accent border-accent/30" },
  warm: { label: "Warm", cls: "bg-chart-3/10 text-ink border-chart-3/40" },
  cold: { label: "Cold", cls: "bg-bg text-muted border-line" },
};

function SummaryTab({ leadId, messageCount }: { leadId: string; messageCount: number }) {
  const { data, error, isLoading, mutate } = useSWR<LeadSummary>(
    ["summary", leadId],
    () => fetchLeadSummary(leadId),
    { revalidateOnFocus: false },
  );
  const [refreshing, setRefreshing] = useState(false);

  async function refresh() {
    setRefreshing(true);
    try {
      await mutate(fetchLeadSummary(leadId, true), { revalidate: false });
    } finally {
      setRefreshing(false);
    }
  }

  const busy = isLoading || refreshing;
  const stale = !!data && !data.empty && messageCount > data.message_count;

  return (
    <div className="max-w-3xl mx-auto p-4 sm:p-6 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-accent" strokeWidth={1.75} />
          <h2 className="text-base font-semibold text-ink">AI summary</h2>
        </div>
        <button
          onClick={refresh}
          disabled={busy}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-line bg-card text-xs font-medium text-ink hover:border-ink/30 disabled:opacity-50"
        >
          <RefreshCw className={cn("w-3.5 h-3.5", busy && "animate-spin")} strokeWidth={1.75} />
          {busy ? "Writing" : "Refresh"}
        </button>
      </div>

      {busy && !data && (
        <div className="bg-card rounded-2xl border border-line p-6 space-y-3">
          <div className="h-5 w-3/4 bg-bg animate-pulse rounded" />
          <div className="h-4 w-full bg-bg animate-pulse rounded" />
          <div className="h-4 w-5/6 bg-bg animate-pulse rounded" />
          <p className="text-xs text-muted pt-2">Reading the conversation</p>
        </div>
      )}

      {error && !data && (
        <div className="bg-card rounded-2xl border border-error/30 p-6 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-error flex-shrink-0 mt-0.5" strokeWidth={1.75} />
          <div>
            <p className="text-sm font-medium text-ink">The summary could not be written</p>
            <p className="text-xs text-muted mt-1">Try again in a moment. The conversation itself is unaffected.</p>
          </div>
        </div>
      )}

      {data?.empty && (
        <div className="bg-card rounded-2xl border border-line p-8 text-center text-sm text-muted">
          There are no messages to summarise yet.
        </div>
      )}

      {data && !data.empty && (
        <>
          {stale && (
            <div className="flex items-center justify-between gap-3 rounded-xl bg-warning/10 border border-warning/30 px-4 py-2.5 text-xs text-warning">
              <span>{messageCount - data.message_count} new message{messageCount - data.message_count === 1 ? "" : "s"} since this summary.</span>
              <button onClick={refresh} className="font-semibold underline">Update</button>
            </div>
          )}

          <div className="bg-card rounded-2xl border border-line p-5 sm:p-6 space-y-5">
            <div className="flex items-start justify-between gap-3">
              <p className="text-lg sm:text-xl font-semibold tracking-[-0.02em] text-ink leading-snug">{data.headline}</p>
              <span className={cn("flex-shrink-0 px-2.5 py-1 rounded-full text-xs font-medium border", INTENT[data.intent].cls)}>
                {INTENT[data.intent].label}
              </span>
            </div>

            <div>
              <p className="label mb-2">What they want</p>
              {data.what_they_want.length === 0 ? (
                <p className="text-sm text-muted">The buyer has not stated a requirement yet.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {data.what_they_want.map(w => (
                    <span key={w} className="px-2.5 py-1 rounded-lg bg-bg border border-line text-sm text-ink">{w}</span>
                  ))}
                </div>
              )}
            </div>

            {data.concerns.length > 0 && (
              <div>
                <p className="label mb-2">Questions and concerns</p>
                <ul className="space-y-1.5">
                  {data.concerns.map(c => (
                    <li key={c} className="flex items-start gap-2 text-sm text-ink/80">
                      <span className="mt-2 w-1 h-1 rounded-full bg-muted flex-shrink-0" />{c}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div>
              <p className="label mb-2">Where it stands</p>
              <p className="text-sm text-ink/80 leading-relaxed">{data.where_it_stands}</p>
            </div>

            <div className="rounded-xl border border-accent/30 bg-accent/10 p-4 flex items-start gap-3">
              <Target className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" strokeWidth={1.75} />
              <div>
                <p className="label !text-accent">Suggested next step</p>
                <p className="text-sm text-ink mt-1">{data.next_action}</p>
              </div>
            </div>
          </div>

          <p className="text-[11px] text-muted">
            Based on {data.message_count} message{data.message_count === 1 ? "" : "s"}, updated{" "}
            {formatDistanceToNow(new Date(data.updated_at), { addSuffix: true })}. Written by AI from this
            conversation only. Check it before you act on it.
          </p>
        </>
      )}
    </div>
  );
}

// ── Where the lead came from ──────────────────────────────────────────────────

function SourceCard({ lead }: { lead: Lead }) {
  const { data: brokers } = useSWR<BrokerRow[]>(
    lead.broker_id ? ["brokers", lead.firm_id] : null,
    () => fetchBrokers(lead.firm_id),
  );
  const broker = brokers?.find(b => b.id === lead.broker_id);

  let title = "Organic or direct";
  let detail: string | null = null;
  const viaNumber = lead.number_label
    ? `Arrived on ${lead.number_label}${lead.owner_name ? `, handled by ${lead.owner_name}` : ""}`
    : null;
  if (lead.broker_id) {
    title = "Channel partner";
    detail = broker ? `${broker.name}${broker.company ? `, ${broker.company}` : ""}` : "Loading";
  } else if (lead.ctwa_source_id) {
    title = "Click-to-WhatsApp ad";
    detail = lead.ctwa_location ?? lead.ctwa_source_id;
  }

  return (
    <div className="bg-card rounded-2xl border border-line p-5 shadow-sm">
      <p className="label mb-3">Source</p>
      <div className="flex items-start gap-2.5">
        <Handshake className="w-4 h-4 text-accent mt-0.5 flex-shrink-0" strokeWidth={1.75} />
        <div>
          <p className="text-sm font-medium text-ink">{title}</p>
          {detail && <p className="text-xs text-muted mt-0.5">{detail}</p>}
          {viaNumber && <p className="text-xs text-ink/70 mt-1">{viaNumber}</p>}
          {lead.broker_id && broker && (
            <p className="mono text-[11px] text-muted mt-1">Link code {broker.code}</p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Registry record for this buyer ─────────────────────────────────────────────

function RegistryRecord({ lead }: { lead: Lead }) {
  const phone10 = lead.phone.replace(/\D/g, "").slice(-10);
  const { data } = useSWR<Registration[]>(
    ["regs-for-lead", lead.firm_id],
    () => fetchRegistrations(lead.firm_id),
  );
  const mine = (data ?? []).filter(r => r.client_phone_full === phone10);

  return (
    <div className="bg-card rounded-2xl border border-line p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <ScrollText className="w-4 h-4 text-accent" strokeWidth={1.75} />
        <p className="label">Registry record</p>
      </div>
      {!data ? (
        <div className="h-10 bg-bg animate-pulse rounded-lg" />
      ) : mine.length === 0 ? (
        <p className="text-sm text-muted">No partner has registered this buyer.</p>
      ) : (
        <ul className="space-y-3">
          {mine.map(r => (
            <li key={r.id} className="text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="mono text-xs text-ink">{r.reference_id}</span>
                <span className={cn(
                  "px-2 py-0.5 rounded-md text-xs font-medium border",
                  r.status === "registered" ? "bg-success/10 text-success border-success/30"
                    : r.status === "duplicate" ? "bg-warning/10 text-warning border-warning/30"
                    : "bg-bg text-muted border-line",
                )}>
                  {r.status === "duplicate" ? "Conflict" : r.status}
                </span>
              </div>
              <p className="text-xs text-muted mt-1">
                {r.broker_name ?? "Unknown number"}{r.project_name ? `, ${r.project_name}` : ""}
              </p>
              <p className="mono text-xs text-ink mt-0.5">{fmtIST(r.registered_at)}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Activity: what the assistant looked up for each reply ─────────────────────

function ActivityTab({ logs }: { logs: RetrievalLog[] | undefined }) {
  if (!logs) return <div className="h-24 bg-bg animate-pulse rounded-2xl" />;
  if (logs.length === 0) {
    return (
      <div className="bg-card rounded-2xl border border-line p-8 text-center text-sm text-muted">
        No lookups yet. Replies from the project record or small talk do not need one.
      </div>
    );
  }
  const sorted = [...logs].sort((a, b) => (b.created_at > a.created_at ? 1 : -1));
  return (
    <div className="space-y-3">
      {sorted.map(l => (
        <div key={l.id} className="bg-card rounded-2xl border border-line p-4 shadow-sm">
          <div className="flex items-center gap-2 flex-wrap">
            <PathTag path={l.path_taken} />
            {l.turn_number != null && <span className="text-[11px] text-muted">Turn {l.turn_number}</span>}
            <span className="mono text-[11px] text-muted ml-auto">{format(new Date(l.created_at), "d MMM, h:mm a")}</span>
          </div>
          <p className="mono text-xs text-ink bg-bg rounded-lg px-2.5 py-1.5 mt-2 break-words">{l.query_original}</p>
          <RetrievalDetail log={l} />
        </div>
      ))}
    </div>
  );
}

// ── Compact AI control for the chat tab ───────────────────────────────────────

function AiControlBar({ lead, onToggle }: { lead: Lead; onToggle: (paused: boolean) => void }) {
  const [busy, setBusy] = useState(false);
  async function toggle() {
    setBusy(true);
    try {
      await pauseAI(lead.id, !lead.ai_paused);
      onToggle(!lead.ai_paused);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className={cn(
      "flex items-center justify-between gap-3 px-4 sm:px-6 py-2.5 border-t text-sm",
      lead.ai_paused ? "bg-warning/10 border-warning/30 text-warning" : "bg-card border-line text-ink/80",
    )}>
      <span className="flex items-center gap-2 min-w-0">
        {lead.ai_paused ? <PauseCircle className="w-4 h-4 flex-shrink-0" /> : <Bot className="w-4 h-4 flex-shrink-0 text-success" />}
        <span className="truncate">{lead.ai_paused ? "AI paused, you are in control" : "AI is handling this conversation"}</span>
      </span>
      <button
        onClick={toggle}
        disabled={busy}
        className="flex-shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent text-on-accent text-xs font-medium hover:bg-accent-hover disabled:opacity-60"
      >
        {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : lead.ai_paused ? <PlayCircle className="w-3.5 h-3.5" /> : <PauseCircle className="w-3.5 h-3.5" />}
        {lead.ai_paused ? "Resume AI" : "Take over"}
      </button>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ConversationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: leadId } = use(params);
  const router = useRouter();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [tab, setTab] = useState<"chat" | "summary" | "details">("chat");
  const [detailTab, setDetailTab] = useState<"lead" | "source" | "activity">("lead");

  const { data: leadData, mutate: reloadLead } = useSWR(
    ["lead", leadId],
    () => fetchLead(leadId),
    { refreshInterval: 10_000 },
  );

  const [lead, setLead] = useState<Lead | null>(null);
  useEffect(() => { if (leadData) setLead(leadData); }, [leadData]);

  const { data: history, mutate: reloadHistory } = useSWR(
    ["history", leadId],
    () => fetchHistory(leadId),
    { refreshInterval: 5_000 },
  );

  const { data: retrievalLogs } = useSWR(
    ["retrieval", leadId],
    () => fetchRetrievalLogs(leadId),
    { refreshInterval: 5_000 },
  );

  const retrievalByTurn = retrievalLogs?.reduce<Record<number, RetrievalLog>>((acc, r) => {
    if (r.turn_number != null) acc[r.turn_number] = r;
    return acc;
  }, {}) ?? {};

  useEffect(() => {
    if (tab === "chat" && scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [history, tab]);

  const sessionId = history?.[0]?.session_id ?? null;

  const handlePauseToggle = useCallback((newPaused: boolean) => {
    if (lead) setLead({ ...lead, ai_paused: newPaused });
    reloadLead();
  }, [lead, reloadLead]);

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Top bar */}
      <div className="flex items-center gap-3 sm:gap-4 px-4 sm:px-6 py-3 sm:py-4 bg-card border-b border-line shadow-sm flex-shrink-0 flex-wrap">
        <button onClick={() => router.back()} className="p-2 rounded-lg hover:bg-bg text-muted transition">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-base font-semibold text-ink truncate">{lead ? displayName(lead) : "Loading…"}</h1>
          <p className="text-xs text-muted">{lead?.phone}</p>
        </div>
        {lead && (
          <div className="flex items-center gap-2">
            <StageBadge stage={lead.stage} />
            {lead.ai_paused ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-warning bg-warning/10 border border-warning/30 px-2.5 py-1 rounded-full">
                <PauseCircle className="w-3 h-3" /> AI Paused
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-success bg-success/10 border border-success/30 px-2.5 py-1 rounded-full">
                <Bot className="w-3 h-3" /> AI Active
              </span>
            )}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 px-4 sm:px-6 bg-card border-b border-line overflow-x-auto flex-shrink-0">
        {([
          ["chat", "Chat", MessageSquare],
          ["summary", "AI summary", Sparkles],
          ["details", "Details", ClipboardList],
        ] as const).map(([id, label, Icon]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={cn(
              "flex items-center gap-2 px-3 sm:px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors whitespace-nowrap flex-shrink-0",
              tab === id ? "border-accent text-accent" : "border-transparent text-muted hover:text-ink",
            )}
          >
            <Icon className="w-4 h-4" strokeWidth={1.75} />
            {label}
            {id === "chat" && history && history.length > 0 && (
              <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded-full bg-bg text-muted">{history.length}</span>
            )}
          </button>
        ))}
      </div>

      {/* Chat */}
      {tab === "chat" && (
        <div className="flex flex-col flex-1 min-h-0">
          <div
            ref={scrollRef}
            className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 space-y-3"
            style={{ backgroundImage: "radial-gradient(circle at 1px 1px, var(--line) 1px, transparent 0)", backgroundSize: "20px 20px" }}
          >
            {!history ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="w-6 h-6 animate-spin text-muted" />
              </div>
            ) : history.length === 0 ? (
              <div className="flex items-center justify-center h-full text-muted text-sm">No messages yet</div>
            ) : (
              history.map((msg, i) => {
                const prev = history[i - 1];
                const showDate = !prev || format(new Date(msg.created_at), "yyyy-MM-dd") !== format(new Date(prev.created_at), "yyyy-MM-dd");
                const retrieval = (msg.sender_type === "ai" && msg.turn_number != null)
                  ? retrievalByTurn[msg.turn_number]
                  : undefined;
                return (
                  <div key={msg.id}>
                    {showDate && (
                      <div className="flex items-center gap-3 my-4">
                        <div className="flex-1 h-px bg-line" />
                        <span className="text-xs text-muted font-medium bg-card px-3 py-1 rounded-full border border-line">
                          {format(new Date(msg.created_at), "d MMM yyyy")}
                        </span>
                        <div className="flex-1 h-px bg-line" />
                      </div>
                    )}
                    <div className={cn("flex", msg.sender_type !== "lead" ? "justify-end" : "justify-start")}>
                      <MessageBubble msg={msg} retrieval={retrieval} />
                    </div>
                  </div>
                );
              })
            )}
          </div>
          {lead && <AiControlBar lead={lead} onToggle={handlePauseToggle} />}
          {lead && lead.ai_paused && (
            <div className="bg-bg border-t border-line p-3 sm:p-4 flex-shrink-0 max-h-[45vh] overflow-y-auto">
              <ReplyBox lead={lead} sessionId={sessionId} onSent={() => reloadHistory()} />
            </div>
          )}
        </div>
      )}

      {/* AI summary */}
      {tab === "summary" && (
        <div className="flex-1 min-h-0 overflow-y-auto">
          <SummaryTab leadId={leadId} messageCount={history?.length ?? 0} />
        </div>
      )}

      {/* Details, split into tabs */}
      {tab === "details" && (
        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className="max-w-xl mx-auto p-4 sm:p-6 space-y-4">
            <div className="flex rounded-xl border border-line bg-card p-1 gap-1">
              {([
                ["lead", "Lead", UserRound],
                ["source", "Source", Handshake],
                ["activity", "Activity", Activity],
              ] as const).map(([id, label, Icon]) => (
                <button
                  key={id}
                  onClick={() => setDetailTab(id)}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    detailTab === id ? "bg-accent text-on-accent" : "text-muted hover:text-ink hover:bg-bg",
                  )}
                >
                  <Icon className="w-4 h-4" strokeWidth={1.75} />
                  {label}
                </button>
              ))}
            </div>

            {!lead ? (
              <div className="space-y-3">
                {[80, 120, 60].map((h, i) => (
                  <div key={i} className="bg-bg animate-pulse rounded-2xl" style={{ height: h }} />
                ))}
              </div>
            ) : detailTab === "lead" ? (
              <LeadInfoPanel lead={lead} onPauseToggle={handlePauseToggle} />
            ) : detailTab === "source" ? (
              <div className="space-y-4">
                <SourceCard lead={lead} />
                <RegistryRecord lead={lead} />
              </div>
            ) : (
              <ActivityTab logs={retrievalLogs} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
