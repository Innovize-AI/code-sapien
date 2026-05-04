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
  ChevronDown,
  ChevronUp,
  Sliders,
  Lock,
  Unlock,
  Zap,
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
import { MultiSelect } from "@/components/ui/multi-select";
import { useConfig } from "@/context/config-context";
import {
  JOB_TITLE_OPTIONS,
  LINKEDIN_INDUSTRIES,
  COMPANY_SIZE_OPTIONS,
  APOLLO_SENIORITY_OPTIONS,
  APOLLO_EMAIL_STATUS_OPTIONS,
  APOLLO_INDUSTRIES,
} from "@/lib/constants";
import {
  discoverLeads,
  enrichLeads,
  checkExistingReports,
  discoverCompetitorLeads,
  getCompetitors,
  Competitor,
  API_URL,
  LeadDiscoveryInput,
} from "@/lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { LeadStatus } from "@/components/bulk-analysis-modal";
import { Spinner } from "@/components/ui/spinner"

const findFormSchema = z
  .object({
    industry: z.union([z.string(), z.array(z.string())]).optional(),
    job_title: z.union([z.string(), z.array(z.string())]).optional(),
    include_similar_titles: z.boolean().optional(),
    location: z.string().optional(),
    provider: z.enum(["tavily", "apollo", "competitor", "linkedin_keyword"]),
    keywords: z.string().optional(),
    person_seniorities: z.array(z.string()).optional(),
    contact_email_status: z.array(z.string()).optional(),
    organization_ids: z.string().optional(),
    organization_locations: z.string().optional(),
    company_size: z.array(z.string()).optional(),
    revenue_min: z.string().optional(),
    revenue_max: z.string().optional(),
    technologies: z.string().optional(),
    technologies_all: z.string().optional(),
    technologies_exclude: z.string().optional(),
    job_postings: z.string().optional(),
    organization_job_locations: z.string().optional(),
    organization_num_jobs_min: z.string().optional(),
    organization_num_jobs_max: z.string().optional(),
    organization_job_posted_at_min: z.string().optional(),
    organization_job_posted_at_max: z.string().optional(),
    organization_domains: z.string().optional(),
    q_keywords: z.string().optional(),
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
      const industry = Array.isArray(data.industry) ? data.industry : [data.industry];
      const jobTitle = Array.isArray(data.job_title) ? data.job_title : [data.job_title];
      
      if (!industry.length || !industry[0]?.trim()) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Industry is required",
          path: ["industry"],
        });
      }
    }
  });

