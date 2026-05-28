"use client"

import { useState } from "react"
import { Sidebar } from "./sidebar"
import { AnalysisSidePanel } from "@/components/analysis-side-panel"
import { GlobalAnalysisStatus } from "@/components/global-analysis-status"
import { Button } from "@/components/ui/button"
import { Menu, BarChart3, X } from "lucide-react"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"

import { useConfig } from "@/context/config-context"

export function DashboardLayout({ children }: { children: React.ReactNode }) {
    const [isAnalysisOpen, setIsAnalysisOpen] = useState(false)
    const { trialMode } = useConfig()

    return (
        <div className="flex h-screen w-full bg-background overflow-hidden">
            {/* Desktop Sidebar */}
            <aside className="hidden md:block h-full shrink-0">
                <Sidebar onAnalyzeClick={() => setIsAnalysisOpen(true)} />
            </aside>

            {/* Mobile Sidebar (Sheet) */}
            <div className="md:hidden fixed top-0 left-0 right-0 h-16 border-b bg-background z-40 flex items-center justify-between px-4">
                <div className="flex items-center gap-2 font-semibold text-lg tracking-tight">
                    <BarChart3 className="w-5 h-5 text-primary" />
                    <span>Glial</span>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="ghost" size="icon" onClick={() => setIsAnalysisOpen(true)}>
                        <BarChart3 className="w-5 h-5" />
                    </Button>
                    <Sheet>
                        <SheetTrigger asChild>
                            <Button variant="ghost" size="icon">
                                <Menu className="w-5 h-5" />
                            </Button>
                        </SheetTrigger>
                        <SheetContent side="left" className="p-0 w-64">
                            <Sidebar />
                        </SheetContent>
                    </Sheet>
                </div>
            </div>

            <main className="flex-1 overflow-y-auto w-full pt-16 md:pt-0">
                <div className="container mx-auto p-4 md:p-8 max-w-7xl">
                    {children}
                </div>
            </main>

            {/* Global Analysis Side Panel */}
            <AnalysisSidePanel
                open={isAnalysisOpen}
                onOpenChange={setIsAnalysisOpen}
            />
        </div>
    )
}
