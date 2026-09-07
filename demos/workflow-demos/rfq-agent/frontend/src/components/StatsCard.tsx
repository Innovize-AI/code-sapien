import type { ReactNode } from "react";

interface Props {
  label: string;
  value: string | number;
  sub?: string;
  icon: ReactNode;
  accent: string;
  iconColor: string;
  trend?: string;
}

export default function StatsCard({ label, value, sub, icon, accent, iconColor, trend }: Props) {
  return (
    <div className="bg-brand-card rounded-2xl p-5 border border-brand-border">
      <div className="flex items-start justify-between mb-4">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${accent}`}>
          <span className={iconColor}>{icon}</span>
        </div>
        {trend && (
          <span className="text-xs font-semibold text-teal-400 bg-teal-500/10 border border-teal-500/20 px-2 py-0.5 rounded-full">{trend}</span>
        )}
      </div>
      <p className="text-2xl font-bold text-brand-text tracking-tight">{value}</p>
      <p className="text-sm text-brand-muted mt-0.5 font-medium">{label}</p>
      {sub && <p className="text-xs mt-0.5" style={{ color: "#444" }}>{sub}</p>}
    </div>
  );
}
