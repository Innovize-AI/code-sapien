"use client";

import { AuthProvider } from "@/context/auth-context";
import { BulkAnalysisProvider } from "@/context/bulk-analysis-context";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { getPersonalICP, getOnboardingStatus } from "@/lib/api";
import { Loader2 } from "lucide-react";

export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const checkICP = async () => {
      // Skip check if we are already on onboarding
      if (pathname === "/onboarding" || pathname === "/login") {
        setIsChecking(false);
        return;
      }

      try {
        const [icp, status] = await Promise.all([
          getPersonalICP(),
          getOnboardingStatus().catch(() => ({ complete: true })),
        ]);
        if (!icp && !status.complete) {
          router.push("/onboarding");
        }
      } catch (e) {
        console.error("Failed to check ICP settings", e);
      } finally {
        setIsChecking(false);
      }
    };

    checkICP();
  }, [pathname, router]);

  if (isChecking) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <AuthProvider>
      <BulkAnalysisProvider>{children}</BulkAnalysisProvider>
    </AuthProvider>
  );
}
