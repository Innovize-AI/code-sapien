"use client";

import useSWR from "swr";
import Link from "next/link";
import { fetchFirms } from "@/lib/api";
import type { Firm, Vertical } from "@/types";
import { Building2, Sun, Home, Plus, CheckCircle2, XCircle, Settings } from "lucide-react";

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

function FirmCard({ firm }: { firm: Firm }) {
  const Icon = VERTICAL_ICON[firm.vertical] ?? Building2;
  const color = VERTICAL_COLOR[firm.vertical] ?? "var(--muted)";

  return (
    <div className="bg-card rounded-2xl border border-line shadow-sm p-5 flex items-start gap-4 hover:border-ink/20 transition">
      <div
        className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)`, border: `1.5px solid color-mix(in srgb, ${color} 28%, transparent)` }}
      >
        <Icon className="w-6 h-6" style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-ink truncate">{firm.firm_display_name}</h3>
          {firm.is_active ? (
            <span className="flex items-center gap-1 text-[10px] font-medium text-success bg-success/10 border border-success/30 px-1.5 py-0.5 rounded-full">
              <CheckCircle2 className="w-3 h-3" /> Active
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] font-medium text-muted bg-bg border border-line px-1.5 py-0.5 rounded-full">
              <XCircle className="w-3 h-3" /> Inactive
            </span>
          )}
        </div>
        <p className="text-xs text-muted mt-0.5">{VERTICAL_LABEL[firm.vertical]}</p>
        <p className="text-xs text-muted mt-1 font-mono truncate">
          {firm.wa_phone_number_id ?? <span className="italic">No WA phone ID configured</span>}
        </p>
      </div>
      <Link
        href={`/admin/firms/${firm.id}`}
        className="flex items-center gap-1.5 text-xs text-muted hover:text-ink/80 border border-line hover:border-ink/30 rounded-lg px-2.5 py-1.5 transition"
      >
        <Settings className="w-3.5 h-3.5" />
        Edit
      </Link>
    </div>
  );
}

export default function FirmsPage() {
  const { data: firms, isLoading } = useSWR<Firm[]>("all-firms", fetchFirms);

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Firms</h1>
          <p className="text-sm text-muted mt-1">Manage client firms and their WhatsApp AI agents</p>
        </div>
        <Link
          href="/admin/firms/new"
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-accent text-on-accent text-sm font-medium hover:bg-accent-hover transition"
        >
          <Plus className="w-4 h-4" />
          Add firm
        </Link>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[0, 1, 2].map(i => (
            <div key={i} className="h-20 bg-bg animate-pulse rounded-2xl" />
          ))}
        </div>
      ) : !firms?.length ? (
        <div className="text-center py-16 bg-card rounded-2xl border border-line">
          <Building2 className="w-10 h-10 text-muted mx-auto mb-3" />
          <p className="text-muted font-medium">No firms yet</p>
          <p className="text-sm text-muted mt-1">Add your first client firm to get started.</p>
          <Link
            href="/admin/firms/new"
            className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-xl bg-accent text-on-accent text-sm font-medium hover:bg-accent-hover transition"
          >
            <Plus className="w-4 h-4" />
            Add firm
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {firms.map(f => <FirmCard key={f.id} firm={f} />)}
        </div>
      )}
    </div>
  );
}
