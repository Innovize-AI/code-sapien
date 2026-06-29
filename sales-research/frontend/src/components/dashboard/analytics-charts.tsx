"use client";

import React, { useState, useEffect, useRef } from "react";
import {
    AreaChart, Area, BarChart, Bar, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DashboardAnalytics, TieredBreakdownItem, ReclassificationItem, AnalyticsPeriod, fetchDashboardAnalytics } from "@/lib/api";
import { format, parseISO } from "date-fns";
import { TrendingUp, TrendingDown, Minus, ExternalLink, FileText } from "lucide-react";
import Link from "next/link";

// ── Constants ─────────────────────────────────────────────────────────────────

const PERIOD_OPTIONS: { value: AnalyticsPeriod; label: string }[] = [
    { value: "7d",  label: "7D"  },
    { value: "14d", label: "14D" },
    { value: "30d", label: "30D" },
    { value: "90d", label: "90D" },
    { value: "12w", label: "12W" },
    { value: "12m", label: "12M" },
];

const PERIOD_LABELS: Record<AnalyticsPeriod, { title: string; subtitle: string; short: string }> = {
    "7d":  { title: "Daily",   subtitle: "Last 7 days",    short: "7d"  },
    "14d": { title: "Daily",   subtitle: "Last 14 days",   short: "14d" },
    "30d": { title: "Daily",   subtitle: "Last 30 days",   short: "30d" },
    "90d": { title: "Daily",   subtitle: "Last 90 days",   short: "90d" },
    "12w": { title: "Weekly",  subtitle: "Last 12 weeks",  short: "12w" },
    "12m": { title: "Monthly", subtitle: "Last 12 months", short: "12m" },
};

const TIERS = ["hot", "hand_raiser", "qualified", "unqualified"] as const;
type Tier = typeof TIERS[number];

const TIER_COLORS: Record<Tier, string> = {
    hot:         "#ef4444",
    hand_raiser: "#10b981",
    qualified:   "#3b82f6",
    unqualified: "#94a3b8",
};

const TIER_LABELS: Record<Tier, string> = {
    hot:         "🔥 Hot",
    hand_raiser: "🙋 Hand Raiser",
    qualified:   "👀 Qualified",
    unqualified: "✗ Unqualified",
};

// Human-readable channel names for lead_source values
const CHANNEL_LABELS: Record<string, string> = {
    apollo:        "Apollo",
    keyword:       "Keywords",
    competitor:    "Competitors",
    linkedin_jobs: "LinkedIn Jobs",
};
const channelLabel = (s: string) => CHANNEL_LABELS[s] ?? s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

// Module-level cache — one fetch shared across all charts for the same period
const _cache = new Map<AnalyticsPeriod, DashboardAnalytics>();

const CARD_CLASS =
    "overflow-hidden border-none bg-gradient-to-br from-white to-zinc-50/50 dark:from-zinc-900/50 dark:to-zinc-950 shadow-2xl shadow-zinc-200/50 dark:shadow-none ring-1 ring-zinc-200/50 dark:ring-zinc-800/50";

// ── Shared hook ───────────────────────────────────────────────────────────────

function usePeriodData(initialData: DashboardAnalytics, initialPeriod: AnalyticsPeriod = "30d") {
    const [period,  setPeriod]  = useState<AnalyticsPeriod>(initialPeriod);
    const [data,    setData]    = useState<DashboardAnalytics>(initialData);
    const [loading, setLoading] = useState(false);
    const seeded = useRef(false);

    if (!seeded.current) { _cache.set(initialPeriod, initialData); seeded.current = true; }

    useEffect(() => {
        if (_cache.has(period)) { setData(_cache.get(period)!); return; }
        setLoading(true);
        fetchDashboardAnalytics(period)
            .then((d) => { if (d) { _cache.set(period, d); setData(d); } })
            .finally(() => setLoading(false));
    }, [period]);

    return { period, setPeriod, data, loading };
}

// ── Shared UI ─────────────────────────────────────────────────────────────────

function PeriodToggle({
    value, onChange, loading,
}: { value: AnalyticsPeriod; onChange: (p: AnalyticsPeriod) => void; loading?: boolean }) {
    return (
        <div className="flex rounded-md border border-zinc-200 dark:border-zinc-800 overflow-hidden shrink-0">
            {PERIOD_OPTIONS.map((opt) => (
                <button
                    key={opt.value}
                    onClick={() => onChange(opt.value)}
                    disabled={loading}
                    className={`px-2 py-1 text-[10px] font-bold transition-colors ${
                        value === opt.value
                            ? "bg-primary text-primary-foreground"
                            : "bg-transparent text-muted-foreground hover:bg-muted"
                    }`}
                >
                    {opt.label}
                </button>
            ))}
        </div>
    );
}

