
"use client"

import { useState, useEffect, useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, useFieldArray } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Loader2, Save, Plus, Trash2, ShieldAlert, UserCheck, Lock, Building2, User, Briefcase } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useAuth } from "@/context/auth-context"
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
    FormDescription,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
    saveICP, getICP, IdealProfileData,
    saveIntegrations, getIntegrations, getUserIntegrations, saveUserIntegrations, IntegrationSettings,
    getCompetitors, addCompetitor, deleteCompetitor, Competitor,
    getSellingProfile, saveSellingProfile, SellingProfileConfig
} from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Checkbox } from "@/components/ui/checkbox"

// --- Schemas ---

const icpFormSchema = z.object({
    industry: z.string().min(2, "Industry is required"),
    company_size: z.string().optional(),
    revenue: z.string().optional(),
    job_title: z.string().min(2, "Available job titles are required"),
    value_proposition: z.string().optional(),
})

const keysFormSchema = z.object({
    tavily_api_key: z.string().optional(),
    apollo_api_key: z.string().optional(),
    user_linkedin_url: z.string().optional().refine(val => !val || val.includes("linkedin.com"), "Must be a valid LinkedIn URL"),
    company_linkedin_url: z.string().optional().refine(val => !val || val.includes("linkedin.com"), "Must be a valid LinkedIn URL"),
    email_config: z.string().optional(),
    slack_webhook_url: z.string().url("Must be a valid URL").optional().or(z.literal("")),
    slack_user_id: z.string().optional(),
})

const sellingProfileSchema = z.object({
    company_name: z.string().min(1, "Company Name is required"),
    description: z.string().min(1, "Description is required"),
    products: z.array(z.object({
        name: z.string().min(1, "Product Name is required"),
        description: z.string().min(1, "Product Description is required"),
        is_strategic_pivot: z.boolean().optional(),
        target_roles: z.array(z.string()).optional() // Handled as comma-sep string in UI for simplicity
    }))
})

