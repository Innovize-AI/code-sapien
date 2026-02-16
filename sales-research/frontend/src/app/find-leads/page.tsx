"use client"

import { useState } from "react"
import { DiscoveryForm } from "@/components/discovery-form"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { AnalysisSidePanel } from "@/components/analysis-side-panel"
import { BulkAnalysisModal, LeadStatus } from "@/components/bulk-analysis-modal"
import { bulkAnalyzeLeads } from "@/lib/api"
import { BarChart3 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useBulkAnalysis } from "@/context/bulk-analysis-context"

export default function FindLeadsPage() {
    const [selectedLead, setSelectedLead] = useState<{ url: string, website: string, result?: any } | null>(null)
    const [isPanelOpen, setIsPanelOpen] = useState(false)

    // Use global bulk analysis state
    const {
        leadsStatus,
        overallStatus,
        isProcessing,
        globalError,
        bulkLeads,
        isBulkModalOpen,
        setIsBulkModalOpen,
        startBulkAnalysis,
        resetBulkAnalysis,
        setBulkLeads
    } = useBulkAnalysis()

    const handleAnalyze = (lead: { url: string, website: string, result?: any }) => {
        setSelectedLead(lead)
        setIsPanelOpen(true)
    }

    const handleBulkAnalyze = (leads: { url: string, website: string }[], options?: { refresh: boolean }) => {
        // If an analysis is already running, we append to it
        // If not running, we start fresh (but don't necessarily reset if we want to keep history)
        setIsBulkModalOpen(true)
        
        startBulkAnalysis(leads, {
            project_urgency: 2,
            lead_source: "Discovery",
            refresh: options?.refresh || false
        })
    }

    const handleRetry = () => {
        startBulkAnalysis(bulkLeads, {
            project_urgency: 2,
            lead_source: "Discovery"
        })
    }

    const handleCloseModal = (open: boolean) => {
        setIsBulkModalOpen(open)
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

                {isProcessing && !isBulkModalOpen && (
                    <div className="bg-primary/10 border border-primary/20 p-4 rounded-lg flex items-center justify-between animate-in fade-in slide-in-from-top-4">
                        <div className="flex items-center gap-3">
                            <div className="relative">
                                <BarChart3 className="w-5 h-5 text-primary" />
                                <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary/40 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary"></span>
                                </span>
                            </div>
                            <div>
                                <p className="font-medium text-sm">Analysis running in background</p>
                                <p className="text-xs text-muted-foreground">{overallStatus}</p>
                            </div>
                        </div>
                        <Button variant="outline" size="sm" onClick={() => setIsBulkModalOpen(true)}>
                            View Progress
                        </Button>
                    </div>
                )}

                <DiscoveryForm
                    onSelect={handleAnalyze}
                    onBulkSelect={handleBulkAnalyze}
                    leadsStatus={leadsStatus}
                />

                {/* Single Lead Analysis Panel */}
                {selectedLead && (
                    <AnalysisSidePanel
                        initialUrl={selectedLead.url}
                        initialWebsite={selectedLead.website}
                        initialData={selectedLead.result || leadsStatus.find(s => s.url === selectedLead.url)?.result}
                        open={isPanelOpen}
                        onOpenChange={setIsPanelOpen}
                    />
                )}

                {/* Bulk Analysis Progress Tracker */}
                <BulkAnalysisModal
                    open={isBulkModalOpen}
                    onOpenChange={handleCloseModal}
                    leads={bulkLeads}
                    leadsStatus={leadsStatus}
                    overallStatus={overallStatus}
                    isProcessing={isProcessing}
                    globalError={globalError}
                    onRetry={handleRetry}
                    onReset={resetBulkAnalysis}
                    onCancel={() => setIsBulkModalOpen(false)}
                />
            </div>
        </DashboardLayout>
    )
}
