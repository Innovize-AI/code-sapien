"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  CalendarCheck,
  LogOut,
  Building2,
  Sun,
  Home,
  ShieldCheck,
  UserCog,
  Eye,
  Plus,
  Handshake,
  ScrollText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { createClient } from "@/lib/supabase";
import { useRole } from "@/hooks/use-role";
import { useFirm } from "@/hooks/use-firm";
import type { Vertical } from "@/types";

const ROLE_CONFIG = {
  admin:     { label: "Admin",     icon: ShieldCheck },
  counselor: { label: "Counselor", icon: UserCog     },
  agent:     { label: "Agent",     icon: UserCog     },
  viewer:    { label: "Viewer",    icon: Eye         },
};

const VERTICAL_ICON: Record<Vertical, React.ElementType> = {
  interior:    Home,
  real_estate: Building2,
  solar:       Sun,
};
const VERTICAL_LABEL: Record<Vertical, string> = {
  interior:    "Interior Design",
  real_estate: "Real Estate",
  solar:       "Solar",
};

const ADMIN_NAV = [
  { href: "/dashboard",    icon: LayoutDashboard, label: "Analytics" },
  { href: "/admin/firms",  icon: Building2,       label: "Firms"     },
];

const STAFF_NAV = [
  { href: "/dashboard",     icon: LayoutDashboard, label: "Analytics"     },
  { href: "/conversations", icon: MessageSquare,   label: "Conversations" },
  { href: "/visits",        icon: CalendarCheck,   label: "Visits"        },
];

// An agent (partner or team member) sees only their own conversations and visits
const AGENT_NAV = [
  { href: "/conversations", icon: MessageSquare, label: "My conversations" },
  { href: "/visits",        icon: CalendarCheck, label: "My visits"        },
];

// Partner and team tools only make sense for a real estate firm
const BROKER_NAV = [
  { href: "/brokers",       icon: Handshake,  label: "Partners and team" },
  { href: "/registrations", icon: ScrollText, label: "Registry"         },
];

export function Sidebar() {
  const pathname = usePathname();
  const { name, email, role, loading: roleLoading } = useRole();
  const { firm, firmId, demoMode, allFirms, switchFirm } = useFirm();

  const [signingOut, setSigningOut] = useState(false);

  const isAdmin  = role === "admin";
  const vertical = firm?.vertical;
  const nav      = isAdmin
    ? ADMIN_NAV
    : role === "agent"
      ? AGENT_NAV
      : vertical === "real_estate"
        ? [...STAFF_NAV, ...BROKER_NAV]
        : STAFF_NAV;
  const roleCfg  = ROLE_CONFIG[role] ?? ROLE_CONFIG.viewer;
  const RoleIcon = roleCfg.icon;

  const VertIcon = vertical ? VERTICAL_ICON[vertical] : Building2;

  async function signOut() {
    if (signingOut) return;
    setSigningOut(true);
    const sb = createClient();
    // scope:'local' clears the cookie instantly without a network round-trip
    await sb.auth.signOut({ scope: "local" });
    window.location.replace("/login");
  }

  return (
    <aside className="w-64 flex-shrink-0 flex flex-col h-full bg-card border-r border-line">

      {/* Product wordmark: Geist 600, tight tracking, ledger green (guidelines.md) */}
      <div className="px-6 py-5 border-b border-line">
        <p className="text-[20px] font-semibold tracking-[-0.03em] leading-none text-accent">
          Speed to Lead
        </p>
        <p className="label mt-2">Innovize AI</p>
      </div>

      {/* Firm display (staff only) */}
      {!isAdmin && (
        <div className="px-3 pt-3 pb-2 border-b border-line">
          {firm ? (
            <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-bg">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 bg-accent/10 text-accent">
                <VertIcon className="w-3.5 h-3.5" strokeWidth={1.75} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-ink truncate">{firm.firm_display_name}</p>
                {vertical && <p className="text-[10px] text-muted">{VERTICAL_LABEL[vertical]}</p>}
              </div>
            </div>
          ) : (
            <div className="h-11 rounded-xl bg-bg animate-pulse" />
          )}
          {demoMode && allFirms.length > 0 && (
            <label className="block mt-2">
              <span className="label">Demo firm</span>
              <select
                value={firmId ?? ""}
                onChange={e => switchFirm(e.target.value)}
                className="mt-1 w-full rounded-lg border border-line bg-card px-2 py-1.5 text-xs text-ink focus:outline-none focus:ring-2 focus:ring-accent"
              >
                {allFirms.map(f => (
                  <option key={f.id} value={f.id}>{f.firm_display_name || f.name}</option>
                ))}
              </select>
            </label>
          )}
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
        {nav.map(({ href, icon: Icon, label }) => {
          const active =
            href === "/dashboard"
              ? pathname === href
              : pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                active
                  ? "bg-accent text-on-accent"
                  : "text-ink/70 hover:bg-bg hover:text-ink",
              )}
            >
              <Icon className="w-4 h-4 flex-shrink-0" strokeWidth={1.75} />
              {label}
            </Link>
          );
        })}

        {/* Admin: quick-add firm */}
        {isAdmin && (
          <Link
            href="/admin/firms/new"
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors mt-1",
              pathname === "/admin/firms/new"
                ? "bg-accent text-on-accent"
                : "text-muted hover:bg-bg hover:text-ink",
            )}
          >
            <Plus className="w-4 h-4 flex-shrink-0" strokeWidth={1.75} />
            Add firm
          </Link>
        )}
      </nav>

      {/* User + sign out */}
      <div className="px-3 py-4 border-t border-line space-y-1">
        {!roleLoading && (
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-bg mb-2">
            <div className="w-8 h-8 rounded-full bg-accent/10 border border-line flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-semibold text-accent">
                {name ? name.charAt(0).toUpperCase() : "?"}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-ink truncate">{name || email}</p>
              <div className="flex items-center gap-1 mt-0.5 text-muted">
                <RoleIcon className="w-3 h-3 flex-shrink-0" strokeWidth={1.75} />
                <span className="text-[11px] font-medium">{roleCfg.label}</span>
              </div>
            </div>
          </div>
        )}

        <button
          onClick={signOut}
          disabled={signingOut}
          className="flex w-full items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium text-muted hover:bg-bg hover:text-ink transition-colors disabled:opacity-50"
        >
          <LogOut className="w-4 h-4" strokeWidth={1.75} />
          {signingOut ? "Signing out" : "Sign out"}
        </button>
      </div>
    </aside>
  );
}
