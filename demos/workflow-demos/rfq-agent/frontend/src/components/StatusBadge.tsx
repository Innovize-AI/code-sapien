import clsx from "clsx";

const MAP: Record<string, { label: string; cls: string; dot: string }> = {
  dispatched:     { label: "Dispatched",   cls: "bg-teal-500/10 text-teal-400 border border-teal-500/20",   dot: "bg-teal-400" },
  pending_review: { label: "Needs Review", cls: "bg-amber-500/10 text-amber-400 border border-amber-500/20", dot: "bg-amber-400" },
  processing:     { label: "Processing",   cls: "bg-blue-500/10 text-blue-400 border border-blue-500/20",    dot: "bg-blue-400" },
  failed:         { label: "Failed",       cls: "bg-red-500/10 text-red-400 border border-red-500/20",       dot: "bg-red-500" },
  rejected:       { label: "Rejected",     cls: "bg-brand-elevated text-brand-muted border border-brand-border", dot: "bg-brand-muted" },
};

export default function StatusBadge({ status }: { status: string }) {
  const cfg = MAP[status] ?? { label: status, cls: "bg-brand-elevated text-brand-muted border border-brand-border", dot: "bg-brand-muted" };
  return (
    <span className={clsx("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold", cfg.cls)}>
      <span className={clsx("w-1.5 h-1.5 rounded-full flex-shrink-0", cfg.dot,
        status === "processing" && "pulse-dot")} />
      {cfg.label}
    </span>
  );
}
