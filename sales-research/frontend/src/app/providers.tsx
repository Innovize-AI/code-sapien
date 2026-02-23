"use client"

import { AuthProvider } from "@/context/auth-context"
import { BulkAnalysisProvider } from "@/context/bulk-analysis-context"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { useRouter, usePathname } from "next/navigation"
import { getICP, getOnboardingStatus } from "@/lib/api"
import { Loader2 } from "lucide-react"

export function Providers({ children }: { children: React.ReactNode }) {
    const router = useRouter()
    const pathname = usePathname()
    const [isChecking, setIsChecking] = useState(true)
    const [queryClient] = useState(() => new QueryClient({
        defaultOptions: {
            queries: {
                staleTime: 60 * 1000,
                refetchOnWindowFocus: false,
            },
        },
    }))

    useEffect(() => {
        const checkICP = async () => {
            // Skip check if we are already on onboarding
            if (pathname === "/onboarding" || pathname === "/login") {
                setIsChecking(false)
                return
            }

            try {
                const [icp, status] = await Promise.all([
                    getICP(),
                    getOnboardingStatus().catch(() => ({ complete: true }))
                ])
                if (!icp && !status.complete) {
                    router.push("/onboarding")
                }
            } catch (e) {
                console.error("Failed to check ICP settings", e)
            } finally {
                setIsChecking(false)
            }
        }

        checkICP()
    }, [pathname, router])

    if (isChecking) {
        return (
            <div className="h-screen w-full flex items-center justify-center bg-background">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        )
    }

    return (
        <QueryClientProvider client={queryClient}>
            <AuthProvider>
                <BulkAnalysisProvider>
                    {children}
                </BulkAnalysisProvider>
            </AuthProvider>
        </QueryClientProvider>
    )
}
