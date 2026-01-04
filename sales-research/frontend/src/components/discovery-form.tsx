"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import Link from "next/link"
import * as z from "zod"
import { Loader2, Search, CheckSquare, Square } from "lucide-react"

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
import { discoverLeads, checkExistingReports } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { LeadStatus } from "@/components/bulk-analysis-modal"

const findFormSchema = z.object({
    industry: z.string().min(2, "Industry is required"),
    job_title: z.string().min(2, "Job title is required"),
    location: z.string().optional(),
    provider: z.enum(["tavily", "apollo"]),
})

type FindFormValues = {
    industry: string;
    job_title: string;
    location?: string;
    provider: "tavily" | "apollo";
}

export function DiscoveryForm({
    onSelect,
    onBulkSelect,
    leadsStatus
}: {
    onSelect?: (lead: { url: string, website: string, result?: any }) => void,
    onBulkSelect?: (leads: { url: string, website: string }[], options?: { refresh: boolean }) => void,
    leadsStatus?: LeadStatus[]
}) {
    const [isLoading, setIsLoading] = useState(false)
    const [results, setResults] = useState<{ url: string, website: string }[]>([])
    const [selectedUrls, setSelectedUrls] = useState<string[]>([])
    const [refreshAll, setRefreshAll] = useState(false)
    const [existingReports, setExistingReports] = useState<Record<string, any>>({})
    const [error, setError] = useState<string | null>(null)

    const findForm = useForm<FindFormValues>({
        resolver: zodResolver(findFormSchema),
        defaultValues: {
            industry: "",
            job_title: "",
            location: "",
            provider: "tavily",
        }
    })

    const toggleUrl = (url: string) => {
        setSelectedUrls(prev =>
            prev.includes(url)
                ? prev.filter(u => u !== url)
                : [...prev, url]
        )
    }

    const selectAll = () => {
        if (selectedUrls.length === results.length && results.length > 0) {
            setSelectedUrls([])
        } else {
            setSelectedUrls(results.map(r => r.url))
        }
    }

    async function onFindSubmit(values: FindFormValues) {
        setIsLoading(true)
        setError(null)
        setResults([])
        setSelectedUrls([])
        setExistingReports({}) // Clear existing reports on new search
        try {
            const data = await discoverLeads(values)
            if (data.leads) {
                setResults(data.leads)

                // Check for existing reports
                const checkLeads = data.leads.map((l: { url: string, website: string }) => ({ linkedin_url: l.url, website: l.website }));
                const existing = await checkExistingReports(checkLeads);
                setExistingReports(existing);

                if (data.leads.length === 0) {
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
                    <div className="flex items-center gap-4">
                        <h3 className="text-lg font-medium">Results</h3>
                        {results.length > 0 && (
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={selectAll}
                                className="h-8 gap-2"
                            >
                                {selectedUrls.length === results.length ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                                <span className="text-xs uppercase tracking-wider font-semibold">Select All</span>
                            </Button>
                        )}
                    </div>
                    <div className="flex items-center gap-4">
                        <span className="text-sm text-muted-foreground">{results.length} found</span>
                        {selectedUrls.length > 0 && (
                            <div className="flex items-center gap-2">
                                <div className="flex items-center gap-2 px-3 py-1 bg-muted rounded-full border mr-2">
                                    <Checkbox
                                        id="refresh-all"
                                        checked={refreshAll}
                                        onCheckedChange={(checked) => setRefreshAll(!!checked)}
                                    />
                                    <label htmlFor="refresh-all" className="text-[10px] font-medium cursor-pointer">Re-run All</label>
                                </div>
                                <Button size="sm" onClick={() => {
                                    if (onBulkSelect) {
                                        const selectedLeads = results.filter(r => selectedUrls.includes(r.url));
                                        onBulkSelect(selectedLeads, { refresh: refreshAll });
                                    }
                                }}>
                                    Bulk Analyze ({selectedUrls.length})
                                </Button>
                            </div>
                        )}
                    </div>
                </div>
                {results.length > 0 ? (
                    <div className="grid gap-3">
                        {results.map((lead, i) => {
                            const status = leadsStatus?.find(s => s.url === lead.url)?.status
                            return (
                                <Card key={i} className={`overflow-hidden transition-colors ${status === 'completed' ? 'border-green-500/50 bg-green-50/10' : 'hover:border-primary/50'}`}>
                                    <CardContent className="p-4 flex items-center gap-4">
                                        <Checkbox
                                            checked={selectedUrls.includes(lead.url)}
                                            onCheckedChange={() => toggleUrl(lead.url)}
                                        />
                                        <div className="flex-1 min-w-0">
                                            <p className="font-medium truncate text-sm">{lead.url}</p>
                                            {lead.website && <p className="text-[10px] text-muted-foreground truncate opacity-70">{lead.website}</p>}
                                        </div>

                                        {status === 'analyzing' ? (
                                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                <Loader2 className="w-3 h-3 animate-spin" />
                                                Analyzing
                                            </div>
                                        ) : (status === 'completed' || existingReports[lead.url]) ? (
                                            (() => {
                                                const existingData = existingReports[lead.url]?.data;
                                                const sessionResult = leadsStatus?.find(s => s.url === lead.url)?.result;
                                                const finalResult = sessionResult || existingData;

                                                return (
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        className="h-8 border-green-200 hover:bg-green-100 bg-green-50/50 text-green-700 font-bold gap-2"
                                                        onClick={() => onSelect && onSelect({ ...lead, result: finalResult })}
                                                    >
                                                        View Report
                                                    </Button>
                                                );
                                            })()
                                        ) : (
                                            <Button size="sm" variant="outline" onClick={() => onSelect && onSelect(lead)}>
                                                Analyze
                                            </Button>
                                        )}
                                    </CardContent>
                                </Card>
                            )
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
    )
}
