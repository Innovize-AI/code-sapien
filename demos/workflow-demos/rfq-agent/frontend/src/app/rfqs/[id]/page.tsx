"use client";
import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft, Package, Truck, MapPin, User, Mail, Calendar,
  AlertTriangle, CheckCircle2, Clock, Send, Loader2, ThumbsUp,
  ThumbsDown, Download, ExternalLink, FileText, ChevronRight,
} from "lucide-react";
import StatusBadge from "@/components/StatusBadge";
import QuoteCard from "@/components/QuoteCard";
import { api } from "@/lib/api";
import type { RFQDetail } from "@/lib/types";
import { fmt_inr, fmt_pct, fmt_date, TRUCK_LABELS, downloadPdf } from "@/lib/utils";
import clsx from "clsx";

function InfoRow({ icon, label, value }: { icon: ReactNode; label: string; value: ReactNode }) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 text-brand-muted flex-shrink-0">{icon}</span>
      <div className="min-w-0">
        <p className="text-[10px] text-brand-muted uppercase tracking-wider font-medium">{label}</p>
        <div className="text-sm text-brand-text mt-0.5">{value}</div>
      </div>
    </div>
  );
}

export default function RFQDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [rfq, setRfq] = useState<RFQDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<"approve" | "reject" | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  useEffect(() => {
    api.detail(id)
      .then((data) => {
        // Unified view lives at inbox/[email_id] — redirect there if source email exists
        if (data.email_id) {
          router.replace(`/inbox/${data.email_id}`);
          return;
        }
        setRfq(data);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message ?? "Not found");
        setLoading(false);
      });
  }, [id, router]);

  const handleApprove = async () => {
    setActionLoading("approve");
    try {
      const res = await api.approve(id);
      setRfq(prev => prev ? { ...prev, status: "dispatched" } : prev);
      setActionMsg(res.email_sent
        ? "Quotation approved and dispatched via email."
        : "Approved. Email not configured — mark as sent manually.");
    } catch (e: unknown) {
      setActionMsg(e instanceof Error ? e.message : "Approval failed");
    } finally { setActionLoading(null); }
  };

  const handleReject = async () => {
    if (!confirm("Reject this RFQ?")) return;
    setActionLoading("reject");
    try {
      await api.reject(id);
      setRfq(prev => prev ? { ...prev, status: "rejected" } : prev);
      setActionMsg("RFQ rejected.");
    } catch (e: unknown) {
      setActionMsg(e instanceof Error ? e.message : "Rejection failed");
    } finally { setActionLoading(null); }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-brand-muted gap-3">
      <Loader2 size={20} className="animate-spin text-teal-500" /> Loading…
    </div>
  );

  if (error || !rfq) return (
    <div className="max-w-5xl mx-auto">
      <Link href="/rfqs" className="flex items-center gap-1 text-sm text-brand-muted hover:text-teal-400 mb-6 transition-colors">
        <ArrowLeft size={14} /> RFQs
      </Link>
      <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-10 text-center">
        <AlertTriangle size={28} className="mx-auto text-red-400 mb-3" />
        <p className="font-semibold text-brand-text mb-1">RFQ not found</p>
        <p className="text-sm text-red-400">{error}</p>
      </div>
    </div>
  );

  const isFreight = rfq.rfq_type === "freight";
  const isPendingReview = rfq.status === "pending_review";

  return (
    <div className="max-w-5xl mx-auto space-y-4">

      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-sm text-brand-muted">
        <Link href="/rfqs" className="hover:text-teal-400 flex items-center gap-1 transition-colors">
          <ArrowLeft size={13} /> RFQs
        </Link>
        <ChevronRight size={13} />
        <span className="font-mono text-xs text-brand-text">{rfq.rfq_id.slice(0, 8).toUpperCase()}</span>
        {rfq.email_id && (
          <>
            <ChevronRight size={13} />
            <Link href={`/inbox/${rfq.email_id}`}
              className="flex items-center gap-1 text-teal-500 hover:text-teal-400 transition-colors font-medium">
              <Mail size={12} /> Source Email
            </Link>
          </>
        )}
      </div>

      {/* Header card */}
      <div className="bg-brand-card rounded-2xl border border-brand-border p-6">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className={clsx("w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0",
                isFreight ? "bg-amber-500/10 border border-amber-500/20" : "bg-teal-500/10 border border-teal-500/20")}>
                {isFreight
                  ? <Truck size={19} className="text-amber-400" />
                  : <Package size={19} className="text-teal-400" />}
              </div>
              <div>
                <h1 className="text-xl font-serif font-bold text-brand-text leading-tight">
                  {rfq.buyer_name ?? rfq.subject ?? "RFQ"}
                </h1>
                <p className="text-sm text-brand-muted">{rfq.sender}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              <StatusBadge status={rfq.status} />
              {rfq.urgency && (
                <span className={clsx("px-2.5 py-0.5 rounded-full text-[10px] font-semibold capitalize border",
                  rfq.urgency === "critical" ? "bg-red-500/10 text-red-400 border-red-500/20"
                    : rfq.urgency === "rush" ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                    : "bg-brand-elevated text-brand-muted border-brand-border")}>
                  {rfq.urgency}
                </span>
              )}
              {rfq.category && (
                <span className="bg-brand-elevated text-brand-muted border border-brand-border px-2.5 py-0.5 rounded-full text-[10px] font-medium capitalize">
                  {rfq.category.replace(/_/g, " ")}
                </span>
              )}
            </div>
          </div>

          <div className="text-right">
            <p className="text-[10px] text-brand-muted mb-1 uppercase tracking-wider font-medium">Total Value</p>
            <p className="text-3xl font-bold text-brand-text">{fmt_inr(rfq.total)}</p>
            {rfq.pricing_confidence != null && (
              <p className={clsx("text-sm font-medium mt-1",
                rfq.pricing_confidence >= 0.8 ? "text-teal-400"
                  : rfq.pricing_confidence >= 0.5 ? "text-amber-400" : "text-red-400")}>
                {fmt_pct(rfq.pricing_confidence)} confidence
              </p>
            )}
          </div>
        </div>

        {/* Source email strip */}
        {rfq.email_id && (
          <Link href={`/inbox/${rfq.email_id}`}
            className="mt-4 flex items-center gap-2.5 px-4 py-2.5 bg-teal-500/5 hover:bg-teal-500/10 rounded-xl border border-teal-500/20 transition-colors group">
            <Mail size={14} className="text-teal-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-teal-400">Source Email</p>
              {rfq.subject && <p className="text-xs text-brand-muted truncate">{rfq.subject}</p>}
            </div>
            <ExternalLink size={13} className="text-teal-500 opacity-50 group-hover:opacity-100 flex-shrink-0 transition-opacity" />
          </Link>
        )}
      </div>

      {/* Pending review */}
      {isPendingReview && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-5">
          <div className="flex items-start gap-3 mb-4">
            <AlertTriangle size={18} className="text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-brand-text">Manual Review Required</p>
              <p className="text-sm text-brand-muted mt-0.5">
                {rfq.review_notes ?? "This RFQ has been flagged for review before dispatch."}
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={handleApprove} disabled={!!actionLoading}
              className="flex items-center gap-2 bg-teal-500 hover:bg-teal-400 disabled:bg-teal-800 disabled:text-teal-600 text-black text-sm font-semibold px-5 py-2.5 rounded-xl transition-colors">
              {actionLoading === "approve" ? <Loader2 size={15} className="animate-spin" /> : <ThumbsUp size={15} />}
              Approve & Dispatch
            </button>
            <button onClick={handleReject} disabled={!!actionLoading}
              className="flex items-center gap-2 bg-brand-elevated hover:bg-red-500/10 border border-brand-border hover:border-red-500/20 text-brand-muted hover:text-red-400 text-sm font-semibold px-5 py-2.5 rounded-xl transition-colors">
              {actionLoading === "reject" ? <Loader2 size={15} className="animate-spin" /> : <ThumbsDown size={15} />}
              Reject
            </button>
            {rfq.draft_quote && (
              <button onClick={() => downloadPdf(rfq.rfq_id)}
                className="flex items-center gap-2 bg-brand-elevated border border-brand-border text-brand-muted hover:text-brand-text text-sm font-medium px-5 py-2.5 rounded-xl transition-colors ml-auto">
                <Download size={15} /> Download PDF
              </button>
            )}
          </div>
          {actionMsg && (
            <p className="mt-3 text-sm text-brand-text bg-brand-card border border-brand-border rounded-xl px-4 py-2.5">{actionMsg}</p>
          )}
        </div>
      )}

      {/* Dispatched */}
      {rfq.status === "dispatched" && (
        <div className="bg-teal-500/10 border border-teal-500/20 rounded-2xl px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 size={18} className="text-teal-400" />
            <div>
              <p className="text-sm font-semibold text-brand-text">Quotation Dispatched</p>
              <p className="text-xs text-brand-muted">Sent to {rfq.sender}</p>
            </div>
          </div>
          <button onClick={() => downloadPdf(rfq.rfq_id)}
            className="flex items-center gap-1.5 text-xs text-teal-400 font-semibold bg-teal-500/10 border border-teal-500/20 hover:bg-teal-500/20 px-3 py-1.5 rounded-lg transition-colors">
            <Download size={13} /> PDF
          </button>
        </div>
      )}

      {actionMsg && rfq.status !== "pending_review" && (
        <div className="bg-brand-card border border-brand-border rounded-xl px-4 py-3 text-sm text-brand-text">{actionMsg}</div>
      )}

      {/* Info + line items */}
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-1 bg-brand-card rounded-2xl border border-brand-border p-5 space-y-4">
          <p className="text-[10px] font-semibold text-brand-muted uppercase tracking-wider">Details</p>
          <InfoRow icon={<User size={13} />}     label="Buyer"     value={rfq.buyer_name} />
          <InfoRow icon={<Mail size={13} />}     label="Contact"   value={rfq.buyer_contact ?? rfq.sender} />
          <InfoRow icon={<MapPin size={13} />}   label="Delivery"  value={rfq.delivery_location} />
          <InfoRow icon={<Calendar size={13} />} label="Deadline"  value={rfq.rfq_deadline} />
          <InfoRow icon={<Clock size={13} />}    label="Received"  value={fmt_date(rfq.created_at)} />
          {rfq.dispatched_at && (
            <InfoRow icon={<Send size={13} />}   label="Dispatched" value={fmt_date(rfq.dispatched_at)} />
          )}
        </div>

        <div className="col-span-2 bg-brand-card rounded-2xl border border-brand-border p-5">
          {isFreight ? (
            <>
              <p className="text-[10px] font-semibold text-brand-muted uppercase tracking-wider mb-4">Freight Details</p>
              <div className="grid grid-cols-2 gap-3">
                {([
                  { label: "Origin",        value: rfq.freight_origin },
                  { label: "Destination",   value: rfq.freight_destination },
                  { label: "Cargo",         value: rfq.freight_cargo_desc },
                  { label: "Weight",        value: rfq.freight_weight_kg != null ? `${rfq.freight_weight_kg.toLocaleString()} kg` : null },
                  { label: "Truck Type",    value: rfq.freight_truck_type ? (TRUCK_LABELS[rfq.freight_truck_type] ?? rfq.freight_truck_type) : null },
                  { label: "Est. Distance", value: rfq.freight_distance_km != null ? `~${rfq.freight_distance_km.toLocaleString()} km` : null },
                ] as { label: string; value: string | null | undefined }[]).map(({ label, value }) => value ? (
                  <div key={label} className="bg-brand-elevated rounded-xl p-3 border border-brand-border">
                    <p className="text-[10px] text-brand-muted uppercase tracking-wider mb-1 font-medium">{label}</p>
                    <p className="text-sm font-semibold text-brand-text">{value}</p>
                  </div>
                ) : null)}
              </div>
              {rfq.freight_quote_amount != null && (
                <div className="mt-4 bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex items-center justify-between">
                  <span className="text-sm font-semibold text-amber-400">Freight Quote</span>
                  <span className="text-2xl font-bold text-brand-text">{fmt_inr(rfq.freight_quote_amount)}</span>
                </div>
              )}
            </>
          ) : (
            <>
              <p className="text-[10px] font-semibold text-brand-muted uppercase tracking-wider mb-4">
                Line Items ({rfq.line_items?.length ?? 0})
              </p>
              {(rfq.line_items?.length ?? 0) === 0 ? (
                <div className="py-10 text-center">
                  <FileText size={28} className="mx-auto text-brand-border mb-2" />
                  <p className="text-sm text-brand-muted">No line items extracted</p>
                </div>
              ) : (
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-brand-border">
                      {["Description", "Qty", "Unit Price", "Disc.", "Subtotal"].map(h => (
                        <th key={h} className={clsx(
                          "pb-2.5 text-[10px] text-brand-muted uppercase tracking-wider font-semibold",
                          h === "Description" ? "text-left" : "text-right"
                        )}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rfq.line_items!.map((item, i) => {
                      const p = rfq.line_pricing?.find(lp => lp.line_item_index === i);
                      const unf = rfq.unfulfillable_items?.includes(i);
                      return (
                        <tr key={i} className={clsx("border-b border-brand-border last:border-0", unf && "opacity-40")}>
                          <td className="py-2.5 pr-3 text-brand-text">
                            <span className={clsx("inline-block w-1.5 h-1.5 rounded-full mr-1.5 mb-0.5",
                              unf ? "bg-red-400" : "bg-teal-400")} />
                            {item.description}
                          </td>
                          <td className="py-2.5 text-right text-brand-muted">{item.quantity ?? "—"} {item.unit ?? ""}</td>
                          <td className="py-2.5 text-right text-brand-muted">{p ? fmt_inr(p.unit_price) : "—"}</td>
                          <td className="py-2.5 text-right text-teal-400">
                            {p?.discount_pct ? `-${Math.round(p.discount_pct * 100)}%` : "—"}
                          </td>
                          <td className="py-2.5 text-right font-bold text-brand-text">{p ? fmt_inr(p.subtotal) : "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    <tr className="border-t-2 border-brand-border">
                      <td colSpan={4} className="pt-3 text-right text-brand-muted font-medium pr-3">Total</td>
                      <td className="pt-3 text-right font-bold text-brand-text">{fmt_inr(rfq.total)}</td>
                    </tr>
                  </tfoot>
                </table>
              )}
            </>
          )}
        </div>
      </div>

      {/* Quote card */}
      {(rfq.draft_quote || (rfq.line_pricing && rfq.line_pricing.length > 0)) && (
        <QuoteCard
          rfq_id={rfq.rfq_id}
          buyer_name={rfq.buyer_name}
          sender={rfq.sender}
          delivery_location={rfq.delivery_location}
          rfq_deadline={rfq.rfq_deadline}
          line_items={rfq.line_items ?? []}
          line_pricing={rfq.line_pricing ?? []}
          total={rfq.total}
          draft_quote={rfq.draft_quote}
          created_at={rfq.created_at}
          dispatched_at={rfq.dispatched_at}
        />
      )}
    </div>
  );
}
