"use client";

import { useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import { format, formatDistanceToNow, isPast } from "date-fns";
import {
  CalendarCheck, CheckCircle, Clock, Home, User,
  RefreshCw, XCircle, AlertCircle, History, Car,
} from "lucide-react";
import { fetchVisits, markAttended, markNoShow } from "@/lib/api";
import { useFirm } from "@/hooks/use-firm";
import type { Visit } from "@/types";

const VERTICAL_LABELS: Record<string, string> = {
  interior:    "Interior Design",
  real_estate: "Real Estate",
  solar:       "Solar",
};

type Tab = "upcoming" | "rescheduled" | "cancelled" | "past";

function VisitCard({
  visit: v,
  variant,
  onMarkAttended,
  onMarkNoShow,
}: {
  visit: Visit;
  variant: Tab;
  onMarkAttended?: () => Promise<void>;
  onMarkNoShow?: () => Promise<void>;
}) {
  const [confirming, setConfirming] = useState(false);
  const [loading, setLoading] = useState<"attended" | "noshow" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cancelled   = variant === "cancelled";
  const rescheduled = variant === "rescheduled";
  const past        = variant === "past";
  const dimmed      = past || cancelled;

  async function handleAttended() {
    if (!onMarkAttended) return;
    setLoading("attended");
    setError(null);
    try { await onMarkAttended(); } catch { setError("Could not update this visit. Try again."); } finally { setLoading(null); }
  }

  async function handleNoShow() {
    if (!onMarkNoShow) return;
    setLoading("noshow");
    setError(null);
    try { await onMarkNoShow(); } catch { setError("Could not update this visit. Try again."); } finally { setLoading(null); setConfirming(false); }
  }

  return (
    <div className={`bg-card rounded-2xl border shadow-sm p-5 flex items-start gap-5 ${
      cancelled   ? "border-error/20 opacity-75" :
      rescheduled ? "border-warning/40" :
      dimmed      ? "opacity-60 border-line" :
                    "border-line hover:border-accent/20 hover:shadow-md transition"
    }`}>

      {/* Date block */}
      <div className={`w-14 h-14 rounded-xl flex flex-col items-center justify-center flex-shrink-0 ${
        cancelled   ? "bg-error/10"    :
        rescheduled ? "bg-warning/10"  :
        dimmed      ? "bg-bg" :
                      "bg-accent"
      }`}>
        <span className={`text-[11px] font-semibold uppercase ${
          cancelled   ? "text-error"    :
          rescheduled ? "text-warning"  :
          dimmed      ? "text-muted"  :
                        "text-accent"
        }`}>
          {format(new Date(v.visit_date), "MMM")}
        </span>
        <span className={`text-xl font-black leading-none ${
          cancelled   ? "text-error"   :
          rescheduled ? "text-warning" :
          dimmed      ? "text-muted" :
                        "text-on-accent"
        }`}>
          {format(new Date(v.visit_date), "d")}
        </span>
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <User className="w-3.5 h-3.5 text-muted flex-shrink-0" />
          <p className="text-sm font-semibold text-ink truncate">{v.lead_name ?? "Lead"}</p>
          {v.lead_type && (
            <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-chart-4/10 text-chart-4">
              {VERTICAL_LABELS[v.lead_type] ?? v.lead_type}
            </span>
          )}
          {rescheduled && (
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-warning/10 text-warning">
              Rescheduled
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
          {v.visit_time_slot && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {v.visit_time_slot}
            </span>
          )}
          {v.config && (
            <span className="flex items-center gap-1">
              <Home className="w-3 h-3" />
              {v.config}
            </span>
          )}
          {v.cab_pickup_address && (
            <span className="flex items-center gap-1">
              <Car className="w-3 h-3" />
              {v.cab_pickup_address}
            </span>
          )}
        </div>

        {v.hesitation_code && (
          <p className="mt-1.5 text-[11px] text-muted italic">
            Hesitation: {v.hesitation_code.replace(/_/g, " ")}
          </p>
        )}

        {cancelled && v.cancellation_reason && (
          <p className="mt-2 text-xs text-muted italic flex items-start gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-px text-error" />
            {v.cancellation_reason}
          </p>
        )}
      </div>

      {/* Right side */}
      <div className="flex flex-col items-end gap-2 flex-shrink-0">
        {cancelled ? (
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-error/10 text-error">
            {v.status === "no_show" ? "No-show" : "Cancelled"}
          </span>
        ) : past ? (
          <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${
            v.attended === true  ? "bg-success/10 text-success" :
            v.attended === false ? "bg-error/10 text-error" :
                                   "bg-bg text-muted"
          }`}>
            {v.attended === true ? "Attended" : v.attended === false ? "No-show" : "Unknown"}
          </span>
        ) : (
          <>
            <span className="text-xs text-muted">
              {formatDistanceToNow(new Date(v.visit_date), { addSuffix: true })}
            </span>

            {onMarkAttended && (
              <div className="flex flex-col items-end gap-1.5">
                {error && <p className="text-xs text-error text-right max-w-[180px]">{error}</p>}
                <button
                  onClick={handleAttended}
                  disabled={loading !== null}
                  className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-success/10 text-success hover:bg-success/10 disabled:opacity-50 transition"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  {loading === "attended" ? "Marking…" : "Mark Attended"}
                </button>

                {confirming ? (
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-muted">Confirm no-show?</span>
                    <button
                      onClick={handleNoShow}
                      disabled={loading !== null}
                      className="text-xs font-semibold px-2 py-1 rounded-lg bg-warning text-on-accent hover:opacity-90 disabled:opacity-50 transition"
                    >
                      {loading === "noshow" ? "…" : "Yes"}
                    </button>
                    <button
                      onClick={() => setConfirming(false)}
                      disabled={loading !== null}
                      className="text-xs font-medium px-2 py-1 rounded-lg bg-bg text-ink/70 hover:bg-line disabled:opacity-50 transition"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirming(true)}
                    disabled={loading !== null}
                    className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-warning/10 text-warning hover:bg-warning/10 disabled:opacity-50 transition"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    No-Show
                  </button>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

const TABS: { id: Tab; label: string; icon: React.ReactNode; emptyText: string }[] = [
  { id: "upcoming",    label: "Upcoming",    icon: <CalendarCheck className="w-4 h-4" />, emptyText: "No upcoming visits" },
  { id: "rescheduled", label: "Rescheduled", icon: <RefreshCw className="w-4 h-4" />,     emptyText: "No rescheduled visits" },
  { id: "cancelled",   label: "Cancelled",   icon: <XCircle className="w-4 h-4" />,       emptyText: "No cancelled visits" },
  { id: "past",        label: "Past",        icon: <History className="w-4 h-4" />,        emptyText: "No past visits" },
];

const TAB_ACTIVE: Record<Tab, string> = {
  upcoming:    "border-accent text-accent",
  rescheduled: "border-warning/40 text-warning",
  cancelled:   "border-error/40 text-error",
  past:        "border-muted text-ink/70",
};

const COUNT_BADGE: Record<Tab, string> = {
  upcoming:    "bg-success/10 text-success",
  rescheduled: "bg-warning/10 text-warning",
  cancelled:   "bg-error/10 text-error",
  past:        "bg-bg text-ink/70",
};

export default function VisitsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("upcoming");
  const { mutate } = useSWRConfig();
  const { firmId } = useFirm();
  const swrKey = firmId ? `visits-all-${firmId}` : "visits-all";
  const { data, isLoading } = useSWR<Visit[]>(
    swrKey,
    () => fetchVisits(firmId ?? undefined),
    { refreshInterval: 60_000 },
  );

  const buckets: Record<Tab, Visit[]> = {
    upcoming:    data?.filter((v) => !isPast(new Date(v.visit_date)) && v.status !== "cancelled" && v.status !== "rescheduled" && v.status !== "no_show" && v.status !== "completed") ?? [],
    rescheduled: data?.filter((v) => v.status === "rescheduled") ?? [],
    cancelled:   data?.filter((v) => v.status === "cancelled" || v.status === "no_show") ?? [],
    past:        data?.filter((v) => v.status === "completed" || (isPast(new Date(v.visit_date)) && v.status !== "cancelled" && v.status !== "no_show")) ?? [],
  };

  const current = buckets[activeTab];
  const tab = TABS.find((t) => t.id === activeTab)!;

  function makeHandlers(leadId: string) {
    return {
      onMarkAttended: async () => {
        await markAttended(leadId);
        await mutate(swrKey);
      },
      onMarkNoShow: async () => {
        await markNoShow(leadId);
        await mutate(swrKey);
      },
    };
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Visits</h1>
        <p className="text-sm text-muted mt-1">Site and experience center visits booked by the AI agent</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-line overflow-x-auto">
        {TABS.map((t) => {
          const count = buckets[t.id].length;
          const isActive = t.id === activeTab;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex items-center gap-2 px-3 sm:px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors whitespace-nowrap flex-shrink-0 ${
                isActive
                  ? TAB_ACTIVE[t.id]
                  : "border-transparent text-muted hover:text-ink/80"
              }`}
            >
              {t.icon}
              {t.label}
              {(!isLoading && count > 0) && (
                <span className={`text-[11px] font-semibold px-1.5 py-0.5 rounded-full ${
                  isActive ? COUNT_BADGE[t.id] : "bg-bg text-muted"
                }`}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 bg-card rounded-2xl animate-pulse border border-line" />
          ))}
        </div>
      ) : current.length === 0 ? (
        <div className="bg-card rounded-2xl border border-line p-12 text-center text-muted text-sm">
          {tab.emptyText}
        </div>
      ) : (
        <div className="space-y-3">
          {current.map((v) => (
            <VisitCard
              key={v.id}
              visit={v}
              variant={activeTab}
              {...(activeTab === "upcoming" ? makeHandlers(v.lead_id) : {})}
            />
          ))}
        </div>
      )}
    </div>
  );
}
