"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { Button } from "@/components/ui/button";
import {
  ArrowRight,
  Search,
  BarChart3,
  Users,
  Zap,
  Loader2,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  fetchDashboardStats,
  fetchHistory,
  DashboardStats,
  DashboardAnalytics,
  fetchDashboardAnalytics,
  getOnboardingStatus,
} from "@/lib/api";
import { ActivityBoard } from "@/components/dashboard/activity-board";
import { AnalyticsCharts } from "@/components/dashboard/analytics-charts";

export default function Home() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [analytics, setAnalytics] = useState<DashboardAnalytics | null>(null);
  const [recentReports, setRecentReports] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        // Check onboarding status first
        const status = await getOnboardingStatus();
        if (!status.complete) {
          router.push("/onboarding");
          return;
        }

        const [statsData, historyData, analyticsData] = await Promise.all([
          fetchDashboardStats(),
          fetchHistory(),
          fetchDashboardAnalytics(),
        ]);
        setStats(statsData);
        setAnalytics(analyticsData);
        // Sort by date desc and take top 5
        const sortedHistory = (historyData?.items || [])
          .sort(
            (a: any, b: any) =>
              new Date(b.created_at).getTime() -
              new Date(a.created_at).getTime(),
          )
          .slice(0, 5);
        setRecentReports(sortedHistory);
      } catch (e) {
        console.error("Failed to load dashboard data", e);
      } finally {
        setIsLoading(false);
      }
    };

    loadDashboardData();
  }, [router]);

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex h-full items-center justify-center min-h-[50vh]">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-8">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-primary">
              Innovize AI
            </h1>
            <p className="text-muted-foreground mt-1">
              Welcome back. Here's your revenue intelligence overview.
            </p>
          </div>
          <div className="flex gap-2">
            <Link href="/find-leads">
              <Button>
                <Search className="w-4 h-4 mr-2" />
                Find New Leads
              </Button>
            </Link>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Total Leads Found"
            value={stats?.total_leads.toLocaleString() || "0"}
            icon={Users}
          // trend={{ value: 12, isPositive: true }} // Trend needs historical data diff
          />
          <StatCard
            title="Avg. Lead Score"
            value={stats?.avg_lead_score.toString() || "0"}
            icon={BarChart3}
          // trend={{ value: 4, isPositive: true }}
          />
          <StatCard
            title="High Potential Leads"
            value={stats?.high_potential_leads.toLocaleString() || "0"}
            icon={Zap}
            description="Score > 70"
          />
          <StatCard
            title="Time Saved"
            value={`${stats?.time_saved_hours.toFixed(1)}h` || "0h"}
            icon={Users}
            description="Estimated (30m/lead)"
          />
        </div>

        {/* Analytics Section */}
        {analytics && <AnalyticsCharts data={analytics} />}

        {/* Main Content Grid */}
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-7">
          {/* Recent Activity / Quick Actions - Spans 4 columns */}
          <Card className="col-span-4">
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <Link href="/find-leads">
                <Card className="hover:bg-muted/50 transition-colors cursor-pointer border-dashed border-2">
                  <CardContent className="flex flex-col items-center justify-center p-6 text-center gap-2">
                    <div className="p-3 bg-primary/10 rounded-full text-primary">
                      <Search className="w-6 h-6" />
                    </div>
                    <h3 className="font-semibold">Find Companies</h3>
                    <p className="text-sm text-muted-foreground">
                      Search by industry, role, and location.
                    </p>
                  </CardContent>
                </Card>
              </Link>
              <Link href="/analyze">
                <Card className="hover:bg-muted/50 transition-colors cursor-pointer border-dashed border-2">
                  <CardContent className="flex flex-col items-center justify-center p-6 text-center gap-2">
                    <div className="p-3 bg-blue-500/10 rounded-full text-blue-500">
                      <BarChart3 className="w-6 h-6" />
                    </div>
                    <h3 className="font-semibold">Analyze Profile</h3>
                    <p className="text-sm text-muted-foreground">
                      Deep dive into a specific LinkedIn profile.
                    </p>
                  </CardContent>
                </Card>
              </Link>
              <Link href="/competitors">
                <Card className="hover:bg-muted/50 transition-colors cursor-pointer border-dashed border-2">
                  <CardContent className="flex flex-col items-center justify-center p-6 text-center gap-2">
                    <div className="p-3 bg-orange-500/10 rounded-full text-orange-500">
                      <Users className="w-6 h-6" />
                    </div>
                    <h3 className="font-semibold">Competitor Post Analysis</h3>
                    <p className="text-sm text-muted-foreground">
                      Compare content strategies across competitors.
                    </p>
                  </CardContent>
                </Card>
              </Link>
            </CardContent>
          </Card>

          {/* Activity Board - Spans 3 columns */}
          <ActivityBoard className="col-span-3" />
        </div>

        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-7">
          {/* Recent History - Spans 3 columns (now increased or full width) */}
          <Card className="col-span-7">
            <CardHeader>
              <CardTitle>Recent Reports</CardTitle>
              <CardDescription>Your last 5 generated reports.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentReports.length === 0 ? (
                  <div className="text-sm text-muted-foreground py-4 text-center">
                    No reports generated yet.
                  </div>
                ) : (
                  recentReports.map((report) => (
                    <Link href={`/reports?id=${report.id}`} key={report.id}>
                      <div className="flex items-center justify-between pb-4 border-b last:border-0 last:pb-0 hover:bg-muted/50 p-2 rounded-md transition-colors cursor-pointer">
                        <div className="flex items-center gap-4">
                          <div className="w-9 h-9 rounded-full bg-muted flex items-center justify-center font-bold text-xs">
                            {(report.fullname || "U")[0]}
                          </div>
                          <div className="space-y-1">
                            <p className="text-sm font-medium leading-none">
                              {report.fullname || "Unknown Lead"}
                            </p>
                            <p className="text-xs text-muted-foreground truncate w-32">
                              {report.linkedin_url ||
                                report.website ||
                                "No link"}
                            </p>
                          </div>
                        </div>
                        <div className="font-medium text-sm">
                          <span
                            className={
                              (report.lead_score || 0) > 70
                                ? "text-green-600 font-bold"
                                : (report.lead_score || 0) > 40
                                  ? "text-yellow-600"
                                  : "text-muted-foreground"
                            }
                          >
                            {report.lead_score || "N/A"}
                          </span>
                        </div>
                      </div>
                    </Link>
                  ))
                )}
              </div>
              <Link href="/history">
                <Button variant="ghost" className="w-full mt-4 text-xs">
                  View All History <ArrowRight className="w-3 h-3 ml-1" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
