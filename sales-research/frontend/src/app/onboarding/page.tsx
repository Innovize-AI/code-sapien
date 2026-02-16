
"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useRouter } from "next/navigation"
import { Loader2, CheckCircle2 } from "lucide-react"

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
import { saveICP, IdealProfileData, getOnboardingStatus, setOnboardingComplete, getICP } from "@/lib/api"

const icpFormSchema = z.object({
    industry: z.string().min(2, "Industry is required"),
    company_size: z.string().optional(),
    revenue: z.string().optional(),
    job_title: z.string().min(2, "Available job titles are required"),
    value_proposition: z.string().optional(),
})

export default function OnboardingPage() {
    const router = useRouter()
    const [isLoading, setIsLoading] = useState(false)
    const [isChecking, setIsChecking] = useState(true)
    const [error, setError] = useState<string | null>(null)

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

    useState(() => {
        async function checkStatus() {
            try {
                const status = await getOnboardingStatus()
                if (status.complete) {
                    router.push("/")
                    return
                }

                const existingIcp = await getICP()
                if (existingIcp) {
                    form.reset(existingIcp)
                }
            } catch (e) {
                console.error("Failed to check status", e)
            } finally {
                setIsChecking(false)
            }
        }
        checkStatus()
    }, [])

    async function onSubmit(values: IdealProfileData) {
        setIsLoading(true)
        setError(null)
        try {
            await saveICP(values)
            await setOnboardingComplete()
            // Redirect to dashboard after saving
            router.push("/")
        } catch (e: any) {
            setError("Failed to save settings. Please try again.")
        } finally {
            setIsLoading(false)
        }
    }

    if (isChecking) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        )
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-background p-4">
            <div className="w-full max-w-2xl">
                <Card className="border-border shadow-lg">
                    <CardHeader className="space-y-1">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">1</div>
                            <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Onboarding</span>
                        </div>
                        <CardTitle className="text-2xl">Define Your Ideal Customer Profile</CardTitle>
                        <CardDescription>
                            Tell us about your target audience. We'll use this to personalize your sales research reports.
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

                                {error && <div className="text-red-500 text-sm">{error}</div>}

                                <Button type="submit" className="w-full" disabled={isLoading}>
                                    {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    Save & Continue
                                </Button>
                            </form>
                        </Form>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
