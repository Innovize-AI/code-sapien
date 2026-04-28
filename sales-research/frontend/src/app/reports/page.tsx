"use client"

import { LeadForm } from "@/components/lead-form"
import { ReportDisplayV2 as ReportDisplay } from "@/components/report-display-v2"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useSearchParams } from "next/navigation"
import { Suspense, useState, useEffect } from "react"
import { Search } from "lucide-react"

function ReportPageContent() {
    const searchParams = useSearchParams()
    const idParam = searchParams.get("id")
    const [researchData, setResearchData] = useState(null)
    const [loading, setLoading] = useState(false)

    // Fetch report by ID
    useEffect(() => {
        const loadReport = async () => {
            if (idParam) {
                setLoading(true)
                try {
                    const { fetchReport } = await import("@/lib/api")
                    const data = await fetchReport(idParam)
                    setResearchData(data)
                } catch (error) {
                    console.error("Failed to load report", error)
                } finally {
                    setLoading(false)
                }
            }
        }
        loadReport()
    }, [idParam])

    return (
        <div className="grid grid-cols-1 gap-8">
            <div className="xl:col-span-1">
                {loading ? (
                    <div className="h-64 flex items-center justify-center bg-muted/20 rounded-2xl border border-dashed border-zinc-200 dark:border-zinc-800">
                        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
                    </div>
                ) : researchData ? (
                    <ReportDisplay data={researchData} />
                ) : (
                    <div className="h-full min-h-[400px] flex flex-col items-center justify-center border-2 border-dashed rounded-xl bg-muted/30 p-8 text-center">
                        <div className="bg-background p-4 rounded-full shadow-sm mb-4">
                            <Search className="w-8 h-8 text-muted-foreground" />
                        </div>
                        <h3 className="text-lg font-medium">Report Not Found</h3>
                        <p className="text-muted-foreground max-w-sm mt-2">
                            We couldn't find the research report you're looking for. Please check the history page.
                        </p>
                    </div>
                )}
            </div>
        </div>
    )
}

export default function ReportsPage() {
    return (
        <DashboardLayout>
            <div className="space-y-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">
                        Research Report
                    </h1>
                    <p className="text-muted-foreground mt-2">
                        Comprehensive insights and strategy for this prospect.
                    </p>
                </div>
                <Suspense fallback={<div>Loading...</div>}>
                    <ReportPageContent />
                </Suspense>
            </div>
        </DashboardLayout>
    )
}
