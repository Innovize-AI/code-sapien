"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { BarChart3, Search, Settings, Home, History, Plus, Users, Link2, UserCheck, BookOpen, LogOut } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

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
    {
        title: "Competitors",
        href: "/competitors",
        icon: Users,
    },
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
]

import { useAuth } from "@/context/auth-context"

export function Sidebar({ onAnalyzeClick }: { onAnalyzeClick?: () => void }) {
    const pathname = usePathname()
    const { user, logout } = useAuth()

    const filteredItems = sidebarItems.filter(item => {
        if (!item.roles) return true;
        return item.roles.includes(user?.role || "user");
    });

    return (
        <div className="flex flex-col h-full border-r bg-sidebar text-sidebar-foreground w-64">
            <div className="p-6 border-b border-sidebar-border">
                <div className="flex items-center gap-2 font-semibold text-xl tracking-tight">
                    <BarChart3 className="w-6 h-6 text-primary" />
                    <span>Innovize AI</span>
                </div>
            </div>

            <div className="px-4 py-4">
                <Button
                    className="w-full justify-start gap-2"
                    onClick={onAnalyzeClick}
                >
                    <Plus className="w-4 h-4" />
                    New Research
                </Button>
            </div>

            <nav className="flex-1 p-4 space-y-1">
                {filteredItems.map((item) => {
                    const isActive = pathname === item.href
                    const content = (
                        <>
                            <item.icon className="w-4 h-4" />
                            <span className="flex-1">{item.title}</span>
                            {item.comingSoon && (
                                <Badge variant="secondary" className="text-[10px] h-4 px-1.5 bg-primary/10 text-primary border-none">
                                    Soon
                                </Badge>
                            )}
                        </>
                    )

                    if (item.comingSoon) {
                        return (
                            <div
                                key={item.title}
                                className={cn(
                                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors opacity-60 cursor-not-allowed",
                                    "text-muted-foreground"
                                )}
                            >
                                {content}
                            </div>
                        )
                    }

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                                isActive
                                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                                    : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-foreground"
                            )}
                        >
                            {content}
                        </Link>
                    )
                })}
            </nav>

            <div className="p-4 border-t border-sidebar-border space-y-2">
                <div className="flex items-center gap-3 px-3 py-2">
                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary uppercase">
                        {user?.email?.[0] || "U"}
                    </div>
                    <div className="flex flex-col flex-1 overflow-hidden">
                        <span className="text-sm font-medium truncate" title={user?.email || "User"}>
                            {user?.email?.split('@')[0] || "User"}
                        </span>
                        <span className="text-xs text-muted-foreground capitalize">{user?.role || "User"}</span>
                    </div>
                </div>
                <Button 
                    variant="ghost" 
                    className="w-full justify-start gap-3 text-muted-foreground hover:text-destructive hover:bg-destructive/10 px-3 h-9"
                    onClick={logout}
                >
                    <LogOut className="w-4 h-4" />
                    <span>Logout</span>
                </Button>
            </div>
        </div>
    )
}
