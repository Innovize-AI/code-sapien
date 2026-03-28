"use client";

import { useState, useEffect } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Globe,
  Linkedin,
  Users,
  DollarSign,
  MapPin,
  TrendingUp,
  Cpu,
  Newspaper,
  Briefcase,
  ExternalLink,
  ChevronRight,
  Loader2,
  Sparkles,
  Activity,
  FileText,
  MessageSquare,
  Zap,
} from "lucide-react";
import { ensureProtocol, cn } from "@/lib/utils";
import { API_URL } from "@/lib/api";

interface CompanyDetailModalProps {
  companyId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onOpenReport?: (reportId: string) => void;
}

interface CompanyData {
  id: string;
  name: string;
  domain?: string;
  website?: string;
  linkedin_url?: string;
  description?: string;
  industries?: string;
  employee_count?: number;
  revenue?: string;
  total_funding?: string;
  headquarters?: string;
  technologies?: string;
  technology_names?: string;
  funding_events?: string;
  latest_funding_stage?: string;
  headcount_growth?: string;
  news?: string;
  hiring?: string;
  updated_at?: string;
  people?: {
    id: string;
    name?: string;
    headline?: string;
    linkedin_url: string;
    email?: string;
    is_fit: boolean;
    is_decision_maker: boolean;
    is_buy_signal?: boolean;
    is_strategic_seller?: boolean;
    intent?: string;
    sentiment?: string;
    post_topic_depth?: string;
    fit_reasoning?: string;
    interaction_history?: string;
    last_interaction_at?: string;
    latest_report_id?: string;
  }[];
}

