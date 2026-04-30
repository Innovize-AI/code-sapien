"use client";

import { AuthProvider } from "@/context/auth-context";
import { BulkAnalysisProvider } from "@/context/bulk-analysis-context";
import { ConfigProvider } from "@/context/config-context";
import { useEffect, useRef, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { getOnboardingStatus } from "@/lib/api";
import { } from "lucide-react";
import { Spinner } from "@/components/ui/spinner"

export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isChecking, setIsChecking] = useState(true);
  // Track whether we've already done the onboarding check this session.
  // This prevents re-running on every client-side navigation.
  const hasChecked = useRef(false);

  useEffect(() => {
    // Skip pages that don't need the check
    if (pathname === "/onboarding" || pathname === "/login") {
      setIsChecking(false);
      return;
    }

    // Only run once per session (not on every pathname change)
    if (hasChecked.current) {
      setIsChecking(false);
      return;
    }

    const checkICP = async () => {
      try {
        const status = await getOnboardingStatus().catch(() => ({ complete: true, migration_complete: true }));
        if (!status.complete) {
          router.push("/onboarding");
        }
      } catch (e) {
        console.error("Failed to check onboarding status", e);
      } finally {
        hasChecked.current = true;
        setIsChecking(false);
      }
    };

    checkICP();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run once on mount, not on every pathname change

  if (isChecking) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-background">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <ConfigProvider>
      <AuthProvider>
        <BulkAnalysisProvider>{children}</BulkAnalysisProvider>
      </AuthProvider>
    </ConfigProvider>
  );
}
