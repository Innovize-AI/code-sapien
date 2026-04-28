"use client"

import { useState, useEffect } from "react"
import { BarChart3, Search, Loader2 } from "lucide-react"
import { generateResearch } from "@/lib/api"
import { useBulkAnalysis } from "@/context/bulk-analysis-context"
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet"
import { LeadForm } from "@/components/lead-form"
import { ReportDisplayV2 as ReportDisplay } from "@/components/report-display-v2"
import { Button } from "@/components/ui/button"

export function AnalysisSidePanel({
    trigger,
    initialUrl = "",
    initialWebsite,
    initialData,
    open: controlledOpen,
    onOpenChange: controlledOnOpenChange
}: {
    trigger?: React.ReactNode,
    initialUrl?: string,
    initialWebsite?: string,
    initialData?: any,
    open?: boolean,
    onOpenChange?: (open: boolean) => void
}) {
    const [uncontrolledOpen, setUncontrolledOpen] = useState(false)
    const [researchData, setResearchData] = useState<any>(initialData || null)
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [refreshStatus, setRefreshStatus] = useState("")
    const { addLeadStatus } = useBulkAnalysis()

    // Sync researchData with initialData when props change
    useEffect(() => {
        setResearchData(initialData || null);
        setIsRefreshing(false);
        setRefreshStatus("");
    }, [initialData, initialUrl]);

    const isControlled = controlledOpen !== undefined
    const open = isControlled ? controlledOpen : uncontrolledOpen
    const setOpen = isControlled ? controlledOnOpenChange : setUncontrolledOpen

    const handleRerun = async () => {
        if (!researchData) return

        setIsRefreshing(true)
        setRefreshStatus("Initiating re-run...")

        try {
            const apiData = {
                linkedin_url: researchData.linkedin_url,
                website: researchData.website,
                refresh: true
            }

            const result = await generateResearch(apiData, (status) => {
                setRefreshStatus(status)
            })

            setResearchData(result)

            // Update global context
            addLeadStatus({
                url: researchData.linkedin_url || researchData.website || "Rerun",
                status: "completed",
                result: result
            })
        } catch (error: any) {
            console.error("Error during re-run:", error)
            setRefreshStatus("Error: " + error.message)
        } finally {
            setIsRefreshing(false)
        }
    }

    return (
        <Sheet open={open} onOpenChange={(val) => {
            if (setOpen) {
                setOpen(val)
            }
            if (!val) {
                // Reset data when closed if needed, or keep it. 
                // Creating a new analysis resets it via "New Search" button.
                // But if we close, we might want to clear if we depend on external state?
                // For now, let's keep it simple.
            }
        }}>
            {trigger && <SheetTrigger asChild>{trigger}</SheetTrigger>}
            <SheetContent side="right" className="sm:max-w-xl w-full h-full overflow-y-auto p-0">
                <div className="p-6">
                    <SheetHeader className="mb-6">
                        <SheetTitle className="flex items-center gap-2">
                            <BarChart3 className="w-5 h-5 text-primary" />
                            Lead Analysis
                        </SheetTitle>
                        <SheetDescription>
                            Enter a LinkedIn URL to generate a deep-dive research report.
                        </SheetDescription>
                    </SheetHeader>

                    {!researchData ? (
                        <LeadForm
                            onSuccess={(data) => setResearchData(data)}
                            defaultUrl={initialUrl}
                            defaultWebsite={initialWebsite}
                        />
                    ) : (
                        <div className="space-y-6">
                            <div className="flex justify-between items-center">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setResearchData(null)}
                                    disabled={isRefreshing}
                                >
                                    <Search className="w-4 h-4 mr-2" />
                                    New Search
                                </Button>
                                {isRefreshing && (
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground bg-primary/5 px-3 py-1 rounded-full border border-primary/10">
                                        <Loader2 className="w-3 h-3 animate-spin text-primary" />
                                        {refreshStatus}
                                    </div>
                                )}
                            </div>
                            <ReportDisplay data={researchData} onRerun={handleRerun} />
                        </div>
                    )}
                </div>
            </SheetContent>
        </Sheet>
    )
}
