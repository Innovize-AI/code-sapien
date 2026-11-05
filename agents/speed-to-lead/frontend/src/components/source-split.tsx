"use client";

import useSWR from "swr";
import Link from "next/link";
import { AlertTriangle, ArrowRight, Megaphone, Handshake, Globe } from "lucide-react";
import { fetchSourceSplit } from "@/lib/api";
import { pct, seconds } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { SourceBucket, SourceSplit } from "@/types";

const SOURCE: Record<SourceBucket["source"], { label: string; icon: React.ElementType; bar: string }> = {
  ad:      { label: "Ads",              icon: Megaphone, bar: "bg-chart-2" },
  broker:  { label: "Channel partners", icon: Handshake, bar: "bg-chart-1" },
  organic: { label: "Organic and direct", icon: Globe,   bar: "bg-chart-5" },
};

/**
 * Where leads come from, how fast each was answered, and how many became visits.
 * Ads and partner leads reach the same sales team, so the comparison is the point.
 */
export function SourceSplitPanel({ firmId, compact = false }: { firmId: string; compact?: boolean }) {
  const { data } = useSWR<SourceSplit>(
    `source-split-${firmId}`,
    () => fetchSourceSplit(firmId, 30),
    { refreshInterval: 30_000 },
  );

  const total = data ? data.sources.reduce((s, b) => s + b.leads, 0) : 0;

  return (
    <div className={cn("bg-card border border-line", compact ? "rounded-xl p-4" : "rounded-2xl p-6")}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="label">Lead sources, last 30 days</p>
          <h2 className={cn("font-semibold text-ink tracking-[-0.02em] mt-1", compact ? "text-sm" : "text-base")}>
            Where buyers come from and how fast they hear back
          </h2>
        </div>
        {data && data.open_conflicts > 0 && (
          <Link
            href="/registrations"
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-warning/10 border border-warning/30 text-xs font-medium text-warning flex-shrink-0"
          >
            <AlertTriangle className="w-3.5 h-3.5" strokeWidth={1.75} />
            {data.open_conflicts} open {data.open_conflicts === 1 ? "conflict" : "conflicts"}
            <ArrowRight className="w-3.5 h-3.5" strokeWidth={1.75} />
          </Link>
        )}
      </div>

      {/* Share of leads */}
      <div className="mt-4 h-2 rounded-full bg-bg overflow-hidden flex">
        {data && total > 0 && data.sources.map(b => (
          <div
            key={b.source}
            className={SOURCE[b.source].bar}
            style={{ width: `${(b.leads / total) * 100}%` }}
            title={`${SOURCE[b.source].label}: ${b.leads}`}
          />
        ))}
      </div>

      <div className={cn("mt-4 grid gap-3", compact ? "grid-cols-1" : "grid-cols-1 md:grid-cols-3")}>
        {!data && [0, 1, 2].map(i => <div key={i} className="h-24 bg-bg animate-pulse rounded-xl" />)}
        {data?.sources.map(b => {
          const S = SOURCE[b.source];
          return (
            <div key={b.source} className="rounded-xl border border-line p-4">
              <div className="flex items-center gap-2 text-muted">
                <span className={cn("w-2 h-2 rounded-full", S.bar)} />
                <S.icon className="w-3.5 h-3.5" strokeWidth={1.75} />
                <span className="text-xs font-medium text-ink/80">{S.label}</span>
              </div>
              <p className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-ink tabular-nums">{b.leads}</p>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div>
                  <dt className="text-muted">Visit rate</dt>
                  <dd className="mono text-ink mt-0.5">{pct(b.visit_rate)}</dd>
                </div>
                <div>
                  <dt className="text-muted">First reply</dt>
                  <dd className="mono text-ink mt-0.5">{seconds(b.median_first_reply_seconds)}</dd>
                </div>
              </dl>
            </div>
          );
        })}
      </div>
    </div>
  );
}
