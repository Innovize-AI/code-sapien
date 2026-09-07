"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  CheckCircle2, Clock, TrendingUp, ArrowRight,
  Package, Truck, Zap, AlertTriangle,
} from "lucide-react";
import StatsCard from "@/components/StatsCard";
import StatusBadge from "@/components/StatusBadge";
import { api } from "@/lib/api";
import type { StatsResponse, RFQListItem } from "@/lib/types";
import { fmt_inr, fmt_date } from "@/lib/utils";

const URGENCY: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border border-red-500/20",
  rush:     "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  standard: "bg-brand-elevated text-brand-muted border border-brand-border",
};

export default function Dashboard() {
  const [stats, setStats] = useState<StatsResponse>({ total: 0, dispatched: 0, pending_review: 0, processing: 0, failed: 0, total_value: 0 });
  const [recent, setRecent] = useState<RFQListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.stats(), api.list({ limit: 10 })])
      .then(([s, { items }]) => { setStats(s); setRecent(items); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const autoRate = stats.total > 0 ? Math.round((stats.dispatched / stats.total) * 100) : 0;

  return (
    <div className="max-w-6xl mx-auto" suppressHydrationWarning>

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-serif font-bold text-brand-text tracking-tight">Dashboard</h1>
          <p className="text-brand-muted text-sm mt-0.5">AI-powered RFQ processing — live overview</p>
        </div>
        <Link href="/submit"
          className="flex items-center gap-2 bg-teal-500 hover:bg-teal-400 text-black text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors">
          <Zap size={15} /> Submit RFQ
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatsCard label="Total RFQs"         value={stats.total}              icon={<TrendingUp size={18} />}  accent="bg-teal-500/10"   iconColor="text-teal-400" />
        <StatsCard label="Auto-Dispatched"     value={stats.dispatched}         sub={`${autoRate}% auto-rate`}  icon={<CheckCircle2 size={18} />} accent="bg-teal-500/10" iconColor="text-teal-400" trend={autoRate > 70 ? `${autoRate}%` : undefined} />
        <StatsCard label="Needs Review"        value={stats.pending_review}     icon={<Clock size={18} />}       accent="bg-amber-500/10"  iconColor="text-amber-400" />
        <StatsCard label="Total Value Quoted"  value={fmt_inr(stats.total_value)} sub="across all RFQs"         icon={<TrendingUp size={18} />}  accent="bg-teal-500/10"   iconColor="text-teal-400" />
      </div>

      {/* Pending review alert */}
      {stats.pending_review > 0 && (
        <div className="flex items-center justify-between bg-amber-500/10 border border-amber-500/20 rounded-xl px-5 py-3.5 mb-6">
          <div className="flex items-center gap-3">
            <AlertTriangle size={16} className="text-amber-400 flex-shrink-0" />
            <p className="text-sm text-amber-300 font-medium">
              {stats.pending_review} RFQ{stats.pending_review > 1 ? "s" : ""} waiting for your review
            </p>
          </div>
          <Link href="/rfqs?status=pending_review"
            className="text-xs font-semibold text-amber-400 hover:text-amber-300 flex items-center gap-1">
            Review now <ArrowRight size={13} />
          </Link>
        </div>
      )}

      {/* Recent submissions */}
      <div className="bg-brand-card rounded-2xl border border-brand-border">
        <div className="flex items-center justify-between px-6 py-4 border-b border-brand-border">
          <h2 className="font-semibold text-brand-text text-sm">Recent Submissions</h2>
          <Link href="/rfqs" className="text-xs text-teal-500 hover:text-teal-400 font-medium flex items-center gap-1">
            View all <ArrowRight size={13} />
          </Link>
        </div>

        {loading ? (
          <div className="py-16 flex items-center justify-center gap-3 text-brand-muted">
            <div className="w-5 h-5 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">Loading…</span>
          </div>
        ) : recent.length === 0 ? (
          <div className="py-20 text-center">
            <div className="w-12 h-12 rounded-2xl bg-brand-elevated border border-brand-border flex items-center justify-center mx-auto mb-4">
              <Package size={20} className="text-brand-muted" />
            </div>
            <p className="text-sm font-medium text-brand-muted">No RFQs yet</p>
            <p className="text-xs text-brand-muted mt-1 mb-4 opacity-60">Submit your first RFQ to get started</p>
            <Link href="/submit"
              className="inline-flex items-center gap-1.5 bg-teal-500 hover:bg-teal-400 text-black text-xs font-semibold px-4 py-2 rounded-lg transition-colors">
              <Zap size={13} /> Submit RFQ
            </Link>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] text-brand-muted uppercase tracking-wider border-b border-brand-border">
                <th className="px-6 py-3 text-left font-semibold">Buyer</th>
                <th className="px-6 py-3 text-left font-semibold">Type</th>
                <th className="px-6 py-3 text-left font-semibold">Urgency</th>
                <th className="px-6 py-3 text-right font-semibold">Value</th>
                <th className="px-6 py-3 text-left font-semibold">Status</th>
                <th className="px-6 py-3 text-left font-semibold">Date</th>
                <th className="px-6 py-3" />
              </tr>
            </thead>
            <tbody>
              {recent.map((rfq) => (
                <tr key={rfq.rfq_id} className="border-b border-brand-border hover:bg-brand-elevated transition-colors">
                  <td className="px-6 py-3.5">
                    <p className="font-semibold text-brand-text text-sm">{rfq.buyer_name || "—"}</p>
                    <p className="text-brand-muted text-xs mt-0.5">{rfq.sender}</p>
                  </td>
                  <td className="px-6 py-3.5">
                    <span className="flex items-center gap-1.5 text-brand-muted text-xs">
                      {rfq.rfq_type === "freight"
                        ? <Truck size={13} className="text-amber-400" />
                        : <Package size={13} className="text-teal-400" />}
                      <span className="capitalize">{rfq.rfq_type ?? "product"}</span>
                    </span>
                  </td>
                  <td className="px-6 py-3.5">
                    {rfq.urgency ? (
                      <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize ${URGENCY[rfq.urgency] ?? URGENCY.standard}`}>
                        {rfq.urgency}
                      </span>
                    ) : <span className="text-brand-muted">—</span>}
                  </td>
                  <td className="px-6 py-3.5 text-right font-semibold text-brand-text">{fmt_inr(rfq.total)}</td>
                  <td className="px-6 py-3.5"><StatusBadge status={rfq.status} /></td>
                  <td className="px-6 py-3.5 text-brand-muted text-xs">{fmt_date(rfq.created_at)}</td>
                  <td className="px-6 py-3.5">
                    <Link href={`/rfqs/${rfq.rfq_id}`} className="text-teal-500 hover:text-teal-400 transition-colors">
                      <ArrowRight size={15} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
