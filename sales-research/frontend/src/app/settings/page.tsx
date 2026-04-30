"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Save,
  Plus,
  Trash2,
  ShieldAlert,
  UserCheck,
  Lock,
  Building2,
  User,
  Briefcase,
  ArrowLeft,
  Zap,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/auth-context";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  savePersonalICP,
  saveGlobalICP,
  getPersonalICP,
  getGlobalICP,
  IdealProfileData,
  saveIntegrations,
  getIntegrations,
  getUserIntegrations,
  saveUserIntegrations,
  IntegrationSettings,
  getCompetitors,
  addCompetitor,
  deleteCompetitor,
  Competitor,
  getSellingProfile,
  saveSellingProfile,
  SellingProfileConfig,
  getUsageStats,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Checkbox } from "@/components/ui/checkbox";
import { MultiSelect } from "@/components/ui/multi-select";
import {
  LINKEDIN_INDUSTRIES,
  COMPANY_SIZE_OPTIONS,
  REVENUE_OPTIONS,
  JOB_TITLE_OPTIONS,
} from "@/lib/constants";

// --- Schemas ---

const icpFormSchema = z.object({
  industry: z.union([z.string(), z.array(z.string())]),
  company_size: z.union([z.string(), z.array(z.string())]).optional(),
  revenue: z.union([z.string(), z.array(z.string())]).optional(),
  job_title: z.union([z.string(), z.array(z.string())]),
  value_proposition: z.string().optional(),
});

const keysFormSchema = z.object({
  tavily_api_key: z.string().optional(),
  apollo_api_key: z.string().optional(),
  user_linkedin_url: z
    .string()
    .optional()
    .refine(
      (val) => !val || val.includes("linkedin.com"),
      "Must be a valid LinkedIn URL",
    ),
  company_linkedin_url: z
    .string()
    .optional()
    .refine(
      (val) => !val || val.includes("linkedin.com"),
      "Must be a valid LinkedIn URL",
    ),
  email_config: z.string().optional(),
  slack_webhook_url: z
    .string()
    .url("Must be a valid URL")
    .optional()
    .or(z.literal("")),
  slack_user_id: z.string().optional(),
  million_verifier_api_key: z.string().optional(),
  million_verifier_enabled: z.boolean().optional(),
  hubspot_access_token: z.string().optional(),
  hubspot_sync_enabled: z.boolean().optional(),
});

const sellingProfileSchema = z.object({
  company_name: z.string().min(1, "Company Name is required"),
  description: z.string().min(1, "Description is required"),
  business_model: z.enum(["product", "service", "hybrid"]).default("product"),
  products: z.array(
    z.object({
      name: z.string().min(1, "Product Name is required"),
      description: z.string().min(1, "Product Description is required"),
      is_strategic_pivot: z.boolean().optional(),
      target_roles: z.array(z.string()).optional(),
      target_industries: z.array(z.string()).optional(),
    }),
  ),
});

import { useConfig } from "@/context/config-context";
import { Spinner } from "@/components/ui/spinner"

