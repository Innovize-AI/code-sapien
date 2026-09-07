"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Mail, Paperclip, RefreshCw, Loader2, Inbox, AlertTriangle, Zap } from "lucide-react";
import { api } from "@/lib/api";
import type { EmailSummary } from "@/lib/types";
import clsx from "clsx";

const CACHE_KEY = "rfq_inbox_emails";
const CACHE_TTL = 2 * 60 * 1000;

function getCached(): EmailSummary[] | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const { ts, data } = JSON.parse(raw);
    if (Date.now() - ts > CACHE_TTL) return null;
    return data;
  } catch { return null; }
}

function setCache(data: EmailSummary[]) {
  try { sessionStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data })); }
  catch { /* ignore */ }
}

const TAG_STYLE: Record<string, string> = {
  RFQ:        "bg-teal-500/10 text-teal-400 border border-teal-500/20",
  Order:      "bg-teal-500/10 text-teal-400 border border-teal-500/20",
  "Follow-up":"bg-amber-500/10 text-amber-400 border border-amber-500/20",
  Complaint:  "bg-red-500/10 text-red-400 border border-red-500/20",
  General:    "bg-brand-elevated text-brand-muted border border-brand-border",
};

export default function InboxPage() {
  const router = useRouter();
  const cached = getCached();
  const [emails, setEmails]   = useState<EmailSummary[]>(cached ?? []);
  const [loading, setLoading] = useState(!cached);
  const [error, setError]     = useState<string | null>(null);
  const [filter, setFilter]   = useState<string>("All");
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const res = await api.listEmails(50);
      setEmails(res.emails);
      setCache(res.emails);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to connect to Gmail");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (!getCached()) load();
  }, [load]);

  const filtered  = filter === "All" ? emails : emails.filter(e => e.tag === filter);
  const tags      = ["All", "RFQ", "Order", "Follow-up", "Complaint", "General"];
  const rfqCount  = emails.filter(e => e.tag === "RFQ").length;

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-serif font-bold text-brand-text tracking-tight">Email Inbox</h1>
          <p className="text-brand-muted text-sm mt-0.5">Incoming emails — RFQs detected and processed automatically</p>
        </div>
        <div className="flex items-center gap-3">
          {rfqCount > 0 && (
            <span className="flex items-center gap-1.5 bg-teal-500/10 text-teal-400 border border-teal-500/20 text-xs font-semibold px-3 py-1.5 rounded-full">
              <Zap size={12} /> {rfqCount} RFQ{rfqCount !== 1 ? "s" : ""} detected
            </span>
          )}
          <button onClick={() => load(true)} disabled={refreshing}
            className="flex items-center gap-1.5 text-sm text-brand-muted hover:text-brand-text border border-brand-border px-3 py-2 rounded-lg hover:bg-brand-elevated transition-colors">
            <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} /> Refresh
          </button>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 bg-brand-card border border-brand-border rounded-lg p-1 mb-5 w-fit">
        {tags.map(tag => (
          <button key={tag} onClick={() => setFilter(tag)}
            className={clsx("px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
              filter === tag
                ? "bg-brand-elevated text-brand-text"
                : "text-brand-muted hover:text-brand-text"
            )}>
            {tag}
            {tag !== "All" && emails.filter(e => e.tag === tag).length > 0 && (
              <span className="ml-1.5 text-xs text-brand-muted">
                {emails.filter(e => e.tag === tag).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 text-brand-muted">
          <Loader2 size={28} className="animate-spin mb-3 text-teal-500" />
          <p className="text-sm">Connecting to Gmail…</p>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-4">
            <AlertTriangle size={22} className="text-red-400" />
          </div>
          <p className="font-semibold text-brand-text mb-1">Gmail connection failed</p>
          <p className="text-brand-muted text-sm max-w-md">{error}</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-brand-muted">
          <Inbox size={32} className="mb-3 opacity-30" />
          <p className="font-medium">No emails found</p>
          {filter !== "All" && <p className="text-sm mt-1">No {filter} emails in your inbox</p>}
        </div>
      ) : (
        <div className="bg-brand-card rounded-2xl border border-brand-border divide-y divide-brand-border overflow-hidden">
          {filtered.map((em) => (
            <div key={em.id}
              onClick={() => router.push(`/inbox/${em.id}`)}
              className={clsx(
                "flex items-start gap-4 px-5 py-4 cursor-pointer hover:bg-brand-elevated transition-colors group",
                em.unread && "bg-teal-500/5"
              )}>
              {/* Avatar */}
              <div className="w-9 h-9 rounded-full bg-brand-elevated border border-brand-border flex items-center justify-center flex-shrink-0 text-brand-text text-sm font-bold">
                {em.from_name.charAt(0).toUpperCase()}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={clsx("text-sm font-semibold truncate", em.unread ? "text-brand-text" : "text-brand-muted")}>
                    {em.from_name}
                  </span>
                  <span className="text-xs text-brand-muted truncate hidden sm:block">{em.from_email}</span>
                  <span className={clsx("ml-auto flex-shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded-full", TAG_STYLE[em.tag] || TAG_STYLE.General)}>
                    {em.tag}
                  </span>
                </div>
                <p className={clsx("text-sm truncate", em.unread ? "text-brand-text font-medium" : "text-brand-muted")}>
                  {em.subject}
                </p>
                {em.preview && (
                  <p className="text-xs text-brand-muted truncate mt-0.5 opacity-60">{em.preview}</p>
                )}
              </div>

              {/* Meta */}
              <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                <span className="text-xs text-brand-muted">{em.date.split(",")[0]}</span>
                <div className="flex items-center gap-1.5">
                  {em.size_kb > 50 && (
                    <Paperclip size={10} className="text-brand-muted" />
                  )}
                  {em.unread && <span className="w-2 h-2 rounded-full bg-teal-500" />}
                </div>
                {em.tag === "RFQ" && (
                  <span className="text-[10px] text-teal-500 font-semibold opacity-0 group-hover:opacity-100 transition-opacity">
                    Process →
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
