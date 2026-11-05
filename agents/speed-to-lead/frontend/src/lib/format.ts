// Date helpers for the registry. Everything is shown in IST because that is the time a
// broker and a sales head will quote when they dispute who registered a client first.

const IST_FULL = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit", month: "short", year: "numeric",
  hour: "numeric", minute: "2-digit", hour12: true, timeZone: "Asia/Kolkata",
});
const IST_SHORT = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit", month: "short",
  hour: "numeric", minute: "2-digit", hour12: true, timeZone: "Asia/Kolkata",
});
const IST_DATE = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit", month: "short", year: "numeric", timeZone: "Asia/Kolkata",
});

export function fmtIST(iso: string | null | undefined, style: "full" | "short" | "date" = "short"): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "-";
  const f = style === "full" ? IST_FULL : style === "date" ? IST_DATE : IST_SHORT;
  return f.format(d).replace(/\bam\b/, "AM").replace(/\bpm\b/, "PM");
}

/** "19 h later", "3 d 2 h later": how long after the first claim a later one arrived. */
export function gapLabel(firstIso: string, laterIso: string): string {
  const ms = new Date(laterIso).getTime() - new Date(firstIso).getTime();
  if (!Number.isFinite(ms) || ms < 0) return "";
  const mins = Math.round(ms / 60000);
  if (mins < 60) return `${mins} min later`;
  const hours = Math.floor(mins / 60);
  if (hours < 48) return `${hours} h ${mins % 60 ? `${mins % 60} min ` : ""}later`.replace("  ", " ");
  const days = Math.floor(hours / 24);
  return `${days} d ${hours % 24} h later`;
}

export function seconds(s: number | null | undefined): string {
  if (s == null) return "-";
  if (s < 90) return `${Math.round(s)} s`;
  if (s < 5400) return `${Math.round(s / 60)} min`;
  return `${(s / 3600).toFixed(1)} h`;
}

export function pct(x: number | null | undefined): string {
  return x == null ? "-" : `${Math.round(x * 100)}%`;
}
