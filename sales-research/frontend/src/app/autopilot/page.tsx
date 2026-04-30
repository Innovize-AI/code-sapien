"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/auth-context";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Zap,
  Search,
  Plus,
  X,
  List,
  Globe,
  Users,
  Briefcase,
  Activity,
  RefreshCcw,
  Trash2,
  User,
  Lock,
} from "lucide-react";
import {
  fetchActivities,
  getCompetitors,
  addCompetitor,
  deleteCompetitor,
  Competitor,
  AutopilotRule,
  getAutopilotRules,
  addAutopilotRule,
  deleteAutopilotRule,
} from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { MultiSelect } from "@/components/ui/multi-select";
import {
  JOB_TITLE_OPTIONS,
  COMPANY_SIZE_OPTIONS,
  APOLLO_SENIORITY_OPTIONS,
  APOLLO_EMAIL_STATUS_OPTIONS,
  LINKEDIN_INDUSTRIES
} from "@/lib/constants";

import { useConfig } from "@/context/config-context";

export default function AutopilotPage() {
  const { user } = useAuth();
  const { trialMode } = useConfig();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [keywordRules, setKeywordRules] = useState<AutopilotRule[]>([]);
  const [newKeyword, setNewKeyword] = useState("");
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [newCompetitorUrl, setNewCompetitorUrl] = useState("");
  const [apolloRules, setApolloRules] = useState<AutopilotRule[]>([]);
  const [apolloInput, setApolloInput] = useState({
    industry: "",
    job_title: [] as string[],
    location: "",
    company_size: [] as string[],
    // Advanced Filters
    person_seniorities: [] as string[],
    contact_email_status: [] as string[],
    organization_domains: "",
    organization_locations: "",
    revenue_min: "",
    revenue_max: "",
    technologies: "",
    job_postings: ""
  });
  const [lastRuns, setLastRuns] = useState<any[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [rules, comps, activities] = await Promise.all([
        getAutopilotRules(),
        getCompetitors(),
        fetchActivities(10),
      ]);

      if (rules) {
        setKeywordRules(rules.filter((r) => r.type === "keyword"));
        setApolloRules(rules.filter((r) => r.type === "apollo_config"));
      }

      if (comps) {
        setCompetitors(comps);
      }

      if (activities) {
        const discoveryActivities = activities.filter(
          (a) =>
            a.type === "comment" ||
            a.title.includes("Autopilot") ||
            a.title.includes("Discovery"),
        );
        setLastRuns(discoveryActivities);
      }
    } catch (error) {
      console.error("Failed to load Autopilot data:", error);
      toast({
        title: "Error",
        description: "Failed to load autopilot settings.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleAddCompetitor = async () => {
    if (!newCompetitorUrl) return;
    if (competitors.length >= 3) {
      toast({
        title: "Limit Reached",
        description:
          "Maximum of 3 competitors allowed. Please remove one first.",
        variant: "destructive",
      });
      return;
    }
    try {
      await addCompetitor({ linkedin_url: newCompetitorUrl });
      const comps = await getCompetitors();
      setCompetitors(comps);
      setNewCompetitorUrl("");
      toast({
        title: "Success",
        description: "Competitor added for monitoring.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to add competitor.",
        variant: "destructive",
      });
    }
  };

  const handleRemoveCompetitor = async (id: string) => {
    try {
      await deleteCompetitor(id);
      setCompetitors(competitors.filter((c) => c.id !== id));
      toast({
        title: "Removed",
        description: "Competitor monitoring disabled.",
      });
    } catch (error: any) {
      if (error.response?.status === 403) {
        toast({
          title: "Denied",
          description: "Only admins or creators can remove competitors.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Error",
          description: "Failed to remove competitor.",
          variant: "destructive",
        });
      }
    }
  };

  const handleAddKeyword = async () => {
    if (!newKeyword) return;
    if (keywordRules.length >= 5) {
      toast({
        title: "Limit Reached",
        description: "Maximum of 5 keywords allowed. Please remove one first.",
        variant: "destructive",
      });
      return;
    }
    try {
      await addAutopilotRule({ type: "keyword", value: newKeyword });
      setNewKeyword("");
      const rules = await getAutopilotRules("keyword");
      setKeywordRules(rules);
      toast({ title: "Success", description: "Keyword added for monitoring." });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to add keyword.",
        variant: "destructive",
      });
    }
  };

  const handleRemoveKeyword = async (id: string) => {
    try {
      await deleteAutopilotRule(id);
      setKeywordRules(keywordRules.filter((r) => r.id !== id));
      toast({ title: "Removed", description: "Keyword rule disabled." });
    } catch (error: any) {
      if (error.response?.status === 403) {
        toast({
          title: "Denied",
          description: "Only admins or creators can remove keywords.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Error",
          description: "Failed to remove keyword.",
          variant: "destructive",
        });
      }
    }
  };

  const handleAddApolloRule = async () => {
    if (!apolloInput.job_title.length && !apolloInput.industry) {
      toast({
        title: "Missing Info",
        description: "Please enter at least Job Titles or Industry.",
        variant: "destructive",
      });
      return;
    }
    setSaving(true);
    try {
      // Format payload for backend ingestion
      const payload = {
        industry: apolloInput.industry,
        person_titles: apolloInput.job_title, // backend expects person_titles as list
        location: apolloInput.location,
        organization_num_employees_ranges: apolloInput.company_size,
        person_seniorities: apolloInput.person_seniorities,
        contact_email_status: apolloInput.contact_email_status,
        organization_domains: apolloInput.organization_domains ? apolloInput.organization_domains.split(",").map(d => d.trim()) : undefined,
        organization_locations: apolloInput.organization_locations ? apolloInput.organization_locations.split(",").map(l => l.trim()) : undefined,
        revenue_min: apolloInput.revenue_min ? parseInt(apolloInput.revenue_min) : undefined,
        revenue_max: apolloInput.revenue_max ? parseInt(apolloInput.revenue_max) : undefined,
        currently_using_any_of_technology_uids: apolloInput.technologies ? apolloInput.technologies.split(",").map(t => t.trim()) : undefined,
        q_organization_job_titles: apolloInput.job_postings ? apolloInput.job_postings.split(",").map(t => t.trim()) : undefined,
      };

      await addAutopilotRule({
        type: "apollo_config",
        value: JSON.stringify(payload),
      });

      setApolloInput({
        industry: "",
        job_title: [],
        location: "",
        company_size: [],
        person_seniorities: [],
        contact_email_status: [],
        organization_domains: "",
        organization_locations: "",
        revenue_min: "",
        revenue_max: "",
        technologies: "",
        job_postings: ""
      });
      const rules = await getAutopilotRules("apollo_config");
      setApolloRules(rules);
      toast({ title: "Success", description: "Apollo discovery rule created." });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to add Apollo rule.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveApolloRule = async (id: string) => {
    try {
      await deleteAutopilotRule(id);
      setApolloRules(apolloRules.filter((r) => r.id !== id));
      toast({ title: "Removed", description: "Apollo rule disabled." });
    } catch (error: any) {
      if (error.response?.status === 403) {
        toast({
          title: "Denied",
          description: "Only admins or creators can remove Apollo rules.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Error",
          description: "Failed to remove Apollo rule.",
          variant: "destructive",
        });
      }
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-[50vh]">
          <RefreshCcw className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
              <Zap className="w-8 h-8 text-primary fill-primary/20" />
              Lead Discovery Autopilot
            </h1>
            <p className="text-muted-foreground mt-2">
              Set up automated rules to find high-intent leads from LinkedIn and Apollo every 24 hours.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="md:col-span-2 space-y-6">
            <Tabs defaultValue={trialMode ? "linkedin" : "apollo"} className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="apollo" className="gap-2 relative">
                  <Search className="w-4 h-4" />
                  Apollo Search
                  {trialMode && (
                    <Badge variant="secondary" className="text-[8px] h-3 px-1 absolute -top-1 -right-1 bg-amber-500 text-white border-none">
                      NOT IN TRIAL
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="linkedin" className="gap-2">
                  <Globe className="w-4 h-4" />
                  LinkedIn Keywords
                </TabsTrigger>
                <TabsTrigger value="competitors" className="gap-2">
                  <Users className="w-4 h-4" />
                  Competitors
                </TabsTrigger>
              </TabsList>

              <TabsContent value="apollo" className="mt-6">
                {trialMode ? (
                  <Card className="border-amber-500/20 bg-amber-500/5 backdrop-blur-sm">
                    <CardHeader className="text-center">
                      <div className="mx-auto w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center mb-4">
                        <Lock className="w-6 h-6 text-amber-600" />
                      </div>
                      <CardTitle>Apollo Discovery is Locked</CardTitle>
                      <CardDescription>
                        Apollo Search is not available in the trial version. Contact support to enable premium discovery features.
                      </CardDescription>
                    </CardHeader>
                    <CardFooter className="justify-center pb-8">
                      <Button variant="outline" className="border-amber-500/50 text-amber-700 hover:bg-amber-500/10">
                        Contact Support to Enable
                      </Button>
                    </CardFooter>
                  </Card>
                ) : (
                  <Card className="border-primary/10 shadow-lg bg-card/50 backdrop-blur-sm">
                    <CardHeader>
                      <CardTitle>Apollo Search Configuration</CardTitle>
                      <CardDescription>
                        Configure advanced Apollo filters. We'll find matching profiles and add them to your pipeline automatically.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Person Filters */}
                      <div className="space-y-4">
                        <div className="space-y-2">
                          <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Person Filters</Label>
                          <div className="space-y-2">
                            <Label>Job Titles</Label>
                            <MultiSelect
                              options={JOB_TITLE_OPTIONS}
                              onChange={(vals) => setApolloInput(prev => ({ ...prev, job_title: vals }))}
                              value={apolloInput.job_title}
                              placeholder="Any job title"
                              className="w-full"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Seniority</Label>
                            <MultiSelect
                              options={APOLLO_SENIORITY_OPTIONS}
                              onChange={(vals) => setApolloInput(prev => ({ ...prev, person_seniorities: vals }))}
                              value={apolloInput.person_seniorities}
                              placeholder="Any seniority"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Email Status</Label>
                            <MultiSelect
                              options={APOLLO_EMAIL_STATUS_OPTIONS}
                              onChange={(vals) => setApolloInput(prev => ({ ...prev, contact_email_status: vals }))}
                              value={apolloInput.contact_email_status}
                              placeholder="e.g. Verified"
                            />
                          </div>
                        </div>
                      </div>

                      {/* Organization Filters */}
                      <div className="space-y-4">
                         <div className="space-y-2">
                          <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Organization Filters</Label>
                          <div className="space-y-2">
                            <Label>Company Size</Label>
                            <MultiSelect
                              options={COMPANY_SIZE_OPTIONS}
                              onChange={(vals) => setApolloInput(prev => ({ ...prev, company_size: vals }))}
                              value={apolloInput.company_size}
                              placeholder="Any headcount"
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <div className="space-y-2">
                              <Label>Revenue Min ($)</Label>
                              <Input 
                                type="number" 
                                placeholder="Min" 
                                value={apolloInput.revenue_min}
                                onChange={(e) => setApolloInput(prev => ({ ...prev, revenue_min: e.target.value }))}
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>Revenue Max ($)</Label>
                              <Input 
                                type="number" 
                                placeholder="Max" 
                                value={apolloInput.revenue_max}
                                onChange={(e) => setApolloInput(prev => ({ ...prev, revenue_max: e.target.value }))}
                              />
                            </div>
                          </div>
                          <div className="space-y-2">
                            <Label>Tech Stack (comma-sep)</Label>
                            <Input 
                              placeholder="e.g. salesforce, hubspot" 
                              value={apolloInput.technologies}
                              onChange={(e) => setApolloInput(prev => ({ ...prev, technologies: e.target.value }))}
                            />
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                       <div className="space-y-2">
                          <Label>Locations (comma-sep)</Label>
                          <Input 
                            placeholder="e.g. California, London" 
                            value={apolloInput.location}
                            onChange={(e) => setApolloInput(prev => ({ ...prev, location: e.target.value }))}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Target Domains (comma-sep)</Label>
                          <Input 
                            placeholder="e.g. apple.com, google.com" 
                            value={apolloInput.organization_domains}
                            onChange={(e) => setApolloInput(prev => ({ ...prev, organization_domains: e.target.value }))}
                          />
                        </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Job Posting Search (comma-sep roles they are hiring for)</Label>
                      <Input 
                        placeholder="e.g. 'Software Engineer', 'Hiring Manager'" 
                        value={apolloInput.job_postings}
                        onChange={(e) => setApolloInput(prev => ({ ...prev, job_postings: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-3 pt-6 border-t">
                      <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                        <List className="w-3 h-3" />
                        Active Apollo Rules
                      </Label>

                      {apolloRules.length === 0 ? (
                        <p className="text-xs text-muted-foreground italic p-4 text-center border-2 border-dashed rounded-lg">
                          No Apollo rules defined yet.
                        </p>
                      ) : (
                        <div className="grid gap-2">
                          {apolloRules.map((rule) => {
                            const initials = rule.creator_name
                              ? rule.creator_name
                                  .split(" ")
                                  .map((n) => n[0])
                                  .join("")
                                  .toUpperCase()
                              : "U";
                            const config = JSON.parse(rule.value);
                            const titles = Array.isArray(config.person_titles) ? config.person_titles.join(", ") : config.job_title;
                            const seniorities = Array.isArray(config.person_seniorities) ? config.person_seniorities.join(", ") : "";
                            const headcount = Array.isArray(config.organization_num_employees_ranges) ? config.organization_num_employees_ranges.join(", ") : config.company_size;
                            
                            return (
                              <div
                                key={rule.id}
                                className="flex items-center justify-between p-3 rounded-lg bg-primary/5 border border-primary/10 group"
                              >
                                <div className="flex items-center gap-3">
                                  <div className="h-7 w-7 rounded-full bg-primary/20 flex items-center justify-center text-[10px] font-bold text-primary border border-primary/20">
                                    {initials}
                                  </div>
                                  <div className="flex flex-col text-xs">
                                    <span className="font-semibold">
                                      {titles || "Any Role"} {seniorities ? `(${seniorities})` : ""}
                                    </span>
                                    <span className="text-muted-foreground">
                                      {config.industry ? `${config.industry} • ` : ""}
                                      {config.location || "Anywhere"} •{" "}
                                      {headcount || "Any Size"}
                                    </span>
                                    {config.organization_domains && Array.isArray(config.organization_domains) && (
                                      <span className="text-[10px] text-primary/70">
                                        Domains: {config.organization_domains.join(", ")}
                                      </span>
                                    )}
                                    <span className="text-[10px] text-muted-foreground/60 mt-1">
                                      Added by {rule.creator_name}
                                    </span>
                                  </div>
                                </div>
                                {(user?.role === "admin" ||
                                  user?.id === rule.created_by_id) && (
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity hover:text-destructive"
                                    onClick={() =>
                                      handleRemoveApolloRule(rule.id)
                                    }
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </Button>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </CardContent>
                  <CardFooter className="bg-muted/30 p-4">
                    <Button 
                      className="w-full" 
                      onClick={handleAddApolloRule}
                      disabled={saving}
                    >
                      {saving ? (
                        <RefreshCcw className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Zap className="w-4 h-4 mr-2" />
                      )}
                      Create Apollo Discovery Rule
                    </Button>
                  </CardFooter>
                </Card>
                )}
              </TabsContent>

              <TabsContent value="linkedin" className="mt-6">
                <Card className="border-primary/10 shadow-lg bg-card/50 backdrop-blur-sm">
                  <CardHeader>
                    <CardTitle>
                      Keyword Monitoring ({keywordRules.length}/5)
                    </CardTitle>
                    <CardDescription>
                      Every day, we'll scan LinkedIn for posts containing these
                      keywords and identify potential leads from the commenters.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <Input
                          className="pl-9"
                          placeholder="e.g. 'hiring sales lead', 'CRM integration problems'..."
                          value={newKeyword}
                          onChange={(e) => setNewKeyword(e.target.value)}
                          onKeyDown={(e) =>
                            e.key === "Enter" && handleAddKeyword()
                          }
                          disabled={keywordRules.length >= 5}
                        />
                      </div>
                      <Button
                        onClick={handleAddKeyword}
                        variant="secondary"
                        disabled={keywordRules.length >= 5}
                      >
                        <Plus className="w-4 h-4 mr-2" />
                        Add
                      </Button>
                    </div>

                    <div className="flex flex-col gap-3 pt-2">
                      {keywordRules.length === 0 ? (
                        <p className="text-sm text-muted-foreground italic p-4 text-center w-full border-2 border-dashed rounded-lg">
                          No keywords added yet.
                        </p>
                      ) : (
                        <div className="grid gap-2">
                          {keywordRules.map((rule) => {
                            const initials = rule.creator_name
                              ? rule.creator_name
                                  .split(" ")
                                  .map((n) => n[0])
                                  .join("")
                                  .toUpperCase()
                              : "U";
                            return (
                              <div
                                key={rule.id}
                                className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border group"
                              >
                                <div className="flex items-center gap-3">
                                  <TooltipProvider>
                                    <Tooltip>
                                      <TooltipTrigger>
                                        <div className="h-6 w-6 rounded-full bg-primary/20 flex items-center justify-center text-[10px] font-bold text-primary border border-primary/20">
                                          {initials}
                                        </div>
                                      </TooltipTrigger>
                                      <TooltipContent>
                                        <p className="text-xs">
                                          Added by{" "}
                                          {rule.creator_name || "Unknown User"}
                                        </p>
                                      </TooltipContent>
                                    </Tooltip>
                                  </TooltipProvider>
                                  <span className="text-sm">{rule.value}</span>
                                </div>
                                {(user?.role === "admin" ||
                                  user?.id === rule.created_by_id) && (
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity hover:text-destructive"
                                    onClick={() => handleRemoveKeyword(rule.id)}
                                  >
                                    <X className="w-4 h-4" />
                                  </Button>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </CardContent>
                  <CardFooter className="bg-primary/5 text-xs text-muted-foreground py-3 border-t">
                    Tip: Use specific phrases that your ideal customers might
                    use in their LinkedIn posts.
                  </CardFooter>
                </Card>
              </TabsContent>

              <TabsContent value="competitors" className="mt-6">
                <Card className="border-primary/10 shadow-lg bg-card/50 backdrop-blur-sm">
                  <CardHeader>
                    <CardTitle>
                      Competitor Tracking ({competitors.length}/3)
                    </CardTitle>
                    <CardDescription>
                      We'll monitor these competitor profiles daily for new
                      posts and capture potential leads from the comments.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <Input
                          className="pl-9"
                          placeholder="Enter competitor LinkedIn URL..."
                          value={newCompetitorUrl}
                          onChange={(e) => setNewCompetitorUrl(e.target.value)}
                          onKeyDown={(e) =>
                            e.key === "Enter" && handleAddCompetitor()
                          }
                          disabled={competitors.length >= 3}
                        />
                      </div>
                      <Button
                        onClick={handleAddCompetitor}
                        variant="secondary"
                        disabled={competitors.length >= 3}
                      >
                        <Plus className="w-4 h-4 mr-2" />
                        Add
                      </Button>
                    </div>

                    <div className="grid gap-3 pt-2">
                      {competitors.length === 0 ? (
                        <p className="text-sm text-muted-foreground italic p-8 text-center w-full border-2 border-dashed rounded-lg">
                          No competitors being monitored yet.
                        </p>
                      ) : (
                        competitors.map((comp) => {
                          const initials = comp.creator_name
                            ? comp.creator_name
                                .split(" ")
                                .map((n) => n[0])
                                .join("")
                                .toUpperCase()
                            : "U";
                          return (
                            <div
                              key={comp.id}
                              className="flex items-center justify-between p-3 rounded-lg bg-muted/40 border group"
                            >
                              <div className="flex items-center gap-3 min-w-0">
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger>
                                      <div className="h-7 w-7 rounded-full bg-secondary/30 flex items-center justify-center text-[10px] font-bold text-secondary-foreground border border-secondary/20">
                                        {initials}
                                      </div>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                      <p className="text-xs">
                                        Monitored by{" "}
                                        {comp.creator_name || "Unknown User"}
                                      </p>
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                                <div className="flex flex-col min-w-0">
                                  <span className="text-sm font-medium truncate">
                                    {comp.name || "LinkedIn Profile"}
                                  </span>
                                  <span className="text-[10px] text-muted-foreground truncate">
                                    {comp.linkedin_url}
                                  </span>
                                </div>
                              </div>
                              {(user?.role === "admin" ||
                                user?.id === comp.created_by_id) && (
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 opacity-0 group-hover:opacity-100 transition-opacity"
                                  onClick={() =>
                                    handleRemoveCompetitor(comp.id)
                                  }
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              )}
                            </div>
                          );
                        })
                      )}
                    </div>
                  </CardContent>
                  <CardFooter className="bg-primary/5 text-xs text-muted-foreground py-3 border-t">
                    Note: We focus on public posts and recent engagement.
                  </CardFooter>
                </Card>
              </TabsContent>

            </Tabs>
          </div>

          <div className="space-y-6">
            <Card className="border-primary/10 shadow-lg h-full">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Activity className="w-5 h-5 text-primary" />
                  Autopilot Logs
                </CardTitle>
                <CardDescription>Recent discovery activities</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="max-h-[600px] overflow-y-auto scrollbar-thin scrollbar-thumb-primary/10 scrollbar-track-transparent">
                  <div className="divide-y divide-border">
                    {lastRuns.length === 0 ? (
                      <div className="p-8 text-center text-sm text-muted-foreground">
                        No recent activity. Once Autopilot runs, results will
                        appear here.
                      </div>
                    ) : (
                      lastRuns.map((run) => (
                        <div
                          key={run.id}
                          className="p-4 flex flex-col gap-1 hover:bg-muted/30 transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-semibold">
                              {run.title}
                            </span>
                            <span className="text-[10px] text-muted-foreground">
                              {new Date(run.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground line-clamp-2">
                            {run.description}
                          </p>
                          <div className="mt-2 text-[10px] flex items-center gap-1.5 text-primary font-medium">
                            <Badge
                              variant="outline"
                              className="text-[10px] h-4 bg-primary/5 text-primary border-primary/20"
                            >
                              COMPLETED
                            </Badge>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
