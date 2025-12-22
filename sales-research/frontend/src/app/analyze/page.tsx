"use client"

import { LeadForm } from "@/components/lead-form"
import { ReportDisplay } from "@/components/report-display"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useSearchParams } from "next/navigation"
import { Suspense, useState, useEffect } from "react"
import { Search } from "lucide-react"

function AnalyzeLeadContent() {
    const searchParams = useSearchParams()
    const urlParam = searchParams.get("url")
    const idParam = searchParams.get("id")
    const [researchData, setResearchData] = useState(null)
    const [defaultUrl, setDefaultUrl] = useState("")
    const [loading, setLoading] = useState(false)

    // Update default URL only when param changes to avoid loop
    useEffect(() => {
        if (urlParam) {
            setDefaultUrl(decodeURIComponent(urlParam))
        }
    }, [urlParam])

    // Fetch report by ID if present
    useEffect(() => {
        const loadReport = async () => {
            if (idParam) {
                setLoading(true)
                try {
                    const { fetchReport } = await import("@/lib/api")
                    const data = await fetchReport(idParam)
                    setResearchData(data)
                    // If the report has a LinkedIn URL, set it as default too
                    if (data.linkedin_url) {
                        setDefaultUrl(data.linkedin_url)
                    }
                } catch (error) {
                    console.error("Failed to load report", error)
                } finally {
                    setLoading(false)
                }
            }
        }
        loadReport()
    }, [idParam])

    const isHistoryView = !!idParam

    return (
        <div className={`grid grid-cols-1 ${isHistoryView ? "xl:grid-cols-1" : "xl:grid-cols-3"} gap-8`}>
            {!isHistoryView && (
                <div className="xl:col-span-1 space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Analysis Input</CardTitle>
                            <CardDescription>
                                Enter details to generate a research report.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <LeadForm onSuccess={setResearchData} defaultUrl={defaultUrl} />
                        </CardContent>
                    </Card>
                </div>
            )}

            <div className={isHistoryView ? "xl:col-span-1" : "xl:col-span-2"}>
                {researchData ? (
                    <ReportDisplay data={researchData} />
                ) : (
                    <div className="h-full min-h-[400px] flex flex-col items-center justify-center border-2 border-dashed rounded-xl bg-muted/30 p-8 text-center animate-in fade-in-50">
                        <div className="bg-background p-4 rounded-full shadow-sm mb-4">
                            <Search className="w-8 h-8 text-muted-foreground" />
                        </div>
                        <h3 className="text-lg font-medium">No Analysis Generated</h3>
                        <p className="text-muted-foreground max-w-sm mt-2">
                            Fill out the form on the left to start your deep dive research.
                        </p>
                    </div>
                )}
            </div>
        </div>
    )
}

export default function AnalyzeLeadPage() {
    return (
        <DashboardLayout>
            <div className="space-y-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">
                        Analyze Lead
                    </h1>
                    <p className="text-muted-foreground mt-2">
                        Get detailed insights, scoring, and strategies for a specific prospect.
                    </p>
                </div>
                <Suspense fallback={<div>Loading...</div>}>
                    <AnalyzeLeadContent />
                </Suspense>
            </div>
        </DashboardLayout>
    )
}
