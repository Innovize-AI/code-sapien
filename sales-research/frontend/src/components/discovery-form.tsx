"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Loader2 } from "lucide-react"

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
import { discoverLeads } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

export function DiscoveryForm({ onSelect }: { onSelect?: (url: string) => void }) {
    const [isLoading, setIsLoading] = useState(false)
    const [results, setResults] = useState<string[]>([])
    const [error, setError] = useState<string | null>(null)

    const findFormSchema = z.object({
        industry: z.string().min(2, "Industry is required"),
        job_title: z.string().min(2, "Job title is required"),
        location: z.string().optional(),
        provider: z.enum(["tavily", "apollo"]).default("tavily"),
    })

    const findForm = useForm<z.infer<typeof findFormSchema>>({
        resolver: zodResolver(findFormSchema),
        defaultValues: {
            industry: "",
            job_title: "",
            location: "",
            provider: "tavily",
        }
    })

    async function onFindSubmit(values: z.infer<typeof findFormSchema>) {
        setIsLoading(true)
        setError(null)
        setResults([])
        try {
            const data = await discoverLeads(values)
            if (data.linkedin_urls) {
                setResults(data.linkedin_urls)
                if (data.linkedin_urls.length === 0) {
                    setError("No leads found matching criteria.")
                }
            } else if (data.error) {
                setError(data.error)
            }
        } catch (e) {
            setError("Failed to fetch leads.")
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="grid gap-6 lg:grid-cols-2">
            <Card className="h-fit">
                <CardHeader>
                    <CardTitle>Search Criteria</CardTitle>
                    <CardDescription>Define your target audience to find new leads.</CardDescription>
                </CardHeader>
                <CardContent>
                    <Form {...findForm}>
                        <form onSubmit={findForm.handleSubmit(onFindSubmit)} className="space-y-4">
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
                            <FormField
                                control={findForm.control}
                                name="provider"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Source Provider</FormLabel>
                                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                                            <FormControl>
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select provider" />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                <SelectItem value="tavily">Web Search (Tavily)</SelectItem>
                                                <SelectItem value="apollo">Apollo Database</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <Button type="submit" disabled={isLoading} className="w-full">
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
                    <h3 className="text-lg font-medium">Results</h3>
                    <span className="text-sm text-muted-foreground">{results.length} found</span>
                </div>
                {results.length > 0 ? (
                    <div className="grid gap-3">
                        {results.map((url, i) => (
                            <Card key={i} className="overflow-hidden">
                                <CardContent className="p-4 flex items-center justify-between gap-4">
                                    <div className="flex-1 min-w-0">
                                        <p className="font-medium truncate text-sm">{url}</p>
                                    </div>
                                    <Button size="sm" variant="secondary" onClick={() => onSelect && onSelect(url)}>
                                        Analyze
                                    </Button>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                ) : (
                    <div className="h-64 border-2 border-dashed rounded-lg flex items-center justify-center text-muted-foreground p-8 text-center">
                        {isLoading ? (
                            <div className="flex flex-col items-center gap-2">
                                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                                <p>Searching for leads...</p>
                            </div>
                        ) : (
                            "Enter search criteria to find matching LinkedIn profiles."
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}
