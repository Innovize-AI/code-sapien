import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function normalizeUrl(url: string | undefined | null): string {
  if (!url) return "";
  try {
    // Remove query parameters
    let normalized = url.split('?')[0];
    // Remove trailing slash
    if (normalized.endsWith('/')) {
      normalized = normalized.slice(0, -1);
    }
    return normalized.trim();
  } catch (e) {
    return url || "";
  }
}