type FindFormValues = {
  industry?: string | string[];
  job_title?: string | string[];
  include_similar_titles?: boolean;
  location?: string;
  provider: "tavily" | "apollo" | "competitor" | "linkedin_keyword";
  keywords?: string;
  person_seniorities?: string[];
  contact_email_status?: string[];
  organization_ids?: string;
  organization_locations?: string;
  company_size?: string[];
  revenue_min?: string;
  revenue_max?: string;
  technologies?: string;
  technologies_all?: string;
  technologies_exclude?: string;
  job_postings?: string;
  organization_job_locations?: string;
  organization_num_jobs_min?: string;
  organization_num_jobs_max?: string;
  organization_job_posted_at_min?: string;
  organization_job_posted_at_max?: string;
  organization_domains?: string;
  q_keywords?: string;
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
  const { trialMode } = useConfig();
  const [keywordInput, setKeywordInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [results, setResults] = useState<
    {
      url: string;
      website: string;
      name?: string;
      comment?: string;
      is_enriched?: boolean;
      metadata?: any;
      fit_score?: number;
      fit_reasoning?: string;
      source_post_url?: string;
    }[]
  >([]);
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
    const token = typeof window !== 'undefined' ? localStorage.getItem("accessToken") : null;
    const sseUrl = `${API_URL}/api/competitor-analysis/events/classification${token ? `?token_query=${token}` : ""}`;
    
    const eventSource = new EventSource(sseUrl);

    eventSource.onerror = (err) => {
      console.error("SSE Error in DiscoveryForm:", err);
      eventSource.close();
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "classification_update" && data.leads) {
          setResults((prevResults) => {
            // Create a map for faster lookup (using normalized URLs)
            const updatesMap = new Map<string, any>();
            data.leads.forEach((l: any) => {
              if (l.linkedin_url) updatesMap.set(normalizeUrl(l.linkedin_url), l);
              if (l.old_linkedin_url) updatesMap.set(normalizeUrl(l.old_linkedin_url), l);
            });

            return prevResults.map((lead) => {
              const leadNorm = normalizeUrl(lead.url);
              const update = updatesMap.get(leadNorm);
              if (update) {
                // If the update provides a better URL (e.g. real LI instead of apollo_id), use it
                const newUrl = (update.linkedin_url && !update.linkedin_url.startsWith('apollo_id:')) 
                  ? update.linkedin_url 
                  : lead.url;

                return {
                  ...lead,
                  url: newUrl,
                  name: lead.name || update.name,
                  metadata: {
                    ...lead.metadata,
                    is_fit: update.is_fit !== undefined ? update.is_fit : lead.metadata?.is_fit,
                    is_competitor: update.is_competitor !== undefined ? update.is_competitor : lead.metadata?.is_competitor,
                    is_decision_maker: update.is_decision_maker !== undefined ? update.is_decision_maker : lead.metadata?.is_decision_maker,
                    is_buy_signal: update.is_buy_signal !== undefined ? update.is_buy_signal : lead.metadata?.is_buy_signal,
                    is_strategic_seller: update.is_strategic_seller !== undefined ? update.is_strategic_seller : lead.metadata?.is_strategic_seller,
                    fit_reasoning: update.fit_reasoning || lead.metadata?.fit_reasoning,
                    apollo_id: update.apollo_id || lead.metadata?.apollo_id,
                    intent: update.intent || lead.metadata?.intent,
                    sentiment: update.sentiment || lead.metadata?.sentiment
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
      industry: [],
      job_title: [],
      include_similar_titles: true,
      location: "",
      provider: "tavily",
      keywords: "",
      person_seniorities: [],
      contact_email_status: [],
      organization_ids: "",
      organization_locations: "",
      company_size: [],
      revenue_min: "",
      revenue_max: "",
      technologies: "",
      technologies_all: "",
      technologies_exclude: "",
      job_postings: "",
      organization_job_locations: "",
      organization_num_jobs_min: "",
      organization_num_jobs_max: "",
      organization_job_posted_at_min: "",
      organization_job_posted_at_max: "",
      organization_domains: "",
      q_keywords: "",
    },
  });


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
          industry: Array.isArray(values.industry) ? values.industry.join(", ") : values.industry || "Keyword Search",
          job_title: Array.isArray(values.job_title) ? values.job_title.join(", ") : values.job_title || "Any",
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
        const jobTitles = Array.isArray(values.job_title) ? values.job_title : [values.job_title || ""];
        const industries = Array.isArray(values.industry) ? values.industry : [values.industry || ""];
        
        // Robust construction: only send fields the backend expects
        const payload: LeadDiscoveryInput = {
          provider: values.provider,
          location: values.location || undefined,
          job_title: values.provider === 'tavily' ? jobTitles.join(" OR ") : jobTitles[0],
          industry: values.provider === 'tavily' ? industries.join(" OR ") : industries[0],
          company_size: values.company_size
        };

        if (values.provider === 'apollo') {
          payload.person_titles = jobTitles;
          payload.industry = industries[0];
          payload.include_similar_titles = values.include_similar_titles;
          payload.person_seniorities = values.person_seniorities;
          payload.contact_email_status = values.contact_email_status;
          payload.organization_num_employees_ranges = values.company_size;
          payload.revenue_min = values.revenue_min ? parseInt(values.revenue_min) : undefined;
          payload.revenue_max = values.revenue_max ? parseInt(values.revenue_max) : undefined;

          if (values.organization_ids) {
            payload.organization_ids = values.organization_ids.split(",").map(id => id.trim()).filter(id => id);
          }
          if (values.organization_locations) {
            payload.organization_locations = values.organization_locations.split(",").map(l => l.trim()).filter(l => l);
          }
          if (values.technologies) {
            payload.currently_using_any_of_technology_uids = values.technologies.split(",").map(t => t.trim()).filter(t => t);
          }
          if (values.technologies_all) {
            payload.currently_using_all_of_technology_uids = values.technologies_all.split(",").map(t => t.trim()).filter(t => t);
          }
          if (values.technologies_exclude) {
            payload.currently_not_using_any_of_technology_uids = values.technologies_exclude.split(",").map(t => t.trim()).filter(t => t);
          }
          if (values.job_postings) {
            payload.q_organization_job_titles = values.job_postings.split(",").map(j => j.trim()).filter(j => j);
          }
          if (values.organization_job_locations) {
            payload.organization_job_locations = values.organization_job_locations.split(",").map(l => l.trim()).filter(l => l);
          }
          if (values.organization_num_jobs_min) {
            payload.organization_num_jobs_range_min = parseInt(values.organization_num_jobs_min);
          }
          if (values.organization_num_jobs_max) {
            payload.organization_num_jobs_range_max = parseInt(values.organization_num_jobs_max);
          }
          if (values.organization_job_posted_at_min) {
            payload.organization_job_posted_at_range_min = values.organization_job_posted_at_min;
          }
          if (values.organization_job_posted_at_max) {
            payload.organization_job_posted_at_range_max = values.organization_job_posted_at_max;
          }
          if (values.organization_domains) {
            payload.organization_domains = values.organization_domains.split(",").map(d => d.trim()).filter(d => d);
          }
          if (values.q_keywords) {
            payload.q_keywords = values.q_keywords;
          }
        }

        const data = await discoverLeads(payload);
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
                        <SelectItem value="tavily" disabled={trialMode}>
                          Web Search (Tavily) {trialMode && "(NOT IN TRIAL)"}
                        </SelectItem>
                        {!trialMode && (
                          <SelectItem value="apollo">
                            Apollo Database
                          </SelectItem>
                        )}
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
                          <MultiSelect
                            options={findForm.watch("provider") === "apollo" ? APOLLO_INDUSTRIES : LINKEDIN_INDUSTRIES}
                            value={Array.isArray(field.value) ? field.value : []}
                            onChange={field.onChange}
                            placeholder="Select industries..."
                            allowCustom
                          />
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
                          <MultiSelect
                            options={JOB_TITLE_OPTIONS}
                            value={Array.isArray(field.value) ? field.value : []}
                            onChange={field.onChange}
                            placeholder="Select job titles..."
                            allowCustom
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  {findForm.watch("provider") === "apollo" && (
                    <FormField
                      control={findForm.control}
                      name="include_similar_titles"
                      render={({ field }) => (
                        <FormItem className="flex items-center gap-2 -mt-1">
                          <FormControl>
                            <Checkbox
                              checked={field.value ?? true}
                              onCheckedChange={field.onChange}
                            />
                          </FormControl>
                          <FormLabel className="!mt-0 text-xs font-normal text-muted-foreground cursor-pointer">
                            Include similar / fuzzy-matched titles
                          </FormLabel>
                        </FormItem>
                      )}
                    />
                  )}
                  <FormField
                    control={findForm.control}
                    name="location"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{findForm.watch("provider") === "apollo" ? "Person Location" : "Location (Optional)"}</FormLabel>
                        <FormControl>
                          <Input placeholder="e.g. San Francisco" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Apollo Advanced Filters */}
                  {findForm.watch("provider") === "apollo" && (
                    <div className="space-y-4 pt-2 border-t mt-4">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="w-full flex items-center justify-between text-muted-foreground hover:text-primary transition-colors h-8"
                        onClick={() => setShowAdvanced(!showAdvanced)}
                      >
                        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider">
                          <Sliders className="w-3 h-3" />
                          Advanced Reach Filters
                        </div>
                        {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </Button>

                      {showAdvanced && (
                        <div className="space-y-4 animate-in fade-in slide-in-from-top-2">
                          <FormField
                            control={findForm.control}
                            name="q_keywords"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Lead Keywords / Bio</FormLabel>
                                <FormControl>
                                  <Input placeholder="e.g. AI enthusiast, Series A founder, sustainability" {...field} />
                                </FormControl>
                                <p className="text-[10px] text-muted-foreground mt-1">Search for keywords in person bio, interests, or profile.</p>
                              </FormItem>
                            )}
                          />

                          <div className="grid grid-cols-2 gap-4">
                            <FormField
                              control={findForm.control}
                              name="person_seniorities"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Seniority</FormLabel>
                                  <FormControl>
                                    <MultiSelect
                                      options={APOLLO_SENIORITY_OPTIONS}
                                      value={field.value || []}
                                      onChange={field.onChange}
                                      placeholder="Any seniority"
                                    />
                                  </FormControl>
                                </FormItem>
                              )}
                            />
                            <FormField
                              control={findForm.control}
                              name="contact_email_status"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Email Status</FormLabel>
                                  <FormControl>
                                    <MultiSelect
                                      options={APOLLO_EMAIL_STATUS_OPTIONS}
                                      value={field.value || []}
                                      onChange={field.onChange}
                                      placeholder="e.g. Verified"
                                    />
                                  </FormControl>
                                </FormItem>
                              )}
                            />
                          </div>

                          <FormField
                            control={findForm.control}
                            name="company_size"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Headcount</FormLabel>
                                <FormControl>
                                  <MultiSelect
                                    options={COMPANY_SIZE_OPTIONS}
                                    value={field.value || []}
                                    onChange={field.onChange}
                                    placeholder="Any size"
                                  />
                                </FormControl>
                              </FormItem>
                            )}
                          />

                          <div className="grid grid-cols-2 gap-4">
                            <FormField
                              control={findForm.control}
                              name="revenue_min"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Revenue Min ($)</FormLabel>
                                  <FormControl>
                                    <Input type="number" placeholder="Min" {...field} />
                                  </FormControl>
                                </FormItem>
                              )}
                            />
                            <FormField
                              control={findForm.control}
                              name="revenue_max"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Revenue Max ($)</FormLabel>
                                  <FormControl>
                                    <Input type="number" placeholder="Max" {...field} />
                                  </FormControl>
                                </FormItem>
                              )}
                            />
                          </div>

                          <FormField
                            control={findForm.control}
                            name="organization_locations"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Company HQ Location</FormLabel>
                                <FormControl>
                                  <Input placeholder="e.g. New York, United States (comma separated)" {...field} />
                                </FormControl>
                                <p className="text-[10px] text-muted-foreground mt-1">Filter by company headquarters.</p>
                              </FormItem>
                            )}
                          />

                          <FormField
                            control={findForm.control}
                            name="technologies"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Uses Any Technology</FormLabel>
                                <FormControl>
                                  <Input placeholder="e.g. salesforce, aws (comma separated)" {...field} />
                                </FormControl>
                                <p className="text-[10px] text-muted-foreground mt-1">Company uses at least one of these.</p>
                              </FormItem>
                            )}
                          />

                          <FormField
                            control={findForm.control}
                            name="technologies_all"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Uses All Technologies</FormLabel>
                                <FormControl>
                                  <Input placeholder="e.g. hubspot, stripe (comma separated)" {...field} />
                                </FormControl>
                                <p className="text-[10px] text-muted-foreground mt-1">Company must use every one of these.</p>
                              </FormItem>
                            )}
                          />

                          <FormField
                            control={findForm.control}
                            name="technologies_exclude"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Exclude Technologies</FormLabel>
                                <FormControl>
                                  <Input placeholder="e.g. competitor_tool (comma separated)" {...field} />
                                </FormControl>
                                <p className="text-[10px] text-muted-foreground mt-1">Exclude companies using any of these.</p>
                              </FormItem>
                            )}
                          />

                          <FormField
                            control={findForm.control}
                            name="job_postings"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Hiring For (Job Title Keywords)</FormLabel>
                                <FormControl>
                                  <Input placeholder="e.g. Sales, Python (comma separated)" {...field} />
                                </FormControl>
                                <p className="text-[10px] text-muted-foreground mt-1">Search active job posting titles.</p>
                              </FormItem>
                            )}
                          />

                          <FormField
                            control={findForm.control}
                            name="organization_job_locations"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Hiring In (Locations)</FormLabel>
                                <FormControl>
                                  <Input placeholder="e.g. Austin, Remote (comma separated)" {...field} />
                                </FormControl>
                                <p className="text-[10px] text-muted-foreground mt-1">Companies actively hiring in these locations.</p>
                              </FormItem>
                            )}
                          />

                          <div className="grid grid-cols-2 gap-4">
                            <FormField
                              control={findForm.control}
                              name="organization_num_jobs_min"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Active Jobs Min</FormLabel>
                                  <FormControl>
                                    <Input type="number" placeholder="Min" {...field} />
                                  </FormControl>
                                </FormItem>
                              )}
                            />
                            <FormField
                              control={findForm.control}
                              name="organization_num_jobs_max"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Active Jobs Max</FormLabel>
                                  <FormControl>
                                    <Input type="number" placeholder="Max" {...field} />
                                  </FormControl>
                                </FormItem>
                              )}
                            />
                          </div>

                          <div className="grid grid-cols-2 gap-4">
                            <FormField
                              control={findForm.control}
                              name="organization_job_posted_at_min"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Job Posted After</FormLabel>
                                  <FormControl>
                                    <Input type="date" {...field} />
                                  </FormControl>
                                </FormItem>
                              )}
                            />
                            <FormField
                              control={findForm.control}
                              name="organization_job_posted_at_max"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Job Posted Before</FormLabel>
                                  <FormControl>
                                    <Input type="date" {...field} />
                                  </FormControl>
                                </FormItem>
                              )}
                            />
                          </div>

                          <FormField
                            control={findForm.control}
                            name="organization_domains"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Target Domains</FormLabel>
                                <FormControl>
                                  <Input placeholder="google.com, apple.com" {...field} />
                                </FormControl>
                              </FormItem>
                            )}
                          />

                          <FormField
                            control={findForm.control}
                            name="organization_ids"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Apollo Company IDs</FormLabel>
                                <FormControl>
                                  <Input placeholder="5f3e4b2a..., 6a1c9d3f... (comma separated)" {...field} />
                                </FormControl>
                                <p className="text-[10px] text-muted-foreground mt-1">Target specific companies by their Apollo ID.</p>
                              </FormItem>
                            )}
                          />
                        </div>
                      )}
                    </div>
                  )}
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
                {isLoading && <Spinner size="md" className="mr-2" />}
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
              <span className="text-sm text-muted-foreground">
                {results.length} found
              </span>
            )}
          </div>
        </div>
        {results.length > 0 ? (
          <div className="grid gap-3">
            {results.map((lead, i) => {
              const leadNorm = normalizeUrl(lead.url);
              const status = leadsStatus?.find(
                (s) => normalizeUrl(s.url) === leadNorm,
              )?.status;
              return (
                <Card
                  key={i}
                  className={`overflow-hidden transition-colors ${status === "completed" ? "border-green-500/50 bg-green-50/10" : "hover:border-primary/50"}`}
                >
                  <CardContent className="p-4 flex items-start gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          {lead.is_enriched === false ? (
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                              <Lock className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                              <span className="text-sm font-medium text-muted-foreground truncate italic">
                                {lead.name || "Unenriched Lead"}
                              </span>
                            </div>
                          ) : (
                            <a
                              href={lead.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-medium truncate text-sm hover:underline hover:text-primary transition-colors"
                            >
                              {lead.name || lead.url}
                            </a>
                          )}
                          <div className="flex flex-wrap gap-1.5 ml-2">
                            {status === "analyzing" && (
                              <Badge
                                variant="secondary"
                                className="text-[9px] h-4 px-1 bg-blue-100 text-blue-700 animate-pulse border-blue-200"
                              >
                                <Spinner size="xs" className="mr-1" />
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
                              !lead.metadata?.is_buy_signal &&
                              !lead.metadata?.is_strategic_seller &&
                              !lead.metadata?.intent &&
                              !lead.metadata?.sentiment &&
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
                            {lead.metadata?.is_buy_signal && (
                              <Badge
                                variant="outline"
                                className="text-[9px] h-4 px-1 bg-violet-50 text-violet-700 border-violet-200"
                              >
                                Buy Signal
                              </Badge>
                            )}
                            {lead.metadata?.is_strategic_seller && (
                              <Badge
                                variant="outline"
                                className="text-[9px] h-4 px-1 bg-zinc-50 text-zinc-700 border-zinc-200"
                              >
                                Strategic Seller
                              </Badge>
                            )}
                            {lead.metadata?.competitor && (
                              <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded-full text-muted-foreground shrink-0 border border-muted-foreground/10">
                                vs {lead.metadata.competitor}
                              </span>
                            )}
                          </div>
                        </div>

                      </div>

                      <div className="text-xs font-semibold text-primary truncate mt-0.5">
                        {lead.comment}
                      </div>

                      <div className="text-[10px] text-muted-foreground truncate mt-0.5 flex items-center gap-2">
                        <span>{lead.website}</span>
                        {lead.metadata?.email_status && (
                          <Badge 
                            variant="outline" 
                            className={`text-[8px] h-3.5 px-1 py-0 uppercase tracking-tighter font-bold ${
                              lead.metadata.email_status === 'verified' ? 'bg-green-50 text-green-700 border-green-200' : 
                              lead.metadata.email_status === 'extrapolated' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                              'bg-gray-50 text-gray-500 border-gray-200'
                            }`}
                          >
                            {lead.metadata.email_status}
                          </Badge>
                        )}
                        {lead.metadata?.seniority && (
                          <span className="text-[9px] text-muted-foreground bg-muted/30 px-1 rounded border border-muted/50">
                            {lead.metadata.seniority}
                          </span>
                        )}
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
                  </CardContent>
                </Card>
              );
            })}
          </div>
        ) : (
          <div className="h-64 border-2 border-dashed rounded-lg flex items-center justify-center text-muted-foreground p-8 text-center bg-muted/20">
            {isLoading ? (
              <div className="flex flex-col items-center gap-2">
                <Spinner size="lg" />
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
