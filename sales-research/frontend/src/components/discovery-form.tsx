"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import * as z from "zod";
import {
  Loader2,
  Search,
  CheckSquare,
  Square,
  ExternalLink,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { normalizeUrl } from "@/lib/utils";
import {
  discoverLeads,
  checkExistingReports,
  discoverCompetitorLeads,
  getCompetitors,
  Competitor,
  API_URL,
} from "@/lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { LeadStatus } from "@/components/bulk-analysis-modal";

const findFormSchema = z
  .object({
    industry: z.string().optional(),
    job_title: z.string().optional(),
    location: z.string().optional(),
    provider: z.enum(["tavily", "apollo", "competitor", "linkedin_keyword"]),
    keywords: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.provider === "linkedin_keyword") {
      if (!data.keywords || data.keywords.trim().length < 3) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Keywords are required (comma separated)",
          path: ["keywords"],
        });
      }
    } else if (data.provider !== "competitor") {
      if (!data.industry || data.industry.trim().length < 2) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Industry is required",
          path: ["industry"],
        });
      }
      if (!data.job_title || data.job_title.trim().length < 2) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Job title is required",
          path: ["job_title"],
        });
      }
    }
  });

type FindFormValues = {
  industry?: string;
  job_title?: string;
  location?: string;
  provider: "tavily" | "apollo" | "competitor" | "linkedin_keyword";
  keywords?: string;
};

