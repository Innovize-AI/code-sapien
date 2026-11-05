"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import {
  MessageCircle, Bot, Users, CalendarCheck,
  AlertTriangle, Activity, PauseCircle, Clock,
  Home, Building2, Sun,
} from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import { fetchStats, fetchVisits, fetchFirms } from "@/lib/api";
import { useRole } from "@/hooks/use-role";
import { useFirm } from "@/hooks/use-firm";
import { SourceSplitPanel } from "@/components/source-split";
import { cn } from "@/lib/utils";
import type { DashboardStats, Firm, Visit } from "@/types";
import type { Vertical } from "@/types";

// ── Vertical config ────────────────────────────────────────────────────────────

const VERTICAL_ICON: Record<Vertical, React.ElementType> = {
  interior:    Home,
  real_estate: Building2,
  solar:       Sun,
};
const VERTICAL_COLOR: Record<Vertical, string> = {
  interior:    "var(--chart-4)",
  real_estate: "var(--chart-2)",
  solar:       "var(--chart-3)",
};
const VERTICAL_LABEL: Record<Vertical, string> = {
  interior:    "Interior Design",
  real_estate: "Real Estate",
  solar:       "Solar",
};

const STAGE_ORDER = ["discovery", "qualification", "portfolio_match", "consideration", "booking", "conversion"];
const STAGE_COLORS: Record<string, string> = {
  discovery:       "bg-neutral-data",
  qualification:   "bg-cost",
  portfolio_match: "bg-chart-4",
  consideration:   "bg-chart-3",
  booking:         "bg-accent",
  conversion:      "bg-success",
};
const STAGE_LABELS: Record<string, string> = {
  discovery:       "Discovery",
  qualification:   "Qualification",
  portfolio_match: "Portfolio",
  consideration:   "Consideration",
  booking:         "Booking",
  conversion:      "Converted",
};

// ── Shared sub-components ──────────────────────────────────────────────────────

function MiniStat({
  icon: Icon, label, value, color,
}: {
  icon: React.ElementType; label: string; value: number | undefined; color: string;
}) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-xl bg-bg border border-line">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${color}`}>
        <Icon className="w-4 h-4 text-on-accent" />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] font-medium text-muted uppercase tracking-wide truncate">{label}</p>
        <p className="text-lg font-semibold text-ink tabular-nums leading-tight">
          {value ?? <span className="inline-block w-8 h-5 bg-line animate-pulse rounded" />}
        </p>
      </div>
    </div>
  );
}

function FunnelBar({ stage, count, total }: { stage: string; count: number; total: number }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="w-24 text-[11px] text-muted font-medium truncate">{STAGE_LABELS[stage] ?? stage}</span>
      <div className="flex-1 h-2 bg-bg rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${STAGE_COLORS[stage] ?? "bg-muted"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-6 text-right text-[11px] font-semibold text-ink/80 tabular-nums">{count}</span>
    </div>
  );
}

// ── Per-firm analytics card ────────────────────────────────────────────────────

