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
import {
  Loader2,
  ExternalLink,
  MessageSquare,
  History,
  UserCheck,
  Globe,
  Users,
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
  const [tabCounts, setTabCounts] = useState<Record<string, number>>({ all: 0, apollo: 0, keyword: 0, competitor: 0 });
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
            className="text-[9px] h-5 px-1.5 bg-emerald-50 text-emerald-700 border-emerald-200 flex items-center gap-1"
          >
            <ShieldCheck className="w-2.5 h-2.5" />
            Verified
          </Badge>
        );
      case "unverified":
      case "invalid":
        return (
          <Badge
            variant="outline"
            className="text-[9px] h-5 px-1.5 bg-red-50 text-red-700 border-red-200 flex items-center gap-1"
          >
            <ShieldAlert className="w-2.5 h-2.5" />
            Unverified
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
    const eventSource = new EventSource(
      `${API_URL}/api/competitor-analysis/events/classification`,
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "classification_update" && data.leads) {
          setProfiles((prevProfiles) => {
            return prevProfiles.map((profile) => {
              // Find matching update: by id, old_url, or current url
              const update = data.leads.find(
                (l: any) =>
                  (l.id && l.id === profile.id) ||
                  (l.old_linkedin_url &&
                    l.old_linkedin_url === profile.linkedin_url) ||
                  l.linkedin_url === profile.linkedin_url,
              );

              if (update) {
                return {
                  ...profile,
                  name: update.name || profile.name,
                  headline: update.headline || profile.headline,
                  linkedin_url: update.linkedin_url || profile.linkedin_url,
                  is_fit: update.is_fit !== undefined ? update.is_fit : profile.is_fit,
                  is_competitor: update.is_competitor !== undefined ? update.is_competitor : profile.is_competitor,
                  is_decision_maker: update.is_decision_maker !== undefined ? update.is_decision_maker : profile.is_decision_maker,
                  fit_reasoning: update.fit_reasoning || profile.fit_reasoning,
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

  const renderProfileGrid = (profileList: IdentifiedProfile[]) => {
    if (profileList.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-20 bg-muted/30 rounded-xl border-2 border-dashed text-center">
          <Users className="w-12 h-12 text-muted-foreground/30 mb-4" />
          <h3 className="text-lg font-semibold text-muted-foreground">
            No profiles found
          </h3>
          <p className="text-sm text-muted-foreground max-w-xs mt-1">
            Try adjusting your search or filters.
          </p>
        </div>
      );
    }
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {profileList.map((profile) => {
          let comments: string[] = [];
          let sources: any[] = [];
          try {
            comments = JSON.parse(profile.comment_history || "[]");
            sources = JSON.parse(profile.source_posts || "[]");
          } catch (e) {
            console.error("Error parsing profile data", e);
          }

          return (
            <Card
              key={profile.id}
              className="group hover:border-primary/50 transition-all duration-300 overflow-hidden flex flex-col relative"
            >
              <div className="absolute top-5 left-4 z-20">
                <Checkbox
                  checked={selectedIds.has(profile.id)}
                  onCheckedChange={() => toggleSelection(profile.id)}
                  disabled={
                    leadsStatus?.find((s) => s.url === profile.linkedin_url)
                      ?.status === "analyzing" ||
                    leadsStatus?.find((s) => s.url === profile.linkedin_url)
                      ?.status === "pending"
                  }
                />
              </div>
              <div className="h-1 bg-muted group-hover:bg-primary/50 transition-colors" />
              <CardHeader className="pb-3 pl-12">
                <div className="flex justify-between items-start">
                  <div className="space-y-1">
                    <CardTitle className="text-lg font-bold group-hover:text-primary transition-colors">
                      {profile.name || "Anonymous Profile"}
                    </CardTitle>
                    <div className="flex flex-wrap items-center gap-3">
                      <a
                        href={profile.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[10px] text-blue-600 hover:underline flex items-center gap-1 opacity-80"
                      >
                        <Globe className="w-2.5 h-2.5" />
                        LinkedIn
                        <ExternalLink className="w-2 h-2" />
                      </a>
                      {profile.website && (
                        <a
                          href={ensureProtocol(profile.website)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[10px] text-emerald-600 hover:underline flex items-center gap-1 opacity-80"
                        >
                          <Globe className="w-2.5 h-2.5" />
                          Website
                          <ExternalLink className="w-2 h-2" />
                        </a>
                      )}
                      {profile.email && (
                        <div className="flex items-center gap-1">
                          <span className="text-[10px] text-muted-foreground">{profile.email}</span>
                          {renderEmailVerificationBadge(profile.email_verification_status)}
                        </div>
                      )}
                    </div>
                    {profile.headline && (
                      <p className="text-xs text-muted-foreground mt-1 text-ellipsis overflow-hidden line-clamp-2">
                        {profile.headline}
                      </p>
                    )}
                    {/* Company Stats (New) */}
                    {profile.company && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {profile.company.industries && (
                          <Badge
                            variant="secondary"
                            className="text-[9px] bg-indigo-50 text-indigo-700 border-indigo-100"
                          >
                            {(() => {
                              try {
                                const inds = JSON.parse(
                                  profile.company.industries,
                                );
                                return Array.isArray(inds) ? inds[0] : inds;
                              } catch (e) {
                                return profile.company.industries;
                              }
                            })()}
                          </Badge>
                        )}
                        {profile.company.employee_count && (
                          <Badge
                            variant="secondary"
                            className="text-[9px] bg-slate-50 text-slate-600 border-slate-100"
                          >
                            <Users className="w-2.5 h-2.5 mr-1" />
                            {profile.company.employee_count.toLocaleString()}
                          </Badge>
                        )}
                        {profile.company.revenue_estimate && (
                          <Badge
                            variant="secondary"
                            className="text-[9px] bg-emerald-50 text-emerald-700 border-emerald-100 font-bold"
                          >
                            $ {profile.company.revenue_estimate}
                          </Badge>
                        )}
                        {profile.company.market_cap && (
                          <Badge
                            variant="secondary"
                            className="text-[9px] bg-amber-50 text-amber-700 border-amber-100 font-bold"
                          >
                            MC: {profile.company.market_cap}
                          </Badge>
                        )}
                        {profile.company.total_funding && (
                          <Badge
                            variant="secondary"
                            className="text-[9px] bg-blue-50 text-blue-700 border-blue-100 font-bold cursor-pointer hover:bg-blue-100 transition-colors"
                            onClick={() => {
                              if (profile.company_id) {
                                setSelectedCompanyId(profile.company_id);
                                setIsCompanyModalOpen(true);
                              }
                            }}
                          >
                            Fund: {profile.company.total_funding}
                          </Badge>
                        )}
                      </div>
                    )}
                    <div className="flex flex-wrap gap-2 mt-2">
                      {(() => {
                        const profileUrl = normalizeUrl(profile.linkedin_url);
                        const leadStatusObj = leadsStatus?.find(
                          (s) => normalizeUrl(s.url) === profileUrl || s.url === profile.linkedin_url,
                        );
                        const status = leadStatusObj?.status;
                        const currentStep = leadStatusObj?.currentStep;

                        if (status === "analyzing") {
                          return (
                            <div className="flex flex-col gap-2 p-3 rounded-lg bg-blue-50 border border-blue-100 animate-pulse w-full">
                              <div className="flex items-center justify-between text-[10px] font-bold text-blue-700">
                                <span className="flex items-center gap-2">
                                  <Loader2 className="w-3 h-3 animate-spin" />
                                  {currentStep || "Researching..."}
                                </span>
                                <span>{leadStatusObj?.progress || 0}%</span>
                              </div>
                              <Progress
                                value={leadStatusObj?.progress || 0}
                                className="h-1 bg-blue-200/50"
                              />
                            </div>
                          );
                        }
                        if (status === "pending") {
                          return (
                            <Badge
                              variant="secondary"
                              className="text-[9px] h-5 px-1.5 bg-gray-100 text-gray-500 border-gray-200"
                            >
                              Queued
                            </Badge>
                          );
                        }
                        return null;
                      })()}
                      {!profile.fit_reasoning &&
                        !profile.is_fit &&
                        !profile.is_competitor &&
                        !(() => {
                          const profileUrl = normalizeUrl(profile.linkedin_url);
                          return leadsStatus?.find(
                            (s) => normalizeUrl(s.url) === profileUrl || s.url === profile.linkedin_url,
                          );
                        })() && (
                          <Badge
                            variant="secondary"
                            className="text-[9px] h-5 px-1.5 bg-gray-100 text-gray-500 animate-pulse"
                          >
                            AI Analyzing...
                          </Badge>
                        )}
                      {profile.outreach_status && (
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[9px] h-5 px-1.5",
                            profile.outreach_status === "not_started"
                              ? "bg-zinc-100 text-zinc-500 border-zinc-200"
                              : profile.outreach_status === "in_progress"
                                ? "bg-amber-50 text-amber-600 border-amber-200"
                                : "bg-green-50 text-green-700 border-green-200",
                          )}
                        >
                          {profile.outreach_status.replace("_", " ")}
                        </Badge>
                      )}
                      {profile.is_competitor && (
                        <Badge
                          variant="destructive"
                          className="text-[10px] h-5 px-1.5"
                        >
                          Competitor
                        </Badge>
                      )}
                      {profile.is_fit && (
                        <Badge
                          variant="outline"
                          className="text-[10px] h-5 px-1.5 bg-green-50 text-green-700 border-green-200 hover:bg-green-100 cursor-help"
                          title={profile.fit_reasoning}
                        >
                          <CheckCircle2 className="w-3 h-3 mr-1" />
                          Potential Fit
                        </Badge>
                      )}
                      {profile.is_buy_signal && (
                        <Badge
                          variant="outline"
                          className="text-[10px] h-5 px-1.5 bg-violet-50 text-violet-700 border-violet-200 hover:bg-violet-100"
                        >
                          <Zap className="w-3 h-3 mr-1" />
                          Buy Signal
                        </Badge>
                      )}
                      {profile.is_strategic_seller && (
                        <Badge
                          variant="outline"
                          className="text-[10px] h-5 px-1.5 bg-zinc-50 text-zinc-700 border-zinc-200 hover:bg-zinc-100"
                        >
                          <TrendingUp className="w-3 h-3 mr-1" />
                          Strategic Seller
                        </Badge>
                      )}
                      {profile.is_decision_maker && (
                        <Badge
                          variant="outline"
                          className="text-[10px] h-5 px-1.5 bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100"
                        >
                          <UserCheck className="w-3 h-3 mr-1" />
                          Decision Maker
                        </Badge>
                      )}
                    </div>
                    {profile.fit_reasoning && (
                      <div className="mt-3 text-[10px] text-muted-foreground bg-muted/40 p-2 rounded border border-muted/50 italic leading-relaxed">
                        <span className="font-semibold not-italic text-primary/70 mr-1">
                          AI Reasoning:
                        </span>
                        {profile.fit_reasoning}
                      </div>
                    )}
                  </div>
                  {sources.length > 0 && (
                    <TooltipProvider>
                      <Tooltip delayDuration={100}>
                        <TooltipTrigger asChild>
                          <div className="group/touchpoints cursor-help">
                            <Badge
                              variant="secondary"
                              className="bg-primary/5 text-[10px] text-primary border-primary/10 hover:bg-primary/10 transition-colors py-1 flex items-center gap-1.5"
                            >
                              <div className="flex items-center gap-1">
                                <Search className="w-2.5 h-2.5 opacity-60" />
                                {getTouchpointStats(profile).keywordCount}
                              </div>
                              <div className="w-px h-2.5 bg-primary/20" />
                              <div className="flex items-center gap-1">
                                <Users className="w-2.5 h-2.5 opacity-60" />
                                {getTouchpointStats(profile).competitorCount}
                              </div>
                            </Badge>
                          </div>
                        </TooltipTrigger>
                        <TooltipContent
                          side="left"
                          className="w-80 p-0 shadow-xl border-primary/20 overflow-hidden"
                        >
                          <div className="p-3 bg-muted/30 border-b border-primary/10 flex items-center justify-between">
                            <span className="font-bold text-xs uppercase tracking-tight">
                              All Discoveries
                            </span>
                            <Badge variant="outline" className="text-[10px]">
                              {getTouchpointStats(profile).totalCount} Total
                            </Badge>
                          </div>
                          <div className="max-h-60 overflow-y-auto p-2 space-y-2 scrollbar-thin">
                            {getTouchpointStats(profile).allTouchpoints.map(
                              (tp, i) => (
                                <div
                                  key={i}
                                  className="p-2 rounded bg-muted/40 border border-muted/50 hover:bg-muted/60 transition-colors"
                                >
                                  <div className="flex items-center gap-1.5 mb-1">
                                    <div className="w-1.5 h-1.5 rounded-full bg-primary/40 shrink-0" />
                                    <span className="text-[10px] font-bold uppercase text-primary/70">
                                      {tp.competitor}
                                    </span>
                                  </div>
                                  <a
                                    href={tp.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-[10px] text-blue-600 hover:underline whitespace-normal italic block pl-3"
                                  >
                                    "{tp.title}"
                                  </a>
                                  {tp.comments.length > 0 && (
                                    <div className="mt-2 pl-3 space-y-1.5 border-l border-primary/10 ml-1">
                                      {tp.comments.map((comment, ci) => (
                                        <div
                                          key={ci}
                                          className="text-[10px] text-muted-foreground leading-relaxed flex gap-1.5"
                                        >
                                          <MessageSquare className="w-2.5 h-2.5 mt-0.5 opacity-40 shrink-0" />
                                          <p className="line-clamp-3">
                                            {comment}
                                          </p>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              ),
                            )}
                          </div>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )}
                </div>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col space-y-6">
                {(() => {
                  const leadStatusObj = leadsStatus?.find(
                    (s) =>
                      normalizeUrl(s.url) === normalizeUrl(profile.linkedin_url),
                  );
                  const status = leadStatusObj?.status;
                  const result = leadStatusObj?.result;
                  const currentStep = leadStatusObj?.currentStep;
                  const reportId =
                    status === "completed" && result?.id
                      ? result.id
                      : profile.latest_report_id;

                  if (reportId) {
                    return (
                      <div
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setSelectedReportId(reportId);
                          setIsReportModalOpen(true);
                        }}
                        className="group/report flex items-center justify-between p-2 rounded-lg bg-primary/5 hover:bg-primary/10 border border-primary/10 transition-colors cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          <div className="bg-primary/10 text-primary p-1.5 rounded-md">
                            <FileText className="w-3.5 h-3.5" />
                          </div>
                          <span className="text-xs font-semibold text-primary">
                            View Research Report
                          </span>
                        </div>
                        <Eye className="w-3.5 h-3.5 text-primary opacity-60 group-hover/report:opacity-100 transition-opacity" />
                      </div>
                    );
                  }
                  return null;
                })()}
                {profile.interaction_history ? (
                  <div className="space-y-4">
                    {JSON.parse(profile.interaction_history).map(
                      (comp: any, ci: number) => (
                        <div
                          key={ci}
                          className="space-y-3 p-3 rounded-lg bg-muted/20 border border-muted/50"
                        >
                          <div className="flex items-center gap-2">
                            <div className="bg-primary/10 text-primary p-1 rounded-md">
                              <Users className="w-3.5 h-3.5" />
                            </div>
                            <span className="text-xs font-bold uppercase tracking-tight">
                              {comp.competitor}
                            </span>
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
                                  {post.comments.map(
                                    (comment: string, comi: number) => (
                                      <div
                                        key={comi}
                                        className="flex gap-2 items-start"
                                      >
                                        <div className="mt-1.5 w-1 h-1 rounded-full bg-muted-foreground/30 shrink-0" />
                                        <p className="text-[11px] text-muted-foreground leading-relaxed italic border-l pl-2 py-0.5 border-primary/10">
                                          "{comment}"
                                        </p>
                                      </div>
                                    ),
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ),
                    )}
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
                          <p
                            key={i}
                            className="text-[10px] text-muted-foreground italic bg-muted/30 p-2 rounded-md border border-muted/50"
                          >
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
                              "{source.title}"{" "}
                              <span className="text-[9px] not-italic text-primary/50 font-medium">
                                ({source.competitor})
                              </span>
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
                    Identified by: {profile.rep_name || "System"}
                  </span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    );
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

  const SortButton = ({
    column,
    label,
  }: {
    column: string;
    label: string | React.ReactNode;
  }) => {
    const isActive = sortBy === column;
    return (
      <button
        onClick={() => toggleSort(column)}
        className={`flex items-center gap-1 hover:text-primary transition-colors ${isActive ? "text-primary font-bold" : ""
          }`}
      >
        {label}
        {isActive ? (
          sortOrder === "asc" ? (
            <ArrowUp className="w-3 h-3" />
          ) : (
            <ArrowDown className="w-3 h-3" />
          )
        ) : (
          <ArrowUpDown className="w-3 h-3 opacity-30" />
        )}
      </button>
    );
  };

  const renderProfileList = (profileList: IdentifiedProfile[]) => {
    if (profileList.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-20 bg-muted/30 rounded-xl border-2 border-dashed text-center">
          <Users className="w-12 h-12 text-muted-foreground/30 mb-4" />
          <h3 className="text-lg font-semibold text-muted-foreground">
            No profiles found
          </h3>
          <p className="text-sm text-muted-foreground max-w-xs mt-1">
            Try adjusting your search or filters.
          </p>
        </div>
      );
    }

    return (
      <div className="rounded-md border bg-card overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40px]">
                <Checkbox
                  checked={
                    selectedIds.size === profileList.length &&
                    profileList.length > 0
                  }
                  onCheckedChange={toggleSelectAll}
                />
              </TableHead>
              <TableHead>
                <SortButton column="name" label="Profile" />
              </TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Industry</TableHead>
              <TableHead>Stats</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>
                <SortButton
                  column="touchpoint_count"
                  label="Interaction History"
                />
              </TableHead>
              <TableHead>AI Reasoning</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {profileList.map((profile) => {
              const profileUrl = normalizeUrl(profile.linkedin_url);
              const leadStatusObj = leadsStatus?.find(
                (s) => normalizeUrl(s.url) === profileUrl || s.url === profile.linkedin_url,
              );
              const status = leadStatusObj?.status;
              const result = leadStatusObj?.result;
              const currentStep = leadStatusObj?.currentStep;
              const reportId =
                status === "completed" && result?.id
                  ? result.id
                  : profile.latest_report_id;

              let interactionHistory: any[] = [];
              let profileMeta: any = {};
              try {
                interactionHistory = JSON.parse(
                  profile.interaction_history || "[]",
                );
              } catch (e) { }
              try {
                profileMeta = JSON.parse(profile.profile_metadata || "{}");
              } catch (e) { }

              return (
                <TableRow key={profile.id}>
                  <TableCell>
                    <Checkbox
                      checked={selectedIds.has(profile.id)}
                      onCheckedChange={() => toggleSelection(profile.id)}
                      disabled={status === "analyzing" || status === "pending" || profile.linkedin_url.startsWith("apollo_id:")}
                    />
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col max-w-[300px]">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-bold truncate">
                          {profile.name || "Anonymous"}
                        </span>
                        {renderEmailVerificationBadge(profile.email_verification_status)}
                      </div>
                      <div className="flex flex-wrap items-center gap-2 mt-0.5">
                        <a
                          href={profile.linkedin_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[10px] text-blue-600 hover:underline flex items-center gap-1"
                        >
                          LinkedIn <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                        {profile.website && (
                          <a
                            href={ensureProtocol(profile.website)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[10px] text-emerald-600 hover:underline flex items-center gap-1"
                          >
                            Website <Globe className="w-2.5 h-2.5" />
                          </a>
                        )}
                        {profile.email && (
                          <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                            {profile.email}
                            {renderEmailVerificationBadge(profile.email_verification_status)}
                          </span>
                        )}
                      </div>
                      {profile.headline && (
                        <p className="text-[10px] text-muted-foreground truncate italic mt-0.5">
                          {profile.headline}
                        </p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div
                      className="flex flex-col group/company cursor-pointer"
                      onClick={() => {
                        if (profile.company_id) {
                          setSelectedCompanyId(profile.company_id);
                          setIsCompanyModalOpen(true);
                        }
                      }}
                    >
                      <span className="text-xs font-semibold truncate max-w-[150px] group-hover/company:text-primary group-hover/company:underline">
                        {profile.company?.name || profile.profile_metadata?.company_name || "—"}
                      </span>
                      {profile.company?.website || profile.website ? (
                        <span className="text-[9px] text-muted-foreground truncate max-w-[150px] opacity-70">
                          {(profile.company?.website || profile.website || "").replace(/^https?:\/\//, "")}
                        </span>
                      ) : null}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className="text-[9px] bg-indigo-50 text-indigo-700 border-indigo-100 max-w-[120px] truncate block text-center"
                    >
                      {(() => {
                        try {
                          const inds = profile.company?.industries 
                            ? JSON.parse(profile.company.industries)
                            : (profile.profile_metadata?.company_industries || []);
                          return Array.isArray(inds) ? inds[0] : inds || "—";
                        } catch (e) {
                          return "—";
                        }
                      })()}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-1">
                      {profile.company?.employee_count && (
                        <div className="text-[9px] text-muted-foreground flex items-center gap-1">
                          <Users className="w-2.5 h-2.5" />
                          {profile.company.employee_count.toLocaleString()}
                        </div>
                      )}
                      {profile.company?.revenue_estimate && (
                        <div className="text-[9px] text-emerald-600 font-bold">
                          $ {profile.company.revenue_estimate}
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {profile.is_competitor && (
                        <Badge variant="destructive" className="text-[9px] h-4">
                          Comp
                        </Badge>
                      )}
                      {profile.is_fit && (
                        <Badge
                          variant="outline"
                          className="text-[9px] h-4 bg-green-50 text-green-700 border-green-200"
                          title={profile.fit_reasoning}
                        >
                          Fit
                        </Badge>
                      )}
                      {profile.is_buy_signal && (
                        <Badge
                          variant="outline"
                          className="text-[9px] h-4 bg-violet-50 text-violet-700 border-violet-200"
                        >
                          Buyer
                        </Badge>
                      )}
                      {profile.is_strategic_seller && (
                        <Badge
                          variant="outline"
                          className="text-[9px] h-4 bg-zinc-50 text-zinc-700 border-zinc-200"
                        >
                          Seller
                        </Badge>
                      )}
                      {profile.is_decision_maker && (
                        <Badge
                          variant="outline"
                          className="text-[9px] h-4 bg-blue-50 text-blue-700 border-blue-200"
                        >
                          DM
                        </Badge>
                      )}
                      {profile.outreach_status && (
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[9px] h-4",
                            profile.outreach_status === "not_started"
                              ? "bg-zinc-100 text-zinc-500 border-zinc-200"
                              : profile.outreach_status === "in_progress"
                                ? "bg-amber-50 text-amber-600 border-amber-200"
                                : "bg-green-50 text-green-700 border-green-200",
                          )}
                        >
                          {profile.outreach_status.replace("_", " ")}
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-normal min-w-[240px] max-w-[450px]">
                    <div className="">
                      {interactionHistory.length > 0 ? (
                        <TooltipProvider>
                          <Tooltip delayDuration={100}>
                            <TooltipTrigger asChild>
                              <div className="flex flex-col gap-1.5 cursor-help group/touchpoints hover:bg-muted/30 p-1.5 rounded-md transition-colors">
                                <div className="flex items-center gap-2">
                                  <Badge
                                    variant="secondary"
                                    className="bg-primary/5 text-[9px] text-primary border-primary/10 py-0.5"
                                  >
                                    <Search className="w-2.5 h-2.5 mr-1 opacity-60" />
                                    {getTouchpointStats(profile).keywordCount}
                                  </Badge>
                                  <Badge
                                    variant="secondary"
                                    className="bg-primary/5 text-[9px] text-primary border-primary/10 py-0.5"
                                  >
                                    <Users className="w-2.5 h-2.5 mr-1 opacity-60" />
                                    {
                                      getTouchpointStats(profile)
                                        .competitorCount
                                    }
                                  </Badge>
                                  <Info className="w-3.5 h-3.5 text-primary/30 group-hover/touchpoints:text-primary transition-colors ml-auto" />
                                </div>
                                {interactionHistory
                                  .slice(0, 1)
                                  .map((comp, i) => (
                                    <div
                                      key={i}
                                      className="text-[10px] whitespace-normal"
                                    >
                                      <span className="font-semibold uppercase text-primary/70">
                                        {comp.competitor}:
                                      </span>{" "}
                                      <span className="text-muted-foreground italic">
                                        "{comp.posts?.[0]?.comments?.[0]}"
                                      </span>
                                    </div>
                                  ))}
                              </div>
                            </TooltipTrigger>
                            <TooltipContent
                              side="left"
                              className="w-80 p-0 shadow-xl border-primary/20 overflow-hidden"
                            >
                              <div className="p-3 bg-muted/30 border-b border-primary/10 flex items-center justify-between">
                                <span className="font-bold text-xs uppercase tracking-tight">
                                  All Discoveries
                                </span>
                                <Badge variant="outline" className="text-[10px] bg-white">
                                  {getTouchpointStats(profile).totalCount} Total
                                </Badge>
                              </div>
                              <div className="max-h-72 overflow-y-auto p-2 space-y-2 scrollbar-thin">
                                {getTouchpointStats(profile).allTouchpoints.map(
                                  (tp, i) => (
                                    <div
                                      key={i}
                                      className="p-2 rounded bg-muted/40 border border-muted/50 hover:bg-muted/60 transition-all"
                                    >
                                      <div className="flex items-center gap-1.5 mb-1">
                                        <div className="w-1.5 h-1.5 rounded-full bg-primary/40 shrink-0" />
                                        <span className="text-[10px] font-bold uppercase text-primary/70">
                                          {tp.competitor}
                                        </span>
                                      </div>
                                      <a
                                        href={tp.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-[10px] text-blue-600 hover:underline whitespace-normal italic block pl-3"
                                      >
                                        "{tp.title}"
                                      </a>
                                      {tp.comments.length > 0 && (
                                        <div className="mt-2 pl-3 space-y-1.5 border-l border-primary/10 ml-1">
                                          {tp.comments.map((comment, ci) => (
                                            <div
                                              key={ci}
                                              className="text-[10px] text-muted-foreground leading-relaxed flex gap-1.5"
                                            >
                                              <MessageSquare className="w-2.5 h-2.5 mt-0.5 opacity-40 shrink-0" />
                                              <p className="line-clamp-3">
                                                {comment}
                                              </p>
                                            </div>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  ),
                                )}
                              </div>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      ) : (
                        <span className="text-[10px] text-muted-foreground italic">
                          No history
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-normal min-w-[200px] max-w-[400px]">
                    {profile.fit_reasoning ? (
                      <div className="text-[10px] text-muted-foreground italic">
                        {profile.fit_reasoning}
                      </div>
                    ) : (
                      <span className="text-[10px] text-muted-foreground italic">
                        No reasoning available
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      {profile.linkedin_url.startsWith("apollo_id:") && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="h-7 text-[10px] px-2 hover:bg-amber-50 hover:text-amber-700 hover:border-amber-200 transition-colors shrink-0 gap-1.5"
                          onClick={() => {
                            if (profileMeta.apollo_id) {
                              handleEnrich([profileMeta.apollo_id]);
                            }
                          }}
                          disabled={isLoading || (profileMeta.apollo_id && enrichingIds.has(profileMeta.apollo_id))}
                        >
                          {(profileMeta.apollo_id && enrichingIds.has(profileMeta.apollo_id)) ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Zap className="w-3 h-3 text-amber-500" />
                          )}
                          Enrich
                        </Button>
                      )}
                      {status === "analyzing" && (
                        <Badge
                          variant="secondary"
                          className="text-[9px] h-7 bg-blue-100/50 text-blue-700 animate-pulse border-blue-200"
                        >
                          <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                          {currentStep ? currentStep : "Processing..."}
                        </Badge>
                      )}
                      {reportId && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 text-primary hover:text-primary hover:bg-primary/10"
                          onClick={() => {
                            setSelectedReportId(reportId);
                            setIsReportModalOpen(true);
                          }}
                        >
                          <Eye className="w-3.5 h-3.5 mr-1" />
                          Report
                        </Button>
                      )}
                      {!status && !reportId && !profile.linkedin_url.startsWith("apollo_id:") && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="h-7 px-2"
                          onClick={() => {
                            const payload = [
                              {
                                url: profile.linkedin_url,
                                website: profile.website || "",
                              },
                            ];
                            setBulkLeads(payload);
                            setIsBulkModalOpen(true);
                            startBulkAnalysis(payload, {
                              project_urgency: 2,
                              lead_source: "Competitor Analysis",
                              refresh: false,
                            });
                          }}
                        >
                          <Play className="w-3.5 h-3.5 mr-1" />
                          Analyze
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    );
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
            <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
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
                <TabsTrigger value="apollo" className="gap-2 group">
                  <Zap className="w-4 h-4 text-primary group-data-[state=active]:fill-primary/20" />
                  Apollo
                  <Badge variant="secondary" className="ml-1 px-1 py-0 h-4 min-w-4 text-[10px]">
                    {tabCounts.apollo ?? 0}
                  </Badge>
                </TabsTrigger>
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
              </TabsList>
              <TabsContent value="all">
                {viewMode === "grid" ? renderProfileGrid(profiles) : renderProfileList(profiles)}
              </TabsContent>
              <TabsContent value="apollo">
                {viewMode === "grid" ? renderProfileGrid(profiles) : renderProfileList(profiles)}
              </TabsContent>
              <TabsContent value="competitor">
                {viewMode === "grid" ? renderProfileGrid(profiles) : renderProfileList(profiles)}
              </TabsContent>
              <TabsContent value="keyword">
                {viewMode === "grid" ? renderProfileGrid(profiles) : renderProfileList(profiles)}
              </TabsContent>
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
