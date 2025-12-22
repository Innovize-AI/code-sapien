"use client"

import { Sidebar } from "./sidebar"

export function DashboardLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex h-screen w-full bg-background overflow-hidden">
            <aside className="hidden md:block h-full">
                <Sidebar />
            </aside>
            <main className="flex-1 overflow-y-auto w-full">
                <div className="container mx-auto p-6 md:p-8 max-w-7xl">
                    {children}
                </div>
            </main>
        </div>
    )
}
