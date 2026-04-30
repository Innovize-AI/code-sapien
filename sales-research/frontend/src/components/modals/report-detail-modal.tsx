"use client";

import { useState, useEffect } from "react";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { ReportDisplayV2 } from "@/components/report-display-v2";
import { fetchReport } from "@/lib/api";
import { Search } from "lucide-react";
import { Spinner } from "@/components/ui/spinner"

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
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()} modal={false}>
      <SheetContent 
        hideOverlay
        onInteractOutside={(e) => e.preventDefault()}
        onPointerDownOutside={(e) => e.preventDefault()}
        className="w-[calc(100vw-var(--sidebar-width,0px))] max-w-none sm:max-w-none p-0 flex flex-col overflow-hidden border-l shadow-2xl transition-[width] duration-300"

      >



        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-full py-20">
              <Spinner size="lg" className="mb-4" />
              <p className="text-muted-foreground animate-pulse font-medium">
                Fetching comprehensive research...
              </p>
            </div>
          ) : data ? (
            <ReportDisplayV2 data={data} />
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