function TierLegend() {
    return (
        <div className="flex gap-4 mt-1 flex-wrap">
            {TIERS.map((t) => (
                <span key={t} className="flex items-center gap-1 text-[10px] font-bold text-zinc-500">
                    <span className="inline-block w-2 h-2 rounded-full" style={{ background: TIER_COLORS[t] }} />
                    {TIER_LABELS[t]}
                </span>
            ))}
        </div>
    );
}

function DeltaBadge({ current, previous }: { current: number; previous: number }) {
    if (previous === 0 && current === 0) return null;
    const delta = current - previous;
    const pct   = previous > 0 ? Math.round((delta / previous) * 100) : null;
    if (delta === 0) return <Minus className="w-3 h-3 text-zinc-400" />;
    const up = delta > 0;
    return (
        <span className={`flex items-center gap-0.5 text-[10px] font-black ${up ? "text-emerald-600" : "text-red-500"}`}>
            {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {pct !== null ? `${up ? "+" : ""}${pct}%` : (up ? `+${delta}` : delta)}
        </span>
    );
}

const TrendTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 p-3 rounded-xl shadow-xl">
            <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-1">{label}</p>
            <p className="text-sm font-black text-primary">{payload[0].value} profiles</p>
        </div>
    );
};

const CompTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 p-3 rounded-xl shadow-xl min-w-[160px]">
            <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-2">{label}</p>
            {payload.map((p: any) => (
                <div key={p.dataKey} className="flex items-center justify-between gap-4 text-xs">
                    <span style={{ color: p.fill ?? p.stroke }}>{TIER_LABELS[p.dataKey as Tier] ?? p.name}</span>
                    <span className="font-black">{p.value}</span>
                </div>
            ))}
        </div>
    );
};

// ── Chart cards (module-level = stable React identity, no Recharts remount) ───

function TrendChart({ initialData }: { initialData: DashboardAnalytics }) {
    const { period, setPeriod, data, loading } = usePeriodData(initialData);
    const dateFormat = period === "12m" ? "MMM yy" : "MMM d";
    const trendData = data.daily_trends.map((d) => ({
        ...d,
        formattedDate: format(parseISO(d.date.slice(0, 10)), dateFormat),
    }));
    const { title, subtitle } = PERIOD_LABELS[period];

    return (
        <Card className={`col-span-4 ${CARD_CLASS} transition-opacity ${loading ? "opacity-50" : ""}`}>
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between gap-2">
                    <div>
                        <CardTitle className="text-lg font-black italic uppercase tracking-tight">{title} Growth</CardTitle>
                        <p className="text-xs text-muted-foreground font-medium">{subtitle}</p>
                    </div>
                    <PeriodToggle value={period} onChange={setPeriod} loading={loading} />
                </div>
            </CardHeader>
            <CardContent className="p-0 pt-4">
                <div className="h-[280px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={trendData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                            <defs>
                                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%"  stopColor="var(--primary)" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="var(--primary)" stopOpacity={0}   />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" className="opacity-[0.05]" />
                            <XAxis dataKey="formattedDate" axisLine={false} tickLine={false} tick={{ fontSize: 10, fontWeight: 600 }} dy={10} />
                            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fontWeight: 600 }} />
                            <Tooltip content={<TrendTooltip />} />
                            <Area type="monotone" dataKey="count" name="Profiles" stroke="var(--primary)" strokeWidth={4} fillOpacity={1} fill="url(#colorCount)" animationDuration={1500} />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}

