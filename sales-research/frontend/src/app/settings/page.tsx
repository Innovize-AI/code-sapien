
"use client"

import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Loader2, Save, Plus, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
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
import { saveICP, getICP, IdealProfileData, saveIntegrations, getIntegrations, IntegrationSettings, getCompetitors, addCompetitor, deleteCompetitor, Competitor } from "@/lib/api"

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
})


export default function SettingsPage() {
    const [isLoading, setIsLoading] = useState(false)
    const [isFetching, setIsFetching] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState<string | null>(null)
    const [competitors, setCompetitors] = useState<Competitor[]>([])
    const [newCompetitorUrl, setNewCompetitorUrl] = useState("")
    const [isAddingCompetitor, setIsAddingCompetitor] = useState(false)

    const form = useForm<IdealProfileData>({
        resolver: zodResolver(icpFormSchema),
        defaultValues: {
            industry: "",
            company_size: "",
            revenue: "",
            job_title: "",
            value_proposition: "",
        },
    })

    const keysForm = useForm<IntegrationSettings>({
        resolver: zodResolver(keysFormSchema),
        defaultValues: {
            tavily_api_key: "",
            apollo_api_key: "",
            user_linkedin_url: "",
            company_linkedin_url: "",
            email_config: "",
            slack_webhook_url: "",
        },

    })

    // Load existing settings
    useEffect(() => {
        const loadSettings = async () => {
            try {
                const [icpData, keysData, competitorsData] = await Promise.all([getICP(), getIntegrations(), getCompetitors()])
                if (icpData) {
                    // Start: Sanitize nulls to empty strings
                    const sanitizedIcp = Object.fromEntries(
                        Object.entries(icpData).map(([k, v]) => [k, v ?? ""])
                    ) as IdealProfileData
                    form.reset(sanitizedIcp)
                }
                if (keysData) {
                    const sanitizedKeys = Object.fromEntries(
                        Object.entries(keysData).map(([k, v]) => [k, v ?? ""])
                    ) as IntegrationSettings
                    keysForm.reset(sanitizedKeys)
                }
                if (competitorsData) {
                    setCompetitors(competitorsData)
                }
            } catch (e) {
                console.error("Failed to load settings", e)
            } finally {
                setIsFetching(false)
            }
        }
        loadSettings()
    }, [form, keysForm])

    const handleAddCompetitor = async () => {
        if (!newCompetitorUrl) return
        setIsAddingCompetitor(true)
        try {
            await addCompetitor({ linkedin_url: newCompetitorUrl })
            setNewCompetitorUrl("")
            const updated = await getCompetitors()
            setCompetitors(updated)
        } catch (e) {
            console.error("Failed to add competitor", e)
        } finally {
            setIsAddingCompetitor(false)
        }
    }

    const handleDeleteCompetitor = async (id: string) => {
        try {
            await deleteCompetitor(id)
            setCompetitors(competitors.filter(c => c.id !== id))
        } catch (e) {
            console.error("Failed to delete competitor", e)
        }
    }

    async function onSubmit(values: IdealProfileData) {
        setIsLoading(true)
        setError(null)
        setSuccess(null)
        try {
            await saveICP(values)
            // Save keys as well
            await saveIntegrations(keysForm.getValues())
            setSuccess("Settings saved successfully!")
            setTimeout(() => setSuccess(null), 3000)
        } catch (e: any) {
            setError("Failed to save settings. Please try again.")
        } finally {
            setIsLoading(false)
        }
    }

    if (isFetching) {
        return (
            <div className="h-full flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    return (
        <div className="max-w-4xl mx-auto py-8">
            <h1 className="text-3xl font-bold mb-8">Settings</h1>

            <div className="grid gap-8">
                <Card className="border-border">
                    <CardHeader>
                        <CardTitle>Ideal Customer Profile</CardTitle>
                        <CardDescription>
                            Configure your target audience parameters for automated research.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                                <FormField
                                    control={form.control}
                                    name="industry"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Target Industry</FormLabel>
                                            <FormControl>
                                                <Input placeholder="e.g. Fintech, Healthcare, SaaS" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <div className="grid grid-cols-2 gap-4">
                                    <FormField
                                        control={form.control}
                                        name="company_size"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Company Size</FormLabel>
                                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                                    <FormControl>
                                                        <SelectTrigger>
                                                            <SelectValue placeholder="Any size" />
                                                        </SelectTrigger>
                                                    </FormControl>
                                                    <SelectContent>
                                                        <SelectItem value="1-10">1-10 employees</SelectItem>
                                                        <SelectItem value="11-50">11-50 employees</SelectItem>
                                                        <SelectItem value="51-200">51-200 employees</SelectItem>
                                                        <SelectItem value="201-500">201-500 employees</SelectItem>
                                                        <SelectItem value="500+">500+ employees</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                    <FormField
                                        control={form.control}
                                        name="revenue"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Annual Revenue</FormLabel>
                                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                                    <FormControl>
                                                        <SelectTrigger>
                                                            <SelectValue placeholder="Any revenue" />
                                                        </SelectTrigger>
                                                    </FormControl>
                                                    <SelectContent>
                                                        <SelectItem value="<$1M">Less than $1M</SelectItem>
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
                                    control={form.control}
                                    name="job_title"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Target Job Titles</FormLabel>
                                            <FormControl>
                                                <Input placeholder="e.g. CTO, VP of Engineering, Product Manager" {...field} />
                                            </FormControl>
                                            <FormDescription>Separate multiple titles with commas.</FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="value_proposition"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Value Proposition (Optional)</FormLabel>
                                            <FormControl>
                                                <Textarea
                                                    placeholder="Briefly describe how your product helps these customers..."
                                                    className="resize-none min-h-[80px]"
                                                    {...field}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <div className="pt-4 border-t">
                                    <h3 className="text-lg font-medium mb-4">Integrations</h3>
                                    <div className="grid gap-4">
                                        <FormField
                                            control={keysForm.control}
                                            name="tavily_api_key"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Tavily API Key</FormLabel>
                                                    <FormControl>
                                                        <Input type="password" placeholder="tvly-..." {...field} />
                                                    </FormControl>
                                                    <FormDescription>Required for web search in lead discovery.</FormDescription>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                        <FormField
                                            control={keysForm.control}
                                            name="apollo_api_key"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Apollo API Key (Optional)</FormLabel>
                                                    <FormControl>
                                                        <Input type="password" placeholder="..." {...field} />
                                                    </FormControl>
                                                    <FormDescription>Required if using Apollo as discovery provider.</FormDescription>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4 mt-4">
                                        <FormField
                                            control={keysForm.control}
                                            name="user_linkedin_url"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Your LinkedIn URL</FormLabel>
                                                    <FormControl>
                                                        <Input placeholder="https://linkedin.com/in/yourname" {...field} />
                                                    </FormControl>
                                                    <FormDescription>Used to track lead engagement with your posts.</FormDescription>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                        <FormField
                                            control={keysForm.control}
                                            name="company_linkedin_url"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Company LinkedIn URL</FormLabel>
                                                    <FormControl>
                                                        <Input placeholder="https://linkedin.com/company/yourcompany" {...field} />
                                                    </FormControl>
                                                    <FormDescription>Used to track lead engagement with company posts.</FormDescription>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                    </div>
                                    <div className="grid gap-4 mt-4">
                                        <FormField
                                            control={keysForm.control}
                                            name="slack_webhook_url"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Slack Webhook URL (Optional)</FormLabel>
                                                    <FormControl>
                                                        <Input placeholder="https://hooks.slack.com/services/..." {...field} />
                                                    </FormControl>
                                                    <FormDescription>Used for real-time activity notifications.</FormDescription>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                    </div>
                                </div>


                                <div className="pt-4 border-t">
                                    <h3 className="text-lg font-medium mb-4">Email Configuration (IMAP)</h3>
                                    <FormField
                                        control={keysForm.control}
                                        name="email_config"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>IMAP Configuration (JSON)</FormLabel>
                                                <FormControl>
                                                    <Textarea
                                                        placeholder='{"imap_server": "imap.gmail.com", "email_user": "your@email.com", "email_password": "app-password"}'
                                                        className="resize-none min-h-[100px] font-mono text-sm"
                                                        {...field}
                                                    />
                                                </FormControl>
                                                <FormDescription>
                                                    Provide IMAP server details in JSON format. Required for email history analysis.
                                                </FormDescription>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                </div>

                                {error && <div className="text-red-500 text-sm">{error}</div>}
                                {success && <div className="text-green-500 text-sm">{success}</div>}

                                <Button type="submit" disabled={isLoading}>
                                    {isLoading ? (
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    ) : (
                                        <Save className="mr-2 h-4 w-4" />
                                    )}
                                    Save Changes
                                </Button>
                            </form>
                        </Form>
                    </CardContent>
                </Card>

                <Card className="border-border">
                    <CardHeader>
                        <CardTitle>Competitor List</CardTitle>
                        <CardDescription>
                            Add competitor LinkedIn profiles to track and generate leads from.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            <div className="flex gap-2">
                                <Input
                                    placeholder="LinkedIn Profile URL"
                                    value={newCompetitorUrl}
                                    onChange={(e) => setNewCompetitorUrl(e.target.value)}
                                    onKeyPress={(e) => e.key === 'Enter' && handleAddCompetitor()}
                                />
                                <Button onClick={handleAddCompetitor} disabled={isAddingCompetitor || !newCompetitorUrl}>
                                    {isAddingCompetitor ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                                    <span className="ml-2">Add</span>
                                </Button>
                            </div>
                            <div className="space-y-2">
                                {competitors.map((competitor) => (
                                    <div key={competitor.id} className="flex items-center justify-between p-2 border rounded-md">
                                        <span className="text-sm truncate max-w-[300px]">{competitor.linkedin_url}</span>
                                        <Button variant="ghost" size="sm" onClick={() => handleDeleteCompetitor(competitor.id)}>
                                            <Trash2 className="h-4 w-4 text-destructive" />
                                        </Button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div >
    )
}
