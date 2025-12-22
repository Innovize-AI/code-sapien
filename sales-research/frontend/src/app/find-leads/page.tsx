"use client"

import { DiscoveryForm } from "@/components/discovery-form"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useRouter } from "next/navigation"

export default function FindLeadsPage() {
    const router = useRouter()

    const handleAnalyze = (url: string) => {
        // Encode URL to pass as query param
        router.push(`/analyze?url=${encodeURIComponent(url)}`)
    }

    return (
        <DashboardLayout>
            <div className="space-y-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Find Leads</h1>
                    <p className="text-muted-foreground mt-2">
                        Discover potential leads using AI-powered search across the web and databases.
                    </p>
                </div>

                <DiscoveryForm onSelect={handleAnalyze} />
            </div>
        </DashboardLayout>
    )
}
