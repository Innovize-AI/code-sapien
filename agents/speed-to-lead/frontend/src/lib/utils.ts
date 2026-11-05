import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function initials(name: string | null, phone: string): string {
  if (!name) return phone.slice(-4);
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

export function displayName(lead: { lead_name?: string | null; wa_name: string | null; phone: string }): string {
  return lead.lead_name ?? lead.wa_name ?? lead.phone;
}
