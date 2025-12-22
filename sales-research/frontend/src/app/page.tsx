"use client"

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { Button } from "@/components/ui/button";
import { ArrowRight, Search, BarChart3, Users, Zap } from "lucide-react";
import Link from "next/link";

export default function Home() {
    return (
        <DashboardLayout>
            <div className="flex flex-col gap-8">
                {/* Header Section */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
                        <p className="text-muted-foreground mt-1">
                            Welcome back. Here's what's happening with your sales research.
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
                        value="1,248"
                        icon={Users}
                        trend={{ value: 12, isPositive: true }}
                    />
                    <StatCard
                        title="Reports Generated"
                        value="56"
                        icon={BarChart3}
                        trend={{ value: 4, isPositive: true }}
                    />
                    <StatCard
                        title="Avg. Lead Score"
                        value="78"
                        icon={Zap}
                        description="High Potential"
                    />
                    <StatCard
                        title="Time Saved"
                        value="24h"
                        icon={Users} // Placeholder icon
                        description="This month"
                    />
                </div>

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
                                        <p className="text-sm text-muted-foreground">Search by industry, role, and location.</p>
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
                                        <p className="text-sm text-muted-foreground">Deep dive into a specific LinkedIn profile.</p>
                                    </CardContent>
                                </Card>
                            </Link>
                        </CardContent>
                    </Card>

                    {/* Recent History - Spans 3 columns */}
                    <Card className="col-span-3">
                        <CardHeader>
                            <CardTitle>Recent Reports</CardTitle>
                            <CardDescription>
                                Your last 5 generated reports.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {/* Placeholder Items */}
                                {[1, 2, 3].map((i) => (
                                    <div key={i} className="flex items-center justify-between pb-4 border-b last:border-0 last:pb-0">
                                        <div className="flex items-center gap-4">
                                            <div className="w-9 h-9 rounded-full bg-muted flex items-center justify-center font-bold text-xs">
                                                L{i}
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-sm font-medium leading-none">Global Tech Lead</p>
                                                <p className="text-xs text-muted-foreground">linkedin.com/in/example...</p>
                                            </div>
                                        </div>
                                        <div className="font-medium text-sm">Score: 85</div>
                                    </div>
                                ))}
                            </div>
                            <Button variant="ghost" className="w-full mt-4 text-xs">
                                View All History <ArrowRight className="w-3 h-3 ml-1" />
                            </Button>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </DashboardLayout>
    );
}
