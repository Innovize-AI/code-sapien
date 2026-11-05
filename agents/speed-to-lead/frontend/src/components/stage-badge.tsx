import { cn } from "@/lib/utils";

const STAGE_CONFIG: Record<string, { label: string; className: string }> = {
  discovery:      { label: "Discovery",      className: "bg-cost/10 text-cost"    },
  qualification:  { label: "Qualification",  className: "bg-chart-4/10 text-chart-4" },
  portfolio_match:{ label: "Portfolio",      className: "bg-chart-4/10 text-chart-4" },
  consideration:  { label: "Consideration",  className: "bg-chart-3/10 text-ink"  },
  booking:        { label: "Booking",        className: "bg-accent/10 text-accent" },
  conversion:     { label: "Converted",      className: "bg-success/10 text-success"  },
};

export function StageBadge({ stage }: { stage: string | null | undefined }) {
  if (!stage) return <span className="text-xs text-muted">-</span>;
  const cfg = STAGE_CONFIG[stage] ?? { label: stage, className: "bg-bg text-ink/70" };
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium", cfg.className)}>
      {cfg.label}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, string> = {
    new:              "bg-cost/10 text-cost border border-line",
    active:           "bg-success/10 text-success border border-success/30",
    warm:             "bg-warning/10 text-warning border border-warning/30",
    cold:             "bg-bg text-muted border border-line",
    visit_scheduled:  "bg-success/10 text-success border border-success/30",
    converted:        "bg-chart-4/10 text-chart-4 border border-line",
  };
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium capitalize", cfg[status] ?? "bg-bg text-ink/70")}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
