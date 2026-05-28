"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import {
  BarChart3,
  Search,
  Settings,
  Home,
  History,
  Plus,
  Users,
  Link2,
  UserCheck,
  BookOpen,
  LogOut,
  Zap,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface SidebarItem {
  title: string;
  href: string;
  icon: any;
  comingSoon?: boolean;
  roles?: string[];
}

const sidebarItems: SidebarItem[] = [
  {
    title: "Dashboard",
    href: "/",
    icon: Home,
  },
  {
    title: "Find Leads",
    href: "/find-leads",
    icon: Search,
  },
  {
    title: "Identified Profiles",
    href: "/profiles",
    icon: UserCheck,
  },
  {
    title: "Autopilot",
    href: "/autopilot",
    icon: Zap,
  },
  {
    title: "Analyze Lead",
    href: "/analyze",
    icon: BarChart3,
  },
  {
    title: "History",
    href: "/history",
    icon: History,
  },
  {
    title: "Integrations",
    href: "/integrations",
    icon: Link2,
    roles: ["admin"],
  },
  // {
  //   title: "Competitors",
  //   href: "/competitors",
  //   icon: Users,
  // },
  {
    title: "Knowledge Base",
    href: "/knowledge-base",
    icon: BookOpen,
    roles: ["admin"],
  },
  {
    title: "Settings",
    href: "/settings",
    icon: Settings,
  },
  {
    title: "Interactive Demo",
    href: "/demo",
    icon: Zap,
  },
];

import { useAuth } from "@/context/auth-context";
import { getUsageStats } from "@/lib/api";

