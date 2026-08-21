"use client";

import { useState, useEffect, useRef } from "react";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { getIdentifiedProfiles, IdentifiedProfile, API_URL, enrichLeads } from "@/lib/api";
import { ExternalLink,
  MessageSquare,
  History,
  UserCheck,
  Globe,
  Users,
  Briefcase,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Play,
  BarChart3,
  CheckCircle2,
  Eye,
  FileText,
  Search,
  List,
  LayoutGrid,
  Info,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Zap,
  TrendingUp,
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { useBulkAnalysis } from "@/context/bulk-analysis-context";
import { BulkAnalysisModal } from "@/components/bulk-analysis-modal";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ensureProtocol, cn, normalizeUrl } from "@/lib/utils";
import { CompanyDetailModal, ReportDetailModal } from "@/components/modals";
import { ProfileGridV2, ProfileListV2 } from "@/components/profiles/profile-views-v2";
import { Spinner } from "@/components/ui/spinner"
import { useConfig } from "@/context/config-context";

function formatTimestamp(dateStr: string) {
  try {
    const date = new Date(dateStr);
    return (
      date.toLocaleDateString() +
      " " +
      date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    );
  } catch (e) {
    return dateStr;
  }
}

const PAGE_SIZE = 100;

export default function ProfilesPage() {
  const { trialMode } = useConfig();
  const [profiles, setProfiles] = useState<IdentifiedProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [enrichingIds, setEnrichingIds] = useState<Set<string>>(new Set());
  const handleEnrich = async (personIds: string[]) => {
    try {
      setEnrichingIds(prev => new Set([...prev, ...personIds]));
      await enrichLeads(personIds);
      // Success - the backend will push updates via SSE when done
    } catch (err) {
      console.error("Enrichment failed", err);
      setError("Failed to enrich profile");
    } finally {
      setEnrichingIds(prev => {
        const next = new Set(prev);
        personIds.forEach(id => next.delete(id));
        return next;
      });
    }
  };

  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [tabCounts, setTabCounts] = useState<Record<string, number>>({ all: 0, apollo: 0, keyword: 0, competitor: 0, job: 0 });
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<"grid" | "list">("list");
  const [sortBy, setSortBy] = useState<string>("touchpoint_count");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [dateFilter, setDateFilter] = useState<string>("all");
  const [isStatusDropdownOpen, setIsStatusDropdownOpen] = useState(false);
  const statusRef = useRef<HTMLDivElement>(null);

  const renderEmailVerificationBadge = (status?: string) => {
    if (!status) return null;

    const s = status.toLowerCase();
    switch (s) {
      case "verified":
      case "ok":
      case "valid":
        return (
          <Badge
            variant="outline"
            className="text-[9px] h-4 px-1.5 bg-emerald-50 text-emerald-700 border-emerald-200 flex items-center gap-1"
          >
            <ShieldCheck className="w-2.5 h-2.5" />
            Verified
          </Badge>
        );
      case "unverified":
      case "invalid":
      case "error":
      case "failed":
        return (
          <Badge
            variant="outline"
            className="text-[9px] h-4 px-1.5 bg-red-600 text-white border-red-700 flex items-center gap-1 font-bold shadow-sm"
          >
            <ShieldAlert className="w-2.5 h-2.5" />
            {s === "invalid" ? "Invalid" : "Error"}
          </Badge>
        );
      case "catch_all":
      case "catchall":
      case "risky":
        return (
          <Badge
            variant="outline"
            className="text-[9px] h-4 px-1.5 bg-amber-100 text-amber-700 border-amber-300 flex items-center gap-1 font-bold"
          >
            <ShieldAlert className="w-2.5 h-2.5" />
            Risky
          </Badge>
        );
      default:
        return (
          <Badge
            variant="outline"
            className="text-[9px] h-5 px-1.5 bg-gray-50 text-gray-600 border-gray-200 flex items-center gap-1"
          >
            <ShieldQuestion className="w-2.5 h-2.5" />
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </Badge>
        );
    }
  };

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
    globalError,
  } = useBulkAnalysis();

  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(
    null,
  );
  const [isCompanyModalOpen, setIsCompanyModalOpen] = useState(false);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [selectedProfileMeta, setSelectedProfileMeta] = useState<{ email?: string; email_verification_status?: string } | null>(null);

  const openReport = (reportId: string, profile: { email?: string; email_verification_status?: string }) => {
    setSelectedReportId(reportId);
    setSelectedProfileMeta({ email: profile.email, email_verification_status: profile.email_verification_status });
    setIsReportModalOpen(true);
  };

  const getDateRange = () => {
    const now = new Date();
    if (dateFilter === "today") return [`${now.toISOString().split('T')[0]}T00:00:00Z`, `${now.toISOString().split('T')[0]}T23:59:59Z`] as [string, string];
    if (dateFilter === "yesterday") { const y = new Date(now); y.setDate(y.getDate() - 1); return [`${y.toISOString().split('T')[0]}T00:00:00Z`, `${y.toISOString().split('T')[0]}T23:59:59Z`] as [string, string]; }
    if (dateFilter === "last_week") { const w = new Date(now); w.setDate(w.getDate() - 7); return [`${w.toISOString().split('T')[0]}T00:00:00Z`, `${now.toISOString().split('T')[0]}T23:59:59Z`] as [string, string]; }
    if (dateFilter === "last_month") { const m = new Date(now); m.setDate(m.getDate() - 30); return [`${m.toISOString().split('T')[0]}T00:00:00Z`, `${now.toISOString().split('T')[0]}T23:59:59Z`] as [string, string]; }
    return [undefined, undefined] as [undefined, undefined];
  };

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      async function loadProfiles() {
        setIsLoading(true);
        try {
          const skip = page * PAGE_SIZE;
          const [date_start, date_end] = getDateRange();
          const data = await getIdentifiedProfiles(
            skip,
            PAGE_SIZE,
            searchQuery,
            statusFilter.length > 0 ? statusFilter : "all",
            sortBy,
            sortOrder,
            date_start,
            date_end,
            activeTab,
          );
          setProfiles(data.profiles || []);
          setTotal(data.total || 0);
          if (data.tab_counts) setTabCounts(data.tab_counts);
        } catch (err) {
          setError("Failed to load identified profiles");
          console.error(err);
        } finally {
          setIsLoading(false);
        }
      }
      loadProfiles();
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [page, searchQuery, statusFilter, sortBy, sortOrder, dateFilter, activeTab]);

  // Click outside for status filter
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        statusRef.current &&
        !statusRef.current.contains(event.target as Node)
      ) {
        setIsStatusDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // SSE Listener for Real-Time Updates
  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem("accessToken") : null;
    const sseUrl = `${API_URL}/api/competitor-analysis/events/classification${token ? `?token_query=${token}` : ""}`;
    
    const eventSource = new EventSource(sseUrl);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "classification_update" && data.leads) {
          setProfiles((prevProfiles) => {
            const updatesMap = new Map<string, any>();
            data.leads.forEach((l: any) => {
              if (l.id) updatesMap.set(l.id, l);
              if (l.linkedin_url) updatesMap.set(normalizeUrl(l.linkedin_url), l);
              if (l.old_linkedin_url) updatesMap.set(normalizeUrl(l.old_linkedin_url), l);
            });

            return prevProfiles.map((profile) => {
              const profileIdUpdate = updatesMap.get(profile.id);
              const profileUrlUpdate = updatesMap.get(normalizeUrl(profile.linkedin_url));
              const update = profileIdUpdate || profileUrlUpdate;

              if (update) {
                return {
                  ...profile,
                  name: update.name || profile.name,
                  headline: update.headline || profile.headline,
                  linkedin_url: update.linkedin_url || profile.linkedin_url,
                  email: update.email || profile.email,
                  email_verification_status: update.email_verification_status || profile.email_verification_status,
                  company: update.company || profile.company,
                  is_fit: update.is_fit !== undefined ? update.is_fit : profile.is_fit,
                  is_competitor: update.is_competitor !== undefined ? update.is_competitor : profile.is_competitor,
                  is_decision_maker: update.is_decision_maker !== undefined ? update.is_decision_maker : profile.is_decision_maker,
                  is_buy_signal: update.is_buy_signal !== undefined ? update.is_buy_signal : profile.is_buy_signal,
                  is_strategic_seller: update.is_strategic_seller !== undefined ? update.is_strategic_seller : profile.is_strategic_seller,
                  fit_reasoning: update.fit_reasoning || profile.fit_reasoning,
                  intent: update.intent || profile.intent,
                  sentiment: update.sentiment || profile.sentiment,
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
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  // Profiles are server-filtered by activeTab — use directly
  const getActiveConfig = () => ({ list: profiles, total });

  const getTouchpointStats = (profile: IdentifiedProfile) => {
    let keywordCount = 0;
    let competitorCount = 0;
    const allTouchpoints: Array<{
      competitor: string;
      title: string;
      url: string;
      comments: string[];
    }> = [];

    try {
      const history = JSON.parse(profile.interaction_history || "[]");
      if (Array.isArray(history)) {
        history.forEach((h: any) => {
          const isKeyword =
            h.competitor === "Keyword Search" ||
            h.competitor === "Keyword" ||
            (h.competitor && h.competitor.startsWith("Keyword:"));

          const posts = h.posts || [];
          if (isKeyword) {
            keywordCount += posts.length;
          } else {
            competitorCount += posts.length;
          }

          if (Array.isArray(posts)) {
            posts.forEach((p: any) => {
              allTouchpoints.push({
                competitor: h.competitor,
                title: p.title,
                url: p.url,
                comments: (p.comments || []) as string[],
              });
            });
          }
        });
      }
    } catch (e) {
      // Quietly handle parse errors
    }

    return {
      keywordCount,
      competitorCount,
      totalCount: keywordCount + competitorCount,
      allTouchpoints,
    };
  };

  const { list: activeList } = getActiveConfig();

  // Auto-deselect leads that are being processed
  useEffect(() => {
    if (selectedIds.size > 0 && leadsStatus.length > 0) {
      const processingUrls = new Set(
        leadsStatus
          .filter(
            (s: any) => s.status === "analyzing" || s.status === "pending",
          )
          .map((s: any) => s.url),
      );

      if (processingUrls.size > 0) {
        // Find IDs of profiles that are now processing
        const idsToRemove: string[] = [];
        activeList.forEach((p) => {
          if (selectedIds.has(p.id) && processingUrls.has(p.linkedin_url)) {
            idsToRemove.push(p.id);
          }
        });

        if (idsToRemove.length > 0) {
          const nextSelected = new Set(selectedIds);
          idsToRemove.forEach((id) => nextSelected.delete(id));
          setSelectedIds(nextSelected);
        }
      }
    }
  }, [leadsStatus, selectedIds, activeList]);

  const toggleSelectAll = () => {
    if (selectedIds.size === activeList.length) {
      setSelectedIds(new Set());
    } else {
      const allIds = new Set(activeList.map((p) => p.id));
      setSelectedIds(allIds);
    }
  };

  const handleBulkAnalyze = () => {
    const selectedProfiles = activeList.filter((p: IdentifiedProfile) =>
      selectedIds.has(p.id),
    );
    const bulkPayload = selectedProfiles.map((p: IdentifiedProfile) => ({
      url: p.linkedin_url,
      website: p.website || "",
    }));

    setBulkLeads(bulkPayload);
    setIsBulkModalOpen(true);

    // Always trigger startBulkAnalysis.
    // The context handles deduplication and appending to the queue even if processing is active.
    startBulkAnalysis(bulkPayload, {
      // Default options for identified profiles
      project_urgency: 2,
      lead_source: "Competitor Analysis",
      refresh: false,
    });
  };


  const toggleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(column);
      setSortOrder("desc");
    }
    setPage(0);
  };


  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex justify-between items-center bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-10 py-4 border-b">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Identified Profiles
            </h1>
            <p className="text-muted-foreground mt-2">
              High-signal prospects discovered and aggregated from competitor
              social interactions.
            </p>
          </div>
          <div className="flex items-center gap-4">
            {selectedIds.size > 0 ? (
              <div className="flex items-center gap-2 animate-in fade-in slide-in-from-top-1">
                <Button size="sm" variant="outline" onClick={toggleSelectAll}>
                  {selectedIds.size === activeList.length
                    ? "Deselect All"
                    : "Select All"}
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
              <div className="flex items-center gap-1 bg-muted/50 p-1 rounded-lg border">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={() => setPage(0)}
                  disabled={page === 0 || isLoading}
                  title="First page"
                >
                  <ChevronLeft className="w-3 h-3" /><ChevronLeft className="w-3 h-3 -ml-2" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0 || isLoading}
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-[10px] font-bold px-2 tabular-nums">
                  {page + 1} / {totalPages}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1 || isLoading}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={() => setPage(totalPages - 1)}
                  disabled={page >= totalPages - 1 || isLoading}
                  title="Last page"
                >
                  <ChevronRight className="w-3 h-3" /><ChevronRight className="w-3 h-3 -ml-2" />
                </Button>
              </div>
            )}
          </div>
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 bg-muted/30 rounded-xl border-2 border-dashed">
            <Spinner size="lg" className="mb-4" />
            <p className="text-muted-foreground animate-pulse font-medium">
              Fetching high-signal profiles...
            </p>
          </div>
        ) : error ? (
          <div className="bg-destructive/10 border border-destructive/20 p-6 rounded-xl text-center">
            <p className="text-destructive font-semibold">{error}</p>
          </div>
        ) : (
          <>
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center gap-3 w-full max-w-xl">
                <div className="relative flex-1">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="search"
                    placeholder="Search by name, headline, or keyword..."
                    className="pl-9 h-10"
                    value={searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value);
                      setPage(0); // Reset to first page on search
                    }}
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Select value={dateFilter} onValueChange={(v) => { setDateFilter(v); setPage(0); }}>
                    <SelectTrigger className="h-10 w-[150px] text-xs font-semibold bg-background border-primary/20 text-foreground">
                      <SelectValue placeholder="Date Range" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Time</SelectItem>
                      <SelectItem value="today">Today</SelectItem>
                      <SelectItem value="yesterday">Yesterday</SelectItem>
                      <SelectItem value="last_week">Last 7 Days</SelectItem>
                      <SelectItem value="last_month">Last 30 Days</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="relative" ref={statusRef}>
                  <div
                    className={`flex items-center gap-2 p-1.5 px-3 rounded-lg border h-10 min-w-[200px] cursor-pointer transition-all duration-200 ${isStatusDropdownOpen
                      ? "bg-background border-primary ring-2 ring-primary/20 shadow-lg"
                      : "bg-background/50 border-primary/10 hover:bg-background/80"
                      }`}
                    onClick={() =>
                      setIsStatusDropdownOpen(!isStatusDropdownOpen)
                    }
                  >
                    <div className="flex-1 flex gap-1 overflow-hidden">
                      {statusFilter.length === 0 ? (
                        <span className="text-sm text-muted-foreground font-medium">
                          Filter by Status
                        </span>
                      ) : (
                        <div className="flex gap-1">
                          {statusFilter.slice(0, 2).map((s) => (
                            <Badge
                              key={s}
                              variant="secondary"
                              className="text-[10px] h-5 px-1 bg-primary/10 text-primary border-primary/20"
                            >
                              {s === "fit"
                                ? "Fit"
                                : s === "competitor"
                                  ? "Comp"
                                  : "DM"}
                            </Badge>
                          ))}
                          {statusFilter.length > 2 && (
                            <Badge
                              variant="secondary"
                              className="text-[10px] h-5 px-1"
                            >
                              +{statusFilter.length - 2}
                            </Badge>
                          )}
                        </div>
                      )}
                    </div>
                    <ChevronDown
                      className={`w-4 h-4 opacity-50 transition-transform duration-200 ${isStatusDropdownOpen ? "rotate-180" : ""}`}
                    />
                  </div>

                  {isStatusDropdownOpen && (
                    <div className="absolute top-11 left-0 z-50 w-64 p-3 bg-background border border-primary/10 rounded-xl shadow-2xl animate-in fade-in zoom-in-95 duration-200 origin-top">
                      <div className="mb-2 text-[10px] uppercase tracking-wider font-bold text-muted-foreground/70">
                        Select Segments
                      </div>
                      <div className="space-y-1">
                        {[
                          {
                            id: "fit",
                            label: "Potential (Fit)",
                            color: "bg-green-500",
                            desc: "Identified as ICP match",
                          },
                          {
                            id: "competitor",
                            label: "Competitor",
                            color: "bg-red-500",
                            desc: "Working for competition",
                          },
                          {
                            id: "dm",
                            label: "Decision Maker",
                            color: "bg-blue-500",
                            desc: "High-level stakeholder",
                          },
                          {
                            id: "buy_signal",
                            label: "Buy Signal",
                            color: "bg-violet-500",
                            desc: "Genuine pain or intent",
                          },
                          {
                            id: "strategic_seller",
                            label: "Strategic Seller",
                            color: "bg-zinc-500",
                            desc: "Self-promoting poster",
                          },
                        ].map((s) => (
                          <div
                            key={s.id}
                            className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all duration-150 ${statusFilter.includes(s.id)
                              ? "bg-primary/5 border border-primary/10"
                              : "hover:bg-primary/5 border border-transparent"
                              }`}
                            onClick={() => {
                              setStatusFilter((prev) =>
                                prev.includes(s.id)
                                  ? prev.filter((x) => x !== s.id)
                                  : [...prev, s.id],
                              );
                              setPage(0);
                            }}
                          >
                            <Checkbox
                              checked={statusFilter.includes(s.id)}
                              onCheckedChange={() => { }}
                            />
                            <div className="flex flex-col gap-0.5 flex-1">
                              <div className="flex items-center gap-2">
                                <div
                                  className={`w-1.5 h-1.5 rounded-full ${s.color}`}
                                />
                                <span className="text-sm font-semibold">
                                  {s.label}
                                </span>
                              </div>
                              <span className="text-[10px] text-muted-foreground">
                                {s.desc}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                      {statusFilter.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-primary/5 flex items-center justify-between">
                          <span className="text-[10px] text-muted-foreground">
                            {statusFilter.length} selected
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-[10px] font-bold text-muted-foreground hover:text-primary transition-colors"
                            onClick={(e) => {
                              e.stopPropagation();
                              setStatusFilter([]);
                              setPage(0);
                            }}
                          >
                            Clear All
                          </Button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center bg-muted/50 p-1 rounded-lg border">
                <Button
                  variant={viewMode === "grid" ? "secondary" : "ghost"}
                  size="sm"
                  className="h-8 px-3 gap-2"
                  onClick={() => setViewMode("grid")}
                >
                  <LayoutGrid className="w-4 h-4" />
                  <span className="hidden sm:inline">Grid</span>
                </Button>
                <Button
                  variant={viewMode === "list" ? "secondary" : "ghost"}
                  size="sm"
                  className="h-8 px-3 gap-2"
                  onClick={() => setViewMode("list")}
                >
                  <List className="w-4 h-4" />
                  <span className="hidden sm:inline">List</span>
                </Button>
              </div>
            </div>

            <Tabs
              defaultValue="all"
              value={activeTab}
              onValueChange={(v) => { setActiveTab(v); setPage(0); setSelectedIds(new Set()); }}
              className="w-full"
            >
              <TabsList className="bg-muted/50 border shadow-sm">
                <TabsTrigger value="all" className="gap-2">
                  <List className="w-4 h-4" />
                  All Leads
                  <Badge variant="secondary" className="ml-1 px-1 py-0 h-4 min-w-4 text-[10px]">
                    {tabCounts.all ?? 0}
                  </Badge>
                </TabsTrigger>
                {!trialMode && (
                  <TabsTrigger value="apollo" className="gap-2 group">
                    <Zap className="w-4 h-4 text-primary group-data-[state=active]:fill-primary/20" />
                    Apollo
                    <Badge variant="secondary" className="ml-1 px-1 py-0 h-4 min-w-4 text-[10px]">
                      {tabCounts.apollo ?? 0}
                    </Badge>
                  </TabsTrigger>
                )}
                <TabsTrigger value="competitor" className="gap-2">
                  <Globe className="w-4 h-4" />
                  Competitor Posts
                  <Badge variant="secondary" className="ml-1 px-1 py-0 h-4 min-w-4 text-[10px]">
                    {tabCounts.competitor ?? 0}
                  </Badge>
                </TabsTrigger>
                <TabsTrigger value="keyword" className="gap-2">
                  <Search className="w-4 h-4" />
                  Keyword Search
                  <Badge variant="secondary" className="ml-1 px-1 py-0 h-4 min-w-4 text-[10px]">
                    {tabCounts.keyword ?? 0}
                  </Badge>
                </TabsTrigger>
                <TabsTrigger value="job" className="gap-2">
                  <Briefcase className="w-4 h-4" />
                  Job Search
                  <Badge variant="secondary" className="ml-1 px-1 py-0 h-4 min-w-4 text-[10px]">
                    {tabCounts.job ?? 0}
                  </Badge>
                </TabsTrigger>
              </TabsList>
              {["all","apollo","competitor","keyword","job"].filter(tab => tab !== "apollo" || !trialMode).map(tab => (
                <TabsContent key={tab} value={tab}>
                  {viewMode === "grid" ? (
                    <ProfileGridV2
                      profiles={profiles}
                      selectedIds={selectedIds}
                      toggleSelection={toggleSelection}
                      toggleSelectAll={toggleSelectAll}
                      leadsStatus={leadsStatus || []}
                      onOpenReport={(id) => { setSelectedReportId(id); setIsReportModalOpen(true); }}
                      onOpenCompany={(id) => { setSelectedCompanyId(id); setIsCompanyModalOpen(true); }}
                      onAnalyze={(profile) => {
                        const payload = [{ url: profile.linkedin_url, website: profile.website || "" }];
                        setBulkLeads(payload);
                        setIsBulkModalOpen(true);
                        startBulkAnalysis(payload, { project_urgency: 2, lead_source: "Competitor Analysis", refresh: false });
                      }}
                      onEnrich={(apolloId) => handleEnrich([apolloId])}
                      enrichingIds={enrichingIds}
                      sortBy={sortBy}
                      sortOrder={sortOrder}
                      onSort={toggleSort}
                    />
                  ) : (
                    <ProfileListV2
                      profiles={profiles}
                      selectedIds={selectedIds}
                      toggleSelection={toggleSelection}
                      toggleSelectAll={toggleSelectAll}
                      leadsStatus={leadsStatus || []}
                      onOpenReport={(id) => { setSelectedReportId(id); setIsReportModalOpen(true); }}
                      onOpenCompany={(id) => { setSelectedCompanyId(id); setIsCompanyModalOpen(true); }}
                      onAnalyze={(profile) => {
                        const payload = [{ url: profile.linkedin_url, website: profile.website || "" }];
                        setBulkLeads(payload);
                        setIsBulkModalOpen(true);
                        startBulkAnalysis(payload, { project_urgency: 2, lead_source: "Competitor Analysis", refresh: false });
                      }}
                      onEnrich={(apolloId) => handleEnrich([apolloId])}
                      enrichingIds={enrichingIds}
                      sortBy={sortBy}
                      sortOrder={sortOrder}
                      onSort={toggleSort}
                    />
                  )}
                </TabsContent>
              ))}
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

      <CompanyDetailModal
        companyId={selectedCompanyId}
        isOpen={isCompanyModalOpen}
        onClose={() => setIsCompanyModalOpen(false)}
      />

      <ReportDetailModal
        reportId={selectedReportId}
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
      />
    </DashboardLayout>
  );
}
