"use client"

import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetDescription
} from "@/components/ui/sheet"
import { Progress } from "@/components/ui/progress"
import { CheckCircle2, CircleDashed, XCircle, Loader2, BarChart3 } from "lucide-react"
import { Button } from "@/components/ui/button"

export type AnalysisStatus = "pending" | "analyzing" | "completed" | "error"

export interface LeadStatus {
    url: string
    status: AnalysisStatus
    error?: string
    currentStep?: string
    result?: any
}

interface BulkAnalysisModalProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    leads: { url?: string, website?: string }[]
    leadsStatus: LeadStatus[]
    overallStatus: string
    isProcessing: boolean
    globalError: string | null
    onRetry: () => void
    onCancel: () => void // Just closes the modal, doesn't necessarily cancel the background process (unless we want it to)
}

export function BulkAnalysisModal({
    open,
    onOpenChange,
    leads,
    leadsStatus,
    overallStatus,
    isProcessing,
    globalError,
    onRetry,
    onCancel
}: BulkAnalysisModalProps) {

    const completedCount = leadsStatus.filter(l => l.status === "completed").length
    const progress = leads.length > 0 ? (completedCount / leads.length) * 100 : 0

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent className="sm:max-w-xl w-full">
                <SheetHeader>
                    <SheetTitle className="flex items-center gap-2">
                        <BarChart3 className="w-5 h-5 text-primary" />
                        Bulk Lead Analysis
                    </SheetTitle>
                    <SheetDescription>
                        Processing {leads.length} leads in parallel.
                    </SheetDescription>
                </SheetHeader>

                <div className="mt-8 space-y-6">
                    <div className="space-y-2">
                        <div className="flex justify-between text-sm font-medium">
                            <span>Overall Progress</span>
                            <span>{Math.round(progress)}%</span>
                        </div>
                        <Progress value={progress} className="h-2" />
                        <p className="text-xs text-muted-foreground animate-pulse">
                            {overallStatus}
                        </p>
                    </div>

                    {globalError && (
                        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                            <p className="text-sm font-medium text-red-500 flex items-center gap-2">
                                <XCircle className="w-4 h-4" />
                                Run Error
                            </p>
                            <p className="text-sm text-red-500/80 mt-1 ml-6">{globalError}</p>
                        </div>
                    )}

                    <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-2">
                        {leadsStatus.map((lead, i) => (
                            <div key={i} className="flex flex-col p-3 rounded-lg border bg-muted/30">
                                <div className="flex items-center justify-between">
                                    <div className="flex-1 min-w-0 mr-4">
                                        <p className="text-sm font-medium truncate">{lead.url}</p>
                                        {lead.status === "analyzing" && lead.currentStep && (
                                            <p className="text-xs text-muted-foreground animate-pulse mt-0.5">
                                                {lead.currentStep}
                                            </p>
                                        )}
                                    </div>
                                    <div className="flex shrink-0 items-center">
                                        {lead.status === "pending" && <CircleDashed className="w-4 h-4 text-muted-foreground" />}
                                        {lead.status === "analyzing" && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
                                        {lead.status === "completed" && <CheckCircle2 className="w-4 h-4 text-green-500" />}
                                        {lead.status === "error" && <XCircle className="w-4 h-4 text-red-500" />}
                                    </div>
                                </div>
                                {lead.error && (
                                    <p className="text-[10px] text-red-500/80 mt-1 line-clamp-1">{lead.error}</p>
                                )}
                            </div>
                        ))}
                    </div>

                    <div className="flex justify-end gap-3 pt-4 border-t">
                        <Button variant="outline" onClick={onCancel}>
                            Close
                        </Button>
                        {!isProcessing && completedCount < leads.length && leads.length > 0 && (
                            <Button onClick={onRetry}>Retry Failed</Button>
                        )}
                    </div>
                </div>
            </SheetContent>
        </Sheet>
    )
}