export function Sidebar({ onAnalyzeClick }: { onAnalyzeClick?: () => void }) {
  const pathname = usePathname();
  const { user, logout, loading } = useAuth();
  const [usage, setUsage] = useState<any>(null);
  const [isCollapsed, setIsCollapsed] = useState(() => {
    if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
      return localStorage.getItem("sidebar-collapsed") === "true";
    }
    return false;
  });

  useEffect(() => {
    const fetchUsage = async () => {
      // Only fetch if we have a user
      if (!user) return;
      
      try {
        const data = await getUsageStats();
        setUsage(data);
      } catch (e) {
        console.error("Failed to fetch usage in sidebar", e);
      }
    };
    
    if (!loading) {
      fetchUsage();
    }
  }, [user, loading]);

  useEffect(() => {
    if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
      const saved = localStorage.getItem("sidebar-collapsed");
      if (saved === "true" && !isCollapsed) {
        setIsCollapsed(true);
      }
    }
  }, []);

  useEffect(() => {
    const updateWidth = () => {
      const width = window.innerWidth < 768 ? "0px" : (isCollapsed ? "72px" : "256px");
      document.documentElement.style.setProperty("--sidebar-width", width);
    };

    updateWidth();
    window.addEventListener("resize", updateWidth);
    return () => window.removeEventListener("resize", updateWidth);
  }, [isCollapsed]);


  const toggleCollapse = () => {
    const next = !isCollapsed;
    setIsCollapsed(next);
    if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
      localStorage.setItem("sidebar-collapsed", String(next));
    }
  };


  const filteredItems = sidebarItems.filter((item) => {
    // Hide Analyze Lead in Trial Mode
    if (usage?.trial_mode && item.href === "/analyze") return false;
    
    if (!item.roles) return true;
    return item.roles.includes(user?.role || "user");
  });

  return (
    <div
      className={cn(
        "flex flex-col h-full border-r bg-sidebar text-sidebar-foreground transition-all duration-300 relative z-20",
        isCollapsed ? "w-[72px]" : "w-64"
      )}
    >
      <div className="p-4 border-b border-sidebar-border flex items-center justify-between h-[73px]">
        {!isCollapsed && (
          <div className="flex items-center gap-2 font-semibold text-xl tracking-tight overflow-hidden">
            <BarChart3 className="w-6 h-6 text-primary shrink-0" />
            <span className="truncate">Glial</span>
          </div>
        )}
        {isCollapsed && (
          <BarChart3 className="w-6 h-6 text-primary shrink-0 mx-auto" />
        )}
        <Button
          variant="ghost"
          size="icon"
          className={cn("shrink-0 h-8 w-8 z-50", isCollapsed ? "absolute -right-4 top-5 bg-sidebar border rounded-full shadow-md hover:bg-muted" : "")}
          onClick={toggleCollapse}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </Button>
      </div>

      <div className={cn("py-4", isCollapsed ? "px-2 flex justify-center" : "px-4")}>
        <Button
          className={cn(
            "w-full transition-all",
            isCollapsed ? "justify-center p-0 h-10 w-10 rounded-full" : "justify-start gap-2"
          )}
          onClick={onAnalyzeClick}
          title={isCollapsed ? "New Research" : undefined}
        >
          <Plus className={cn("shrink-0", isCollapsed ? "w-5 h-5" : "w-4 h-4")} />
          {!isCollapsed && "New Research"}
        </Button>
      </div>

      <nav className="flex-1 px-3 space-y-1 overflow-x-hidden">
        {filteredItems.map((item) => {
          const isActive = pathname === item.href;
          const content = (
            <>
              <item.icon className={cn("shrink-0 transition-all", isCollapsed ? "w-5 h-5 mx-auto" : "w-4 h-4")} />
              {!isCollapsed && <span className="flex-1 truncate">{item.title}</span>}
              {!isCollapsed && item.comingSoon && (
                <Badge
                  variant="secondary"
                  className="text-[10px] h-4 px-1.5 bg-primary/10 text-primary border-none shrink-0"
                >
                  Soon
                </Badge>
              )}
            </>
          );

          if (item.comingSoon) {
            return (
              <div
                key={item.title}
                className={cn(
                  "flex items-center gap-3 py-2.5 rounded-lg text-sm font-medium transition-colors opacity-60 cursor-not-allowed text-muted-foreground",
                  isCollapsed ? "justify-center px-0" : "px-3"
                )}
                title={isCollapsed ? `${item.title} (Coming Soon)` : undefined}
              >
                {content}
              </div>
            );
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-foreground",
                isCollapsed ? "justify-center px-0" : "px-3"
              )}
              title={isCollapsed ? item.title : undefined}
            >
              {content}
            </Link>
          );
        })}
      </nav>

      {/* Usage Indicator for Trial Users */}
      {!isCollapsed && usage?.trial_mode && (
        <div className="mx-3 mb-4 p-3 rounded-lg bg-primary/5 border border-primary/20 space-y-4">
          {/* Research Usage */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              <span className="flex items-center gap-1">
                <Search className="w-3 h-3 text-primary" />
                Research
              </span>
              <span>{usage.research.used}/{usage.research.limit}</span>
            </div>
            <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
               <div 
                  className="h-full bg-primary transition-all duration-500" 
                  style={{ width: `${Math.min(100, (usage.research.used / usage.research.limit) * 100)}%` }}
              />
            </div>
          </div>

          {/* Classification Usage */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              <span className="flex items-center gap-1">
                <UserCheck className="w-3 h-3 text-emerald-500" />
                Classifications
              </span>
              <span>{usage.classification.used}/{usage.classification.limit}</span>
            </div>
            <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
               <div 
                  className="h-full bg-emerald-500 transition-all duration-500" 
                  style={{ width: `${Math.min(100, (usage.classification.used / usage.classification.limit) * 100)}%` }}
              />
            </div>
          </div>

          {/* Lead Discovery Usage */}
          {usage.lead_discovery && (
            <div className="space-y-1.5">
              <div className="flex justify-between text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                <span className="flex items-center gap-1">
                  <Search className="w-3 h-3 text-orange-500" />
                  Lead Bank
                </span>
                <span>{usage.lead_discovery.used}/{usage.lead_discovery.limit}</span>
              </div>
              <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                <div 
                    className="h-full bg-orange-500 transition-all duration-500" 
                    style={{ width: `${Math.min(100, (usage.lead_discovery.used / usage.lead_discovery.limit) * 100)}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}
      {isCollapsed && usage?.trial_mode && (
        <div className="flex justify-center mb-4" title={`Usage: ${usage.research.used}/${usage.research.limit}`}>
          <div className="relative">
            <Zap className="w-5 h-5 text-primary" />
            <div className="absolute -top-1 -right-1 w-2 h-2 bg-primary rounded-full animate-pulse" />
          </div>
        </div>
      )}

      <div className="p-4 border-t border-sidebar-border space-y-2">
        {!isCollapsed ? (
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary uppercase shrink-0">
              {user?.email?.[0] || "U"}
            </div>
            <div className="flex flex-col flex-1 overflow-hidden">
              <span
                className="text-sm font-medium truncate"
                title={user?.email || "User"}
              >
                {user?.email?.split("@")[0] || "User"}
              </span>
              <span className="text-xs text-muted-foreground capitalize truncate">
                {user?.role || "User"}
              </span>
            </div>
          </div>
        ) : (
          <div className="w-8 h-8 mx-auto rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary uppercase shrink-0 mb-2" title={user?.email || "User"}>
            {user?.email?.[0] || "U"}
          </div>
        )}
        <Button
          variant="ghost"
          className={cn(
            "w-full gap-3 text-muted-foreground hover:text-destructive hover:bg-destructive/10 px-3 h-9",
            isCollapsed ? "justify-center" : "justify-start"
          )}
          onClick={logout}
          title={isCollapsed ? "Logout" : undefined}
        >
          <LogOut className="w-4 h-4 shrink-0" />
          {!isCollapsed && <span>Logout</span>}
        </Button>
      </div>
    </div>
  );
}
