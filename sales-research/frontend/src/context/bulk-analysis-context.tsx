"use client"

import React, { createContext, useContext, useState, ReactNode } from "react"
import { LeadStatus } from "@/components/bulk-analysis-modal"
import { bulkAnalyzeLeads } from "@/lib/api"

interface BulkAnalysisContextType {
    leadsStatus: LeadStatus[]
    overallStatus: string
    isProcessing: boolean
    globalError: string | null
    bulkLeads: { url?: string, website?: string }[]
    isBulkModalOpen: boolean
    setIsBulkModalOpen: (open: boolean) => void
    startBulkAnalysis: (leads: { url?: string, website?: string }[], options: any) => Promise<void>
    setBulkLeads: (leads: { url?: string, website?: string }[]) => void
    addLeadStatus: (lead: LeadStatus) => void
    lastSingleAnalysisUrl: string | null
    setLastSingleAnalysisUrl: (url: string | null) => void
}

const BulkAnalysisContext = createContext<BulkAnalysisContextType | undefined>(undefined)

export function BulkAnalysisProvider({ children }: { children: ReactNode }) {
    const [leadsStatus, setLeadsStatus] = useState<LeadStatus[]>([])
    const [overallStatus, setOverallStatus] = useState<string>("Initializing...")
    const [isProcessing, setIsProcessing] = useState(false)
    const [globalError, setGlobalError] = useState<string | null>(null)
    const [bulkLeads, setBulkLeads] = useState<{ url?: string, website?: string }[]>([])
    const [isBulkModalOpen, setIsBulkModalOpen] = useState(false)
    const [lastSingleAnalysisUrl, setLastSingleAnalysisUrl] = useState<string | null>(null)

    const startBulkAnalysis = async (leads: { url?: string, website?: string }[], options: any) => {
        setIsProcessing(true)
        setGlobalError(null)
        setLeadsStatus(leads.map(lead => ({ url: lead.url || "Unknown Lead", status: "pending" })))
        setBulkLeads(leads) // Ensure leads are set

        try {
            const results = await bulkAnalyzeLeads(
                leads,
                options,
                (update) => {
                    // Update: { status, url? }
                    if (update.url) {
                        setLeadsStatus(prev => prev.map(lead => {
                            if (lead.url === update.url || (lead.url === "Unknown Lead" && !update.url)) {
                                return { ...lead, status: "analyzing", currentStep: update.status }
                            }
                            return lead
                        }))
                    } else {
                        setOverallStatus(update.status)
                    }
                }
            )

            const updatedStatus = leads.map(lead => {
                const leadUrl = lead.url || "Unknown Lead"
                const found = results.find((r: any) => r.linkedin_url === lead.url)

                if (found?.error) {
                    return { url: leadUrl, status: "error" as const, error: found.error }
                }
                const result = found?.result;
                console.log(`DEBUG: Lead ${leadUrl} Result ID:`, result?.id);
                return { url: leadUrl, status: "completed" as const, result: result }
            })
            setLeadsStatus(updatedStatus)
        } catch (err: any) {
            setOverallStatus("Bulk analysis failed")
            setGlobalError(err.message || "An unexpected error occurred.")
        } finally {
            setIsProcessing(false)
        }
    }

    const addLeadStatus = (lead: LeadStatus) => {
        setLeadsStatus(prev => {
            const exists = prev.find(l => l.url === lead.url)
            if (exists) {
                return prev.map(l => l.url === lead.url ? lead : l)
            }
            return [...prev, lead]
        })
    }

    return (
        <BulkAnalysisContext.Provider value={{
            leadsStatus,
            overallStatus,
            isProcessing,
            globalError,
            bulkLeads,
            isBulkModalOpen,
            setIsBulkModalOpen,
            startBulkAnalysis,
            setBulkLeads,
            addLeadStatus,
            lastSingleAnalysisUrl,
            setLastSingleAnalysisUrl
        }}>
            {children}
        </BulkAnalysisContext.Provider>
    )
}

export function useBulkAnalysis() {
    const context = useContext(BulkAnalysisContext)
    if (context === undefined) {
        throw new Error("useBulkAnalysis must be used within a BulkAnalysisProvider")
    }
    return context
}