// Period comparison — one group per tier, 2 bars each: current (tier color) + previous (gray)
function PeriodComparisonChart({ initialData }: { initialData: DashboardAnalytics }) {
    const { period, setPeriod, data, loading } = usePeriodData(initialData);
    const { short } = PERIOD_LABELS[period];

    // One data point per tier so X-axis = tier name
    const chartData = TIERS.map((tier) => ({
        tier,
        name:     TIER_LABELS[tier],
        current:  data.lead_quality[tier]        ?? 0,
        previous: data.previous_summary?.[tier]  ?? 0,
        color:    TIER_COLORS[tier],
    }));

    const totalCurr = chartData.reduce((s, r) => s + r.current,  0);
    const totalPrev = chartData.reduce((s, r) => s + r.previous, 0);

    return (
        <Card className={`col-span-3 ${CARD_CLASS} transition-opacity ${loading ? "opacity-50" : ""}`}>
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between gap-2">
                    <div>
                        <CardTitle className="text-lg font-black italic uppercase tracking-tight">Period Comparison</CardTitle>
                        <p className="text-xs text-muted-foreground font-medium">Each tier — current vs previous</p>
                    </div>
                    <PeriodToggle value={period} onChange={setPeriod} loading={loading} />
                </div>
                <div className="flex gap-4 mt-1">
                    <span className="flex items-center gap-1 text-[10px] font-bold text-zinc-500">
                        <span className="inline-block w-3 h-2 rounded-sm bg-primary" /> Current ({short})
                    </span>
                    <span className="flex items-center gap-1 text-[10px] font-bold text-zinc-500">
                        <span className="inline-block w-3 h-2 rounded-sm bg-zinc-300 dark:bg-zinc-600 opacity-60" /> Previous ({short})
                    </span>
                </div>
            </CardHeader>
            <CardContent className="pt-0">
                {/* Total summary */}
                <div className="flex gap-3 mb-3">
                    <div className="flex-1 bg-muted/40 rounded-lg px-3 py-2">
                        <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Current</p>
                        <div className="flex items-end gap-2">
                            <p className="text-2xl font-black">{totalCurr}</p>
                            <DeltaBadge current={totalCurr} previous={totalPrev} />
                        </div>
                    </div>
                    <div className="flex-1 bg-muted/40 rounded-lg px-3 py-2">
                        <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Previous</p>
                        <p className="text-2xl font-black">{totalPrev}</p>
                    </div>
                </div>

                {/* Per-tier delta list */}
                <div className="space-y-1.5 mb-3">
                    {chartData.map((row) => (
                        <div key={row.tier} className="flex items-center gap-2 text-[11px]">
                            <span className="w-2 h-2 rounded-full shrink-0" style={{ background: row.color }} />
                            <span className="w-24 font-semibold text-muted-foreground shrink-0">{TIER_LABELS[row.tier]}</span>
                            <span className="font-black">{row.current}</span>
                            <DeltaBadge current={row.current} previous={row.previous} />
                            <span className="text-muted-foreground ml-auto">prev {row.previous}</span>
                        </div>
                    ))}
                </div>

                {/* Grouped bars: 4 groups (one per tier), 2 bars each — NO stackId */}
                <div className="h-[150px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData} barCategoryGap="28%" barGap={3}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" className="opacity-[0.05]" />
                            <XAxis
                                dataKey="name"
                                axisLine={false} tickLine={false}
                                tick={{ fontSize: 9, fontWeight: 700 }}
                                tickFormatter={(v: string) => v.replace(/^[^\s]+\s/, "")} // strip emoji for compact label
                            />
                            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fontWeight: 600 }} />
                            <Tooltip
                                cursor={{ fill: "transparent" }}
                                content={({ active, payload, label: lbl }: any) => {
                                    if (!active || !payload?.length) return null;
                                    const row = chartData.find((r) => r.name === lbl);
                                    return (
                                        <div className="bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 p-3 rounded-xl shadow-xl min-w-[150px]">
                                            <p className="text-xs font-bold mb-2" style={{ color: row?.color }}>{lbl}</p>
                                            {payload.map((p: any) => (
                                                <div key={p.dataKey} className="flex justify-between gap-4 text-xs">
                                                    <span className="text-zinc-500">{p.dataKey === "current" ? `Current (${short})` : `Previous (${short})`}</span>
                                                    <span className="font-black">{p.value}</span>
                                                </div>
                                            ))}
                                            {row && (
                                                <div className="border-t border-zinc-100 dark:border-zinc-800 mt-1.5 pt-1.5 flex justify-between text-xs">
                                                    <span className="text-zinc-400">Δ</span>
                                                    <span className={`font-black ${row.current >= row.previous ? "text-emerald-600" : "text-red-500"}`}>
                                                        {row.current - row.previous >= 0 ? "+" : ""}{row.current - row.previous}
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                    );
                                }}
                            />
                            {/* Current: colored by tier via Cell */}
                            <Bar dataKey="current" name="Current" radius={[3, 3, 0, 0]} maxBarSize={22} animationDuration={900}>
                                {chartData.map((entry) => (
                                    <Cell key={entry.tier} fill={entry.color} />
                                ))}
                            </Bar>
                            {/* Previous: uniform gray */}
                            <Bar dataKey="previous" name="Previous" fill="#94a3b8" fillOpacity={0.5} radius={[3, 3, 0, 0]} maxBarSize={22} animationDuration={900} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}

// Discovery-channel chart: Apollo / Keywords / Competitors / LinkedIn Jobs / any other lead_source
// Shows current vs previous total side by side per channel (no stacking)
function DiscoverySourceChart({ initialData }: { initialData: DashboardAnalytics }) {
    const { period, setPeriod, data, loading } = usePeriodData(initialData);

    const items = data.source_breakdown;

    // Two bars per channel — current total and previous total
    const chartData = items.map((item) => ({
        name:     channelLabel(item.name),
        current:  item.total,
        previous: item.prev_total,
    }));

    return (
        <Card className={`col-span-7 ${CARD_CLASS} transition-opacity ${loading ? "opacity-50" : ""}`}>
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between gap-2">
                    <div>
                        <CardTitle className="text-lg font-black italic uppercase tracking-tight">Discovery Channels</CardTitle>
                        <p className="text-xs text-muted-foreground font-medium">Leads by source — current vs previous period</p>
                    </div>
                    <PeriodToggle value={period} onChange={setPeriod} loading={loading} />
                </div>
                <div className="flex gap-4 mt-1">
                    <span className="flex items-center gap-1 text-[10px] font-bold text-zinc-500">
                        <span className="inline-block w-2 h-2 rounded-full bg-primary" /> Current
                    </span>
                    <span className="flex items-center gap-1 text-[10px] font-bold text-zinc-500">
                        <span className="inline-block w-2 h-2 rounded-full bg-zinc-300 dark:bg-zinc-600" /> Previous
                    </span>
                </div>
            </CardHeader>
            <CardContent>
                {chartData.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">No data for this period</p>
                ) : (
                    <>
                        {/* Mini summary cards */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                            {items.map((item) => (
                                <div key={item.name} className="bg-muted/40 rounded-lg p-3">
                                    <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest truncate">{channelLabel(item.name)}</p>
                                    <div className="flex items-end gap-2 mt-1">
                                        <p className="text-xl font-black">{item.total}</p>
                                        <DeltaBadge current={item.total} previous={item.prev_total} />
                                    </div>
                                    {/* Tier mini bar */}
                                    <div className="flex h-1.5 rounded-full overflow-hidden bg-muted mt-2">
                                        {TIERS.map((t) => {
                                            const val = item[t];
                                            return val > 0 ? (
                                                <div key={t} className="h-full" style={{ width: `${(val / (item.total || 1)) * 100}%`, background: TIER_COLORS[t] }} />
                                            ) : null;
                                        })}
                                    </div>
                                    <div className="flex justify-between text-[9px] text-muted-foreground mt-1">
                                        <span>prev {item.prev_total}</span>
                                        {TIERS.filter((t) => item[t] > 0).slice(0, 1).map((t) => (
                                            <span key={t} style={{ color: TIER_COLORS[t] }}>{item[t]} {TIER_LABELS[t]}</span>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Grouped bar chart — current vs previous per channel, no stacking */}
                        <div className="h-[180px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={chartData} barCategoryGap="35%" barGap={4}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" className="opacity-[0.05]" />
                                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fontWeight: 700 }} />
                                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fontWeight: 600 }} />
                                    <Tooltip cursor={{ fill: "transparent" }} formatter={(v: any, name?: string) => [v, name === "current" ? "Current period" : "Previous period"]} />
                                    <Bar dataKey="current"  name="Current"  fill="var(--primary)"   radius={[4, 4, 0, 0]} maxBarSize={40} animationDuration={900} />
                                    <Bar dataKey="previous" name="Previous" fill="#94a3b8"           radius={[4, 4, 0, 0]} maxBarSize={40} animationDuration={900} fillOpacity={0.6} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </>
                )}
            </CardContent>
        </Card>
    );
}

// Generic comparison chart for keywords or competitors
// Horizontal grouped bars: source name | [current bar] | [previous bar] | delta
function SourceComparisonChart({ initialData, dataKey, label, className }: {
    initialData: DashboardAnalytics;
    dataKey: "keyword_breakdown" | "competitor_breakdown";
    label: string;
    className?: string;
}) {
    const { period, setPeriod, data, loading } = usePeriodData(initialData);
    const items: TieredBreakdownItem[] = data[dataKey].slice(0, 8);

    // Build grouped bar data: one row per source, current vs previous per tier (4+4 bars = too many)
    // Instead: one row per source with 4 current-tier bars grouped side by side.
    // For comparison: a separate row showing prev totals as a muted bar.
    // Simplest clear approach: show one grouped bar chart per source name,
    // with current tier bars (4 bars) + 1 gray "previous total" bar.
    // This is NOT stacked — all bars are side by side.

    const chartData = items.map((item) => ({
        name:        item.name.length > 18 ? item.name.slice(0, 18) + "…" : item.name,
        fullName:    item.name,
        hot:         item.hot,
        hand_raiser: item.hand_raiser,
        qualified:   item.qualified,
        unqualified: item.unqualified,
        prev:        item.prev_total,
    }));

    return (
        <Card className={`${CARD_CLASS} transition-opacity ${loading ? "opacity-50" : ""} ${className ?? ""}`}>
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-2">
                    <div>
                        <CardTitle className="text-lg font-black italic uppercase tracking-tight">{label}</CardTitle>
                        <p className="text-xs text-muted-foreground font-medium">Current tiers + prev total — grouped</p>
                    </div>
                    <PeriodToggle value={period} onChange={setPeriod} loading={loading} />
                </div>
                <div className="flex gap-4 mt-1 flex-wrap">
                    {TIERS.map((t) => (
                        <span key={t} className="flex items-center gap-1 text-[10px] font-bold text-zinc-500">
                            <span className="w-2 h-2 rounded-full inline-block" style={{ background: TIER_COLORS[t] }} />
                            {TIER_LABELS[t]}
                        </span>
                    ))}
                    <span className="flex items-center gap-1 text-[10px] font-bold text-zinc-500">
                        <span className="w-2 h-2 rounded-full inline-block bg-zinc-300 dark:bg-zinc-600" />
                        ◁ Prev total
                    </span>
                </div>
            </CardHeader>
            <CardContent className="pt-0">
                {items.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">No data for this period</p>
                ) : (
                    <>
                        {/* Delta summary list — quick scan */}
                        <div className="space-y-1.5 mb-4">
                            {items.slice(0, 5).map((item) => (
                                <div key={item.name} className="flex items-center gap-2 text-[11px]">
                                    <span className="w-28 truncate font-semibold shrink-0" title={item.name}>{item.name}</span>
                                    <span className="font-black">{item.total}</span>
                                    <DeltaBadge current={item.total} previous={item.prev_total} />
                                    <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden flex ml-1">
                                        {TIERS.map((t) => item[t] > 0 ? (
                                            <div key={t} className="h-full" style={{ width: `${(item[t] / (item.total || 1)) * 100}%`, background: TIER_COLORS[t] }} />
                                        ) : null)}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Grouped bar chart — current tier bars + previous total bar, NO stacking */}
                        <div className="h-[200px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart
                                    layout="vertical"
                                    data={chartData}
                                    margin={{ top: 0, right: 10, left: 0, bottom: 0 }}
                                    barCategoryGap="25%"
                                    barGap={2}
                                >
                                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="currentColor" className="opacity-[0.05]" />
                                    <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 10 }} />
                                    <YAxis
                                        dataKey="name"
                                        type="category"
                                        axisLine={false}
                                        tickLine={false}
                                        width={110}
                                        tick={{ fontSize: 10, fontWeight: 700 }}
                                    />
                                    <Tooltip cursor={{ fill: "transparent" }} content={({ active, payload, label: lbl }: any) => {
                                        if (!active || !payload?.length) return null;
                                        const item = items.find((i) => i.name.startsWith(lbl?.replace("…", "")));
                                        return (
                                            <div className="bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 p-3 rounded-xl shadow-xl min-w-[160px]">
                                                <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-2 truncate">{item?.name ?? lbl}</p>
                                                {payload.map((p: any) => (
                                                    <div key={p.dataKey} className="flex justify-between gap-4 text-xs">
                                                        <span style={{ color: p.fill }}>{p.dataKey === "prev" ? "◁ Previous" : (TIER_LABELS[p.dataKey as Tier] ?? p.dataKey)}</span>
                                                        <span className="font-black">{p.value}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        );
                                    }} />
                                    {/* Current period: 4 tier bars, grouped, NOT stacked */}
                                    {TIERS.map((t) => (
                                        <Bar key={t} dataKey={t} name={TIER_LABELS[t]} fill={TIER_COLORS[t]} radius={[0, 3, 3, 0]} maxBarSize={10} animationDuration={900} />
                                    ))}
                                    {/* Previous total — gray bar for comparison */}
                                    <Bar dataKey="prev" name="Previous total" fill="#94a3b8" radius={[0, 3, 3, 0]} maxBarSize={10} animationDuration={900} fillOpacity={0.5} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </>
                )}
            </CardContent>
        </Card>
    );
}

// ── Source comparison table ───────────────────────────────────────────────────

type SortKey = "hot" | "hand_raiser" | "qualified" | "unqualified" | "total";
type TabKey  = "competitors" | "keywords" | "channels";

const PREV_KEY: Record<SortKey, keyof TieredBreakdownItem> = {
    hot:         "prev_hot",
    hand_raiser: "prev_hand_raiser",
    qualified:   "prev_qualified",
    unqualified: "prev_unqualified",
    total:       "prev_total",
};

const TABLE_COLS: { key: SortKey; label: string }[] = [
    { key: "hot",         label: "🔥 Hot"       },
    { key: "hand_raiser", label: "🙋 Hand Raiser" },
    { key: "qualified",   label: "👀 Qualified"  },
    { key: "unqualified", label: "✗ Unqualified" },
    { key: "total",       label: "Total"         },
];

function SourceComparisonTable({ initialData }: { initialData: DashboardAnalytics }) {
    const { period, setPeriod, data, loading } = usePeriodData(initialData);
    const [tab,     setTab]     = useState<TabKey>("competitors");
    const [sortKey, setSortKey] = useState<SortKey>("total");
    const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

    const TABS: { key: TabKey; label: string }[] = [
        { key: "competitors", label: "Competitors"         },
        { key: "keywords",    label: "Keywords"            },
        { key: "channels",    label: "Discovery Channels"  },
    ];

    const rows = (
        tab === "competitors" ? data.competitor_breakdown :
        tab === "keywords"    ? data.keyword_breakdown    :
        data.source_breakdown.map((i) => ({ ...i, name: channelLabel(i.name) }))
    ).filter((i) => i.total > 0 || i.prev_total > 0);

    const sorted = [...rows].sort((a, b) => {
        const av = (a[sortKey] as number) ?? 0;
        const bv = (b[sortKey] as number) ?? 0;
        return sortDir === "desc" ? bv - av : av - bv;
    });

    const handleSort = (key: SortKey) => {
        if (sortKey === key) setSortDir((d) => d === "desc" ? "asc" : "desc");
        else { setSortKey(key); setSortDir("desc"); }
    };

    return (
        <Card className={`col-span-7 ${CARD_CLASS} transition-opacity ${loading ? "opacity-50" : ""}`}>
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div>
                        <CardTitle className="text-lg font-black italic uppercase tracking-tight">Source Breakdown</CardTitle>
                        <p className="text-xs text-muted-foreground font-medium">Current → previous with delta, per tier</p>
                    </div>
                    <PeriodToggle value={period} onChange={setPeriod} loading={loading} />
                </div>

                {/* Tabs */}
                <div className="flex gap-1 mt-2">
                    {TABS.map((t) => (
                        <button
                            key={t.key}
                            onClick={() => setTab(t.key)}
                            className={`px-3 py-1 text-xs font-bold rounded-full transition-colors ${
                                tab === t.key
                                    ? "bg-primary text-primary-foreground"
                                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                            }`}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>
            </CardHeader>

            <CardContent className="pt-0 overflow-x-auto">
                {sorted.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">No data for this period</p>
                ) : (
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-zinc-100 dark:border-zinc-800">
                                <th className="text-left py-2 pr-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest w-44">
                                    Source
                                </th>
                                {TABLE_COLS.map((col) => (
                                    <th
                                        key={col.key}
                                        onClick={() => handleSort(col.key)}
                                        className={`text-right py-2 px-3 text-[10px] font-bold uppercase tracking-widest cursor-pointer select-none whitespace-nowrap transition-colors ${
                                            sortKey === col.key
                                                ? "text-primary"
                                                : "text-muted-foreground hover:text-foreground"
                                        }`}
                                    >
                                        {col.label}
                                        {sortKey === col.key && (
                                            <span className="ml-1">{sortDir === "desc" ? "↓" : "↑"}</span>
                                        )}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {sorted.map((item) => (
                                <tr
                                    key={item.name}
                                    className="border-b border-zinc-50 dark:border-zinc-800/50 last:border-0 hover:bg-muted/30 transition-colors"
                                >
                                    {/* Source name */}
                                    <td className="py-2.5 pr-4">
                                        <span className="text-xs font-semibold truncate block max-w-[160px]" title={item.name}>
                                            {item.name}
                                        </span>
                                    </td>

                                    {/* Tier cells */}
                                    {TABLE_COLS.map((col) => {
                                        const curr = item[col.key] as number;
                                        const prev = item[PREV_KEY[col.key]] as number;
                                        const delta = curr - prev;
                                        const pct   = prev > 0 ? Math.round((delta / prev) * 100) : null;
                                        const color = col.key !== "total" ? TIER_COLORS[col.key as Tier] : undefined;

                                        return (
                                            <td key={col.key} className="py-2.5 px-3 text-right">
                                                <div className="flex flex-col items-end gap-0.5">
                                                    {/* current value */}
                                                    <span
                                                        className="text-sm font-black"
                                                        style={color ? { color } : undefined}
                                                    >
                                                        {curr}
                                                    </span>

                                                    {/* previous → delta */}
                                                    <div className="flex items-center gap-1 justify-end">
                                                        <span className="text-[10px] text-muted-foreground">→ {prev}</span>
                                                        {delta !== 0 && (
                                                            <span className={`text-[10px] font-black ${delta > 0 ? "text-emerald-600" : "text-red-500"}`}>
                                                                {delta > 0 ? "↑" : "↓"}
                                                                {pct !== null ? `${Math.abs(pct)}%` : Math.abs(delta)}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </CardContent>
        </Card>
    );
}

// ── AI Accuracy / Reclassification card ──────────────────────────────────────

const TIER_BADGE: Record<string, { label: string; color: string }> = {
    hot:         { label: "🔥 Hot",         color: TIER_COLORS.hot         },
    hand_raiser: { label: "🙋 Hand Raiser", color: TIER_COLORS.hand_raiser },
    qualified:   { label: "👀 Qualified",   color: TIER_COLORS.qualified   },
    unqualified: { label: "✗ Unqualified",  color: TIER_COLORS.unqualified },
};

function ReclassificationTable({ rows, emptyMsg }: {
    rows: ReclassificationItem[];
    emptyMsg: string;
}) {
    if (rows.length === 0) {
        return <p className="text-xs text-muted-foreground text-center py-4">{emptyMsg}</p>;
    }
    return (
        <table className="w-full text-xs">
            <thead>
                <tr className="border-b border-zinc-100 dark:border-zinc-800">
                    <th className="text-left py-1.5 pr-3 font-bold text-muted-foreground uppercase tracking-widest text-[10px]">Name</th>
                    <th className="text-left py-1.5 pr-3 font-bold text-muted-foreground uppercase tracking-widest text-[10px]">Basic AI</th>
                    <th className="text-right py-1.5 pr-3 font-bold text-muted-foreground uppercase tracking-widest text-[10px]">Research Score</th>
                    <th className="text-right py-1.5 font-bold text-muted-foreground uppercase tracking-widest text-[10px]">Report</th>
                </tr>
            </thead>
            <tbody>
                {rows.map((item, i) => {
                    const badge = TIER_BADGE[item.initial_tier];
                    const scoreColor = item.lead_score < 40 ? "#ef4444" : item.lead_score > 70 ? "#10b981" : "#f59e0b";
                    return (
                        <tr key={i} className="border-b border-zinc-50 dark:border-zinc-800/50 last:border-0 hover:bg-muted/30 transition-colors">
                            {/* Name + optional LinkedIn */}
                            <td className="py-2 pr-3">
                                <div className="flex items-center gap-1.5">
                                    <span className="font-semibold truncate max-w-[140px]">{item.name}</span>
                                    {item.linkedin_url && (
                                        <a href={item.linkedin_url} target="_blank" rel="noreferrer"
                                            className="text-muted-foreground hover:text-primary shrink-0" title="LinkedIn profile">
                                            <ExternalLink className="w-3 h-3" />
                                        </a>
                                    )}
                                </div>
                            </td>

                            {/* Basic AI tier badge */}
                            <td className="py-2 pr-3">
                                <span className="text-[10px] font-black px-1.5 py-0.5 rounded-full whitespace-nowrap"
                                    style={{ background: `${badge?.color}22`, color: badge?.color }}>
                                    {badge?.label ?? item.initial_tier}
                                </span>
                            </td>

                            {/* Research score */}
                            <td className="py-2 pr-3 text-right">
                                <span className="font-black text-sm" style={{ color: scoreColor }}>{item.lead_score}</span>
                                <span className="text-muted-foreground text-[10px] ml-0.5">/100</span>
                            </td>

                            {/* Deep report link */}
                            <td className="py-2 text-right">
                                {item.report_id ? (
                                    <Link href={`/reports?id=${item.report_id}`}
                                        className="inline-flex items-center gap-1 text-[10px] font-bold text-primary hover:underline whitespace-nowrap">
                                        <FileText className="w-3 h-3" />
                                        View
                                    </Link>
                                ) : (
                                    <span className="text-[10px] text-muted-foreground">—</span>
                                )}
                            </td>
                        </tr>
                    );
                })}
            </tbody>
        </table>
    );
}

function ReclassificationCard({ initialData }: { initialData: DashboardAnalytics }) {
    const { period, setPeriod, data, loading } = usePeriodData(initialData);
    const [tab, setTab] = useState<"overestimated" | "underestimated">("overestimated");
    const r = data.reclassification;

    return (
        <Card className={`col-span-7 ${CARD_CLASS} transition-opacity ${loading ? "opacity-50" : ""}`}>
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div>
                        <CardTitle className="text-lg font-black italic uppercase tracking-tight">AI Accuracy Check</CardTitle>
                        <p className="text-xs text-muted-foreground font-medium">
                            Basic classification vs deep research score — where did the AI get it wrong?
                        </p>
                    </div>
                    <PeriodToggle value={period} onChange={setPeriod} loading={loading} />
                </div>
            </CardHeader>
            <CardContent className="pt-0">
                {!r || r.total_with_reports === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                        No leads with both a basic classification and a deep research report in this period.
                    </p>
                ) : (
                    <>
                        {/* Summary stat row */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                            <div className="bg-muted/40 rounded-lg p-3">
                                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Leads Analysed</p>
                                <p className="text-2xl font-black mt-1">{r.total_with_reports}</p>
                            </div>
                            <div className="bg-emerald-500/10 rounded-lg p-3">
                                <p className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest">AI Accuracy</p>
                                <p className="text-2xl font-black mt-1 text-emerald-600">{r.accuracy_pct}%</p>
                                <p className="text-[10px] text-muted-foreground">{r.confirmed_high_count + r.confirmed_low_count} agreed</p>
                            </div>
                            <div className="bg-red-500/10 rounded-lg p-3">
                                <p className="text-[10px] font-bold text-red-500 uppercase tracking-widest">Overestimated</p>
                                <p className="text-2xl font-black mt-1 text-red-500">{r.overestimated_count}</p>
                                <p className="text-[10px] text-muted-foreground">said good → score &lt; 40</p>
                            </div>
                            <div className="bg-amber-500/10 rounded-lg p-3">
                                <p className="text-[10px] font-bold text-amber-600 uppercase tracking-widest">Hidden Gems</p>
                                <p className="text-2xl font-black mt-1 text-amber-600">{r.underestimated_count}</p>
                                <p className="text-[10px] text-muted-foreground">said unfit → score &gt; 70</p>
                            </div>
                        </div>

                        {/* Tab switcher */}
                        <div className="flex gap-1 mb-3">
                            <button
                                onClick={() => setTab("overestimated")}
                                className={`px-3 py-1 text-xs font-bold rounded-full transition-colors ${
                                    tab === "overestimated"
                                        ? "bg-red-500 text-white"
                                        : "bg-muted text-muted-foreground hover:bg-muted/80"
                                }`}
                            >
                                Overestimated ({r.overestimated_count})
                            </button>
                            <button
                                onClick={() => setTab("underestimated")}
                                className={`px-3 py-1 text-xs font-bold rounded-full transition-colors ${
                                    tab === "underestimated"
                                        ? "bg-amber-500 text-white"
                                        : "bg-muted text-muted-foreground hover:bg-muted/80"
                                }`}
                            >
                                Hidden Gems ({r.underestimated_count})
                            </button>
                        </div>

                        {tab === "overestimated" ? (
                            <>
                                <p className="text-[10px] text-muted-foreground mb-2">
                                    Basic AI classified these as <strong>hot / hand raiser / qualified</strong>, but deep research scored them below 40.
                                </p>
                                <ReclassificationTable
                                    rows={r.overestimated}
                                    emptyMsg="No overestimated leads in this period."
                                />
                            </>
                        ) : (
                            <>
                                <p className="text-[10px] text-muted-foreground mb-2">
                                    Basic AI classified these as <strong>unqualified</strong>, but deep research scored them above 70.
                                </p>
                                <ReclassificationTable
                                    rows={r.underestimated}
                                    emptyMsg="No hidden gems found in this period."
                                />
                            </>
                        )}
                    </>
                )}
            </CardContent>
        </Card>
    );
}

// ── Main export ───────────────────────────────────────────────────────────────

export function AnalyticsCharts({ initialData }: { initialData: DashboardAnalytics }) {
    return (
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-7">
            {/* Row 1: growth trend + overall tier comparison */}
            <TrendChart            initialData={initialData} />
            <PeriodComparisonChart initialData={initialData} />

            {/* Row 2: discovery channel comparison (full width) */}
            <DiscoverySourceChart  initialData={initialData} />

            {/* Row 3: keyword vs competitor breakdowns */}
            <SourceComparisonChart initialData={initialData} dataKey="keyword_breakdown"    label="Keyword Discovery"  className="col-span-4" />
            <SourceComparisonChart initialData={initialData} dataKey="competitor_breakdown" label="Competitor Sources"  className="col-span-3" />

            {/* Row 4: sortable comparison table per competitor / keyword / channel */}
            <SourceComparisonTable initialData={initialData} />

            {/* Row 5: AI accuracy — basic tier vs deep research score */}
            <ReclassificationCard initialData={initialData} />
        </div>
    );
}
