"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import MarkdownView from "@/components/MarkdownView";
import {
  ArrowLeft, FileText, Loader2, Zap, CheckCircle2, Clock,
  AlertTriangle, ArrowUpRight, Tag, Paperclip, Package,
  CircleDot, Send, ThumbsUp, ThumbsDown, Download,
  MapPin, User, Calendar, RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";
import type { EmailDetail, RFQDetail } from "@/lib/types";
import { fmt_inr, fmt_pct, fmt_date, downloadPdf } from "@/lib/utils";
import StatusBadge from "@/components/StatusBadge";
import clsx from "clsx";

const TAG_STYLE: Record<string, string> = {
  RFQ:         "bg-teal-500/10 text-teal-400 border border-teal-500/20",
  Order:       "bg-teal-500/10 text-teal-400 border border-teal-500/20",
  "Follow-up": "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  Complaint:   "bg-red-500/10 text-red-400 border border-red-500/20",
  General:     "bg-brand-elevated text-brand-muted border border-brand-border",
};

function initials(name: string) {
  return name.split(" ").filter(Boolean).map(w => w[0]).join("").slice(0, 2).toUpperCase();
}

function Avatar({ name, size = "md" }: { name: string; size?: "sm" | "md" }) {
  const sz = size === "sm" ? "w-6 h-6 text-[10px]" : "w-8 h-8 text-xs";
  return (
    <div className={clsx(sz, "rounded-full bg-brand-elevated border border-brand-border flex items-center justify-center font-bold text-brand-text flex-shrink-0")}>
      {initials(name)}
    </div>
  );
}

function DetailRow({ icon, label, value }: { icon: React.ReactNode; label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 text-brand-muted flex-shrink-0">{icon}</span>
      <div>
        <p className="text-[10px] text-brand-muted uppercase tracking-wider font-medium">{label}</p>
        <p className="text-xs text-brand-text mt-0.5">{value}</p>
      </div>
    </div>
  );
}

export default function EmailRFQPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [email, setEmail]       = useState<EmailDetail | null>(null);
  const [rfq, setRfq]           = useState<RFQDetail | null>(null);
  const [emailLoading, setEmailLoading] = useState(true);
  const [rfqLoading, setRfqLoading]     = useState(false);
  const [processing, setProcessing]     = useState(false);
  const [approving, setApproving]       = useState(false);
  const [actionMsg, setActionMsg]       = useState<string | null>(null);
  const [error, setError]               = useState<string | null>(null);

  const rfqSummary = email?.rfq ?? null;
  const messages   = email?.thread_messages ?? (email ? [email] : []);

  // Load email, then load full RFQ detail
  useEffect(() => {
    api.getEmail(id)
      .then(async (em) => {
        setEmail(em);
        if (em.rfq?.rfq_id) {
          setRfqLoading(true);
          api.detail(em.rfq.rfq_id)
            .then(setRfq)
            .catch(console.error)
            .finally(() => setRfqLoading(false));
        }
      })
      .catch(e => setError(e.message))
      .finally(() => setEmailLoading(false));
  }, [id]);

  // Poll while processing
  useEffect(() => {
    if (rfqSummary?.status !== "processing") return;
    const t = setInterval(async () => {
      const em = await api.getEmail(id).catch(() => null);
      if (!em) return;
      setEmail(em);
      if (em.rfq?.rfq_id) {
        const detail = await api.detail(em.rfq.rfq_id).catch(() => null);
        if (detail) setRfq(detail);
      }
    }, 3000);
    return () => clearInterval(t);
  }, [id, rfqSummary?.status]);

  const handleProcess = async () => {
    setProcessing(true);
    try {
      await api.processEmail(id);
      const em = await api.getEmail(id);
      setEmail(em);
      if (em.rfq?.rfq_id) {
        const detail = await api.detail(em.rfq.rfq_id).catch(() => null);
        if (detail) setRfq(detail);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Processing failed");
    } finally { setProcessing(false); }
  };

  const handleApprove = async () => {
    if (!rfqSummary) return;
    setApproving(true);
    setActionMsg(null);
    try {
      const res = await api.approve(rfqSummary.rfq_id);
      setActionMsg(res.email_sent ? "Quote dispatched to buyer." : "Approved — configure email to dispatch automatically.");
      const em = await api.getEmail(id);
      setEmail(em);
      if (em.rfq?.rfq_id) {
        const detail = await api.detail(em.rfq.rfq_id).catch(() => null);
        if (detail) setRfq(detail);
      }
    } catch (e: unknown) {
      setActionMsg(e instanceof Error ? e.message : "Approval failed");
    } finally { setApproving(false); }
  };

  const handleReject = async () => {
    if (!rfqSummary || !confirm("Reject this RFQ?")) return;
    try {
      await api.reject(rfqSummary.rfq_id);
      const em = await api.getEmail(id);
      setEmail(em);
      if (em.rfq?.rfq_id) {
        const detail = await api.detail(em.rfq.rfq_id).catch(() => null);
        if (detail) setRfq(detail);
      }
    } catch (e: unknown) {
      setActionMsg(e instanceof Error ? e.message : "Rejection failed");
    }
  };

  // ── Loading / error states ────────────────────────────────────────────────
  if (emailLoading) return (
    <div className="flex items-center justify-center h-64 gap-3 text-brand-muted">
      <Loader2 size={18} className="animate-spin text-teal-500" />
      <span className="text-sm">Loading…</span>
    </div>
  );

  if (error || !email) return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <AlertTriangle size={28} className="text-red-400 mb-3" />
      <p className="font-semibold text-brand-text">{error || "Email not found"}</p>
      <Link href="/inbox" className="mt-4 text-sm text-teal-500 hover:text-teal-400 transition-colors">← Back to inbox</Link>
    </div>
  );

  const hasPricing  = (rfq?.line_pricing?.length ?? 0) > 0;
  const hasItems    = (rfq?.line_items?.length ?? 0) > 0;
  const pricingMap  = Object.fromEntries((rfq?.line_pricing ?? []).map(p => [p.line_item_index, p]));
  const draftQuote  = rfq?.draft_quote ?? rfqSummary?.draft_quote ?? null;
  const isPending   = rfqSummary?.status === "pending_review";
  const isDispatched = rfqSummary?.status === "dispatched";

  return (
    <div className="max-w-7xl mx-auto space-y-5">

      {/* Breadcrumb */}
      <Link href="/inbox" className="inline-flex items-center gap-1.5 text-sm text-brand-muted hover:text-teal-400 transition-colors">
        <ArrowLeft size={14} /> Inbox
      </Link>

      {/* ── Subject header ── */}
      <div className="bg-brand-card border border-brand-border rounded-2xl px-7 py-5">
        <div className="flex items-start justify-between gap-6">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <span className={clsx("inline-flex items-center gap-1 text-[10px] font-semibold px-2.5 py-1 rounded-full tracking-wide uppercase flex-shrink-0",
                TAG_STYLE[email.tag] ?? TAG_STYLE.General)}>
                <Tag size={9} /> {email.tag}
              </span>
              {rfqSummary && <StatusBadge status={rfqSummary.status} />}
            </div>
            <h1 className="text-xl font-serif font-bold text-brand-text leading-snug">{email.subject}</h1>
            <div className="flex items-center gap-4 mt-2.5 text-xs text-brand-muted flex-wrap">
              <div className="flex items-center gap-2">
                <Avatar name={email.from_name || email.from_email} size="sm" />
                <span className="font-medium text-brand-text">{email.from_name || email.from_email}</span>
                {email.from_name && <span>{email.from_email}</span>}
              </div>
              <span className="flex items-center gap-1"><Clock size={11} /> {email.date}</span>
              {messages.length > 1 && (
                <span className="flex items-center gap-1"><CircleDot size={11} /> {messages.length} messages</span>
              )}
            </div>
          </div>

          {/* Value summary in header */}
          {rfqSummary?.total != null && (
            <div className="text-right flex-shrink-0">
              <p className="text-[10px] text-brand-muted uppercase tracking-wider font-medium mb-1">Quoted Value</p>
              <p className="text-2xl font-bold text-brand-text tabular-nums">{fmt_inr(rfqSummary.total)}</p>
              {rfq?.pricing_confidence != null && (
                <p className={clsx("text-xs font-medium mt-0.5",
                  rfq.pricing_confidence >= 0.8 ? "text-teal-400"
                  : rfq.pricing_confidence >= 0.5 ? "text-amber-400" : "text-red-400")}>
                  {fmt_pct(rfq.pricing_confidence)} confidence
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Two-column body ── */}
      <div className="flex gap-5 items-start">

        {/* LEFT: email thread */}
        <div className="flex-1 min-w-0">
          {messages.map((msg, index) => {
            const isLast = index === messages.length - 1;
            return (
              <div key={msg.id || index} className="flex gap-4">
                <div className="flex flex-col items-center flex-shrink-0 w-8">
                  <Avatar name={msg.from_name || msg.from_email} />
                  {!isLast && <div className="flex-1 w-px bg-brand-border mt-2" />}
                </div>
                <div className={clsx(
                  "flex-1 min-w-0 rounded-2xl border overflow-hidden mb-4",
                  isLast ? "border-brand-border bg-brand-card" : "border-brand-border bg-brand-card opacity-55"
                )}>
                  <div className="flex items-center justify-between px-5 py-3 border-b border-brand-border">
                    <div className="flex items-baseline gap-2 min-w-0">
                      <span className="text-sm font-semibold text-brand-text">{msg.from_name || msg.from_email}</span>
                      {msg.from_name && <span className="text-xs text-brand-muted truncate">{msg.from_email}</span>}
                    </div>
                    <span className="text-xs text-brand-muted flex-shrink-0 ml-4">{msg.date}</span>
                  </div>
                  <pre className="px-5 py-5 whitespace-pre-wrap text-sm text-brand-text font-sans leading-7 opacity-90">
                    {msg.body || "(No content)"}
                  </pre>
                  {msg.attachments && msg.attachments.length > 0 && (
                    <div className="px-5 pb-4 pt-1 border-t border-brand-border">
                      <p className="text-[10px] text-brand-muted uppercase tracking-wider font-semibold mb-2">Attachments</p>
                      <div className="grid grid-cols-2 gap-2">
                        {msg.attachments.map((att, i) => (
                          <div key={i} className="flex items-center gap-2 p-2.5 bg-brand-elevated rounded-xl border border-brand-border">
                            <FileText size={13} className="text-brand-muted flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-medium text-brand-text truncate">{att.filename}</p>
                              <p className="text-[10px] text-brand-muted">{att.size_kb} KB</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Email-level attachments */}
          {email.attachments.length > 0 && (
            <div className="ml-12 rounded-2xl border border-brand-border bg-brand-card p-4 mb-4">
              <p className="text-[10px] font-semibold text-brand-muted uppercase tracking-wider mb-2.5">Files · {email.attachments.length}</p>
              <div className="grid grid-cols-2 gap-2">
                {email.attachments.map((att, i) => (
                  <div key={i} className="flex items-center gap-2.5 p-2.5 bg-brand-elevated rounded-xl border border-brand-border">
                    <FileText size={13} className="text-brand-muted flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-brand-text truncate">{att.filename}</p>
                      <p className="text-[10px] text-brand-muted">{att.size_kb} KB</p>
                    </div>
                    <Paperclip size={11} className="text-brand-muted flex-shrink-0" />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT: RFQ panel */}
        <div className="w-[360px] flex-shrink-0 sticky top-6 space-y-3">

          {rfqSummary ? (
            <>
              {/* ── Actions card ── */}
              <div className={clsx("rounded-2xl border overflow-hidden",
                isPending ? "border-amber-500/20 bg-brand-card"
                : isDispatched ? "border-teal-500/20 bg-brand-card"
                : "border-brand-border bg-brand-card")}>

                {/* Status strip */}
                <div className={clsx("px-5 py-3 border-b flex items-center justify-between",
                  isPending ? "bg-amber-500/5 border-amber-500/20"
                  : isDispatched ? "bg-teal-500/5 border-teal-500/20"
                  : rfqSummary.status === "processing" ? "bg-blue-500/5 border-blue-500/20"
                  : "bg-brand-elevated border-brand-border")}>
                  <div className="flex items-center gap-2">
                    {rfqSummary.status === "processing"
                      ? <Loader2 size={13} className="animate-spin text-blue-400" />
                      : rfqSummary.status === "dispatched"
                      ? <CheckCircle2 size={13} className="text-teal-400" />
                      : rfqSummary.status === "pending_review"
                      ? <AlertTriangle size={13} className="text-amber-400" />
                      : <RefreshCw size={13} className="text-brand-muted" />}
                    <StatusBadge status={rfqSummary.status} />
                  </div>
                  <button onClick={() => router.push(`/rfqs/${rfqSummary.rfq_id}`)}
                    className="text-[10px] text-brand-muted hover:text-teal-400 flex items-center gap-1 transition-colors">
                    Full view <ArrowUpRight size={10} />
                  </button>
                </div>

                <div className="p-5 space-y-4">
                  {/* Quoted value */}
                  {rfqSummary.total != null ? (
                    <div>
                      <p className="text-[10px] text-brand-muted uppercase tracking-wider font-medium mb-1">Quoted Value</p>
                      <p className="text-3xl font-bold text-brand-text tabular-nums">{fmt_inr(rfqSummary.total)}</p>
                      {rfq?.pricing_confidence != null && (
                        <div className="flex items-center gap-2 mt-1.5">
                          <div className="flex-1 h-1 bg-brand-elevated rounded-full overflow-hidden">
                            <div className={clsx("h-full rounded-full transition-all",
                              rfq.pricing_confidence >= 0.8 ? "bg-teal-400"
                              : rfq.pricing_confidence >= 0.5 ? "bg-amber-400" : "bg-red-400")}
                              style={{ width: `${rfq.pricing_confidence * 100}%` }} />
                          </div>
                          <span className={clsx("text-[10px] font-semibold tabular-nums",
                            rfq.pricing_confidence >= 0.8 ? "text-teal-400"
                            : rfq.pricing_confidence >= 0.5 ? "text-amber-400" : "text-red-400")}>
                            {fmt_pct(rfq.pricing_confidence)}
                          </span>
                        </div>
                      )}
                    </div>
                  ) : rfqSummary.status === "processing" ? (
                    <p className="text-sm text-brand-muted">Calculating quote…</p>
                  ) : null}

                  {/* Action buttons */}
                  {isPending && (
                    <div className="space-y-2">
                      <button onClick={handleApprove} disabled={approving}
                        className="w-full flex items-center justify-center gap-2 bg-teal-500 hover:bg-teal-400 disabled:bg-teal-500/30 disabled:text-teal-700 text-black text-sm font-semibold py-2.5 rounded-xl transition-colors">
                        {approving ? <Loader2 size={14} className="animate-spin" /> : <ThumbsUp size={14} />}
                        {approving ? "Sending…" : "Approve & Send Quote"}
                      </button>
                      <div className="flex gap-2">
                        <button onClick={handleReject}
                          className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl border border-brand-border text-xs font-semibold text-brand-muted hover:border-red-500/30 hover:text-red-400 transition-colors">
                          <ThumbsDown size={12} /> Reject
                        </button>
                        <button onClick={() => downloadPdf(rfqSummary.rfq_id)}
                          className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl border border-brand-border text-xs font-semibold text-brand-muted hover:bg-brand-elevated hover:text-brand-text transition-colors">
                          <Download size={12} /> PDF
                        </button>
                      </div>
                    </div>
                  )}
                  {isDispatched && (
                    <button onClick={() => downloadPdf(rfqSummary.rfq_id)}
                      className="w-full flex items-center justify-center gap-2 border border-brand-border text-xs font-semibold text-brand-muted hover:bg-brand-elevated hover:text-brand-text py-2.5 rounded-xl transition-colors">
                      <Download size={13} /> Download PDF
                    </button>
                  )}
                  {actionMsg && (
                    <p className="text-xs text-brand-muted bg-brand-elevated rounded-xl px-3 py-2">{actionMsg}</p>
                  )}
                </div>
              </div>

              {/* ── Buyer details ── */}
              {rfqLoading ? (
                <div className="rounded-2xl border border-brand-border bg-brand-card p-5 flex items-center gap-2 text-brand-muted text-sm">
                  <Loader2 size={14} className="animate-spin text-teal-500" /> Loading details…
                </div>
              ) : rfq && (
                <div className="rounded-2xl border border-brand-border bg-brand-card p-5 space-y-3">
                  <p className="text-[10px] font-semibold text-brand-muted uppercase tracking-wider">Buyer</p>
                  <DetailRow icon={<User size={12} />}     label="Company"  value={rfq.buyer_name} />
                  <DetailRow icon={<Send size={12} />}     label="Contact"  value={rfq.buyer_contact ?? rfq.sender} />
                  <DetailRow icon={<MapPin size={12} />}   label="Delivery" value={rfq.delivery_location} />
                  <DetailRow icon={<Calendar size={12} />} label="Required" value={rfq.rfq_deadline} />
                  <DetailRow icon={<Clock size={12} />}    label="Received" value={fmt_date(rfq.created_at)} />
                </div>
              )}

              {/* ── Line items ── */}
              {rfq && hasItems && (
                <div className="rounded-2xl border border-brand-border bg-brand-card overflow-hidden">
                  <div className="px-5 py-3 border-b border-brand-border flex items-center justify-between">
                    <p className="text-[10px] font-semibold text-brand-muted uppercase tracking-wider">
                      Line Items · {rfq.line_items!.length}
                    </p>
                    {rfq.urgency && (
                      <span className={clsx("text-[10px] font-semibold px-2 py-0.5 rounded-full border capitalize",
                        rfq.urgency === "critical" ? "bg-red-500/10 text-red-400 border-red-500/20"
                        : rfq.urgency === "rush" ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                        : "bg-brand-elevated text-brand-muted border-brand-border")}>
                        {rfq.urgency}
                      </span>
                    )}
                  </div>
                  <div className="divide-y divide-brand-border">
                    {rfq.line_items!.map((item, i) => {
                      const p = pricingMap[i];
                      const unfulfillable = rfq.unfulfillable_items?.includes(i);
                      return (
                        <div key={i} className={clsx("px-5 py-3 flex items-start gap-3", unfulfillable && "opacity-40")}>
                          <span className={clsx("mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0",
                            unfulfillable ? "bg-red-400" : p ? "bg-teal-400" : "bg-brand-muted")} />
                          <div className="flex-1 min-w-0">
                            <p className="text-xs text-brand-text leading-snug">{item.description}</p>
                            <p className="text-[10px] text-brand-muted mt-0.5">
                              {item.quantity ?? "?"} {item.unit ?? ""}
                              {p?.discount_pct ? ` · -${Math.round(p.discount_pct * 100)}%` : ""}
                            </p>
                          </div>
                          <p className="text-xs font-semibold text-brand-text tabular-nums flex-shrink-0">
                            {p ? fmt_inr(p.subtotal) : "—"}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                  {hasPricing && rfqSummary.total != null && (
                    <div className="px-5 py-3 border-t border-brand-border bg-brand-elevated flex items-center justify-between">
                      <p className="text-xs font-semibold text-brand-text">Total</p>
                      <p className="text-sm font-bold text-brand-text tabular-nums">{fmt_inr(rfqSummary.total)}</p>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            /* ── No RFQ yet ── */
            <div className="rounded-2xl border border-brand-border bg-brand-card overflow-hidden">
              <div className="px-5 pt-5 pb-4">
                <div className="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center mb-3">
                  <Zap size={18} className="text-teal-400" />
                </div>
                <p className="text-sm font-semibold text-brand-text mb-1">Run RFQ Agent</p>
                <p className="text-xs text-brand-muted leading-relaxed">
                  Extract line items, match your catalog, and generate a quotation from this email.
                </p>
              </div>
              <div className="px-5 pb-5">
                <button onClick={handleProcess} disabled={processing}
                  className="w-full flex items-center justify-center gap-2 bg-teal-500 hover:bg-teal-400 disabled:bg-teal-500/30 disabled:text-teal-700 text-black text-sm font-semibold py-2.5 rounded-xl transition-colors">
                  {processing ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                  {processing ? "Running…" : "Run Agent"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Draft quotation ── */}
      {draftQuote && (
        <div className="rounded-2xl border border-brand-border bg-brand-card overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-brand-border">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center flex-shrink-0">
                <Send size={14} className="text-teal-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-brand-text">Draft Quotation Email</p>
                <p className="text-xs text-brand-muted">To: {email.from_email}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isDispatched ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/20 text-teal-400 text-xs font-semibold">
                  <CheckCircle2 size={11} /> Sent
                </span>
              ) : isPending ? (
                <>
                  <button onClick={handleReject}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-brand-border text-xs font-semibold text-brand-muted hover:border-red-500/30 hover:text-red-400 transition-colors">
                    <ThumbsDown size={12} /> Reject
                  </button>
                  <button onClick={handleApprove} disabled={approving}
                    className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:bg-teal-500/30 text-black text-xs font-semibold transition-colors">
                    {approving ? <Loader2 size={12} className="animate-spin" /> : <ThumbsUp size={12} />}
                    {approving ? "Sending…" : "Approve & Send"}
                  </button>
                </>
              ) : null}
              <button onClick={() => rfqSummary && downloadPdf(rfqSummary.rfq_id)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-brand-border text-xs font-semibold text-brand-muted hover:bg-brand-elevated hover:text-brand-text transition-colors">
                <Download size={12} /> PDF
              </button>
            </div>
          </div>
          <MarkdownView className="px-7 py-6 max-h-[520px] overflow-y-auto">
            {draftQuote}
          </MarkdownView>
        </div>
      )}

    </div>
  );
}
