"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, FilePlus, ClipboardList, Zap, Settings, Inbox } from "lucide-react";
import clsx from "clsx";

const NAV = [
  { href: "/dashboard", label: "Dashboard",   icon: LayoutDashboard },
  { href: "/submit",    label: "Submit RFQ",  icon: FilePlus },
  { href: "/rfqs",      label: "All RFQs",    icon: ClipboardList },
  { href: "/inbox",     label: "Email Inbox", icon: Inbox },
  { href: "/settings",  label: "Settings",    icon: Settings },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="fixed inset-y-0 left-0 w-[240px] flex flex-col z-50 bg-brand-card border-r border-brand-border">

      {/* Brand */}
      <div className="px-5 py-6 border-b border-brand-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-teal-500/10 border border-teal-500/20">
            <Zap size={15} className="text-teal-400" />
          </div>
          <div>
            <p className="text-brand-text font-semibold text-sm leading-tight">RFQ Agent</p>
            <p className="text-brand-muted text-[11px] mt-0.5">by InnovizeAI</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-5 space-y-0.5">
        <p className="text-brand-muted text-[10px] font-semibold uppercase tracking-widest px-3 mb-3">Menu</p>
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = path === href || path.startsWith(href + "/");
          return (
            <Link key={href} href={href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all relative",
                active
                  ? "bg-teal-500/10 text-teal-400"
                  : "text-brand-muted hover:text-brand-text hover:bg-brand-elevated"
              )}>
              {active && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full bg-teal-500" />
              )}
              <span className={clsx(
                "w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 transition-all",
                active ? "text-teal-400" : "text-brand-muted"
              )}>
                <Icon size={15} />
              </span>
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Live indicator */}
      <div className="px-5 py-5 border-t border-brand-border">
        <div className="flex items-center gap-2.5">
          <span className="w-2 h-2 rounded-full bg-teal-400 pulse-dot" />
          <span className="text-brand-muted text-[11px]">Agent online</span>
        </div>
      </div>
    </aside>
  );
}