export function DiscoveryForm({
  onSelect,
  onBulkSelect,
  leadsStatus = [],
}: {
  onSelect?: (lead: { url: string; website: string; result?: any }) => void;
  onBulkSelect?: (
    leads: { url: string; website: string }[],
    options?: { refresh: boolean },
  ) => void;
  leadsStatus?: LeadStatus[];
}) {
  const [keywordInput, setKeywordInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<
    {
      url: string;
      website: string;
      name?: string;
      comment?: string;
      metadata?: any;
      fit_score?: number;
      fit_reasoning?: string;
      source_post_url?: string;
    }[]
  >([]);
  const [selectedUrls, setSelectedUrls] = useState<string[]>([]);
  const [refreshAll, setRefreshAll] = useState(false);
  const [existingReports, setExistingReports] = useState<Record<string, any>>(
    {},
  );
  const [error, setError] = useState<string | null>(null);
  const [allCompetitors, setAllCompetitors] = useState<Competitor[]>([]);
  const [selectedCompetitorUrls, setSelectedCompetitorUrls] = useState<
    string[]
  >([]);
  // SSE Listener for Real-Time Updates
  useEffect(() => {
    const eventSource = new EventSource(
      `${API_URL}/api/competitor-analysis/events/classification`,
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "classification_update" && data.leads) {
          setResults((prevResults) => {
            // Create a map for faster lookup
            const updatesMap = new Map<string, any>(
              data.leads.map((l: any) => [l.linkedin_url, l]),
            );

            return prevResults.map((lead) => {
              const update = updatesMap.get(lead.url);
              if (update) {
                return {
                  ...lead,
                  metadata: {
                    ...lead.metadata,
                    is_fit: update.is_fit,
                    is_competitor: update.is_competitor,
                    is_decision_maker: update.is_decision_maker,
                    fit_reasoning: update.fit_reasoning,
                  },
                };
              }
              return lead;
            });
          });
        }
      } catch (error) {
        console.error("Error parsing SSE event:", error);
      }
    };

    return () => {
      eventSource.close();
    };
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getCompetitors();
        setAllCompetitors(data);
        setSelectedCompetitorUrls(data.map((c) => c.linkedin_url));
      } catch (e) {
        console.error("Failed to load competitors", e);
      }
    };
    load();
  }, []);

  const findForm = useForm<FindFormValues>({
    resolver: zodResolver(findFormSchema),
    defaultValues: {
      industry: "",
      job_title: "",
      location: "",
      provider: "tavily",
      keywords: "",
    },
  });

  const toggleUrl = (url: string) => {
    setSelectedUrls((prev) =>
      prev.includes(url) ? prev.filter((u) => u !== url) : [...prev, url],
    );
  };

  const selectAll = () => {
    if (selectedUrls.length === results.length && results.length > 0) {
      setSelectedUrls([]);
    } else {
      setSelectedUrls(results.map((r) => r.url));
    }
  };

  // Keyword logic
  const handleAddKeyword = (currentDetails: string | undefined) => {
    if (!keywordInput.trim()) return;
    const details = currentDetails || "";
    const current = details.split(",").filter((k) => k.trim());
    if (!current.includes(keywordInput.trim())) {
      const newVal = [...current, keywordInput.trim()].join(",");
      findForm.setValue("keywords", newVal);
    }
    setKeywordInput("");
  };

  const handleRemoveKeyword = (
    target: string,
    currentDetails: string | undefined,
  ) => {
    const details = currentDetails || "";
    const current = details.split(",").filter((k) => k.trim());
    const newVal = current.filter((k) => k !== target).join(",");
    findForm.setValue("keywords", newVal);
  };

  const handleKeywordKeyDown = (
    e: React.KeyboardEvent,
    currentDetails: string | undefined,
  ) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddKeyword(currentDetails);
    } else if (e.key === "Backspace" && !keywordInput && currentDetails) {
      const current = currentDetails.split(",").filter((k) => k.trim());
      if (current.length > 0) {
        handleRemoveKeyword(current[current.length - 1], currentDetails);
      }
    }
  };

  async function onFindSubmit(values: FindFormValues) {
    setIsLoading(true);
    setError(null);
    setResults([]);
    setSelectedUrls([]);
    setExistingReports({}); // Clear existing reports on new search
    try {
      if (values.provider === "competitor") {
        const data = await discoverCompetitorLeads(selectedCompetitorUrls);
        if (data.leads) {
          const mappedLeads = data.leads
            .map((l: any) => ({
              name: l.name,
              url: l.linkedin_url || "", // Ensure url is always a string
              website: "", // Keep website for consistency with other lead types
              comment: l.comment_text,
              source_post_url: l.source_post_url,
              fit_score: l.fit_score, // Keep fit_score at top level if needed for display
              metadata: {
                competitor: l.competitor,
                source_post: l.source_post,
                headline: l.headline,
                is_fit: l.is_fit,
                is_competitor: l.is_competitor,
                is_decision_maker: l.is_decision_maker,
                fit_reasoning: l.fit_reasoning, // Move fit_reasoning to metadata
              },
            }))
            .filter((l) => !!l.url);
          setResults(mappedLeads);

          // Check for existing reports
          const checkLeads = mappedLeads.map((l) => ({
            linkedin_url: normalizeUrl(l.url),
            website: l.website,
          }));
          const existing = await checkExistingReports(checkLeads);
          setExistingReports(existing);

          if (mappedLeads.length === 0) {
            setError(
              (data as any).message || "No leads found from competitors.",
            );
          }
        }
      } else if (values.provider === "linkedin_keyword") {
        // Pass dummy values for required fields
        const payload = {
          industry: values.industry || "Keyword Search",
          job_title: values.job_title || "Any",
          location: values.location,
          provider: values.provider,
          keywords: values.keywords
            ? values.keywords
                .split(",")
                .map((k) => k.trim())
                .filter((k) => k)
            : [],
        };
        const data = await discoverLeads(payload as any);

        if (data.leads) {
          const mappedLeads = data.leads.map((l: any) => ({
            name: l.name,
            url: l.linkedin_url || l.url,
            website: l.website || "",
            comment: l.comment,
            source_post_url: l.source_post_url,
            metadata: {
              headline: l.headline,
              is_fit: l.is_fit,
              is_competitor: l.is_competitor,
              is_decision_maker: l.is_decision_maker,
              fit_reasoning: l.fit_reasoning,
              competitor: l.competitor,
              source_post: l.source_post,
            },
          }));
          setResults(mappedLeads);
          const checkLeads = mappedLeads.map(
            (l: { url: string; website: string }) => ({
              linkedin_url: normalizeUrl(l.url),
              website: l.website,
            }),
          );
          const existing = await checkExistingReports(checkLeads);
          setExistingReports(existing);

          if (data.leads.length === 0) {
            setError("No leads found matching keywords.");
          }
        } else if (data.error) {
          setError(data.error);
        }
      } else {
        const data = await discoverLeads(values as any);
        if (data.leads) {
          setResults(data.leads);
          const checkLeads = data.leads.map(
            (l: { url: string; website: string }) => ({
              linkedin_url: normalizeUrl(l.url),
              website: l.website,
            }),
          );
          const existing = await checkExistingReports(checkLeads);
          setExistingReports(existing);

          if (data.leads.length === 0) {
            setError("No leads found matching criteria.");
          }
        } else if (data.error) {
          setError(data.error);
        }
      }
    } catch (e) {
      setError("Failed to fetch leads.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card className="h-fit">
        <CardHeader>
          <CardTitle>Search Criteria</CardTitle>
          <CardDescription>
            Define your target audience to find new leads.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...findForm}>
            <form
              onSubmit={findForm.handleSubmit(onFindSubmit)}
              className="space-y-4"
            >
              {/* 1. Provider Selection (Top) */}
              <FormField
                control={findForm.control}
                name="provider"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Source Provider</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      defaultValue={field.value}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select provider" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="tavily">
                          Web Search (Tavily)
                        </SelectItem>
                        <SelectItem value="apollo">Apollo Database</SelectItem>
                        <SelectItem value="linkedin_keyword">
                          LinkedIn Keywords
                        </SelectItem>
                        <SelectItem value="competitor">
                          Competitor Comments
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* 2. Conditional Inputs */}
              {(findForm.watch("provider") === "tavily" ||
                findForm.watch("provider") === "apollo") && (
                <>
                  <FormField
                    control={findForm.control}
                    name="industry"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Industry</FormLabel>
                        <FormControl>
                          <Input placeholder="e.g. FinTech" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={findForm.control}
                    name="job_title"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Job Title</FormLabel>
                        <FormControl>
                          <Input placeholder="e.g. CTO" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={findForm.control}
                    name="location"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Location (Optional)</FormLabel>
                        <FormControl>
                          <Input placeholder="e.g. San Francisco" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </>
              )}

              {findForm.watch("provider") === "linkedin_keyword" && (
                <FormField
                  control={findForm.control}
                  name="keywords"
                  render={({ field }) => {
                    const strings = field.value
                      ? field.value.split(",").filter((k: string) => k.trim())
                      : [];
                    return (
                      <FormItem>
                        <FormLabel>Keywords</FormLabel>
                        <div className="space-y-2">
                          <div className="flex flex-wrap gap-2 p-2 border rounded-md bg-white focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
                            {strings.map((k: string, i: number) => (
                              <Badge
                                key={i}
                                variant="secondary"
                                className="gap-1 pr-1 flex items-center"
                              >
                                {k}
                                <button
                                  type="button"
                                  onClick={() =>
                                    handleRemoveKeyword(k, field.value || "")
                                  }
                                  className="hover:bg-muted rounded-full p-0.5"
                                >
                                  <span className="sr-only">Remove</span>
                                  <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    width="12"
                                    height="12"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    className="w-3 h-3"
                                  >
                                    <path d="M18 6 6 18" />
                                    <path d="m6 6 12 12" />
                                  </svg>
                                </button>
                              </Badge>
                            ))}
                            <input
                              className="flex-1 outline-none bg-transparent text-sm min-w-[200px]"
                              placeholder={
                                strings.length === 0
                                  ? "Type keyword and press Enter..."
                                  : ""
                              }
                              value={keywordInput}
                              onChange={(e) => setKeywordInput(e.target.value)}
                              onKeyDown={(e) =>
                                handleKeywordKeyDown(e, field.value || "")
                              }
                              onBlur={() => handleAddKeyword(field.value || "")}
                            />
                          </div>
                          <p className="text-[10px] text-muted-foreground">
                            Press Enter to add multiple keywords.
                          </p>
                        </div>
                        <FormMessage />
                      </FormItem>
                    );
                  }}
                />
              )}

              {findForm.watch("provider") === "competitor" && (
                <div className="space-y-2 mt-4 p-4 bg-muted/30 rounded-lg border border-dashed">
                  <FormLabel className="flex justify-between items-center">
                    Monitor Competitors
                    <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                      {selectedCompetitorUrls.length} Selected
                    </span>
                  </FormLabel>
                  <div className="grid gap-2 max-h-40 overflow-y-auto pr-2 custom-scrollbar">
                    {allCompetitors.length === 0 ? (
                      <p className="text-xs text-muted-foreground py-2 italic text-center">
                        No competitors configured. Add some in Settings.
                      </p>
                    ) : (
                      allCompetitors.map((c) => (
                        <div
                          key={c.id}
                          className="flex items-center gap-2 group"
                        >
                          <Checkbox
                            id={`comp-${c.id}`}
                            checked={selectedCompetitorUrls.includes(
                              c.linkedin_url,
                            )}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                setSelectedCompetitorUrls((prev) => [
                                  ...prev,
                                  c.linkedin_url,
                                ]);
                              } else {
                                setSelectedCompetitorUrls((prev) =>
                                  prev.filter((u) => u !== c.linkedin_url),
                                );
                              }
                            }}
                          />
                          <label
                            htmlFor={`comp-${c.id}`}
                            className="text-xs truncate cursor-pointer select-none group-hover:text-primary transition-colors flex-1"
                          >
                            {c.name ||
                              c.linkedin_url
                                .split("/in/")[1]
                                ?.replace("/", "") ||
                              c.linkedin_url}
                          </label>
                        </div>
                      ))
                    )}
                  </div>
                  {allCompetitors.length > 0 && (
                    <div className="flex justify-end pt-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        type="button"
                        className="h-6 text-[10px] px-2"
                        onClick={() => {
                          if (
                            selectedCompetitorUrls.length ===
                            allCompetitors.length
                          ) {
                            setSelectedCompetitorUrls([]);
                          } else {
                            setSelectedCompetitorUrls(
                              allCompetitors.map((c) => c.linkedin_url),
                            );
                          }
                        }}
                      >
                        {selectedCompetitorUrls.length === allCompetitors.length
                          ? "Deselect All"
                          : "Select All"}
                      </Button>
                    </div>
                  )}
                </div>
              )}

              <Button
                type="submit"
                disabled={
                  isLoading ||
                  (findForm.watch("provider") === "competitor" &&
                    selectedCompetitorUrls.length === 0)
                }
                className="w-full"
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Find Leads
              </Button>
            </form>
          </Form>
          {error && <div className="text-red-500 text-sm mt-4">{error}</div>}
        </CardContent>
      </Card>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h3 className="text-lg font-medium">Results</h3>
            {results.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={selectAll}
                className="h-8 gap-2"
              >
                {selectedUrls.length === results.length ? (
                  <CheckSquare className="w-4 h-4" />
                ) : (
                  <Square className="w-4 h-4" />
                )}
                <span className="text-xs uppercase tracking-wider font-semibold">
                  Select All
                </span>
              </Button>
            )}
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">
              {results.length} found
            </span>
            {selectedUrls.length > 0 && (
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-2 px-3 py-1 bg-muted rounded-full border mr-2">
                  <Checkbox
                    id="refresh-all"
                    checked={refreshAll}
                    onCheckedChange={(checked) => setRefreshAll(!!checked)}
                  />
                  <label
                    htmlFor="refresh-all"
                    className="text-[10px] font-medium cursor-pointer"
                  >
                    Re-run All
                  </label>
                </div>
                <Button
                  size="sm"
                  onClick={() => {
                    if (onBulkSelect) {
                      const selectedLeads = results.filter((r) =>
                        selectedUrls.includes(r.url),
                      );
                      onBulkSelect(selectedLeads, { refresh: refreshAll });
                      setSelectedUrls([]); // Clear selection to allow new additions immediately
                      setRefreshAll(false);
                    }
                  }}
                >
                  Analyze Selected ({selectedUrls.length})
                </Button>
              </div>
            )}
          </div>
        </div>
        {results.length > 0 ? (
          <div className="grid gap-3">
            {results.map((lead, i) => {
              const status = leadsStatus?.find(
                (s) => s.url === lead.url,
              )?.status;
              return (
                <Card
                  key={i}
                  className={`overflow-hidden transition-colors ${status === "completed" ? "border-green-500/50 bg-green-50/10" : "hover:border-primary/50"}`}
                >
                  <CardContent className="p-4 flex items-start gap-4">
                    <Checkbox
                      checked={selectedUrls.includes(lead.url)}
                      onCheckedChange={() => toggleUrl(lead.url)}
                      className="mt-1"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <a
                            href={lead.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-medium truncate text-sm hover:underline hover:text-primary transition-colors"
                          >
                            {lead.name || lead.url}
                          </a>
                          <div className="flex flex-wrap gap-1.5 ml-2">
                            {status === "analyzing" && (
                              <Badge
                                variant="secondary"
                                className="text-[9px] h-4 px-1 bg-blue-100 text-blue-700 animate-pulse border-blue-200"
                              >
                                <Loader2 className="w-2 h-2 mr-1 animate-spin" />
                                Researching...
                              </Badge>
                            )}
                            {status === "pending" && (
                              <Badge
                                variant="secondary"
                                className="text-[9px] h-4 px-1 bg-gray-100 text-gray-500 border-gray-200"
                              >
                                Queued
                              </Badge>
                            )}
                            {!lead.metadata?.fit_reasoning &&
                              !lead.metadata?.is_fit &&
                              !lead.metadata?.is_competitor &&
                              status !== "analyzing" &&
                              status !== "pending" && (
                                <Badge
                                  variant="secondary"
                                  className="text-[9px] h-4 px-1 bg-gray-100 text-gray-500 animate-pulse"
                                >
                                  AI Analyzing...
                                </Badge>
                              )}
                            {lead.metadata?.is_competitor && (
                              <Badge
                                variant="destructive"
                                className="text-[9px] h-4 px-1"
                              >
                                Competitor
                              </Badge>
                            )}
                            {lead.metadata?.is_fit && (
                              <Badge
                                variant="outline"
                                className="text-[9px] h-4 px-1 bg-green-50 text-green-700 border-green-200"
                                title={lead.metadata?.fit_reasoning}
                              >
                                Fit
                              </Badge>
                            )}
                            {lead.metadata?.is_decision_maker && (
                              <Badge
                                variant="outline"
                                className="text-[9px] h-4 px-1 bg-blue-50 text-blue-700 border-blue-200"
                              >
                                Decision Maker
                              </Badge>
                            )}
                            {lead.metadata?.competitor && (
                              <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded-full text-muted-foreground shrink-0 border border-muted-foreground/10">
                                vs {lead.metadata.competitor}
                              </span>
                            )}
                          </div>
                        </div>

                        {status === "completed" && onSelect && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 text-xs px-2 ml-2 hover:bg-primary/5 hover:text-primary transition-colors shrink-0"
                            onClick={() => {
                              const leadResult = leadsStatus?.find(
                                (s) => s.url === lead.url,
                              );
                              if (leadResult && leadResult.result) {
                                onSelect({
                                  ...lead,
                                  result: leadResult.result,
                                });
                              }
                            }}
                          >
                            <ExternalLink className="w-3 h-3 mr-1.5" />
                            View Report
                          </Button>
                        )}
                      </div>

                      <div className="text-xs text-muted-foreground truncate mt-0.5">
                        {lead.website}
                      </div>

                      {lead.metadata?.fit_reasoning && (
                        <div className="mt-2 text-[10px] text-muted-foreground bg-muted/40 p-2 rounded border border-muted/50 italic leading-relaxed">
                          <span className="font-semibold not-italic text-primary/70 mr-1">
                            AI Reasoning:
                          </span>
                          {lead.metadata.fit_reasoning}
                        </div>
                      )}

                      {lead.comment ? (
                        <div className="space-y-2 mt-1">
                          <p className="text-[10px] text-muted-foreground italic line-clamp-4 opacity-70 whitespace-pre-line">
                            "{lead.comment}"
                          </p>
                          {lead.source_post_url &&
                            lead.metadata?.source_post && (
                              <div className="flex flex-col gap-1.5 mt-2 pt-2 border-t border-muted/50">
                                <p className="text-[9px] uppercase tracking-wider font-semibold text-muted-foreground/70">
                                  Source Posts:
                                </p>
                                {(lead.metadata.source_post as string)
                                  .split(" | ")
                                  .map((text, idx) => {
                                    const urls = (
                                      lead.source_post_url as string
                                    ).split(",");
                                    const url = urls[idx] || urls[0];
                                    return (
                                      <a
                                        key={idx}
                                        href={url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-[10px] text-muted-foreground hover:text-blue-600 hover:underline flex items-start gap-1 group/post"
                                      >
                                        <ExternalLink className="w-2.5 h-2.5 mt-0.5 shrink-0 opacity-40 group-hover/post:opacity-100" />
                                        <span className="line-clamp-1 italic">
                                          "{text}"
                                        </span>
                                      </a>
                                    );
                                  })}
                              </div>
                            )}
                        </div>
                      ) : (
                        lead.website && (
                          <a
                            href={
                              lead.website.startsWith("http")
                                ? lead.website
                                : `https://${lead.website}`
                            }
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[10px] text-muted-foreground hover:underline truncate opacity-70 block mt-0.5"
                          >
                            {lead.website}
                          </a>
                        )
                      )}
                      {lead.fit_reasoning && (
                        <p className="text-[10px] text-primary/80 mt-1 line-clamp-1 group-hover:line-clamp-none transition-all">
                          <strong>AI Insight:</strong> {lead.fit_reasoning}
                        </p>
                      )}
                    </div>

                    <div className="flex flex-col items-end gap-2 shrink-0">
                      {lead.fit_score !== undefined && (
                        <div
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                            lead.fit_score >= 8
                              ? "bg-green-100 text-green-700 border-green-200"
                              : lead.fit_score >= 5
                                ? "bg-yellow-100 text-yellow-700 border-yellow-200"
                                : "bg-red-100 text-red-700 border-red-200"
                          }`}
                        >
                          Fit: {lead.fit_score}/10
                        </div>
                      )}

                      {status === "analyzing" ? (
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Analyzing
                        </div>
                      ) : status === "completed" ||
                        existingReports[normalizeUrl(lead.url)] ? (
                        (() => {
                          const existingData =
                            existingReports[normalizeUrl(lead.url)]?.data;
                          const sessionResult = leadsStatus?.find(
                            (s) => s.url === lead.url,
                          )?.result;
                          const finalResult = sessionResult || existingData;

                          return (
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-8 border-green-200 hover:bg-green-100 bg-green-50/50 text-green-700 font-bold gap-2"
                              onClick={() =>
                                onSelect &&
                                onSelect({ ...lead, result: finalResult })
                              }
                            >
                              View Report
                            </Button>
                          );
                        })()
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onSelect && onSelect(lead)}
                        >
                          Analyze
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        ) : (
          <div className="h-64 border-2 border-dashed rounded-lg flex items-center justify-center text-muted-foreground p-8 text-center bg-muted/20">
            {isLoading ? (
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p>Searching for leads...</p>
              </div>
            ) : (
              <div className="space-y-2">
                <Search className="w-8 h-8 mx-auto opacity-20" />
                <p>Enter search criteria to find matching LinkedIn profiles.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
