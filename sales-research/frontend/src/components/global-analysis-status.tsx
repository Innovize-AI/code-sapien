
"use client";

import { useBulkAnalysis } from "@/context/bulk-analysis-context";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

export function GlobalAnalysisStatus() {
    const { isProcessing, overallStatus, setIsBulkModalOpen } = useBulkAnalysis();

    if (!isProcessing) return null;

    return (
        <div className="fixed bottom-4 right-4 z-50 w-80 bg-background border rounded-lg shadow-lg p-4 animate-in slide-in-from-bottom-5">
            <div className="flex items-start justify-between gap-4">
                <div className="space-y-1">
                    <h4 className="text-sm font-semibold flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        Analysis running
                    </h4>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                        {overallStatus || "Processing leads..."}
                    </p>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsBulkModalOpen(true)}
                    className="shrink-0"
                >
                    View Progress
                </Button>
            </div>
        </div>
    );
}