export default function SettingsPage() {
    const queryClient = useQueryClient()
    const { user } = useAuth()
    const isAdmin = user?.role === "admin"

    // --- Queries ---

    const { data: globalIcp, isLoading: isIcpLoading, error: icpError } = useQuery({
        queryKey: ["settings", "icp"],
        queryFn: getICP
    })

    const { data: globalKeys, isLoading: isKeysLoading } = useQuery({
        queryKey: ["settings", "integrations"],
        queryFn: getIntegrations,
        enabled: isAdmin
    })

    const { data: globalSelling, isLoading: isSellingLoading } = useQuery({
        queryKey: ["settings", "selling-profile"],
        queryFn: getSellingProfile
    })

    const { data: competitorsList, isLoading: isCompetitorsLoading } = useQuery({
        queryKey: ["settings", "competitors"],
        queryFn: getCompetitors
    })

    const { data: userIntegrations, isLoading: isUserIntegrationsLoading } = useQuery({
        queryKey: ["settings", "user-integrations"],
        queryFn: getUserIntegrations
    })

    // Local state for non-form elements
    const [success, setSuccess] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [newCompetitorUrl, setNewCompetitorUrl] = useState("")

    // --- Forms ---

    // 1. Personal Settings Form (User Context)
    const personalForm = useForm<IntegrationSettings & IdealProfileData>({
        resolver: zodResolver(z.intersection(keysFormSchema, icpFormSchema)),
        defaultValues: {
            // ICP Defaults
            industry: "", company_size: "", revenue: "", job_title: "", value_proposition: "",
            // User Integrations Defaults
            user_linkedin_url: "", email_config: "", slack_user_id: ""
        }
    })

    // 2. Organization Settings Form (Global Context)
    const orgForm = useForm<IntegrationSettings & IdealProfileData & SellingProfileConfig>({
        // We might need a loose schema here since admins only edit parts, or split into sub-forms. 
        // For simplicity, we'll use separate submit handlers but one state object isn't ideal.
        // Let's keep them separate in logic.
        defaultValues: {}
    })

    // We'll use separate form instances for Org sections to manage validation cleanliness
    const globalIcpForm = useForm<IdealProfileData>({ resolver: zodResolver(icpFormSchema) })
    const globalKeysForm = useForm<IntegrationSettings>({ resolver: zodResolver(keysFormSchema) })
    const sellingProfileForm = useForm<SellingProfileConfig>({
        resolver: zodResolver(sellingProfileSchema),
        defaultValues: {
            company_name: "",
            description: "",
            products: []
        }
    })

    const { fields: productFields, append: appendProduct, remove: removeProduct } = useFieldArray({
        control: sellingProfileForm.control,
        name: "products"
    });

    // Sync form data when queries finish
    useEffect(() => {
        if (userIntegrations) {
            personalForm.setValue("user_linkedin_url", userIntegrations.user_linkedin_url || "")
            personalForm.setValue("email_config", userIntegrations.email_config || "")
            personalForm.setValue("slack_user_id", userIntegrations.slack_user_id || "")
        }
    }, [userIntegrations, personalForm])

    useEffect(() => {
        if (globalIcp) {
            const icpValues = {
                industry: globalIcp.industry || "",
                company_size: globalIcp.company_size || "",
                revenue: globalIcp.revenue || "",
                job_title: globalIcp.job_title || "",
                value_proposition: globalIcp.value_proposition || ""
            }
            personalForm.reset({ ...personalForm.getValues(), ...icpValues })
            globalIcpForm.reset(icpValues)
        }
    }, [globalIcp, personalForm, globalIcpForm])

    useEffect(() => {
        if (globalKeys) globalKeysForm.reset(globalKeys)
    }, [globalKeys, globalKeysForm])

    useEffect(() => {
        if (globalSelling) sellingProfileForm.reset(globalSelling)
    }, [globalSelling, sellingProfileForm])

    // --- Mutations ---

    const invalidateSettings = () => {
        queryClient.invalidateQueries({ queryKey: ["settings"] })
        setSuccess("Settings saved successfully")
        setTimeout(() => setSuccess(null), 3000)
    }

    const personalMutation = useMutation({
        mutationFn: async (values: any) => {
            await Promise.all([
                saveUserIntegrations({
                    user_linkedin_url: values.user_linkedin_url,
                    email_config: values.email_config,
                    slack_user_id: values.slack_user_id
                }),
                saveICP({
                    industry: values.industry,
                    company_size: values.company_size,
                    revenue: values.revenue,
                    job_title: values.job_title,
                    value_proposition: values.value_proposition
                })
            ])
        },
        onSuccess: invalidateSettings,
        onError: () => setError("Failed to save personal settings")
    })

    const globalIcpMutation = useMutation({
        mutationFn: saveICP,
        onSuccess: invalidateSettings,
        onError: () => setError("Failed to update Global ICP")
    })

    const globalKeysMutation = useMutation({
        mutationFn: saveIntegrations,
        onSuccess: invalidateSettings,
        onError: () => setError("Failed to update keys")
    })

    const sellingProfileMutation = useMutation({
        mutationFn: saveSellingProfile,
        onSuccess: invalidateSettings,
        onError: () => setError("Failed to update selling profile")
    })

    const addCompetitorMutation = useMutation({
        mutationFn: (url: string) => addCompetitor({ linkedin_url: url }),
        onSuccess: () => {
            setNewCompetitorUrl("")
            queryClient.invalidateQueries({ queryKey: ["settings", "competitors"] })
        }
    })

    const deleteCompetitorMutation = useMutation({
        mutationFn: deleteCompetitor,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings", "competitors"] })
    })

    // --- Handlers ---

    const handleSavePersonal = (values: any) => personalMutation.mutate(values)
    const handleSaveGlobalICP = (values: IdealProfileData) => globalIcpMutation.mutate(values)
    const handleSaveGlobalKeys = (values: IntegrationSettings) => globalKeysMutation.mutate(values)
    const handleSaveSellingProfile = (values: SellingProfileConfig) => sellingProfileMutation.mutate(values)
    const handleAddCompetitor = () => {
        if (newCompetitorUrl) addCompetitorMutation.mutate(newCompetitorUrl)
    }
    const handleDeleteCompetitor = (id: string) => deleteCompetitorMutation.mutate(id)

    const isFetching = isIcpLoading || isKeysLoading || isSellingLoading || isCompetitorsLoading || isUserIntegrationsLoading
    const isLoading = personalMutation.isPending || globalIcpMutation.isPending || globalKeysMutation.isPending || sellingProfileMutation.isPending


    if (isFetching) {
        return (
            <div className="h-full flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    return (
        <div className="max-w-5xl mx-auto py-8 px-4">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold">Settings</h1>
                    <p className="text-muted-foreground mt-1">Manage your personal preferences and organization defaults.</p>
                </div>
                <Badge variant="outline" className={isAdmin ? "text-primary border-primary/20 bg-primary/5" : "text-amber-500 border-amber-500/20 bg-amber-500/5"}>
                    {isAdmin ? <ShieldAlert className="w-3 h-3 mr-1" /> : <UserCheck className="w-3 h-3 mr-1" />}
                    {isAdmin ? "Admin Access" : "Representative Access"}
                </Badge>
            </div>

            {error && <Alert variant="destructive" className="mb-6"><AlertTitle>Error</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
            {success && <Alert className="mb-6 border-green-500/20 bg-green-500/5 text-green-700"><AlertTitle>Success</AlertTitle><AlertDescription>{success}</AlertDescription></Alert>}

            <Tabs defaultValue="personal" className="w-full space-y-6">
                <TabsList className="grid w-full grid-cols-2 lg:w-[400px]">
                    <TabsTrigger value="personal" className="gap-2"><User className="w-4 h-4" /> Personal Settings</TabsTrigger>
                    <TabsTrigger value="organization" className="gap-2"><Building2 className="w-4 h-4" /> Organization</TabsTrigger>
                </TabsList>

                {/* --- PERSONAL SETTINGS TAB --- */}
                <TabsContent value="personal" className="space-y-6 animate-in fade-in slide-in-from-top-2">
                    <Alert className="border-blue-500/20 bg-blue-500/5">
                        <UserCheck className="h-4 w-4 text-blue-500" />
                        <AlertTitle className="text-blue-500">Member Configuration</AlertTitle>
                        <AlertDescription className="text-blue-500/80">
                            Settings configured here apply <strong>only to you</strong> and override organization defaults.
                        </AlertDescription>
                    </Alert>

                    <Form {...personalForm}>
                        <form onSubmit={personalForm.handleSubmit(handleSavePersonal)} className="space-y-8">

                            {/* Personal Identity */}
                            <Card>
                                <CardHeader><CardTitle>Identity & Integrations</CardTitle><CardDescription>Your private credentials for research.</CardDescription></CardHeader>
                                <CardContent className="space-y-4">
                                    <FormField
                                        control={personalForm.control}
                                        name="user_linkedin_url"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Your LinkedIn URL</FormLabel>
                                                <FormControl><Input placeholder="https://linkedin.com/in/yourname" {...field} /></FormControl>
                                                <FormDescription>Used to track lead engagement on your posts.</FormDescription>
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
                                                <FormDescription>Required for analyzing your email history with leads.</FormDescription>
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
                                                <FormControl><Input placeholder="U01234567" {...field} /></FormControl>
                                                <FormDescription>Used to identify you when you click buttons in Slack.</FormDescription>
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
                                    <CardDescription>Customize the Ideal Customer Profile for your specific territory or focus.</CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <FormField
                                        control={personalForm.control}
                                        name="industry"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Target Industry</FormLabel>
                                                <FormControl><Input placeholder="e.g. Fintech" {...field} /></FormControl>
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
                                                    <FormLabel>Company Size</FormLabel>
                                                    <Select onValueChange={field.onChange} value={field.value}>
                                                        <FormControl><SelectTrigger><SelectValue placeholder="Any" /></SelectTrigger></FormControl>
                                                        <SelectContent>
                                                            <SelectItem value="1-10">1-10</SelectItem>
                                                            <SelectItem value="11-50">11-50</SelectItem>
                                                            <SelectItem value="51-200">51-200</SelectItem>
                                                            <SelectItem value="201-500">201-500</SelectItem>
                                                            <SelectItem value="500+">500+</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                        <FormField
                                            control={personalForm.control}
                                            name="revenue"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Revenue</FormLabel>
                                                    <Select onValueChange={field.onChange} value={field.value}>
                                                        <FormControl><SelectTrigger><SelectValue placeholder="Any" /></SelectTrigger></FormControl>
                                                        <SelectContent>
                                                            <SelectItem value="<$1M">&lt;$1M</SelectItem>
                                                            <SelectItem value="$1M-$10M">$1M - $10M</SelectItem>
                                                            <SelectItem value="$10M-$50M">$10M - $50M</SelectItem>
                                                            <SelectItem value="$50M+">$50M+</SelectItem>
                                                        </SelectContent>
                                                    </Select>
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
                                                <FormLabel>Job Titles</FormLabel>
                                                <FormControl><Input placeholder="CTO, VP Eng" {...field} /></FormControl>
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
                                                <FormControl><Textarea placeholder="How I pitch to this segment..." {...field} /></FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                </CardContent>
                            </Card>

                            <div className="flex justify-end">
                                <Button type="submit" disabled={isLoading} size="lg">
                                    {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                                    Save Personal Settings
                                </Button>
                            </div>
                        </form>
                    </Form>
                </TabsContent>

                {/* --- ORGANIZATION SETTINGS TAB --- */}
                <TabsContent value="organization" className="space-y-6 animate-in fade-in slide-in-from-top-2">
                    {!isAdmin && (
                        <Alert variant="destructive" className="border-amber-500/20 bg-amber-500/5">
                            <Lock className="h-4 w-4 text-amber-500" />
                            <AlertTitle className="text-amber-500">Read Only Mode</AlertTitle>
                            <AlertDescription className="text-amber-500/80">
                                You are viewing organization-wide defaults. Only administrators can modify these settings.
                            </AlertDescription>
                        </Alert>
                    )}

                    {/* Selling Profile */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Selling Profile</CardTitle>
                            <CardDescription>Define what the organization sells. This context is used to generate strategic pivots and match scores.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Form {...sellingProfileForm}>
                                <form onSubmit={sellingProfileForm.handleSubmit(handleSaveSellingProfile)} className="space-y-6">
                                    <div className="grid grid-cols-2 gap-4">
                                        <FormField
                                            control={sellingProfileForm.control}
                                            name="company_name"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Company Name</FormLabel>
                                                    <FormControl><Input {...field} disabled={!isAdmin} /></FormControl>
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
                                                    <FormControl><Input {...field} disabled={!isAdmin} /></FormControl>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                    </div>

                                    <div className="space-y-3">
                                        <div className="flex justify-between items-center">
                                            <h4 className="text-sm font-semibold">Products & Services</h4>
                                            {isAdmin && (
                                                <Button type="button" variant="outline" size="sm" onClick={() => appendProduct({ name: "", description: "" })}>
                                                    <Plus className="w-3 h-3 mr-1" /> Add Product
                                                </Button>
                                            )}
                                        </div>
                                        {productFields.map((field, index) => (
                                            <div key={field.id} className="p-4 border rounded-lg bg-muted/10 space-y-3 relative group">
                                                {isAdmin && (
                                                    <Button type="button" variant="ghost" size="sm" className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity" onClick={() => removeProduct(index)}>
                                                        <Trash2 className="w-3 h-3 text-destructive" />
                                                    </Button>
                                                )}
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                    <FormField
                                                        control={sellingProfileForm.control}
                                                        name={`products.${index}.name`}
                                                        render={({ field }) => (
                                                            <FormItem>
                                                                <FormLabel className="text-xs">Product Name</FormLabel>
                                                                <FormControl><Input {...field} disabled={!isAdmin} className="h-8" /></FormControl>
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
                                                            <FormLabel className="text-xs">Target Roles (comma separated)</FormLabel>
                                                            <FormControl>
                                                                <Input
                                                                    {...field}
                                                                    value={Array.isArray(field.value) ? field.value.join(", ") : (field.value || "")}
                                                                    onChange={e => field.onChange(e.target.value.split(",").map(s => s.trim()))}
                                                                    disabled={!isAdmin}
                                                                    placeholder="Founder, CTO, VP Sales"
                                                                    className="h-8"
                                                                />
                                                            </FormControl>
                                                            <FormMessage />
                                                        </FormItem>
                                                    )}
                                                />
                                                <FormField
                                                    control={sellingProfileForm.control}
                                                    name={`products.${index}.description`}
                                                    render={({ field }) => (
                                                        <FormItem>
                                                            <FormLabel className="text-xs">Value & Capabilities</FormLabel>
                                                            <FormControl><Textarea {...field} disabled={!isAdmin} className="min-h-[60px] resize-none" /></FormControl>
                                                            <FormMessage />
                                                        </FormItem>
                                                    )}
                                                />
                                            </div>
                                        ))}
                                    </div>

                                    {isAdmin && (
                                        <div className="flex justify-end">
                                            <Button type="submit" disabled={isLoading} size="sm" variant="outline">
                                                {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
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
                            <CardDescription>The default research baseline for the entire organization.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Form {...globalIcpForm}>
                                <form onSubmit={globalIcpForm.handleSubmit(handleSaveGlobalICP)} className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <FormField
                                            control={globalIcpForm.control}
                                            name="industry"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Industry</FormLabel>
                                                    <FormControl><Input {...field} disabled={!isAdmin} /></FormControl>
                                                </FormItem>
                                            )}
                                        />
                                        <FormField
                                            control={globalIcpForm.control}
                                            name="job_title"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Job Title</FormLabel>
                                                    <FormControl><Input {...field} disabled={!isAdmin} /></FormControl>
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
                                                <FormControl><Textarea {...field} disabled={!isAdmin} className="h-20" /></FormControl>
                                            </FormItem>
                                        )}
                                    />
                                    {isAdmin && (
                                        <div className="flex justify-end">
                                            <Button type="submit" disabled={isLoading} size="sm" variant="outline">Update Global ICP</Button>
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
                            <CardDescription>Competitor profiles monitored for lead sourcing.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {isAdmin && (
                                    <div className="flex gap-2">
                                        <Input
                                            placeholder="LinkedIn Profile URL"
                                            value={newCompetitorUrl}
                                            onChange={(e) => setNewCompetitorUrl(e.target.value)}
                                            onKeyPress={(e) => e.key === 'Enter' && handleAddCompetitor()}
                                        />
                                        <Button onClick={handleAddCompetitor} disabled={addCompetitorMutation.isPending || !newCompetitorUrl}>
                                            {addCompetitorMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                                        </Button>
                                    </div>
                                )}
                                <div className="space-y-2">
                                    {(competitorsList || []).map((competitor) => (
                                        <div key={competitor.id} className="flex items-center justify-between p-2 border rounded-md bg-muted/20">
                                            <div className="flex items-center gap-2">
                                                <Briefcase className="w-4 h-4 text-muted-foreground" />
                                                <span className="text-sm truncate max-w-[300px]">{competitor.linkedin_url}</span>
                                            </div>
                                            {isAdmin && (
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleDeleteCompetitor(competitor.id)}
                                                    disabled={deleteCompetitorMutation.isPending}
                                                >
                                                    {deleteCompetitorMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4 text-destructive" />}
                                                </Button>
                                            )}
                                        </div>
                                    ))}
                                    {(!competitorsList || competitorsList.length === 0) && <p className="text-sm text-muted-foreground italic">No competitors tracked.</p>}
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Global Keys */}
                    <Card>
                        <CardHeader>
                            <CardTitle>API Integrations</CardTitle>
                            <CardDescription>Organization-wide keys for data providers.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Form {...globalKeysForm}>
                                <form onSubmit={globalKeysForm.handleSubmit(handleSaveGlobalKeys)} className="space-y-4">
                                    <FormField
                                        control={globalKeysForm.control}
                                        name="tavily_api_key"
                                        render={({ field }) => (
                                            <FormItem>
                                                <div className="flex items-center justify-between">
                                                    <FormLabel>Tavily API Key</FormLabel>
                                                    {!isAdmin && <Badge variant="outline" className="text-xs h-5"><Lock className="w-2 h-2 mr-1" /> Admin Only</Badge>}
                                                </div>
                                                <FormControl><Input type="password" {...field} disabled={!isAdmin} /></FormControl>
                                            </FormItem>
                                        )}
                                    />
                                    <div className="flex justify-end pt-2">
                                        {isAdmin && <Button type="submit" disabled={isLoading} size="sm" variant="outline">Update Keys</Button>}
                                    </div>
                                </form>
                            </Form>
                        </CardContent>
                    </Card>

                </TabsContent>
            </Tabs>
        </div >
    )
}
