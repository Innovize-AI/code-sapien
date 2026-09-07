import type { RFQStatus } from "./types";

export function fmt_inr(value: number | null | undefined): string {
  if (value == null) return "—";
  return "₹" + value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function fmt_pct(value: number | null | undefined): string {
  if (value == null) return "—";
  return Math.round(value * 100) + "%";
}

export function fmt_date(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export const STATUS_LABELS: Record<RFQStatus, string> = {
  dispatched: "Auto-Dispatched",
  pending_review: "Pending Review",
  processing: "Processing",
  failed: "Failed",
  approved: "Approved",
  rejected: "Rejected",
};

export const STATUS_COLORS: Record<RFQStatus, string> = {
  dispatched: "bg-emerald-100 text-emerald-800",
  pending_review: "bg-amber-100 text-amber-800",
  processing: "bg-blue-100 text-blue-800",
  failed: "bg-red-100 text-red-800",
  approved: "bg-emerald-100 text-emerald-800",
  rejected: "bg-red-100 text-red-800",
};

export const URGENCY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  rush: "bg-orange-100 text-orange-700",
  standard: "bg-slate-100 text-slate-600",
};

export async function downloadPdf(rfqId: string) {
  const res = await fetch(`/api/rfq/${rfqId}/pdf`);
  if (!res.ok) throw new Error("PDF generation failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `quote-${rfqId.slice(0, 8).toUpperCase()}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export const TRUCK_LABELS: Record<string, string> = {
  mini: "Mini Truck / Tempo (< 1 ton)",
  medium: "Medium Truck / Canter (1–5 ton)",
  large: "Large Truck (5–15 ton)",
  trailer: "Trailer / Multi-axle (15+ ton)",
};
