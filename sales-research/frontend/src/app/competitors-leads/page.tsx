"use client"

import { useState, useEffect } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Users, Search, ExternalLink } from "lucide-react"
import { getCompetitors, discoverCompetitorLeads, CompetitorLead, Competitor } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Spinner } from "@/components/ui/spinner"

export default function CompetitorLeadsPage() {
    const [competitors, setCompetitors] = useState<Competitor[]>([])
    const [leads, setLeads] = useState<CompetitorLead[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [isFetching, setIsFetching] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const loadCompetitors = async () => {
            try {
                const data = await getCompetitors()
                setCompetitors(data)
            } catch (e) {
                console.error("Failed to load competitors", e)
            } finally {
                setIsFetching(false)
            }
        }
        loadCompetitors()
    }, [])

    const handleDiscover = async () => {
        if (competitors.length === 0) return

        setIsLoading(true)
        setError(null)
        try {
            const urls = competitors.map(c => c.linkedin_url)
            const res = await discoverCompetitorLeads(urls) as any
            console.log("Discover Leads Response:", res)

            if (res.error) {
                setError(res.error)
                setLeads([])
                return
            }

            const leadsData = res.leads || []
            setLeads(leadsData)
            if (leadsData.length === 0) {
                setError("No leads found from the selected competitors.")
            }
        } catch (e: any) {
            setError(e.message || "Failed to discover leads")
        } finally {
            setIsLoading(false)
        }
    }

    if (isFetching) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-full">
                    <Spinner size="lg" />
                </div>
            </DashboardLayout>
        )
    }

    return (
        <DashboardLayout>
            <div className="flex flex-col gap-8 max-w-6xl mx-auto">
                <div className="flex flex-col gap-2">
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
                        <Users className="w-8 h-8 text-primary" />
                        Competitor Lead Discovery
                    </h1>
                    <p className="text-muted-foreground">
                        Find potential buyers by identifying who's commenting on your competitors' LinkedIn posts.
                    </p>
                </div>

                <div className="flex gap-4 items-center">
                    <div className="text-sm font-medium">
                        Monitoring {competitors.length} competitors
                    </div>
                    <Button onClick={handleDiscover} disabled={isLoading || competitors.length === 0}>
                        {isLoading ? <Spinner size="md" className="mr-2" /> : <Search className="mr-2 h-4 w-4" />}
                        Generate Leads
                    </Button>
                </div>

                {error && <div className="p-4 bg-destructive/10 text-destructive rounded-md">{error}</div>}

                <div className="grid gap-4">
                    {leads.map((lead, index) => (
                        <Card key={index} className="overflow-hidden">
                            <CardContent className="p-6">
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <h3 className="text-lg font-bold">{lead.name}</h3>
                                        <p className="text-sm text-muted-foreground italic">"{lead.comment_text}"</p>
                                    </div>
                                    <div className="flex flex-col items-end gap-2">
                                        <Badge variant="outline">Commented on {lead.competitor}</Badge>
                                        {lead.linkedin_url && (
                                            <Button variant="ghost" size="sm" asChild>
                                                <a href={lead.linkedin_url} target="_blank" rel="noopener noreferrer">
                                                    View Profile <ExternalLink className="ml-2 h-3 w-3" />
                                                </a>
                                            </Button>
                                        )}
                                    </div>
                                </div>
                                <div className="text-xs text-muted-foreground mt-2 border-t pt-2">
                                    Source Post: {lead.source_post}
                                </div>
                            </CardContent>
                        </Card>
                    ))}

                    {leads.length === 0 && !isLoading && (
                        <div className="text-center py-12 border-2 border-dashed rounded-lg">
                            <Users className="mx-auto h-12 w-12 text-muted-foreground mb-4 opacity-20" />
                            <h3 className="text-lg font-medium">No leads generated yet</h3>
                            <p className="text-muted-foreground">Click the "Generate Leads" button to start discovering potential buyers.</p>
                        </div>
                    )}
                </div>
            </div>
        </DashboardLayout>
    )
}
