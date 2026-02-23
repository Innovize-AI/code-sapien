"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { fetchHistory } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { Calendar, ExternalLink, ArrowRight, Loader2 } from "lucide-react";
import { useBulkAnalysis } from "@/context/bulk-analysis-context";
import { useAuth } from "@/context/auth-context";

interface HistoryItem {
    id: string;
    created_at: string;
    linkedin_url: string;
    lead_score: number;
    rep_name?: string;
    // Optional fields for UI handling of temporary items
    status?: 'pending' | 'analyzing' | 'completed' | 'error';
    isTemporary?: boolean;
    result?: any;
    currentStep?: string;
}

export default function HistoryPage() {
    const { user } = useAuth();
    const { leadsStatus } = useBulkAnalysis();

    const { data: history = [], isLoading: loading } = useQuery({
        queryKey: ["history"],
        queryFn: fetchHistory
    });

    // Merge history with temporary bulk analysis items
    const displayHistory: HistoryItem[] = [
        ...leadsStatus.map(lead => ({
            id: `temp-${lead.url}`,
            created_at: new Date().toISOString(), // Show as 'just now' effectively
            linkedin_url: lead.url,
            lead_score: lead.result?.lead_score || 0,
            rep_name: user?.full_name || "You",
            status: lead.status,
            isTemporary: true,
            result: lead.result,
            currentStep: lead.currentStep
        })),
        ...history
    ];

    return (
        <DashboardLayout>
            <div className="flex flex-col gap-8">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Research History</h1>
                    <p className="text-muted-foreground mt-2">
                        View past lead analyses and reports.
                    </p>
                </div>

                <Card>
                    <CardHeader>
                        <CardTitle>Recent Reports</CardTitle>
                        <CardDescription>
                            A list of all generated sales research reports.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {loading && history.length === 0 ? (
                            <div className="flex justify-center p-8">
                                <span className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full"></span>
                            </div>
                        ) : displayHistory.length === 0 ? (
                            <div className="text-center p-8 text-muted-foreground">
                                No reports found. Generate your first lead analysis!
                            </div>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Date</TableHead>
                                        <TableHead>Representative</TableHead>
                                        <TableHead>LinkedIn URL</TableHead>
                                        <TableHead>Lead Score</TableHead>
                                        <TableHead className="text-right">Action</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {displayHistory.map((item) => (
                                        <TableRow key={item.id} className={item.isTemporary ? "bg-muted/30" : ""}>
                                            <TableCell className="font-medium flex items-center gap-2">
                                                <Calendar className="h-4 w-4 text-muted-foreground" />
                                                {new Date(item.created_at).toLocaleDateString()}
                                                {item.isTemporary && (
                                                    <Badge variant="outline" className="ml-2 text-xs h-5">
                                                        {item.status === 'analyzing' ? 'Processing' : 'Unsaved'}
                                                    </Badge>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant="outline" className="text-[10px] font-normal">
                                                    {item.rep_name || "System"}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="truncate max-w-[300px]">
                                                <a href={item.linkedin_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:underline">
                                                    {item.linkedin_url} <ExternalLink className="h-3 w-3" />
                                                </a>
                                            </TableCell>
                                            <TableCell>
                                                {item.status === 'analyzing' || item.status === 'pending' ? (
                                                    <div className="flex items-center gap-2 text-muted-foreground text-sm">
                                                        <Loader2 className="h-3 w-3 animate-spin" />
                                                        <span className="truncate max-w-[150px]" title={item.currentStep || "Analyzing..."}>
                                                            {item.currentStep || "Analyzing..."}
                                                        </span>
                                                    </div>
                                                ) : (
                                                    <Badge variant={item.lead_score > 70 ? "default" : "secondary"}>
                                                        {item.lead_score}
                                                    </Badge>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-right">
                                                {item.isTemporary ? (
                                                    item.status === 'completed' && item.result?.id ? (
                                                        <Link href={`/reports?id=${item.result.id}`}>
                                                            <span className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3">
                                                                View Report <ArrowRight className="ml-2 h-4 w-4" />
                                                            </span>
                                                        </Link>
                                                    ) : item.status === 'completed' ? (
                                                        <span className="text-xs text-muted-foreground">ID missing - Check Find Leads</span>
                                                    ) : (
                                                        <span className="text-xs text-muted-foreground">
                                                            {item.status === 'error' ? 'Failed' : 'Processing...'}
                                                        </span>
                                                    )
                                                ) : (
                                                    <Link href={`/reports?id=${item.id}`}>
                                                        <span className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3">
                                                            View Report <ArrowRight className="ml-2 h-4 w-4" />
                                                        </span>
                                                    </Link>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        )}
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}