function FirmAnalyticsCard({ firm }: { firm: Firm }) {
  const Icon     = VERTICAL_ICON[firm.vertical] ?? Building2;
  const color    = VERTICAL_COLOR[firm.vertical] ?? "var(--muted)";

  const { data: stats } = useSWR<DashboardStats>(
    `stats-${firm.id}`,
    () => fetchStats(firm.id),
    { refreshInterval: 60_000 },
  );

  const funnelTotal = stats
    ? Object.values(stats.funnel ?? {}).reduce((s, n) => s + n, 0)
    : 0;

  return (
    <div className="bg-card rounded-2xl border border-line shadow-sm overflow-hidden">
      {/* Firm header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-line">
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)`, border: `1.5px solid color-mix(in srgb, ${color} 28%, transparent)` }}
        >
          <Icon className="w-4.5 h-4.5" style={{ color }} />
        </div>
        <div>
          <p className="text-sm font-semibold text-ink">{firm.firm_display_name}</p>
          <p className="text-[11px] text-muted">{VERTICAL_LABEL[firm.vertical]}</p>
        </div>
        {!firm.is_active && (
          <span className="ml-auto text-[10px] font-medium text-muted bg-bg px-2 py-0.5 rounded-full">
            Inactive
          </span>
        )}
      </div>

      {/* Chat usage vs plan cap */}
      {firm.plan && (
        <div className="px-4 pb-2">
          <div className="flex items-center justify-between text-[11px] mb-1">
            <span className="text-muted">Chats this month</span>
            <span className="font-semibold text-ink/70 tabular-nums">
              {firm.monthly_chats_used} / {firm.plan.monthly_chat_cap}
            </span>
          </div>
          <div className="h-1.5 bg-bg rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full",
                firm.monthly_chats_used / firm.plan.monthly_chat_cap >= 0.9
                  ? "bg-error"
                  : firm.monthly_chats_used / firm.plan.monthly_chat_cap >= 0.75
                    ? "bg-warning"
                    : "bg-success",
              )}
              style={{ width: `${Math.min(100, Math.round((firm.monthly_chats_used / firm.plan.monthly_chat_cap) * 100))}%` }}
            />
          </div>
          <p className="text-[10px] text-muted mt-1">{firm.plan.label} · Rs. {firm.plan.price_monthly.toLocaleString("en-IN")}/mo</p>
        </div>
      )}

      {/* Stats grid */}
      <div className="p-4 grid grid-cols-2 gap-2">
        <MiniStat icon={Users}         label="Leads"        value={stats?.leads_captured}       color="bg-chart-4" />
        <MiniStat icon={CalendarCheck} label="Visits"       value={stats?.visits_booked}        color="bg-success"  />
        <MiniStat icon={MessageCircle} label="Messages"     value={stats?.total_messages}       color="bg-cost"   />
        <MiniStat icon={Bot}           label="AI Replies"   value={stats?.ai_replies}           color="bg-chart-4" />
        <MiniStat icon={Activity}      label="Active"       value={stats?.active_conversations} color="bg-success"/>
        <MiniStat icon={PauseCircle}   label="AI Paused"    value={stats?.ai_paused_count}      color="bg-warning"  />
        <MiniStat icon={AlertTriangle} label="Fallbacks"    value={stats?.fallbacks_triggered}  color="bg-error"    />
      </div>

      {/* Funnel */}
      <div className="px-4 pb-4">
        <p className="text-[11px] font-semibold text-muted uppercase tracking-wide mb-2">Funnel</p>
        {stats ? (
          <div className="space-y-1.5">
            {STAGE_ORDER.map(stage => (
              <FunnelBar key={stage} stage={stage} count={stats.funnel?.[stage] ?? 0} total={funnelTotal} />
            ))}
          </div>
        ) : (
          <div className="space-y-1.5">
            {STAGE_ORDER.map(s => (
              <div key={s} className="h-4 bg-bg animate-pulse rounded-full" />
            ))}
          </div>
        )}
      </div>

      {firm.vertical === "real_estate" && (
        <div className="px-4 pb-4">
          <SourceSplitPanel firmId={firm.id} compact />
        </div>
      )}
    </div>
  );
}

// ── Staff single-firm view (counselor / viewer) ────────────────────────────────

