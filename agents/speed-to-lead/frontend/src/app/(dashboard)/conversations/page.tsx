"use client";

import { useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import useSWR from "swr";
import { formatDistanceToNow } from "date-fns";
import { Search, Bot, PauseCircle, ChevronRight, Filter } from "lucide-react";
import { fetchBrokers, fetchConversations } from "@/lib/api";
import { useRole } from "@/hooks/use-role";
import { useFirm } from "@/hooks/use-firm";
import { StageBadge } from "@/components/stage-badge";
import { initials, displayName } from "@/lib/utils";
import type { BrokerRow, Lead } from "@/types";

const STAGES = ["", "discovery", "qualification", "portfolio_match", "consideration", "booking", "conversion"];

const VERTICAL_LABELS: Record<string, string> = {
  interior:    "Interior",
  real_estate: "Real Estate",
  solar:       "Solar",
};

function Avatar({ lead }: { lead: Lead }) {
  return (
    <div className="w-10 h-10 rounded-full bg-accent text-on-accent flex items-center justify-center text-xs font-semibold flex-shrink-0">
      {initials(lead.lead_name, lead.phone)}
    </div>
  );
}

export default function ConversationsPage() {
  const router = useRouter();
  const params = useSearchParams();
  const { firmId } = useFirm();
  const { role } = useRole();
  const isAgent = role === "agent";
  const [owner, setOwner] = useState(params.get("owner") ?? "");
  const [search, setSearch] = useState("");
  const [stage, setStage] = useState("");
  const [aiPausedOnly, setAiPausedOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState({ search: "", stage: "", aiPausedOnly: false, owner: params.get("owner") ?? "" });

  const { data: people } = useSWR<BrokerRow[]>(
    !isAgent && firmId ? ["people", firmId] : null,
    () => fetchBrokers(firmId!),
  );

  const { data, isLoading } = useSWR(
    ["conversations", firmId, query, page],
    () => fetchConversations({
      firm_id: firmId ?? undefined,
      page,
      search: query.search || undefined,
      stage: query.stage || undefined,
      ai_paused: query.aiPausedOnly ? true : undefined,
      owner_id: query.owner || undefined,
    }),
    { refreshInterval: 15_000 },
  );

  const applyFilters = useCallback(() => {
    setPage(1);
    setQuery({ search, stage, aiPausedOnly, owner });
  }, [search, stage, aiPausedOnly, owner]);

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-ink">{isAgent ? "My conversations" : "Conversations"}</h1>
          <p className="text-sm text-muted mt-1">
            {isAgent ? "Buyers who messaged your numbers" : "All WhatsApp lead threads"}
          </p>
        </div>
        {data && <span className="text-sm text-muted font-medium">{data.length} shown</span>}
      </div>

      {/* Filters */}
      <div className="bg-card rounded-2xl border border-line shadow-sm p-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && applyFilters()}
            placeholder="Search name or phone…"
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-line text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition"
          />
        </div>

        <div className="flex items-center gap-1.5">
          <Filter className="w-3.5 h-3.5 text-muted" />
          <select
            value={stage}
            onChange={(e) => setStage(e.target.value)}
            className="py-2 pl-2 pr-7 rounded-lg border border-line text-sm text-ink/80 focus:outline-none focus:ring-2 focus:ring-accent/20 bg-card cursor-pointer"
          >
            {STAGES.map((s) => (
              <option key={s} value={s}>
                {s ? s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) : "All stages"}
              </option>
            ))}
          </select>
        </div>

        {!isAgent && people && people.length > 0 && (
          <select
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
            className="py-2 pl-2 pr-7 rounded-lg border border-line text-sm text-ink/80 focus:outline-none focus:ring-2 focus:ring-accent/20 bg-card cursor-pointer"
          >
            <option value="">All people</option>
            {people.map((p) => (
              <option key={p.id} value={p.id}>{p.name}{p.kind === "team" ? " (team)" : ""}</option>
            ))}
          </select>
        )}

        <label className="flex items-center gap-2 cursor-pointer text-sm text-ink/80 select-none">
          <input
            type="checkbox"
            checked={aiPausedOnly}
            onChange={(e) => setAiPausedOnly(e.target.checked)}
            className="rounded border-line"
          />
          AI paused only
        </label>

        <button
          onClick={applyFilters}
          className="px-4 py-2 bg-accent text-on-accent text-sm font-medium rounded-lg hover:bg-accent-hover transition"
        >
          Search
        </button>
      </div>

      {/* Table */}
      <div className="bg-card rounded-2xl border border-line shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line">
                {["Lead", "Phone", "Config / Type", ...(isAgent ? [] : ["Owner"]), "Stage", "Turn", "Last Active", "AI Status", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: isAgent ? 8 : 9 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 bg-bg animate-pulse rounded-full w-20" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : data?.length === 0 ? (
                <tr>
                  <td colSpan={isAgent ? 8 : 9} className="px-4 py-16 text-center text-muted text-sm">
                    No conversations found
                  </td>
                </tr>
              ) : (
                data?.map((lead: Lead, idx: number) => (
                  <tr
                    key={`${lead.id}-${idx}`}
                    className="hover:bg-bg transition cursor-pointer"
                    onClick={() => router.push(`/conversations/${lead.id}`)}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <Avatar lead={lead} />
                        <span className="font-medium text-ink whitespace-nowrap">{displayName(lead)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted font-mono text-xs">{lead.phone}</td>
                    <td className="px-4 py-3">
                      {lead.config || lead.lead_type ? (
                        <div className="flex flex-col gap-0.5">
                          {lead.config && <span className="font-medium text-ink">{lead.config}</span>}
                          {lead.lead_type && (
                            <span className="text-[11px] text-muted uppercase">
                              {VERTICAL_LABELS[lead.lead_type] ?? lead.lead_type}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-muted">-</span>
                      )}
                    </td>
                    {!isAgent && (
                      <td className="px-4 py-3">
                        {lead.owner_name ? (
                          <div className="flex flex-col gap-0.5">
                            <span className="text-ink whitespace-nowrap">{lead.owner_name}</span>
                            <span className="text-[11px] text-muted whitespace-nowrap">
                              {lead.number_label ?? (lead.owner_kind === "team" ? "Team" : "Partner")}
                            </span>
                          </div>
                        ) : (
                          <span className="text-muted text-xs">Main number</span>
                        )}
                      </td>
                    )}
                    <td className="px-4 py-3">
                      <StageBadge stage={lead.stage} />
                    </td>
                    <td className="px-4 py-3 text-ink/70 tabular-nums">{lead.turn_count ?? "-"}</td>
                    <td className="px-4 py-3 text-muted whitespace-nowrap text-xs">
                      {formatDistanceToNow(new Date(lead.last_active), { addSuffix: true })}
                    </td>
                    <td className="px-4 py-3">
                      {lead.ai_paused ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-warning bg-warning/10 border border-warning/30 px-2 py-0.5 rounded-full">
                          <PauseCircle className="w-3 h-3" /> Paused
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-success bg-success/10 border border-success/30 px-2 py-0.5 rounded-full">
                          <Bot className="w-3 h-3" /> Active
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <ChevronRight className="w-4 h-4 text-muted" />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {data && data.length >= 30 && (
          <div className="border-t border-line px-4 py-3 flex items-center justify-between">
            <button disabled={page === 1} onClick={() => setPage((p) => p - 1)} className="text-sm text-ink/70 font-medium disabled:opacity-40">← Previous</button>
            <span className="text-xs text-muted">Page {page}</span>
            <button onClick={() => setPage((p) => p + 1)} className="text-sm text-ink/70 font-medium">Next →</button>
          </div>
        )}
      </div>
    </div>
  );
}
