"use client"

import { useState } from "react"
import { BarChart3, Search } from "lucide-react"
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet"
import { LeadForm } from "@/components/lead-form"
import { ReportDisplay } from "@/components/report-display"
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

    // Update internal state if initialData changes (e.g. re-opening with new data)
    if (initialData && researchData !== initialData) {
        setResearchData(initialData)
    }

    const isControlled = controlledOpen !== undefined
    const open = isControlled ? controlledOpen : uncontrolledOpen
    const setOpen = isControlled ? controlledOnOpenChange : setUncontrolledOpen

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
                                >
                                    <Search className="w-4 h-4 mr-2" />
                                    New Search
                                </Button>
                            </div>
                            <ReportDisplay data={researchData} />
                        </div>
                    )}
                </div>
            </SheetContent>
        </Sheet>
    )
}
