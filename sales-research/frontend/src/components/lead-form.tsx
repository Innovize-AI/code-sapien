"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Loader2, XCircle } from "lucide-react"
import { useBulkAnalysis } from "@/context/bulk-analysis-context"

import { Button } from "@/components/ui/button"
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { generateResearch, LeadData } from "@/lib/api"

const formSchema = z.object({
    linkedin_url: z.string().optional(),
    website: z.string().optional(),
    email: z.string().email({ message: "Please enter a valid email." }).optional().or(z.literal("")),
    lead_source: z.string().optional(),
    download_marketing_material: z.boolean().default(false),
    demo_requested: z.boolean().default(false),
    referral_partner_introduction: z.boolean().default(false),
    project_urgency: z.string().optional(),
    refresh: z.boolean().default(false),
}).refine(data => {
    const hasLinkedin = !!data.linkedin_url && data.linkedin_url.length > 0;
    const hasWebsite = !!data.website && data.website.length > 0;
    return hasLinkedin || hasWebsite;
}, {
    message: "Either LinkedIn URL or Website URL is required.",
    path: ["linkedin_url"],
});

type FormValues = z.infer<typeof formSchema>;

interface LeadFormProps {
    onSuccess: (data: any) => void
    defaultUrl?: string
    defaultWebsite?: string
}

export function LeadForm({ onSuccess, defaultUrl, defaultWebsite }: LeadFormProps) {
    const [isLoading, setIsLoading] = useState(false)
    const [statusMessage, setStatusMessage] = useState("")
    const [error, setError] = useState<string | null>(null)
    const { addLeadStatus } = useBulkAnalysis()

    const form = useForm({
        resolver: zodResolver(formSchema),
        defaultValues: {
            linkedin_url: defaultUrl || "",
            website: defaultWebsite || "",
            email: "",
            lead_source: "",
            download_marketing_material: false,
            demo_requested: false,
            referral_partner_introduction: false,
            project_urgency: "",
            refresh: false,
        },
    })

    async function onSubmit(values: FormValues) {
        setIsLoading(true)
        setError(null)
        setStatusMessage("Initializing...")

        // Add to global context as pending
        addLeadStatus({ url: values.linkedin_url || values.website || "Single Analysis", status: "pending" })

        try {
            const urgencyMap: Record<string, number> = {
                "Low": 1,
                "Medium": 2,
                "High": 3
            }

            const apiData: LeadData = {
                linkedin_url: values.linkedin_url,
                website: values.website,
                email: values.email || undefined,
                lead_source: values.lead_source || undefined,
                download_marketing_material: values.download_marketing_material,
                demo_requested: values.demo_requested,
                referral_partner_introduction: values.referral_partner_introduction,
                project_urgency: values.project_urgency ? urgencyMap[values.project_urgency] : undefined,
                refresh: values.refresh,
            }

            const result = await generateResearch(apiData, (status) => {
                setStatusMessage(status)
                // Update global context with progress
                addLeadStatus({
                    url: values.linkedin_url || values.website || "Single Analysis",
                    status: "analyzing",
                    currentStep: status
                })
            })

            // Update global context with completion
            addLeadStatus({
                url: values.linkedin_url || values.website || "Single Analysis",
                status: "completed",
                result: result
            })

            onSuccess(result)
        } catch (error: any) {
            console.error("Error generating research:", error)
            setError(error.message || "Failed to generate research. Please try again.")
            // Update global context with error
            addLeadStatus({
                url: values.linkedin_url || values.website || "Single Analysis",
                status: "error",
                error: error.message
            })
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                <FormField
                    control={form.control}
                    name="linkedin_url"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>LinkedIn URL</FormLabel>
                            <FormControl>
                                <Input placeholder="https://www.linkedin.com/in/..." {...field} />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />
                <FormField
                    control={form.control}
                    name="website"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Website URL</FormLabel>
                            <FormControl>
                                <Input placeholder="https://example.com" {...field} />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />
                <FormField
                    control={form.control}
                    name="email"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Email (Optional)</FormLabel>
                            <FormControl>
                                <Input placeholder="email@example.com" {...field} />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField
                        control={form.control}
                        name="lead_source"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Lead Source</FormLabel>
                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select a source" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        <SelectItem value="Referral">Referral</SelectItem>
                                        <SelectItem value="Inbound Marketing">Inbound Marketing</SelectItem>
                                        <SelectItem value="Paid Ads">Paid Ads</SelectItem>
                                        <SelectItem value="Cold Outreach">Cold Outreach</SelectItem>
                                    </SelectContent>
                                </Select>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="project_urgency"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Project Urgency</FormLabel>
                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select urgency" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        <SelectItem value="Low">Low</SelectItem>
                                        <SelectItem value="Medium">Medium</SelectItem>
                                        <SelectItem value="High">High</SelectItem>
                                    </SelectContent>
                                </Select>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <div className="flex flex-col space-y-2">
                    <FormField
                        control={form.control}
                        name="download_marketing_material"
                        render={({ field }) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                <FormControl>
                                    <Checkbox
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                                <div className="space-y-1 leading-none">
                                    <FormLabel>
                                        Downloaded Marketing Material
                                    </FormLabel>
                                </div>
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={form.control}
                        name="demo_requested"
                        render={({ field }) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                <FormControl>
                                    <Checkbox
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                                <div className="space-y-1 leading-none">
                                    <FormLabel>
                                        Demo Requested
                                    </FormLabel>
                                </div>
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={form.control}
                        name="referral_partner_introduction"
                        render={({ field }) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                <FormControl>
                                    <Checkbox
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                                <div className="space-y-1 leading-none">
                                    <FormLabel>
                                        Referral Partner Introduction
                                    </FormLabel>
                                </div>
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={form.control}
                        name="refresh"
                        render={({ field }) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4 bg-primary/5 border-primary/20">
                                <FormControl>
                                    <Checkbox
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                                <div className="space-y-1 leading-none">
                                    <FormLabel className="text-primary font-semibold">
                                        Refresh / Re-run Research
                                    </FormLabel>
                                    <p className="text-[10px] text-muted-foreground">
                                        Check this to bypass existing report and get fresh data.
                                    </p>
                                </div>
                            </FormItem>
                        )}
                    />
                </div>

                {error && (
                    <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg space-y-3">
                        <div className="flex items-center justify-between">
                            <p className="text-sm font-medium text-red-500 flex items-center gap-2">
                                <XCircle className="w-4 h-4" />
                                Research Error
                            </p>
                        </div>
                        <p className="text-sm text-red-500/80 ml-6">{error}</p>
                        
                        {error.includes("Selling Profile") && (
                            <div className="ml-6 pt-2">
                                <Button 
                                    variant="outline" 
                                    size="sm" 
                                    className="text-xs bg-red-500/5 border-red-500/20 hover:bg-red-500/10 text-red-600"
                                    onClick={() => window.location.href = "/settings?tab=organization"}
                                >
                                    Configure Selling Profile
                                </Button>
                            </div>
                        )}
                    </div>
                )}



                <Button type="submit" disabled={isLoading} className="w-full">
                    {isLoading ? (
                        <div className="flex items-center gap-2">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span>{statusMessage || "Analyzing..."}</span>
                        </div>
                    ) : (
                        "Generate Research"
                    )}
                </Button>
            </form>
        </Form>
    )
}