function StatCard({
  icon: Icon, label, value, color, sub,
}: {
  icon: React.ElementType; label: string; value: number | undefined; color: string; sub?: string;
}) {
  return (
    <div className="bg-card rounded-2xl shadow-sm border border-line p-5 flex items-start gap-4">
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${color}`}>
        <Icon className="w-5 h-5 text-on-accent" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-muted truncate">{label}</p>
        <p className="text-2xl font-semibold text-ink mt-0.5 tabular-nums">
          {value ?? <span className="w-16 h-7 bg-bg animate-pulse rounded inline-block" />}
        </p>
        {sub && <p className="text-xs text-muted mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

function StaffDashboard({ firmId, isRealEstate }: { firmId: string; isRealEstate: boolean }) {
  const { data: stats } = useSWR<DashboardStats>(
    `stats-${firmId}`,
    () => fetchStats(firmId),
    { refreshInterval: 30_000 },
  );
  const { data: visitsRaw } = useSWR<Visit[]>(
    `visits-${firmId}`,
    () => fetchVisits(firmId),
    { refreshInterval: 60_000 },
  );

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const visits = visitsRaw?.filter(
    v => new Date(v.visit_date) >= today && v.status !== "cancelled" && v.status !== "completed"
  );

  const funnelTotal = stats
    ? Object.values(stats.funnel ?? {}).reduce((s, n) => s + n, 0)
    : 0;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={MessageCircle} label="Total Messages"       value={stats?.total_messages}       color="bg-cost"    />
        <StatCard icon={Bot}           label="AI Replies Sent"      value={stats?.ai_replies}           color="bg-chart-4"  />
        <StatCard icon={Users}         label="Leads Captured"       value={stats?.leads_captured}       color="bg-chart-4"  />
        <StatCard icon={CalendarCheck} label="Visits Booked"        value={stats?.visits_booked}        color="bg-success"   />
        <StatCard icon={AlertTriangle} label="Fallbacks Triggered"  value={stats?.fallbacks_triggered}  color="bg-error"     sub="unanswered Qs" />
        <StatCard icon={Activity}      label="Active Conversations" value={stats?.active_conversations} color="bg-success" sub="open sessions" />
        <StatCard icon={PauseCircle}   label="AI Paused"            value={stats?.ai_paused_count}      color="bg-warning"   sub="human takeover" />
      </div>

      {isRealEstate && <SourceSplitPanel firmId={firmId} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card rounded-2xl shadow-sm border border-line p-6">
          <h2 className="text-base font-semibold text-ink mb-5">Conversation Funnel</h2>
          {stats ? (
            <div className="space-y-3">
              {STAGE_ORDER.map(stage => (
                <div key={stage} className="flex items-center gap-3">
                  <span className="w-28 text-xs text-ink/70 font-medium truncate">{STAGE_LABELS[stage]}</span>
                  <div className="flex-1 h-2.5 bg-bg rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${STAGE_COLORS[stage] ?? "bg-muted"}`}
                      style={{ width: funnelTotal > 0 ? `${Math.round(((stats.funnel?.[stage] ?? 0) / funnelTotal) * 100)}%` : "0%" }}
                    />
                  </div>
                  <span className="w-8 text-right text-xs font-semibold text-ink tabular-nums">{stats.funnel?.[stage] ?? 0}</span>
                </div>
              ))}
              <div className="pt-2 border-t border-line flex justify-between text-xs text-muted">
                <span>Total active sessions</span>
                <span className="font-semibold text-ink/80 tabular-nums">{funnelTotal}</span>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {STAGE_ORDER.map(s => <div key={s} className="h-5 bg-bg animate-pulse rounded-full" />)}
            </div>
          )}
        </div>

        <div className="bg-card rounded-2xl shadow-sm border border-line p-6">
          <h2 className="text-base font-semibold text-ink mb-5">
            Upcoming Visits
            {visits && visits.length > 0 && (
              <span className="ml-2 text-xs font-medium bg-success/10 text-success px-2 py-0.5 rounded-full">
                {visits.length} scheduled
              </span>
            )}
          </h2>
          {!visits ? (
            <div className="space-y-2">
              {[0, 1, 2].map(i => <div key={i} className="h-12 bg-bg animate-pulse rounded-xl" />)}
            </div>
          ) : visits.length === 0 ? (
            <div className="text-center py-10 text-muted text-sm">No upcoming visits scheduled</div>
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {visits.map(v => (
                <div key={v.id} className="flex items-center gap-3 p-3 rounded-xl border border-line hover:bg-bg transition">
                  <div className="w-10 h-10 rounded-xl bg-success/10 border border-success/30 flex flex-col items-center justify-center flex-shrink-0">
                    <span className="text-[10px] font-semibold text-success">{format(new Date(v.visit_date), "MMM").toUpperCase()}</span>
                    <span className="text-sm font-semibold text-success leading-none">{format(new Date(v.visit_date), "d")}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-ink truncate">{v.lead_name ?? v.phone ?? "Lead"}</p>
                    <p className="text-xs text-muted">
                      {v.visit_time_slot ?? "Morning"}
                      {v.config && ` · ${v.config}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-muted">
                    <Clock className="w-3 h-3" />
                    {formatDistanceToNow(new Date(v.visit_date), { addSuffix: true })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { role } = useRole();
  const router = useRouter();
  useEffect(() => { if (role === "agent") router.replace("/conversations"); }, [role, router]);
  const { firmId, firm } = useFirm();
  const isAdmin = role === "admin";

  const { data: allFirms } = useSWR<Firm[]>(isAdmin ? "all-firms" : null, fetchFirms);

  if (isAdmin) {
    return (
      <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Analytics</h1>
          <p className="text-sm text-muted mt-1">Performance across all firms</p>
        </div>

        {!allFirms ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {[0, 1, 2].map(i => (
              <div key={i} className="h-96 bg-bg animate-pulse rounded-2xl" />
            ))}
          </div>
        ) : allFirms.length === 0 ? (
          <div className="text-center py-20 text-muted">No firms set up yet.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {allFirms.map(firm => (
              <FirmAnalyticsCard key={firm.id} firm={firm} />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Analytics</h1>
        <p className="text-sm text-muted mt-1">Live lead pipeline, refreshes every 30 s</p>
      </div>
      {firmId
        ? <StaffDashboard firmId={firmId} isRealEstate={firm?.vertical === "real_estate"} />
        : <div className="text-muted text-sm">Loading…</div>
      }
    </div>
  );
}
