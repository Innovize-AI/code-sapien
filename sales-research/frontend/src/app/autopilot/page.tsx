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

export default function AutopilotPage() {
  const { user } = useAuth();
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
    job_title: "",
    location: "",
    company_size: "",
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
    if (!apolloInput.job_title && !apolloInput.industry) {
      toast({
        title: "Missing Info",
        description: "Please enter at least a Job Title or Industry.",
        variant: "destructive",
      });
      return;
    }
    setSaving(true);
    try {
      await addAutopilotRule({
        type: "apollo_config",
        value: JSON.stringify(apolloInput),
      });
      setApolloInput({
        industry: "",
        job_title: "",
        location: "",
        company_size: "",
      });
      const rules = await getAutopilotRules("apollo_config");
      setApolloRules(rules);
      toast({ title: "Success", description: "Apollo search rule added." });
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
              Set up automated rules to find high-intent leads every 24 hours.
              Track who added what for better team coordination.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="md:col-span-2 space-y-6">
            <Tabs defaultValue="linkedin" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="linkedin" className="gap-2">
                  <Globe className="w-4 h-4" />
                  LinkedIn Keywords
                </TabsTrigger>
                <TabsTrigger value="competitors" className="gap-2">
                  <Users className="w-4 h-4" />
                  Competitors
                </TabsTrigger>
                <TabsTrigger value="apollo" className="gap-2">
                  <Search className="w-4 h-4" />
                  Apollo Search
                </TabsTrigger>
              </TabsList>

              <TabsContent value="linkedin" className="mt-6">
                <Card className="border-primary/10 shadow-lg bg-card/50 backdrop-blur-sm">
                  <CardHeader>
                    <CardTitle>Keyword Monitoring</CardTitle>
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
                        />
                      </div>
                      <Button onClick={handleAddKeyword} variant="secondary">
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
                    <CardTitle>Competitor Tracking</CardTitle>
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
                        />
                      </div>
                      <Button onClick={handleAddCompetitor} variant="secondary">
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

              <TabsContent value="apollo" className="mt-6">
                <Card className="border-primary/10 shadow-lg bg-card/50 backdrop-blur-sm">
                  <CardHeader>
                    <CardTitle>Apollo Lead Gen</CardTitle>
                    <CardDescription>
                      Configure filters to automatically pull targeted profiles
                      from Apollo into your research queue.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label className="flex items-center gap-2">
                          <Briefcase className="w-4 h-4 text-primary" />
                          Job Titles
                        </Label>
                        <Input
                          placeholder="e.g. VP of Sales, CTO"
                          value={apolloInput.job_title}
                          onChange={(e) =>
                            setApolloInput({
                              ...apolloInput,
                              job_title: e.target.value,
                            })
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="flex items-center gap-2">
                          <Globe className="w-4 h-4 text-primary" />
                          Industry
                        </Label>
                        <Input
                          placeholder="e.g. SaaS, FinTech"
                          value={apolloInput.industry}
                          onChange={(e) =>
                            setApolloInput({
                              ...apolloInput,
                              industry: e.target.value,
                            })
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="flex items-center gap-2">
                          <Globe className="w-4 h-4 text-primary" />
                          Location
                        </Label>
                        <Input
                          placeholder="e.g. United States, London"
                          value={apolloInput.location}
                          onChange={(e) =>
                            setApolloInput({
                              ...apolloInput,
                              location: e.target.value,
                            })
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="flex items-center gap-2">
                          <Users className="w-4 h-4 text-primary" />
                          Company Size
                        </Label>
                        <Input
                          placeholder="e.g. 50-200"
                          value={apolloInput.company_size}
                          onChange={(e) =>
                            setApolloInput({
                              ...apolloInput,
                              company_size: e.target.value,
                            })
                          }
                        />
                      </div>
                    </div>

                    <Button
                      onClick={handleAddApolloRule}
                      className="w-full"
                      variant="secondary"
                      disabled={saving}
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      Add Apollo Discovery Rule
                    </Button>

                    <div className="space-y-3 pt-4 border-t">
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
                                      {config.job_title || "Any Role"} in{" "}
                                      {config.industry || "Any Industry"}
                                    </span>
                                    <span className="text-muted-foreground">
                                      {config.location || "Anywhere"} •{" "}
                                      {config.company_size || "Any Size"}
                                    </span>
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
                  <CardFooter className="bg-primary/5 text-xs text-muted-foreground py-3 border-t">
                    Apollo discovery will fetch up to 10 new leads per day
                    matching these criteria.
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
