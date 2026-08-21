import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function normalizeUrl(url: string | undefined | null): string {
  if (!url) return "";
  try {
    let normalized = url.trim();

    // Add https if missing for parsing
    if (!normalized.startsWith('http://') && !normalized.startsWith('https://')) {
      normalized = 'https://' + normalized;
    }

    const urlObj = new URL(normalized);

    // Standardize domain: lowercase, remove www.
    let host = urlObj.hostname.toLowerCase();
    if (host.startsWith('www.')) {
      host = host.slice(4);
    }

    // Standardize path: remove trailing slash
    let path = urlObj.pathname;
    if (path.endsWith('/') && path.length > 1) {
      path = path.slice(0, -1);
    }

    // Reconstruct without query/frag
    return `https://${host}${path}`;
  } catch (e) {
    // Fallback logic
    if (!url) return "";
    let fallback = url.split('?')[0].split('#')[0].trim();
    if (fallback.endsWith('/')) {
      fallback = fallback.slice(0, -1);
    }
    return fallback;
  }
}

export function ensureProtocol(url: string | undefined | null): string {
  if (!url) return "";
  let trimmed = url.trim();
  if (!/^https?:\/\//i.test(trimmed)) {
    return `https://${trimmed}`;
  }
  return trimmed;
}