export default function SettingsPage() {
  const { trialMode } = useConfig();
  const router = useRouter();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [isLoading, setIsLoading] = useState(false);
  const [isFetching, setIsFetching] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [newCompetitorUrl, setNewCompetitorUrl] = useState("");
  const [isAddingCompetitor, setIsAddingCompetitor] = useState(false);
  const [usage, setUsage] = useState<any>(null);

  // --- Forms ---

  // 1. Personal Settings Form (User Context)
  const personalForm = useForm<IntegrationSettings & IdealProfileData>({
    resolver: zodResolver(z.intersection(keysFormSchema, icpFormSchema)),
    defaultValues: {
      // ICP Defaults
      industry: [],
      company_size: [],
      revenue: [],
      job_title: "",
      value_proposition: "",
      // User Integrations Defaults
      user_linkedin_url: "",
      email_config: "",
      slack_user_id: "",
    },
  });

  // 2. Organization Settings Form (Global Context)
  const orgForm = useForm<
    IntegrationSettings & IdealProfileData & SellingProfileConfig
  >({
    // We might need a loose schema here since admins only edit parts, or split into sub-forms.
    // For simplicity, we'll use separate submit handlers but one state object isn't ideal.
    // Let's keep them separate in logic.
    defaultValues: {},
  });

  // We'll use separate form instances for Org sections to manage validation cleanliness
  const globalIcpForm = useForm<IdealProfileData>({
    resolver: zodResolver(icpFormSchema),
  });
  const globalKeysForm = useForm<IntegrationSettings>({
    resolver: zodResolver(keysFormSchema),
  });
  const sellingProfileForm = useForm<SellingProfileConfig>({
    resolver: zodResolver(sellingProfileSchema),
    defaultValues: {
      company_name: "",
      description: "",
      business_model: "product",
      products: [],
    },
  });

  const {
    fields: productFields,
    append: appendProduct,
    remove: removeProduct,
  } = useFieldArray({
    control: sellingProfileForm.control,
    name: "products",
  });

  // Load Data
  useEffect(() => {
    const loadSettings = async () => {
      setIsFetching(true);
      try {
        // Fetch Global Data
        const [
          resolvedIcp,
          globalIcp,
          globalKeys,
          globalSelling,
          competitorsList,
        ] = await Promise.all([
          getPersonalICP(), // Resolved for personal tab
          getGlobalICP(), // Explicit global for organization tab
          isAdmin ? getIntegrations() : Promise.resolve(null),
          getSellingProfile(),
          getCompetitors(),
        ]);

        // Fetch Personal Data
        const userIntegrations = await getUserIntegrations();
        // We can't easily fetch "User Only ICP" separate from "Resolved ICP" with current API
        // without modifying backend to explicitly separate them.
        // Workaround: We will use the resolved ICP for the Personal Tab as "Your Current Configuration".

        // Populate Personal Form
        if (userIntegrations) {
          personalForm.setValue(
            "user_linkedin_url",
            userIntegrations.user_linkedin_url || "",
          );
          personalForm.setValue(
            "email_config",
            userIntegrations.email_config || "",
          );
          personalForm.setValue(
            "slack_user_id",
            userIntegrations.slack_user_id || "",
          );
        }
        if (resolvedIcp) {
          const personalIcpValues = {
            industry: Array.isArray(resolvedIcp.industry)
              ? resolvedIcp.industry
              : [],
            company_size: Array.isArray(resolvedIcp.company_size)
              ? resolvedIcp.company_size
              : [],
            revenue: Array.isArray(resolvedIcp.revenue)
              ? resolvedIcp.revenue
              : [],
            job_title: Array.isArray(resolvedIcp.job_title)
              ? resolvedIcp.job_title
              : resolvedIcp.job_title
                ? (resolvedIcp.job_title as string)
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean)
                : [],
            value_proposition: resolvedIcp.value_proposition || "",
          };
          personalForm.reset({
            ...personalForm.getValues(),
            ...personalIcpValues,
          });
        }

        if (globalIcp) {
          const globalIcpValues = {
            industry: Array.isArray(globalIcp.industry)
              ? globalIcp.industry
              : [],
            company_size: Array.isArray(globalIcp.company_size)
              ? globalIcp.company_size
              : [],
            revenue: Array.isArray(globalIcp.revenue) ? globalIcp.revenue : [],
            job_title: Array.isArray(globalIcp.job_title)
              ? globalIcp.job_title
              : globalIcp.job_title
                ? (globalIcp.job_title as string)
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean)
                : [],
            value_proposition: globalIcp.value_proposition || "",
          };
          globalIcpForm.reset(globalIcpValues);
        }

        // Populate Org Forms
        if (globalKeys) {
          const sanitizedKeys = {
            tavily_api_key: globalKeys.tavily_api_key || "",
            apollo_api_key: globalKeys.apollo_api_key || "",
            user_linkedin_url: globalKeys.user_linkedin_url || "",
            company_linkedin_url: globalKeys.company_linkedin_url || "",
            email_config: globalKeys.email_config || "",
            slack_webhook_url: globalKeys.slack_webhook_url || "",
            slack_user_id: globalKeys.slack_user_id || "",
            million_verifier_api_key: globalKeys.million_verifier_api_key || "",
            million_verifier_enabled: !!globalKeys.million_verifier_enabled,
            hubspot_access_token: globalKeys.hubspot_access_token || "",
            hubspot_sync_enabled: !!globalKeys.hubspot_sync_enabled,
          };
          globalKeysForm.reset(sanitizedKeys);
        }
        if (globalSelling) {
          const sanitizedSelling = {
            company_name: globalSelling.company_name || "",
            description: globalSelling.description || "",
            business_model: globalSelling.business_model || "product",
            products: globalSelling.products || [],
          };
          sellingProfileForm.reset(sanitizedSelling);
        }
        if (competitorsList) {
          setCompetitors(competitorsList);
        }
        
        const usageStats = await getUsageStats();
        setUsage(usageStats);
      } catch (e) {
        console.error("Failed to load settings", e);
        setError("Failed to load settings.");
      } finally {
        setIsFetching(false);
      }
    };
    loadSettings();
  }, [isAdmin]);

  // --- Handlers ---

  const handleSavePersonal = async (values: any) => {
    setIsLoading(true);
    setSuccess(null);
    setError(null);
    try {
      // Save User Integrations
      await saveUserIntegrations({
        user_linkedin_url: values.user_linkedin_url,
        email_config: values.email_config,
        slack_user_id: values.slack_user_id,
      });
      // Save User ICP Override explicitly via the personal endpoint
      await savePersonalICP({
        industry: values.industry,
        company_size: values.company_size,
        revenue: values.revenue,
        job_title: values.job_title,
        value_proposition: values.value_proposition,
      });
      setSuccess("Personal settings saved successfully.");
      setTimeout(() => setSuccess(null), 3000);
    } catch (e) {
      setError("Failed to save personal settings.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveGlobalICP = async (values: IdealProfileData) => {
    if (!isAdmin) return;
    setIsLoading(true);
    setSuccess(null);
    setError(null);
    try {
      // Admin calling saveGlobalICP explicitly updates Organizational Settings
      await saveGlobalICP(values);
      setSuccess("Global ICP updated.");
      setTimeout(() => setSuccess(null), 3000);
    } catch (e) {
      setError("Failed to update Global ICP.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveGlobalKeys = async (values: IntegrationSettings) => {
    if (!isAdmin) return;
    setIsLoading(true);
    setSuccess(null);
    setError(null);
    try {
      await saveIntegrations(values);
      setSuccess("Integration keys updated.");
      setTimeout(() => setSuccess(null), 3000);
    } catch (e) {
      setError("Failed to update keys.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveSellingProfile = async (values: SellingProfileConfig) => {
    if (!isAdmin) return;
    setIsLoading(true);
    setSuccess(null);
    setError(null);
    try {
      await saveSellingProfile(values);
      setSuccess("Selling profile updated.");
      setTimeout(() => setSuccess(null), 3000);
    } catch (e) {
      setError("Failed to update selling profile.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddCompetitor = async () => {
    if (!newCompetitorUrl) return;
    setIsAddingCompetitor(true);
    try {
      await addCompetitor({ linkedin_url: newCompetitorUrl });
      setNewCompetitorUrl("");
      const updated = await getCompetitors();
      setCompetitors(updated);
    } catch (e) {
      console.error("Failed to add competitor", e);
    } finally {
      setIsAddingCompetitor(false);
    }
  };

  const handleDeleteCompetitor = async (id: string) => {
    try {
      await deleteCompetitor(id);
      setCompetitors(competitors.filter((c) => c.id !== id));
    } catch (e) {
      console.error("Failed to delete competitor", e);
    }
  };

  if (isFetching) {
    return (
      <div className="h-full flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto py-8 px-4">
      <div className="flex justify-between items-center mb-8">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push("/")}
            className="rounded-full h-10 w-10 border bg-muted/20 hover:bg-muted/40 transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Settings</h1>
            <p className="text-muted-foreground mt-1">
              Manage your personal preferences and organization defaults.
            </p>
          </div>
        </div>
        <Badge
          variant="outline"
          className={
            isAdmin
              ? "text-primary border-primary/20 bg-primary/5"
              : "text-amber-500 border-amber-500/20 bg-amber-500/5"
          }
        >
          {isAdmin ? (
            <ShieldAlert className="w-3 h-3 mr-1" />
          ) : (
            <UserCheck className="w-3 h-3 mr-1" />
          )}
          {isAdmin ? "Admin Access" : "Representative Access"}
        </Badge>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert className="mb-6 border-green-500/20 bg-green-500/5 text-green-700">
          <AlertTitle>Success</AlertTitle>
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      {usage?.trial_mode && (
        <Card className="mb-6 border-primary/20 bg-primary/5">
          <CardHeader className="py-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <Zap className="w-5 h-5 text-primary" />
              Trial Usage & Limits
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
             <div className="flex flex-col gap-1 p-3 rounded-lg bg-card border">
                <span className="text-xs text-muted-foreground uppercase font-bold tracking-wider">Deep Researches</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold">{usage.research.used}</span>
                  <span className="text-sm text-muted-foreground">/ {usage.research.limit} used</span>
                </div>
                <div className="w-full h-1.5 bg-muted rounded-full mt-2 overflow-hidden">
                  <div 
                    className="h-full bg-primary transition-all" 
                    style={{ width: `${Math.min(100, (usage.research.used / usage.research.limit) * 100)}%` }}
                  />
                </div>
                <span className="text-[10px] text-muted-foreground mt-1">
                  {usage.research.remaining} researches remaining
                </span>
             </div>
             <div className="flex flex-col gap-1 p-3 rounded-lg bg-card border">
                <span className="text-xs text-muted-foreground uppercase font-bold tracking-wider">Profile Classifications</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold">{usage.classification.used}</span>
                  <span className="text-sm text-muted-foreground">/ {usage.classification.limit} leads</span>
                </div>
                <div className="w-full h-1.5 bg-muted rounded-full mt-2 overflow-hidden">
                  <div 
                    className="h-full bg-primary transition-all" 
                    style={{ width: `${Math.min(100, (usage.classification.used / usage.classification.limit) * 100)}%` }}
                  />
                </div>
                <span className="text-[10px] text-muted-foreground mt-1">
                  {usage.classification.remaining} classifications remaining
                </span>
             </div>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="personal" className="w-full space-y-6">
        <TabsList className="grid w-full grid-cols-2 lg:w-[400px]">
          <TabsTrigger value="personal" className="gap-2">
            <User className="w-4 h-4" /> Personal Settings
          </TabsTrigger>
          <TabsTrigger value="organization" className="gap-2">
            <Building2 className="w-4 h-4" /> Organization
          </TabsTrigger>
        </TabsList>

        {/* --- PERSONAL SETTINGS TAB --- */}
        <TabsContent
          value="personal"
          className="space-y-6 animate-in fade-in slide-in-from-top-2"
        >
          <Alert className="border-blue-500/20 bg-blue-500/5">
            <UserCheck className="h-4 w-4 text-blue-500" />
            <AlertTitle className="text-blue-500">
              Member Configuration
            </AlertTitle>
            <AlertDescription className="text-blue-500/80">
              Settings configured here apply <strong>only to you</strong> and
              override organization defaults.
            </AlertDescription>
          </Alert>

          <Form {...personalForm}>
            <form
              onSubmit={personalForm.handleSubmit(handleSavePersonal)}
              className="space-y-8"
            >
              {/* Personal Identity */}
              <Card>
                <CardHeader>
                  <CardTitle>Identity & Integrations</CardTitle>
                  <CardDescription>
                    Your private credentials for research.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={personalForm.control}
                    name="user_linkedin_url"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Your LinkedIn URL</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="https://linkedin.com/in/yourname"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Used to track lead engagement on your posts.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={personalForm.control}
                    name="email_config"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>IMAP Configuration (JSON)</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder='{"imap_server": "...", "email_user": "...", "email_password": "..."}'
                            className="font-mono text-sm min-h-[80px]"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Required for analyzing your email history with leads.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={personalForm.control}
                    name="slack_user_id"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Slack Member ID</FormLabel>
                        <FormControl>
                          <Input placeholder="U01234567" {...field} />
                        </FormControl>
                        <FormDescription>
                          Used to identify you when you click buttons in Slack.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>

              {/* Personal ICP Override */}
              <Card>
                <CardHeader>
                  <CardTitle>Personal ICP Override</CardTitle>
                  <CardDescription>
                    Customize the Ideal Customer Profile for your specific
                    territory or focus.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={personalForm.control}
                    name="industry"
                    render={({ field }) => (
                      <FormItem>
                        <FormControl>
                          <MultiSelect
                            label="Target Industries"
                            options={LINKEDIN_INDUSTRIES}
                            value={field.value || []}
                            onChange={field.onChange}
                            placeholder="Search & select industries..."
                            allowCustom
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={personalForm.control}
                      name="company_size"
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <MultiSelect
                              label="Company Sizes"
                              options={COMPANY_SIZE_OPTIONS}
                              value={field.value || []}
                              onChange={field.onChange}
                              placeholder="Select sizes..."
                              hideSearch
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={personalForm.control}
                      name="revenue"
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <MultiSelect
                              label="Revenue Ranges"
                              options={REVENUE_OPTIONS}
                              value={field.value || []}
                              onChange={field.onChange}
                              placeholder="Select revenue..."
                              hideSearch
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                  <FormField
                    control={personalForm.control}
                    name="job_title"
                    render={({ field }) => (
                      <FormItem>
                        <FormControl>
                          <MultiSelect
                            label="Target Job Titles"
                            options={JOB_TITLE_OPTIONS}
                            value={field.value || []}
                            onChange={field.onChange}
                            placeholder="e.g. CTO, VP Engineering..."
                            allowCustom
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={personalForm.control}
                    name="value_proposition"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>My Value Prop</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="How I pitch to this segment..."
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>

              <div className="flex justify-end">
                <Button type="submit" disabled={isLoading} size="lg">
                  {isLoading ? (
                    <Spinner size="md" className="mr-2" />
                  ) : (
                    <Save className="mr-2 h-4 w-4" />
                  )}
                  Save Personal Settings
                </Button>
              </div>
            </form>
          </Form>
        </TabsContent>

        {/* --- ORGANIZATION SETTINGS TAB --- */}
        <TabsContent
          value="organization"
          className="space-y-6 animate-in fade-in slide-in-from-top-2"
        >
          {!isAdmin && (
            <Alert
              variant="destructive"
              className="border-amber-500/20 bg-amber-500/5"
            >
              <Lock className="h-4 w-4 text-amber-500" />
              <AlertTitle className="text-amber-500">Read Only Mode</AlertTitle>
              <AlertDescription className="text-amber-500/80">
                You are viewing organization-wide defaults. Only administrators
                can modify these settings.
              </AlertDescription>
            </Alert>
          )}

          {/* Selling Profile */}
          <Card>
            <CardHeader>
              <CardTitle>Selling Profile</CardTitle>
              <CardDescription>
                Define what the organization sells. This context is used to
                generate strategic pivots and match scores.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...sellingProfileForm}>
                <form
                  onSubmit={sellingProfileForm.handleSubmit(
                    handleSaveSellingProfile,
                  )}
                  className="space-y-6"
                >
                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={sellingProfileForm.control}
                      name="company_name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Company Name</FormLabel>
                          <FormControl>
                            <Input {...field} disabled={!isAdmin} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={sellingProfileForm.control}
                      name="description"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Company Tagline</FormLabel>
                          <FormControl>
                            <Input {...field} disabled={!isAdmin} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <FormField
                    control={sellingProfileForm.control}
                    name="business_model"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Business Model</FormLabel>
                        <Select
                          onValueChange={field.onChange}
                          defaultValue={field.value}
                          disabled={!isAdmin}
                          value={field.value}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select your model" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="product">Product-Led (Tools, SaaS, HW)</SelectItem>
                            <SelectItem value="service">Service-Led (Agency, Consulting, Managed)</SelectItem>
                            <SelectItem value="hybrid">Hybrid (Product + Services)</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormDescription>
                          Determines if the AI pitches technical features or strategic expertise.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <h4 className="text-sm font-semibold">
                        Products & Services
                      </h4>
                      {isAdmin && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            appendProduct({
                              name: "",
                              description: "",
                              target_roles: [],
                              target_industries: [],
                            })
                          }
                        >
                          <Plus className="w-3 h-3 mr-1" /> Add Product
                        </Button>
                      )}
                    </div>
                    {productFields.map((field, index) => (
                      <div
                        key={field.id}
                        className="p-4 border rounded-lg bg-muted/10 space-y-3 relative group"
                      >
                        {isAdmin && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={() => removeProduct(index)}
                          >
                            <Trash2 className="w-3 h-3 text-destructive" />
                          </Button>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <FormField
                            control={sellingProfileForm.control}
                            name={`products.${index}.name`}
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="text-xs">
                                  Product Name
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    {...field}
                                    disabled={!isAdmin}
                                    className="h-8"
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={sellingProfileForm.control}
                            name={`products.${index}.is_strategic_pivot`}
                            render={({ field }) => (
                              <FormItem className="flex flex-row items-end space-x-2 space-y-0 h-full pb-2">
                                <FormControl>
                                  <Checkbox
                                    checked={field.value}
                                    onCheckedChange={field.onChange}
                                    disabled={!isAdmin}
                                  />
                                </FormControl>
                                <FormLabel className="font-normal text-xs cursor-pointer">
                                  Mark as Strategic Pivot (Hero Product)
                                </FormLabel>
                              </FormItem>
                            )}
                          />
                        </div>
                        <FormField
                          control={sellingProfileForm.control}
                          name={`products.${index}.target_roles`}
                          render={({ field }) => (
                            <FormItem>
                              <MultiSelect
                                label="Target Roles"
                                options={JOB_TITLE_OPTIONS}
                                value={field.value || []}
                                onChange={field.onChange}
                                placeholder="Founder, CTO, VP Sales..."
                                allowCustom
                              />
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={sellingProfileForm.control}
                          name={`products.${index}.target_industries`}
                          render={({ field }) => (
                            <FormItem>
                              <MultiSelect
                                label="Target Industries"
                                options={LINKEDIN_INDUSTRIES}
                                value={field.value || []}
                                onChange={field.onChange}
                                placeholder="Logistics, Software, Healthcare..."
                                allowCustom
                              />
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={sellingProfileForm.control}
                          name={`products.${index}.description`}
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="text-xs">
                                Value & Capabilities
                              </FormLabel>
                              <FormControl>
                                <Textarea
                                  {...field}
                                  disabled={!isAdmin}
                                  className="min-h-[60px] resize-none"
                                />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                      </div>
                    ))}
                  </div>

                  {isAdmin && (
                    <div className="flex justify-end">
                      <Button
                        type="submit"
                        disabled={isLoading}
                        size="sm"
                        variant="outline"
                      >
                        {isLoading ? (
                          <Spinner size="md" className="mr-2" />
                        ) : (
                          <Save className="mr-2 h-4 w-4" />
                        )}
                        Update Selling Profile
                      </Button>
                    </div>
                  )}
                </form>
              </Form>
            </CardContent>
          </Card>

          {/* Global ICP */}
          <Card>
            <CardHeader>
              <CardTitle>Global Ideal Customer Profile</CardTitle>
              <CardDescription>
                The default research baseline for the entire organization.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...globalIcpForm}>
                <form
                  onSubmit={globalIcpForm.handleSubmit(handleSaveGlobalICP)}
                  className="space-y-4"
                >
                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={globalIcpForm.control}
                      name="industry"
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <MultiSelect
                              label="Industries"
                              options={LINKEDIN_INDUSTRIES}
                              value={field.value || []}
                              onChange={field.onChange}
                              placeholder="Search industries..."
                              allowCustom
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={globalIcpForm.control}
                      name="company_size"
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <MultiSelect
                              label="Company Sizes"
                              options={COMPANY_SIZE_OPTIONS}
                              value={field.value || []}
                              onChange={field.onChange}
                              placeholder="Select sizes..."
                              hideSearch
                              disabled={!isAdmin}
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={globalIcpForm.control}
                      name="revenue"
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <MultiSelect
                              label="Revenue Ranges"
                              options={REVENUE_OPTIONS}
                              value={field.value || []}
                              onChange={field.onChange}
                              placeholder="Select revenue..."
                              hideSearch
                              disabled={!isAdmin}
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={globalIcpForm.control}
                      name="job_title"
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <MultiSelect
                              label="Job Titles"
                              options={JOB_TITLE_OPTIONS}
                              value={field.value || []}
                              onChange={field.onChange}
                              placeholder="e.g. CTO, VP Engineering..."
                              allowCustom
                              disabled={!isAdmin}
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                  </div>
                  <FormField
                    control={globalIcpForm.control}
                    name="value_proposition"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Global Value Prop</FormLabel>
                        <FormControl>
                          <Textarea
                            {...field}
                            disabled={!isAdmin}
                            className="h-20"
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  {isAdmin && (
                    <div className="flex justify-end">
                      <Button
                        type="submit"
                        disabled={isLoading}
                        size="sm"
                        variant="outline"
                      >
                        Update Global ICP
                      </Button>
                    </div>
                  )}
                </form>
              </Form>
            </CardContent>
          </Card>

          {/* Competitors */}
          <Card>
            <CardHeader>
              <CardTitle>Competitor Tracking</CardTitle>
              <CardDescription>
                Competitor profiles monitored for lead sourcing.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {isAdmin && (
                  <div className="flex gap-2">
                    <Input
                      placeholder="LinkedIn Profile URL"
                      value={newCompetitorUrl}
                      onChange={(e) => setNewCompetitorUrl(e.target.value)}
                      onKeyPress={(e) =>
                        e.key === "Enter" && handleAddCompetitor()
                      }
                    />
                    <Button
                      onClick={handleAddCompetitor}
                      disabled={isAddingCompetitor || !newCompetitorUrl}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                )}
                <div className="space-y-2">
                  {competitors.map((competitor) => (
                    <div
                      key={competitor.id}
                      className="flex items-center justify-between p-2 border rounded-md bg-muted/20"
                    >
                      <div className="flex items-center gap-2">
                        <Briefcase className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm truncate max-w-[300px]">
                          {competitor.linkedin_url}
                        </span>
                      </div>
                      {isAdmin && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteCompetitor(competitor.id)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      )}
                    </div>
                  ))}
                  {competitors.length === 0 && (
                    <p className="text-sm text-muted-foreground italic">
                      No competitors tracked.
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Global Keys */}
          <Card>
            <CardHeader>
              <CardTitle>Core API Keys</CardTitle>
              <CardDescription>
                Organization-wide keys for data providers.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...globalKeysForm}>
                <form
                  onSubmit={globalKeysForm.handleSubmit(handleSaveGlobalKeys)}
                  className="space-y-4"
                >
                  <FormField
                    control={globalKeysForm.control}
                    name="tavily_api_key"
                    render={({ field }) => (
                      <FormItem>
                        <div className="flex items-center justify-between">
                          <FormLabel>Tavily API Key</FormLabel>
                          {!isAdmin && (
                            <Badge variant="outline" className="text-xs h-5">
                              <Lock className="w-2 h-2 mr-1" /> Admin Only
                            </Badge>
                          )}
                        </div>
                        <FormControl>
                          <Input
                            type="password"
                            {...field}
                            disabled={!isAdmin || trialMode}
                            placeholder={trialMode ? "Contact support to enable Web Search" : ""}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                      <FormField
                        control={globalKeysForm.control}
                        name="apollo_api_key"
                        render={({ field }) => (
                          <FormItem>
                            <div className="flex items-center justify-between">
                              <FormLabel className="flex items-center gap-2">
                                Apollo API Key
                                {trialMode && (
                                  <Badge variant="secondary" className="text-[10px] h-4 bg-amber-500 text-white border-none">
                                    NOT IN TRIAL
                                  </Badge>
                                )}
                              </FormLabel>
                              {!isAdmin && !trialMode && (
                                <Badge variant="outline" className="text-xs h-5">
                                  <Lock className="w-2 h-2 mr-1" /> Admin Only
                                </Badge>
                              )}
                            </div>
                            <FormControl>
                              <Input
                                type="password"
                                {...field}
                                disabled={!isAdmin || trialMode}
                                placeholder={trialMode ? "Contact support to enable Apollo integration" : ""}
                              />
                            </FormControl>
                          </FormItem>
                        )}
                      />
                  <div className="flex justify-end pt-2">
                    {isAdmin && (
                      <Button
                        type="submit"
                        disabled={isLoading}
                        size="sm"
                        variant="outline"
                      >
                        Update Keys
                      </Button>
                    )}
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
