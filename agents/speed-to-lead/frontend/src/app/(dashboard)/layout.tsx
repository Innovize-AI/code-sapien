"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Menu, X } from "lucide-react";
import { Sidebar } from "@/components/sidebar";
import { useRole } from "@/hooks/use-role";

// An agent (partner or team member) may open only their own conversations and visits
const AGENT_PATHS = ["/conversations", "/visits"];

// Desktop (lg and up): fixed sidebar. Below that: a top bar with a menu button and a slide-in drawer.
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { role, loading } = useRole();

  // Send an agent back to their conversations if they open a page that is not theirs
  useEffect(() => {
    if (loading || role !== "agent") return;
    if (!AGENT_PATHS.some(p => pathname === p || pathname.startsWith(p + "/"))) {
      router.replace("/conversations");
    }
  }, [loading, role, pathname, router]);

  // Close the drawer after navigating, and on Escape
  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="flex h-full">
      <div className="hidden lg:block h-full flex-shrink-0">
        <Sidebar />
      </div>

      {/* Mobile top bar */}
      <header className="lg:hidden fixed top-0 inset-x-0 h-14 z-40 bg-card border-b border-line flex items-center gap-3 px-4">
        <button
          onClick={() => setOpen(true)}
          aria-label="Open menu"
          className="p-2 -ml-2 rounded-lg text-ink hover:bg-bg"
        >
          <Menu className="w-5 h-5" strokeWidth={1.75} />
        </button>
        <p className="text-[17px] font-semibold tracking-[-0.03em] text-accent">Speed to Lead</p>
      </header>

      {/* Mobile drawer */}
      {open && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="relative h-full shadow-xl">
            <Sidebar />
            <button
              onClick={() => setOpen(false)}
              aria-label="Close menu"
              className="absolute top-4 right-3 p-1.5 rounded-lg text-muted hover:bg-bg hover:text-ink"
            >
              <X className="w-5 h-5" strokeWidth={1.75} />
            </button>
          </div>
          <button
            aria-label="Close menu"
            onClick={() => setOpen(false)}
            className="flex-1 bg-ink/40"
          />
        </div>
      )}

      <main className="flex-1 min-w-0 overflow-y-auto bg-bg pt-14 lg:pt-0">
        {children}
      </main>
    </div>
  );
}
