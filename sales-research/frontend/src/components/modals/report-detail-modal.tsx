"use client";

import { useState, useEffect } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ReportDisplay } from "@/components/report-display";
import { fetchReport } from "@/lib/api";
import { Loader2, Search } from "lucide-react";

interface ReportDetailModalProps {
  reportId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export function ReportDetailModal({
  reportId,
  isOpen,
  onClose,
}: ReportDetailModalProps) {
  const [data, setData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const loadReport = async () => {
      if (reportId && isOpen) {
        setIsLoading(true);
        try {
          const result = await fetchReport(reportId);
          setData(result);
        } catch (error) {
          console.error("Failed to fetch report:", error);
          setData(null);
        } finally {
          setIsLoading(false);
        }
      } else if (!isOpen) {
        // Clear data when closed to avoid stale content next time
        setData(null);
      }
    };

    loadReport();
  }, [reportId, isOpen]);

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="sm:max-w-2xl md:max-w-3xl lg:max-w-5xl xl:max-w-6xl w-full p-0 flex flex-col overflow-hidden">
        <SheetHeader className="p-6 border-b bg-background sticky top-0 z-20">
          <SheetTitle className="text-xl font-bold flex items-center gap-2">
            Research Report
          </SheetTitle>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto bg-muted/5 scrollbar-thin">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-full py-20">
              <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
              <p className="text-muted-foreground animate-pulse font-medium">
                Fetching comprehensive research...
              </p>
            </div>
          ) : data ? (
            <div className="p-0">
              <ReportDisplay data={data} />
            </div>
          ) : (
            <div className="flex h-full flex-col items-center justify-center p-12 text-center text-muted-foreground border-2 border-dashed m-6 rounded-3xl opacity-60">
              <Search className="w-10 h-10 mb-4 opacity-20" />
              <p className="text-lg font-medium">Report Not Found</p>
              <p className="max-w-sm mt-2">
                We couldn't retrieve the specific research details for this
                lead.
              </p>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
