"use client";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Package, Truck, Mail, ArrowUpRight, ChevronLeft, ChevronRight,
  FileText, AlertCircle, Clock, CheckCircle2, RefreshCw,
} from "lucide-react";
import StatusBadge from "@/components/StatusBadge";
import { api } from "@/lib/api";
import type { RFQListItem } from "@/lib/types";
import { fmt_inr, fmt_date, fmt_pct } from "@/lib/utils";
import clsx from "clsx";

const FILTERS = [
  { label: "All",          value: "",               icon: FileText },
  { label: "Dispatched",   value: "dispatched",     icon: CheckCircle2 },
  { label: "Needs Review", value: "pending_review", icon: AlertCircle },
  { label: "Processing",   value: "processing",     icon: RefreshCw },
  { label: "Failed",       value: "failed",         icon: AlertCircle },
];

export default function RFQListPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage]   = useState(1);
  const [items, setItems] = useState<RFQListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const LIMIT = 15;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.list({ status: statusFilter || undefined, page, limit: LIMIT });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setPage(1); }, [statusFilter]);

  const pages = Math.ceil(total / LIMIT);
  const start = (page - 1) * LIMIT + 1;
  const end   = Math.min(page * LIMIT, total);

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-serif font-bold text-brand-text tracking-tight">RFQ Pipeline</h1>
          <p className="text-sm text-brand-muted mt-0.5">{total} submissions total</p>
        </div>
        <Link href="/submit"
          className="inline-flex items-center gap-2 bg-teal-500 hover:bg-teal-400 text-black text-sm font-semibold px-4 py-2 rounded-xl transition-colors">
          + New RFQ
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-1.5 flex-wrap">
        {FILTERS.map(({ label, value, icon: Icon }) => (
          <button key={value} onClick={() => setStatusFilter(value)}
            className={clsx(
              "inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all",
              statusFilter === value
                ? "bg-teal-500 text-black"
                : "bg-brand-card text-brand-muted border border-brand-border hover:border-teal-500/30 hover:text-teal-400"
            )}>
            <Icon size={13} /> {label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-brand-card rounded-2xl border border-brand-border overflow-hidden">
        {/* Header row */}
        <div className="grid grid-cols-[2fr_1fr_1fr_auto_auto_auto_auto] gap-4 px-5 py-3 border-b border-brand-border bg-brand-elevated">
          {["Buyer", "Type", "Category / Urgency", "Total", "Confidence", "Status", ""].map((h) => (
            <p key={h} className="text-[10px] font-semibold text-brand-muted uppercase tracking-widest">{h}</p>
          ))}
        </div>

        {loading ? (
          <div className="py-24 text-center">
            <div className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-brand-muted">Loading RFQs…</p>
          </div>
        ) : items.length === 0 ? (
          <div className="py-24 text-center">
            <FileText size={36} className="mx-auto text-brand-border mb-4" />
            <p className="text-sm font-medium text-brand-muted">No RFQs found</p>
            {statusFilter && <p className="text-xs text-brand-muted mt-1 opacity-60">Try a different filter</p>}
          </div>
        ) : (
          <div className="divide-y divide-brand-border">
            {items.map((rfq) => (
              <div key={rfq.rfq_id}
                onClick={() => router.push(`/rfqs/${rfq.rfq_id}`)}
                className="grid grid-cols-[2fr_1fr_1fr_auto_auto_auto_auto] gap-4 items-center px-5 py-3.5 hover:bg-brand-elevated transition-colors group cursor-pointer">

                {/* Buyer */}
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-brand-text truncate text-sm">
                      {rfq.buyer_name || rfq.sender.split("@")[0]}
                    </p>
                    <span className="text-[9px] font-mono text-brand-muted bg-brand-elevated border border-brand-border px-1.5 py-0.5 rounded flex-shrink-0">
                      {rfq.rfq_id.slice(0, 6).toUpperCase()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <p className="text-xs text-brand-muted truncate">{rfq.sender}</p>
                    {rfq.email_id && (
                      <Link href={`/inbox/${rfq.email_id}`}
                        onClick={(e) => { e.stopPropagation(); }}
                        className="flex-shrink-0 flex items-center gap-1 text-[10px] text-teal-500 hover:text-teal-400 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                        <Mail size={10} /> source
                      </Link>
                    )}
                  </div>
                  <p className="text-[10px] text-brand-muted mt-0.5 opacity-50">{fmt_date(rfq.created_at)}</p>
                </div>

                {/* Type */}
                <div className="flex items-center gap-1.5">
                  {rfq.rfq_type === "freight"
                    ? <><Truck size={13} className="text-amber-400" /><span className="text-xs text-brand-muted">Freight</span></>
                    : <><Package size={13} className="text-teal-400" /><span className="text-xs text-brand-muted">Product</span></>}
                </div>

                {/* Category + Urgency */}
                <div className="space-y-1">
                  {rfq.category && (
                    <p className="text-xs text-brand-muted capitalize">{rfq.category.replace(/_/g, " ")}</p>
                  )}
                  {rfq.urgency && (
                    <span className={clsx("inline-block px-2 py-0.5 rounded-md text-[10px] font-semibold capitalize",
                      rfq.urgency === "critical" ? "bg-red-500/10 text-red-400 border border-red-500/20"
                        : rfq.urgency === "rush" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        : "bg-brand-elevated text-brand-muted border border-brand-border")}>
                      {rfq.urgency}
                    </span>
                  )}
                </div>

                {/* Total */}
                <p className="text-sm font-bold text-brand-text tabular-nums text-right">
                  {rfq.total != null ? fmt_inr(rfq.total) : "—"}
                </p>

                {/* Confidence */}
                <div className="text-right">
                  {rfq.pricing_confidence != null ? (
                    <span className={clsx("text-xs font-semibold tabular-nums",
                      rfq.pricing_confidence >= 0.8 ? "text-teal-400"
                        : rfq.pricing_confidence >= 0.5 ? "text-amber-400"
                        : "text-red-400")}>
                      {fmt_pct(rfq.pricing_confidence)}
                    </span>
                  ) : <span className="text-xs text-brand-muted opacity-40">—</span>}
                </div>

                {/* Status */}
                <StatusBadge status={rfq.status} />

                {/* Actions */}
                <div className="flex items-center gap-1">
                  {rfq.email_id && (
                    <Link href={`/inbox/${rfq.email_id}`} onClick={(e) => e.stopPropagation()}
                      title="View source email"
                      className="p-1.5 rounded-lg text-brand-muted hover:text-teal-400 hover:bg-teal-500/10 transition-colors">
                      <Mail size={14} />
                    </Link>
                  )}
                  <span className="p-1.5 rounded-lg text-brand-muted">
                    <ArrowUpRight size={14} />
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-between px-5 py-3.5 border-t border-brand-border bg-brand-elevated">
            <p className="text-xs text-brand-muted">
              Showing <span className="font-medium text-brand-text">{start}–{end}</span> of <span className="font-medium text-brand-text">{total}</span>
            </p>
            <div className="flex gap-1.5">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-brand-border text-sm text-brand-muted disabled:opacity-30 hover:bg-brand-card hover:text-brand-text transition-colors">
                <ChevronLeft size={14} /> Prev
              </button>
              <button onClick={() => setPage(p => Math.min(pages, p + 1))} disabled={page === pages}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-brand-border text-sm text-brand-muted disabled:opacity-30 hover:bg-brand-card hover:text-brand-text transition-colors">
                Next <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