export function CompanyDetailModal({
  companyId,
  isOpen,
  onClose,
  onOpenReport,
}: CompanyDetailModalProps) {
  const [company, setCompany] = useState<CompanyData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen && companyId) {
      fetchCompanyDetails(companyId);
    }
  }, [isOpen, companyId]);

  const fetchCompanyDetails = async (id: string) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/companies/${id}`);
      if (response.ok) {
        const data = await response.json();
        setCompany(data);
      }
    } catch (error) {
      console.error("Failed to fetch company details:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const parseJson = (str: string | undefined): any[] => {
    try {
      return str ? JSON.parse(str) : [];
    } catch (e) {
      return [];
    }
  };

  if (!isOpen) return null;

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent className="sm:max-w-2xl md:max-w-3xl lg:max-w-5xl xl:max-w-6xl w-full overflow-y-auto p-0 border-l border-primary/10 transition-all duration-300">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : company ? (
          <div className="flex flex-col h-full bg-background">
            {/* Header Content */}
            <div className="p-6 border-b bg-muted/5">
              <div className="flex items-center gap-2 text-[10px] text-muted-foreground uppercase font-bold tracking-widest mb-4">
                <span>Profiles</span>
                <ChevronRight className="w-3 h-3" />
                <span className="text-primary/70">{company.name}</span>
              </div>

              <div className="flex justify-between items-start">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-xl bg-primary/10 flex items-center justify-center text-primary font-bold text-2xl border border-primary/20 shadow-sm">
                    {company.name.charAt(0)}
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold tracking-tight">
                      {company.name}
                    </h2>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge
                        variant="outline"
                        className="bg-green-50 text-green-700 border-green-200 text-[10px] font-bold"
                      >
                        Expansion Potential
                      </Badge>
                      {company.website && (
                        <a
                          href={ensureProtocol(company.website)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-muted-foreground hover:text-primary flex items-center gap-1 transition-colors"
                        >
                          {company.website.replace(/^https?:\/\//, "")}
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {company.linkedin_url && (
                    <Button
                      variant="ghost"
                      size="icon"
                      asChild
                      className="h-9 w-9 border border-muted/50"
                    >
                      <a
                        href={company.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Linkedin className="w-4 h-4 text-[#0077b5]" />
                      </a>
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-9 w-9 border border-muted/50"
                  >
                    <Sparkles className="w-4 h-4 text-primary" />
                  </Button>
                </div>
              </div>
            </div>

            {/* Tabs Sidebar/Top */}
            <Tabs defaultValue="overview" className="flex-1 flex flex-col">
              <div className="px-6 bg-muted/5 border-b">
                <TabsList className="bg-transparent border-0 h-11 p-0 gap-6">
                  <TabsTrigger
                    value="overview"
                    className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-11 p-0 font-bold text-xs uppercase tracking-tight"
                  >
                    Overview
                  </TabsTrigger>
                  <TabsTrigger
                    value="signals"
                    className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-11 p-0 font-bold text-xs uppercase tracking-tight"
                  >
                    Signals
                  </TabsTrigger>
                  <TabsTrigger
                    value="people"
                    className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-11 p-0 font-bold text-xs uppercase tracking-tight"
                  >
                    People
                  </TabsTrigger>
                  <TabsTrigger
                    value="activity"
                    className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-11 p-0 font-bold text-xs uppercase tracking-tight"
                  >
                    Recent Activity
                  </TabsTrigger>
                </TabsList>
              </div>

              {/* Tab Content */}
              <TabsContent
                value="overview"
                className="flex-1 p-6 space-y-8 m-0 overflow-y-auto"
              >
                {/* Field Grid */}
                <div className="grid grid-cols-3 gap-y-6 gap-x-8">
                  <div className="space-y-1">
                    <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                      Company Name
                    </p>
                    <p className="text-sm font-semibold">{company.name}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                      Industry
                    </p>
                    <p className="text-sm font-semibold">
                      {parseJson(company.industries)?.[0] ||
                        company.industries ||
                        "—"}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                      Employee Count
                    </p>
                    <p className="text-sm font-semibold">
                      {company.employee_count?.toLocaleString() || "—"}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                      Revenue
                    </p>
                    <p className="text-sm font-semibold text-emerald-600 font-bold">
                      {company.revenue || "—"}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                      Domain
                    </p>
                    <p className="text-sm font-semibold truncate hover:text-primary transition-colors cursor-pointer">
                      {company.domain ||
                        company.website?.replace(/^https?:\/\/(www\.)?/, "") ||
                        "—"}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                      Headquarters
                    </p>
                    <p className="text-sm font-semibold">
                      {company.headquarters || "—"}
                    </p>
                  </div>
                </div>

                {/* Tech Stack (Moved from Signals) */}
                <div className="space-y-4 pt-4 border-t">
                  <div className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-primary/70">
                    <Cpu className="w-4 h-4" />
                    Tech Stack
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {parseJson(company.technology_names || company.technologies)
                      .length > 0 ? (
                      parseJson(
                        company.technology_names || company.technologies,
                      ).map((tech: string, i: number) => (
                        <Badge
                          key={i}
                          variant="secondary"
                          className="bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border-indigo-100/50 py-1 px-3"
                        >
                          {tech}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-xs text-muted-foreground italic pl-1">
                        No technology data available.
                      </span>
                    )}
                  </div>
                </div>

                {/* Company Summary */}
                <div className="bg-primary/5 rounded-xl border border-primary/10 overflow-hidden shadow-sm">
                  <div className="p-4 border-b border-primary/10 flex items-center justify-between bg-primary/[0.02]">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-primary" />
                      <h3 className="text-sm font-bold tracking-tight">
                        Company Summary ✨
                      </h3>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className="text-[9px] font-bold text-primary/60 border-primary/20"
                      >
                        AI ENRICHED
                      </Badge>
                    </div>
                  </div>
                  <div className="p-5 text-sm leading-relaxed text-muted-foreground space-y-4 whitespace-pre-wrap">
                    {company.description ||
                      "No primary summary available for this company yet."}
                  </div>
                </div>
              </TabsContent>

              <TabsContent
                value="signals"
                className="flex-1 p-6 space-y-6 m-0 overflow-y-auto"
              >
                {/* Growth Trends (Moved from Overview to Signals) */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-primary/70">
                    <TrendingUp className="w-4 h-4" />
                    Growth Trends
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 rounded-xl border border-muted-foreground/10 bg-muted/10 space-y-1 text-center">
                      <p className="text-[10px] font-bold uppercase text-muted-foreground/70">
                        6 Months
                      </p>
                      <p
                        className={cn(
                          "text-lg font-bold",
                          (parseJson(company.headcount_growth as any) as any)[
                            "6_month"
                          ] >= 0
                            ? "text-emerald-600"
                            : "text-rose-600",
                        )}
                      >
                        {(parseJson(company.headcount_growth as any) as any)[
                          "6_month"
                        ] !== undefined
                          ? `${(parseJson(company.headcount_growth as any) as any)["6_month"]}%`
                          : "—"}
                      </p>
                    </div>
                    <div className="p-4 rounded-xl border border-muted-foreground/10 bg-muted/10 space-y-1 text-center">
                      <p className="text-[10px] font-bold uppercase text-muted-foreground/70">
                        12 Months
                      </p>
                      <p
                        className={cn(
                          "text-lg font-bold",
                          (parseJson(company.headcount_growth as any) as any)[
                            "12_month"
                          ] >= 0
                            ? "text-emerald-600"
                            : "text-rose-600",
                        )}
                      >
                        {(parseJson(company.headcount_growth as any) as any)[
                          "12_month"
                        ] !== undefined
                          ? `${(parseJson(company.headcount_growth as any) as any)["12_month"]}%`
                          : "—"}
                      </p>
                    </div>
                    <div className="p-4 rounded-xl border border-muted-foreground/10 bg-muted/10 space-y-1 text-center">
                      <p className="text-[10px] font-bold uppercase text-muted-foreground/70">
                        24 Months
                      </p>
                      <p
                        className={cn(
                          "text-lg font-bold",
                          (parseJson(company.headcount_growth as any) as any)[
                            "24_month"
                          ] >= 0
                            ? "text-emerald-600"
                            : "text-rose-600",
                        )}
                      >
                        {(parseJson(company.headcount_growth as any) as any)[
                          "24_month"
                        ] !== undefined
                          ? `${(parseJson(company.headcount_growth as any) as any)["24_month"]}%`
                          : "—"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Hiring */}
                <div className="space-y-4 pt-4 border-t">
                  <div className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-primary/70">
                    <Briefcase className="w-4 h-4" />
                    Recent Hiring
                  </div>
                  <div className="grid grid-cols-1 gap-2">
                    {parseJson(company.hiring).length > 0 ? (
                      parseJson(company.hiring).map((job: any, i: number) => {
                        const isString = typeof job === "string";
                        const title = isString ? job : job.title;
                        const url = isString ? null : job.url;
                        const category = isString
                          ? "Open"
                          : job.category || "Open";

                        return (
                          <div
                            key={i}
                            className="flex items-center justify-between p-3 rounded-lg border border-muted/50 bg-muted/10 hover:bg-muted/20 transition-colors group/job"
                          >
                            <div className="flex flex-col">
                              <span className="text-sm font-semibold group-hover/job:text-primary transition-colors">
                                {title}
                              </span>
                              {url && (
                                <a
                                  href={url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-[10px] text-blue-600 hover:underline flex items-center gap-1 mt-0.5"
                                >
                                  View Posting{" "}
                                  <ExternalLink className="w-2 h-2" />
                                </a>
                              )}
                            </div>
                            <Badge
                              variant="outline"
                              className="text-[10px] uppercase font-bold bg-background/50"
                            >
                              {category}
                            </Badge>
                          </div>
                        );
                      })
                    ) : (
                      <span className="text-xs text-muted-foreground italic pl-1">
                        No recent hiring signals found.
                      </span>
                    )}
                  </div>
                </div>

                {/* News */}
                <div className="space-y-4 pt-4 border-t">
                  <div className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-primary/70">
                    <Newspaper className="w-4 h-4" />
                    Latest News
                  </div>
                  <div className="space-y-3">
                    {parseJson(company.news).length > 0 ? (
                      parseJson(company.news).map((item: any, i: number) => {
                        const isString = typeof item === "string";
                        const title = isString ? item : item.title;
                        const source = isString
                          ? "News"
                          : item.source || "News";
                        const date = isString ? "" : item.date || "";
                        const url = isString ? null : item.url || item.link;

                        return (
                          <div
                            key={i}
                            className="p-3 rounded-lg bg-muted/10 border border-muted/50 space-y-2 group/news"
                          >
                            <h4 className="text-sm font-bold line-clamp-2 leading-tight group-hover/news:text-primary transition-colors">
                              {title}
                            </h4>
                            <div className="flex items-center justify-between text-[10px] text-muted-foreground uppercase font-bold tracking-tight">
                              <div className="flex items-center gap-2">
                                <span>{source}</span>
                                {url && (
                                  <a
                                    href={url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-blue-600 hover:underline flex items-center gap-1"
                                  >
                                    Read <ExternalLink className="w-2 h-2" />
                                  </a>
                                )}
                              </div>
                              <span>{date}</span>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <span className="text-xs text-muted-foreground italic pl-1">
                        No recent news events found.
                      </span>
                    )}
                  </div>
                </div>
              </TabsContent>

              <TabsContent
                value="activity"
                className="flex-1 p-0 m-0 overflow-y-auto"
              >
                {(() => {
                  const news = parseJson(company.news);
                  const hiring = parseJson(company.hiring);
                  const funding = parseJson(company.funding_events);
                  const people = company.people || [];

                  // Prepare unified feed items
                  const feedItems: any[] = [];

                  // 1. Social Signals (Identified Profiles)
                  people.forEach((p) => {
                    console.log(p);
                    try {
                      const history = p.interaction_history
                        ? JSON.parse(p.interaction_history as any)
                        : [];
                      console.log(history);
                      history.forEach((h: any) => {
                        const isKeyword = h.competitor?.startsWith("Keyword:");
                        const typeLabel = isKeyword
                          ? "Intent via Keyword"
                          : `Engaged with ${h.competitor}`;

                        (h.posts || []).forEach((post: any) => {
                          // If there are comments, push one entry per comment for full visibility
                          if (post.comments && post.comments.length > 0) {
                            post.comments.forEach((comment: string) => {
                              feedItems.push({
                                type: "social",
                                date:
                                  post.date ||
                                  p.last_interaction_at ||
                                  company.updated_at,
                                title: `${p.name || "A lead"} (${typeLabel})`,
                                description: `Commented: "${comment}" on "${post.title}"`,
                                icon: <MessageSquare className="w-4 h-4" />,
                                color: isKeyword
                                  ? "text-amber-600 bg-amber-50 border-amber-100"
                                  : "text-blue-600 bg-blue-50 border-blue-100",
                                url: post.url,
                                is_buy_signal: p.is_buy_signal,
                                is_strategic_seller: p.is_strategic_seller,
                                sentiment: p.sentiment,
                              });
                            });
                          } else {
                            // If no comments, just show the post interaction (likely the reason they were identified)
                            feedItems.push({
                              type: "social",
                              date:
                                post.date ||
                                p.last_interaction_at ||
                                company.updated_at,
                              title: `${p.name || "A lead"} (${typeLabel})`,
                              description: `Interacted with post: "${post.title}"`,
                              icon: <Activity className="w-4 h-4" />,
                              color: isKeyword
                                ? "text-amber-600 bg-amber-50 border-amber-100"
                                : "text-blue-600 bg-blue-50 border-blue-100",
                              url: post.url,
                              is_buy_signal: p.is_buy_signal,
                              is_strategic_seller: p.is_strategic_seller,
                              sentiment: p.sentiment,
                            });
                          }
                        });
                      });
                    } catch (e) {
                      console.error(
                        "Error parsing interaction history for feed",
                        e,
                      );
                    }
                  });

                  // 2. Funding Events (Apollo)
                  funding.forEach((f: any) => {
                    feedItems.push({
                      type: "funding",
                      date: f.date,
                      title: `${f.type || "Funding Round"} Announced`,
                      description: `Raised ${f.amount || "a significant amount"} ${f.currency || "USD"}${f.investors ? ` from ${f.investors}` : ""}.`,
                      icon: <DollarSign className="w-4 h-4" />,
                      color: "text-amber-600 bg-amber-50 border-amber-100",
                      url: f.news_url,
                    });
                  });

                  // 3. News Items (LinkedIn Scraper)
                  news.forEach((n: any) => {
                    const isStr = typeof n === "string";
                    feedItems.push({
                      type: "news",
                      date: isStr ? company.updated_at : n.date,
                      title: isStr ? "Company Update" : n.title,
                      description: isStr
                        ? n
                        : n.source || "Corporate announcement",
                      icon: <Newspaper className="w-4 h-4" />,
                      color: "text-indigo-600 bg-indigo-50 border-indigo-100",
                      url: isStr ? null : n.url || n.link,
                    });
                  });

                  // 4. Hiring (LinkedIn Scraper)
                  hiring.forEach((h: any) => {
                    const isStr = typeof h === "string";
                    feedItems.push({
                      type: "hiring",
                      date: isStr
                        ? company.updated_at
                        : h.posted_at || company.updated_at,
                      title: "New Job Opening",
                      description: isStr ? h : h.title,
                      icon: <Briefcase className="w-4 h-4" />,
                      color:
                        "text-emerald-600 bg-emerald-50 border-emerald-100",
                      url: isStr ? null : h.url,
                    });
                  });

                  // Sort by date desc
                  feedItems.sort(
                    (a, b) =>
                      new Date(b.date || 0).getTime() -
                      new Date(a.date || 0).getTime(),
                  );

                  if (feedItems.length === 0) {
                    return (
                      <div className="flex flex-col items-center justify-center h-[400px] text-center space-y-2 opacity-50">
                        <Activity className="w-10 h-10 mb-2" />
                        <h4 className="text-sm font-bold">
                          No Activity Recorded
                        </h4>
                        <p className="text-xs">
                          We haven't detected any recent news, hiring, or social
                          signals for this company.
                        </p>
                      </div>
                    );
                  }

                  return (
                    <div className="p-6 relative">
                      {/* Timeline Line */}
                      <div className="absolute left-8 top-8 bottom-8 w-0.5 bg-muted-foreground/10" />

                      <div className="space-y-8">
                        {feedItems.map((item, i) => (
                          <div key={i} className="relative pl-10 group">
                            {/* Dot/Icon */}
                            <div
                              className={cn(
                                "absolute left-[0.45rem] top-0 w-8 h-8 rounded-full border flex items-center justify-center z-10 shadow-sm transition-transform group-hover:scale-110",
                                item.color,
                              )}
                            >
                              {item.icon}
                            </div>

                            <div className="space-y-1.5">
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">
                                  {item.date
                                    ? new Date(item.date).toLocaleDateString(
                                        undefined,
                                        {
                                          month: "short",
                                          day: "numeric",
                                          year: "numeric",
                                        },
                                      )
                                    : "Recently"}
                                </span>
                                <div className="h-px flex-1 bg-muted-foreground/5" />
                              </div>

                              <div className="bg-muted/5 border border-muted/50 rounded-xl p-4 hover:bg-muted/10 transition-all hover:border-primary/20 shadow-sm relative overflow-hidden">
                                <div className="flex items-start justify-between gap-4">
                                  <div className="flex-1">
                                    <h5 className="text-sm font-bold tracking-tight mb-1 group-hover:text-primary transition-colors flex items-center gap-2">
                                      {item.title}
                                      {item.sentiment === "positive" && (
                                        <div
                                          className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]"
                                          title="Positive Sentiment"
                                        />
                                      )}
                                      {item.sentiment === "negative" && (
                                        <div
                                          className="w-1.5 h-1.5 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]"
                                          title="Negative Sentiment"
                                        />
                                      )}
                                    </h5>
                                    <p className="text-xs text-muted-foreground leading-relaxed italic">
                                      {item.description}
                                    </p>
                                  </div>

                                  {/* Signals */}
                                  <div className="flex flex-col gap-1 items-end shrink-0">
                                    {item.is_buy_signal && (
                                      <Badge
                                        variant="outline"
                                        className="text-[8px] h-4 bg-violet-50 text-violet-700 border-violet-200 uppercase font-bold px-1 animate-pulse"
                                      >
                                        <Zap className="w-2 h-2 mr-0.5" />
                                        Buy Signal
                                      </Badge>
                                    )}
                                    {item.is_strategic_seller && (
                                      <Badge
                                        variant="outline"
                                        className="text-[8px] h-4 bg-zinc-100 text-zinc-600 border-zinc-200 uppercase font-bold px-1"
                                      >
                                        Strategic Seller
                                      </Badge>
                                    )}
                                  </div>
                                </div>

                                {item.url && (
                                  <a
                                    href={item.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1.5 text-[10px] font-bold text-blue-600 hover:underline mt-3 uppercase tracking-tight"
                                  >
                                    View Source
                                    <ExternalLink className="w-2.5 h-2.5" />
                                  </a>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </TabsContent>

              <TabsContent
                value="people"
                className="flex-1 p-6 space-y-6 m-0 overflow-y-auto"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-primary/70">
                    <Users className="w-4 h-4" />
                    Identified Profiles ({company.people?.length || 0})
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4">
                  {company.people && company.people.length > 0 ? (
                    company.people.map((person) => (
                      <div
                        key={person.id}
                        className="p-5 rounded-2xl border border-muted/50 bg-muted/5 hover:bg-muted/10 transition-all group/person relative overflow-hidden"
                      >
                        <div className="absolute top-0 right-0 p-4 flex flex-col gap-1 items-end">
                          <Badge
                            variant={person.is_fit ? "default" : "secondary"}
                            className="text-[10px] font-bold"
                          >
                            {person.is_fit ? "FIT" : "REJECTED"}
                          </Badge>
                          {person.is_buy_signal && (
                            <Badge
                              variant="outline"
                              className="text-[9px] h-5 bg-violet-50 text-violet-700 border-violet-200 uppercase font-bold px-1.5 animate-pulse"
                            >
                              <Zap className="w-2.5 h-2.5 mr-1" />
                              Buy Signal
                            </Badge>
                          )}
                          {person.is_strategic_seller && (
                            <Badge
                              variant="outline"
                              className="text-[9px] h-5 bg-zinc-100 text-zinc-600 border-zinc-200 uppercase font-bold px-1.5"
                            >
                              Strategic Seller
                            </Badge>
                          )}
                          {person.intent && (
                            <Badge
                              variant="outline"
                              className="text-[9px] h-5 bg-blue-50 text-blue-700 border-blue-200 uppercase font-bold px-1.5"
                            >
                              {person.intent}
                            </Badge>
                          )}
                        </div>

                        <div className="flex items-start gap-4">
                          <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary font-bold text-lg ring-1 ring-primary/20 shrink-0">
                            {person.name?.charAt(0) || "?"}
                          </div>
                          <div className="flex-1 pr-16">
                            <h4 className="font-bold text-base group-hover/person:text-primary transition-colors mb-0.5">
                              {person.name || "Unknown"}
                            </h4>
                            <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed mb-3">
                              {person.headline || "No headline provided"}
                            </p>

                            <div className="flex items-center gap-4">
                              <a
                                href={person.linkedin_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[11px] text-[#0077b5] font-bold hover:underline flex items-center gap-1.5"
                              >
                                <Linkedin className="w-3.5 h-3.5" />
                                LinkedIn Profile
                              </a>
                              {person.email && (
                                <div className="text-[11px] text-muted-foreground flex items-center gap-1.5">
                                  <Globe className="w-3.5 h-3.5" />
                                  {person.email}
                                </div>
                              )}
                              {person.latest_report_id && onOpenReport && (
                                <button
                                  onClick={() =>
                                    onOpenReport(person.latest_report_id!)
                                  }
                                  className="text-[11px] text-primary font-bold hover:underline flex items-center gap-1.5"
                                >
                                  <FileText className="w-3.5 h-3.5" />
                                  View Report
                                </button>
                              )}
                            </div>
                          </div>
                        </div>

                        {person.fit_reasoning && (
                          <div className="mt-4 pt-4 border-t border-muted/30">
                            <p className="text-[11px] text-muted-foreground leading-relaxed italic line-clamp-2">
                              &ldquo;{person.fit_reasoning}&rdquo;
                            </p>
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="flex h-[200px] flex-col items-center justify-center text-muted-foreground border-2 border-dashed rounded-3xl opacity-60">
                      <Users className="w-8 h-8 mb-3 opacity-20" />
                      <p className="text-sm font-medium">
                        No people identified for this company yet.
                      </p>
                    </div>
                  )}
                </div>
              </TabsContent>
            </Tabs>

            {/* Footer */}
            <div className="p-4 border-t bg-muted/10 flex justify-between items-center text-[10px] text-muted-foreground font-medium uppercase tracking-tight">
              <span>ID: {company.id}</span>
              <span>
                Last Updated:{" "}
                {company.updated_at
                  ? new Date(company.updated_at).toLocaleDateString()
                  : "Recently"}
              </span>
            </div>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center p-12 text-center text-muted-foreground">
            No company details found.
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
