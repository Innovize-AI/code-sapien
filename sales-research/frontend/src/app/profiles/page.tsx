"use client"

import { useState, useEffect } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { getIdentifiedProfiles, IdentifiedProfile } from "@/lib/api"
import { Loader2, ExternalLink, MessageSquare, History, UserCheck, Globe, Users, ChevronLeft, ChevronRight, Play, BarChart3, CheckCircle2, Eye, FileText, Search } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { useBulkAnalysis } from "@/context/bulk-analysis-context"
import { BulkAnalysisModal } from "@/components/bulk-analysis-modal"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

function formatTimestamp(dateStr: string) {
    try {
        const date = new Date(dateStr)
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch (e) {
        return dateStr
    }
}

const PAGE_SIZE = 100

export default function ProfilesPage() {
    const [profiles, setProfiles] = useState<IdentifiedProfile[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [page, setPage] = useState(0)
    const [total, setTotal] = useState(0)
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
    const [activeTab, setActiveTab] = useState("all")
    const [searchQuery, setSearchQuery] = useState("")

    // Bulk Analysis Context
    const {
        isProcessing,
        overallStatus,
        bulkLeads,
        isBulkModalOpen,
        setIsBulkModalOpen,
        startBulkAnalysis,
        resetBulkAnalysis,
        setBulkLeads,
        leadsStatus,
        globalError
    } = useBulkAnalysis()

    useEffect(() => {
        const timeoutId = setTimeout(() => {
            async function loadProfiles() {
                setIsLoading(true)
                try {
                    const skip = page * PAGE_SIZE
                    const data = await getIdentifiedProfiles(skip, PAGE_SIZE, searchQuery)
                    setProfiles(data.profiles || [])
                    setTotal(data.total || 0)
                } catch (err) {
                    setError("Failed to load identified profiles")
                    console.error(err)
                } finally {
                    setIsLoading(false)
                }
            }
            loadProfiles()
        }, 500) // Debounce search

        return () => clearTimeout(timeoutId)
    }, [page, searchQuery])

    // SSE Listener for Real-Time Updates
    useEffect(() => {
        const eventSource = new EventSource('http://localhost:8000/api/competitor-analysis/events/classification');

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'classification_update' && data.leads) {
                    setProfiles(prevProfiles => {
                        // Create a map for faster lookup
                        const updatesMap = new Map<string, any>(data.leads.map((l: any) => [l.linkedin_url, l]));

                        return prevProfiles.map(profile => {
                            const update = updatesMap.get(profile.linkedin_url);
                            if (update) {
                                return {
                                    ...profile,
                                    is_fit: update.is_fit,
                                    is_competitor: update.is_competitor,
                                    is_decision_maker: update.is_decision_maker,
                                    fit_reasoning: update.fit_reasoning
                                };
                            }
                            return profile;
                        });
                    });
                }
            } catch (error) {
                console.error("Error parsing SSE event:", error);
            }
        };

        eventSource.onerror = (err) => {
            console.error("SSE Error:", err);
            eventSource.close();
        };

        return () => {
            eventSource.close();
        };
    }, []);

    const toggleSelection = (id: string) => {
        const newSelected = new Set(selectedIds)
        if (newSelected.has(id)) {
            newSelected.delete(id)
        } else {
            newSelected.add(id)
        }
        setSelectedIds(newSelected)
    }

    const isKeywordLead = (profile: IdentifiedProfile) => {
        try {
            const history = JSON.parse(profile.interaction_history || "[]");
            return history.some((h: any) =>
                h.competitor === "Keyword Search" ||
                h.competitor === "Keyword" ||
                (h.competitor && h.competitor.startsWith("Keyword:"))
            );
        } catch (e) {
            return false;
        }
    }

    const keywordProfiles = profiles.filter(isKeywordLead);
    const competitorProfiles = profiles.filter(p => !isKeywordLead(p));

    const getActiveConfig = () => {
        if (activeTab === "keyword") return { list: keywordProfiles, total: keywordProfiles.length };
        if (activeTab === "competitor") return { list: competitorProfiles, total: competitorProfiles.length };
        return { list: profiles, total: profiles.length };
    }

    const { list: activeList } = getActiveConfig();

    // Auto-deselect leads that are being processed
    useEffect(() => {
        if (selectedIds.size > 0 && leadsStatus.length > 0) {
            const processingUrls = new Set(
                leadsStatus
                    .filter(s => s.status === 'analyzing' || s.status === 'pending')
                    .map(s => s.url)
            );
            
            if (processingUrls.size > 0) {
                // Find IDs of profiles that are now processing
                const idsToRemove: string[] = [];
                activeList.forEach(p => {
                    if (selectedIds.has(p.id) && processingUrls.has(p.linkedin_url)) {
                        idsToRemove.push(p.id);
                    }
                });

                if (idsToRemove.length > 0) {
                    const nextSelected = new Set(selectedIds);
                    idsToRemove.forEach(id => nextSelected.delete(id));
                    setSelectedIds(nextSelected);
                }
            }
        }
    }, [leadsStatus, selectedIds, activeList]);

    const toggleSelectAll = () => {
        if (selectedIds.size === activeList.length) {
            setSelectedIds(new Set())
        } else {
            const allIds = new Set(activeList.map(p => p.id))
            setSelectedIds(allIds)
        }
    }

    const handleBulkAnalyze = () => {
        const selectedProfiles = activeList.filter(p => selectedIds.has(p.id))
        const bulkPayload = selectedProfiles.map(p => ({
            url: p.linkedin_url,
            website: "" // Add website if available in profile metadata later
        }))

        setBulkLeads(bulkPayload)
        setIsBulkModalOpen(true)
        
        // Always trigger startBulkAnalysis. 
        // The context handles deduplication and appending to the queue even if processing is active.
        startBulkAnalysis(bulkPayload, {
            // Default options for identified profiles
            project_urgency: 2,
            lead_source: "Competitor Analysis",
            refresh: false
        })
    }

    const renderProfileGrid = (profileList: IdentifiedProfile[]) => {
        if (profileList.length === 0) {
            return (
                <div className="flex flex-col items-center justify-center py-20 bg-muted/30 rounded-xl border-2 border-dashed text-center">
                    <Users className="w-12 h-12 text-muted-foreground/30 mb-4" />
                    <h3 className="text-lg font-semibold text-muted-foreground">No profiles found</h3>
                    <p className="text-sm text-muted-foreground max-w-xs mt-1">
                        Try adjusting your search or filters.
                    </p>
                </div>
            )
        }
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {profileList.map((profile) => {
                    let comments: string[] = []
                    let sources: any[] = []
                    try {
                        comments = JSON.parse(profile.comment_history || "[]")
                        sources = JSON.parse(profile.source_posts || "[]")
                    } catch (e) {
                        console.error("Error parsing profile data", e)
                    }

                    return (
                        <Card key={profile.id} className="group hover:border-primary/50 transition-all duration-300 overflow-hidden flex flex-col relative">
                            <div className="absolute top-5 left-4 z-20">
                                <Checkbox
                                    checked={selectedIds.has(profile.id)}
                                    onCheckedChange={() => toggleSelection(profile.id)}
                                    disabled={leadsStatus?.find(s => s.url === profile.linkedin_url)?.status === 'analyzing' || leadsStatus?.find(s => s.url === profile.linkedin_url)?.status === 'pending'}
                                />
                            </div>
                            <div className="h-1 bg-muted group-hover:bg-primary/50 transition-colors" />
                            <CardHeader className="pb-3 pl-12">
                                <div className="flex justify-between items-start">
                                    <div className="space-y-1">
                                        <CardTitle className="text-lg font-bold group-hover:text-primary transition-colors">
                                            {profile.name || "Anonymous Profile"}
                                        </CardTitle>
                                        <a
                                            href={profile.linkedin_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-xs text-blue-600 hover:underline flex items-center gap-1 opacity-80"
                                        >
                                            <Globe className="w-3 h-3" />
                                            LinkedIn Profile
                                            <ExternalLink className="w-2.5 h-2.5" />
                                        </a>
                                        {profile.headline && (
                                            <p className="text-xs text-muted-foreground mt-1 text-ellipsis overflow-hidden line-clamp-2">
                                                {profile.headline}
                                            </p>
                                        )}
                                        <div className="flex flex-wrap gap-2 mt-2">
                                            {(() => {
                                                const status = leadsStatus?.find(s => s.url === profile.linkedin_url)?.status;
                                                if (status === 'analyzing') {
                                                    return (
                                                        <Badge variant="secondary" className="text-[9px] h-5 px-1.5 bg-blue-100 text-blue-700 animate-pulse border-blue-200">
                                                            <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                                                            Researching...
                                                        </Badge>
                                                    );
                                                }
                                                if (status === 'pending') {
                                                    return (
                                                        <Badge variant="secondary" className="text-[9px] h-5 px-1.5 bg-gray-100 text-gray-500 border-gray-200">
                                                            Queued
                                                        </Badge>
                                                    );
                                                }
                                                return null;
                                            })()}
                                            {(!profile.fit_reasoning && !profile.is_fit && !profile.is_competitor && !leadsStatus?.find(s => s.url === profile.linkedin_url)) && (
                                                <Badge variant="secondary" className="text-[9px] h-5 px-1.5 bg-gray-100 text-gray-500 animate-pulse">
                                                    AI Analyzing...
                                                </Badge>
                                            )}
                                            {profile.is_competitor && (
                                                <Badge variant="destructive" className="text-[10px] h-5 px-1.5">
                                                    Competitor
                                                </Badge>
                                            )}
                                            {profile.is_fit && (
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 bg-green-50 text-green-700 border-green-200 hover:bg-green-100 cursor-help" title={profile.fit_reasoning}>
                                                    <CheckCircle2 className="w-3 h-3 mr-1" />
                                                    Potential Fit
                                                </Badge>
                                            )}
                                            {profile.is_decision_maker && (
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100">
                                                    <UserCheck className="w-3 h-3 mr-1" />
                                                    Decision Maker
                                                </Badge>
                                            )}
                                        </div>
                                        {profile.fit_reasoning && (
                                            <div className="mt-3 text-[10px] text-muted-foreground bg-muted/40 p-2 rounded border border-muted/50 italic leading-relaxed">
                                                <span className="font-semibold not-italic text-primary/70 mr-1">AI Reasoning:</span>
                                                {profile.fit_reasoning}
                                            </div>
                                        )}
                                    </div>
                                    {sources.length > 1 && (
                                        <Badge variant="secondary" className="bg-primary/5 text-primary border-primary/10">
                                            {sources.length} Touchpoints
                                        </Badge>
                                    )}
                                </div>
                            </CardHeader>
                            <CardContent className="flex-1 flex flex-col space-y-6">
                                {(() => {
                                    const status = leadsStatus?.find(s => s.url === profile.linkedin_url)?.status;
                                    const result = leadsStatus?.find(s => s.url === profile.linkedin_url)?.result;
                                    
                                    // Use the fresh result ID if available (completed this session), otherwise fallback to stored ID
                                    // Ensure we strictly use the ID and never 'latest' to avoid race conditions
                                    const reportId = (status === 'completed' && result?.id) ? result.id : profile.latest_report_id;
                                    
                                    if (reportId) {
                                        return (
                                            <a href={`/reports?id=${reportId}`} className="group/report flex items-center justify-between p-2 rounded-lg bg-primary/5 hover:bg-primary/10 border border-primary/10 transition-colors cursor-pointer">
                                                <div className="flex items-center gap-2">
                                                    <div className="bg-primary/10 text-primary p-1.5 rounded-md">
                                                        <FileText className="w-3.5 h-3.5" />
                                                    </div>
                                                    <span className="text-xs font-semibold text-primary">View Research Report</span>
                                                </div>
                                                <Eye className="w-3.5 h-3.5 text-primary opacity-60 group-hover/report:opacity-100 transition-opacity" />
                                            </a>
                                        )
                                    }
                                    return null;
                                })()}
                                {profile.interaction_history ? (
                                    <div className="space-y-4">
                                        {JSON.parse(profile.interaction_history).map((comp: any, ci: number) => (
                                            <div key={ci} className="space-y-3 p-3 rounded-lg bg-muted/20 border border-muted/50">
                                                <div className="flex items-center gap-2">
                                                    <div className="bg-primary/10 text-primary p-1 rounded-md">
                                                        <Users className="w-3.5 h-3.5" />
                                                    </div>
                                                    <span className="text-xs font-bold uppercase tracking-tight">{comp.competitor}</span>
                                                </div>

                                                <div className="space-y-3 pl-2 border-l-2 border-primary/20">
                                                    {comp.posts.map((post: any, pi: number) => (
                                                        <div key={pi} className="space-y-2">
                                                            <a
                                                                href={post.url}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="text-xs font-semibold text-blue-600 hover:underline line-clamp-1 italic flex items-center gap-1.5"
                                                            >
                                                                <ExternalLink className="w-3 h-3 opacity-60" />
                                                                "{post.title}"
                                                            </a>

                                                            <div className="space-y-1.5 pl-3">
                                                                {post.comments.map((comment: string, comi: number) => (
                                                                    <div key={comi} className="flex gap-2 items-start">
                                                                        <div className="mt-1.5 w-1 h-1 rounded-full bg-muted-foreground/30 shrink-0" />
                                                                        <p className="text-[11px] text-muted-foreground leading-relaxed italic border-l pl-2 py-0.5 border-primary/10">
                                                                            "{comment}"
                                                                        </p>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <>
                                        {/* Fallback for legacy data */}
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider font-semibold text-muted-foreground/70">
                                                <MessageSquare className="w-3 h-3" />
                                                Interaction history
                                            </div>
                                            <div className="space-y-2 max-h-32 overflow-y-auto pr-2 scrollbar-thin">
                                                {comments.map((comment, i) => (
                                                    <p key={i} className="text-[10px] text-muted-foreground italic bg-muted/30 p-2 rounded-md border border-muted/50">
                                                        "{comment}"
                                                    </p>
                                                ))}
                                            </div>
                                        </div>

                                        <div className="space-y-2 flex-1">
                                            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider font-semibold text-muted-foreground/70">
                                                <History className="w-3 h-3" />
                                                Discovered through
                                            </div>
                                            <div className="flex flex-col gap-1.5">
                                                {sources.map((source, i) => (
                                                    <a
                                                        key={i}
                                                        href={source.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-[10px] text-muted-foreground hover:text-blue-600 hover:underline flex items-start gap-1 p-1 rounded hover:bg-muted/50 transition-colors"
                                                    >
                                                        <ExternalLink className="w-2.5 h-2.5 mt-0.5 shrink-0 opacity-40" />
                                                        <span className="line-clamp-1 italic truncate">
                                                            "{source.title}" <span className="text-[9px] not-italic text-primary/50 font-medium">({source.competitor})</span>
                                                        </span>
                                                    </a>
                                                ))}
                                            </div>
                                        </div>
                                    </>
                                )}

                                <div className="pt-4 border-t flex justify-between items-center text-[9px] text-muted-foreground font-medium">
                                    <span className="flex items-center gap-1">
                                        Last Active: {formatTimestamp(profile.last_interaction_at)}
                                    </span>
                                    <span className="flex items-center gap-1 opacity-70">
                                        Identified by: {(profile as any).rep_name || "System"}
                                    </span>
                                </div>
                            </CardContent>
                        </Card>
                    )
                })}
            </div>
        )
    }

    const totalPages = Math.ceil(total / PAGE_SIZE)

    return (
        <DashboardLayout>
            <div className="space-y-6">
                <div className="flex justify-between items-center bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-10 py-4 border-b">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">Identified Profiles</h1>
                        <p className="text-muted-foreground mt-2">
                            High-signal prospects discovered and aggregated from competitor social interactions.
                        </p>
                    </div>
                    <div className="flex items-center gap-4">
                        {selectedIds.size > 0 ? (
                            <div className="flex items-center gap-2 animate-in fade-in slide-in-from-top-1">
                                <Button size="sm" variant="outline" onClick={toggleSelectAll}>
                                    {selectedIds.size === activeList.length ? "Deselect All" : "Select All"}
                                </Button>
                                <Button size="sm" onClick={handleBulkAnalyze} className="gap-2">
                                    <Play className="w-4 h-4" />
                                    Analyze Selected ({selectedIds.size})
                                </Button>
                            </div>
                        ) : (
                            <Badge variant="outline" className="px-3 py-1 gap-2">
                                <UserCheck className="w-4 h-4 text-primary" />
                                {total} Active Leads
                            </Badge>
                        )}

                        {totalPages > 1 && (
                            <div className="flex items-center gap-2 bg-muted/50 p-1 rounded-lg border">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 w-8 p-0"
                                    onClick={() => setPage(p => Math.max(0, p - 1))}
                                    disabled={page === 0 || isLoading}
                                >
                                    <ChevronLeft className="w-4 h-4" />
                                </Button>
                                <span className="text-[10px] font-bold px-2 uppercase tracking-tighter">
                                    Page {page + 1} of {totalPages}
                                </span>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 w-8 p-0"
                                    onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                                    disabled={page >= totalPages - 1 || isLoading}
                                >
                                    <ChevronRight className="w-4 h-4" />
                                </Button>
                            </div>
                        )}
                    </div>
                </div>

                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-20 bg-muted/30 rounded-xl border-2 border-dashed">
                        <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
                        <p className="text-muted-foreground animate-pulse font-medium">Fetching high-signal profiles...</p>
                    </div>
                ) : error ? (
                    <div className="bg-destructive/10 border border-destructive/20 p-6 rounded-xl text-center">
                        <p className="text-destructive font-semibold">{error}</p>
                    </div>
                ) : (
                    <>
                        <div className="flex justify-between items-center mb-4">
                            <div className="relative w-full max-w-sm">
                                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                                <Input
                                    type="search"
                                    placeholder="Search by name, headline, or keyword..."
                                    className="pl-9"
                                    value={searchQuery}
                                    onChange={(e) => {
                                        setSearchQuery(e.target.value)
                                        setPage(0) // Reset to first page on search
                                    }}
                                />
                            </div>
                        </div>

                        <Tabs defaultValue="all" value={activeTab} onValueChange={setActiveTab} className="w-full">
                            <TabsList className="mb-4">
                            <TabsTrigger value="all">All ({profiles.length})</TabsTrigger>
                            <TabsTrigger value="keyword">Keywords ({keywordProfiles.length})</TabsTrigger>
                            <TabsTrigger value="competitor">Competitors ({competitorProfiles.length})</TabsTrigger>
                        </TabsList>
                        <TabsContent value="all">{renderProfileGrid(profiles)}</TabsContent>
                        <TabsContent value="keyword">{renderProfileGrid(keywordProfiles)}</TabsContent>
                        <TabsContent value="competitor">{renderProfileGrid(competitorProfiles)}</TabsContent>
                    </Tabs>
                    </>
                )}
            </div>
            <BulkAnalysisModal
                open={isBulkModalOpen}
                onOpenChange={setIsBulkModalOpen}
                leads={bulkLeads}
                leadsStatus={leadsStatus}
                overallStatus={overallStatus}
                isProcessing={isProcessing}
                globalError={globalError}
                onRetry={handleBulkAnalyze}
                onReset={resetBulkAnalysis}
                onCancel={() => setIsBulkModalOpen(false)}
            />
        </DashboardLayout>
    )
}
