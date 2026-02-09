"use client"

import { useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Plus, Trash2, Loader2, BarChart3, Users } from "lucide-react"
import { analyzeCompetitors } from "@/lib/api"
import ReactMarkdown from "react-markdown"

export default function CompetitorAnalysisPage() {
    const [urls, setUrls] = useState<string[]>([""])
    const [isLoading, setIsLoading] = useState(false)
    const [report, setReport] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)

    const addUrlField = () => {
        setUrls([...urls, ""])
    }

    const removeUrlField = (index: number) => {
        if (urls.length > 1) {
            const newUrls = [...urls]
            newUrls.splice(index, 1)
            setUrls(newUrls)
        }
    }

    const handleUrlChange = (index: number, value: string) => {
        const newUrls = [...urls]
        newUrls[index] = value
        setUrls(newUrls)
    }

    const handleAnalyze = async () => {
        const filteredUrls = urls.filter(url => url.trim() !== "")
        if (filteredUrls.length === 0) {
            setError("Please enter at least one LinkedIn URL.")
            return
        }

        setIsLoading(true)
        setError(null)
        setReport(null)

        try {
            const res = await analyzeCompetitors(filteredUrls)
            if (res.error) {
                setError(res.error)
            } else {
                setReport(res.report)
            }
        } catch (e: any) {
            setError(e.message || "An error occurred during analysis.")
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <DashboardLayout>
            <div className="flex flex-col gap-8 max-w-4xl mx-auto">
                <div className="flex flex-col gap-2">
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
                        <Users className="w-8 h-8 text-primary" />
                        Competitor Analysis
                    </h1>
                    <p className="text-muted-foreground">
                        Add competitor LinkedIn URLs to get a detailed breakdown of their content strategy, hooks, and CTAs.
                    </p>
                </div>

                <div className="grid gap-8">
                    <Card>
                        <CardHeader>
                            <CardTitle>Competitor Profiles</CardTitle>
                            <CardDescription>
                                Enter the full LinkedIn profile URLs of your competitors.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {urls.map((url, index) => (
                                <div key={index} className="flex gap-2">
                                    <Input
                                        placeholder="https://www.linkedin.com/in/competitor-profile"
                                        value={url}
                                        onChange={(e) => handleUrlChange(index, e.target.value)}
                                        onKeyPress={(e) => e.key === 'Enter' && handleAnalyze()}
                                    />
                                    <Button
                                        variant="outline"
                                        size="icon"
                                        onClick={() => removeUrlField(index)}
                                        disabled={urls.length <= 1}
                                        className="shrink-0"
                                    >
                                        <Trash2 className="w-4 h-4 text-destructive" />
                                    </Button>
                                </div>
                            ))}

                            <div className="flex flex-col sm:flex-row gap-2 pt-2">
                                <Button
                                    variant="outline"
                                    className="grow"
                                    onClick={addUrlField}
                                >
                                    <Plus className="w-4 h-4 mr-2" />
                                    Add Another Competitor
                                </Button>
                                <Button
                                    className="grow sm:grow-0 sm:min-w-[150px]"
                                    onClick={handleAnalyze}
                                    disabled={isLoading}
                                >
                                    {isLoading ? (
                                        <>
                                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                            Analyzing...
                                        </>
                                    ) : (
                                        <>
                                            <BarChart3 className="w-4 h-4 mr-2" />
                                            Start Analysis
                                        </>
                                    )}
                                </Button>
                            </div>

                            {error && (
                                <p className="text-sm font-medium text-destructive mt-2">
                                    {error}
                                </p>
                            )}
                        </CardContent>
                    </Card>

                    {report && (
                        <Card className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <CardHeader className="border-b bg-muted/30">
                                <CardTitle>Analysis Results</CardTitle>
                            </CardHeader>
                            <CardContent className="p-6">
                                <div className="prose prose-sm dark:prose-invert max-w-none">
                                    <ReactMarkdown>{report}</ReactMarkdown>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>
            </div>
        </DashboardLayout>
    )
}
