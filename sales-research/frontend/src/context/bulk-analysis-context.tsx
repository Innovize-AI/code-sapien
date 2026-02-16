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
    resetBulkAnalysis: () => void
    setBulkLeads: (leads: { url?: string, website?: string }[]) => void
    addLeadStatus: (lead: LeadStatus) => void
    lastSingleAnalysisUrl: string | null
    setLastSingleAnalysisUrl: (url: string | null) => void
}

const BulkAnalysisContext = createContext<BulkAnalysisContextType | undefined>(undefined)

export function BulkAnalysisProvider({ children }: { children: ReactNode }) {
    const [leadsStatus, setLeadsStatus] = useState<LeadStatus[]>([])
    const [overallStatus, setOverallStatus] = useState<string>("Ready")
    const [activeBatches, setActiveBatches] = useState(0)
    const [globalError, setGlobalError] = useState<string | null>(null)
    const [bulkLeads, setBulkLeads] = useState<{ url?: string, website?: string }[]>([])
    const [isBulkModalOpen, setIsBulkModalOpen] = useState(false)
    const [lastSingleAnalysisUrl, setLastSingleAnalysisUrl] = useState<string | null>(null)

    const isProcessing = activeBatches > 0

    // Milestone progress mapping
    const NODE_PROGRESS_MAP: Record<string, number> = {
        "collector": 5,
        "linkedin_profile_fetcher": 10,
        "linkedin_posts_fetcher": 15,
        "linkedin_engagement_fetcher": 20,
        "linkedin_company_fetcher": 25,
        "linkedin_profile_analyzer": 30,
        "website_scraper": 35,
        "website_analyzer": 40,
        "lead_data_extractor": 50,
        "lead_scorer": 60,
        "pain_point_discovery": 70,
        "strategic_rag_researcher": 75,
        "solution_mapping": 80,
        "narrative_arbitrator": 85,
        "strategic_recommender": 90,
        "outreach_designer": 95,
        "follow_up_designer": 95,
        "report_generator": 100
    };

    const startBulkAnalysis = async (leads: { url?: string, website?: string }[], options: any) => {
        // Only add leads that aren't already being processed or completed
        const currentUrls = new Set(leadsStatus.map(l => l.url));
        const newLeads = leads.filter(l => !currentUrls.has(l.url || "Unknown Lead"));
        
        if (newLeads.length === 0 && leads.length > 0) {
            // Check if we are just re-running failed ones
            const failedUrls = new Set(leadsStatus.filter(l => l.status === 'error').map(l => l.url));
            const reRunLeads = leads.filter(l => failedUrls.has(l.url || "Unknown Lead"));
            if (reRunLeads.length > 0) {
                // We'll proceed with these
            } else {
                return; // Nothing new to do
            }
        }

        const leadsToProcess = newLeads.length > 0 ? newLeads : leads;

        setActiveBatches(prev => prev + 1)
        setGlobalError(null)
        
        // Update leadsStatus to include new leads or reset failed ones
        setLeadsStatus(prev => {
            const updated = [...prev];
            leadsToProcess.forEach(lead => {
                const url = lead.url || "Unknown Lead";
                const index = updated.findIndex(l => l.url === url);
                const leadStatus: LeadStatus = { 
                    url, 
                    status: "pending",
                    progress: 0 
                };
                if (index > -1) {
                    updated[index] = leadStatus;
                } else {
                    updated.push(leadStatus);
                }
            });
            return updated;
        })

        // Accumulate in bulkLeads for the modal
        setBulkLeads(prev => {
            const updated = [...prev];
            leadsToProcess.forEach(lead => {
                if (!updated.find(l => l.url === lead.url)) {
                    updated.push(lead);
                }
            });
            return updated;
        })

        try {
            await bulkAnalyzeLeads(
                leadsToProcess,
                options,
                (update) => {
                    if (update.url) {
                        const milestoneProgress = NODE_PROGRESS_MAP[update.status] || 0;
                        setLeadsStatus(prev => prev.map(lead => {
                            if (lead.url === update.url) {
                                // If research is finishing, it might say "Synthesizing research..."
                                // We want to maintain the highest progress reached.
                                const currentProgress = lead.progress || 0;
                                const newProgress = Math.max(currentProgress, milestoneProgress);
                                return { 
                                    ...lead, 
                                    status: "analyzing", 
                                    currentStep: update.status,
                                    progress: newProgress
                                }
                            }
                            return lead
                        }))
                    } else {
                        setOverallStatus(update.status)
                    }
                }
            ).then(results => {
                setLeadsStatus(prev => prev.map(lead => {
                    const found = results.find((r: any) => r.linkedin_url === lead.url)
                    if (!found) return lead;

                    if (found?.error) {
                        return { ...lead, status: "error" as const, error: found.error, progress: 0 }
                    }
                    return { ...lead, status: "completed" as const, result: found.result, progress: 100 }
                }))
            })
        } catch (err: any) {
            setOverallStatus("Bulk analysis batch failed")
            setGlobalError(err.message || "An unexpected error occurred.")
        } finally {
            setActiveBatches(prev => Math.max(0, prev - 1))
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

    const resetBulkAnalysis = () => {
        setActiveBatches(0)
        setLeadsStatus([])
        setBulkLeads([])
        setOverallStatus("Ready")
        setGlobalError(null)
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
            resetBulkAnalysis,
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
