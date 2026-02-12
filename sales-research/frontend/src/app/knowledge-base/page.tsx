"use client"

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Book, FileText, Award, Terminal, RefreshCw, CheckCircle2, AlertCircle, Loader2, ArrowUpRight, Plus, FolderOpen } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchKnowledgeNamespaces, syncKnowledgeBase, fetchKnowledgeFiles, ingestKnowledgeFile, NamespaceInfo, KnowledgeFile } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger, SheetFooter } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function KnowledgeBasePage() {
    const [namespaces, setNamespaces] = useState<NamespaceInfo[]>([]);
    const [knowledgeFiles, setKnowledgeFiles] = useState<KnowledgeFile[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSyncing, setIsSyncing] = useState(false);
    const [activeTab, setActiveTab] = useState("playbooks");
    const { toast } = useToast();

    // Form state for ingestion
    const [newFilePath, setNewFilePath] = useState("");
    const [newNamespace, setNewNamespace] = useState("playbooks");
    const [isIngesting, setIsIngesting] = useState(false);
    const [isSheetOpen, setIsSheetOpen] = useState(false);

    const loadData = async () => {
        try {
            const [nsData, filesData] = await Promise.all([
                fetchKnowledgeNamespaces(),
                fetchKnowledgeFiles()
            ]);
            setNamespaces(nsData);
            setKnowledgeFiles(filesData);
        } catch (e) {
            console.error("Failed to load knowledge base data", e);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleSync = async () => {
        setIsSyncing(true);
        try {
            await syncKnowledgeBase();
            toast({
                title: "Sync Started",
                description: "The Knowledge Base is being updated in the background.",
            });
            setTimeout(loadData, 5000); // Wait longer for background task
        } catch (e) {
            toast({
                title: "Sync Failed",
                description: "An error occurred while starting the sync.",
                variant: "destructive"
            });
        } finally {
            setIsSyncing(false);
        }
    };

    const handleIngest = async () => {
        if (!newFilePath) return;
        setIsIngesting(true);
        try {
            await ingestKnowledgeFile(newFilePath, newNamespace);
            toast({
                title: "Asset Ingested",
                description: "Successfully added to the Knowledge Base.",
            });
            setIsSheetOpen(false);
            setNewFilePath("");
            loadData();
        } catch (e) {
            toast({
                title: "Ingestion Failed",
                description: "Ensure the path is correct and accessible.",
                variant: "destructive"
            });
        } finally {
            setIsIngesting(false);
        }
    };

    if (isLoading) {
        return (
            <DashboardLayout>
                <div className="flex h-full items-center justify-center min-h-[50vh]">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
            </DashboardLayout>
        );
    }

    const playbooks = knowledgeFiles.filter(f => !f.name.includes("one-pager") && !f.name.includes("offerings"));
    const solutions = knowledgeFiles.filter(f => f.name.includes("one-pager") || f.name.includes("offerings"));
    const caseStudies = knowledgeFiles.filter(f => f.name.includes("case-study"));

    return (
        <DashboardLayout>
            <div className="flex flex-col gap-8">
                {/* Header */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight text-primary">Knowledge Base</h1>
                        <p className="text-muted-foreground mt-1">
                            Manage the strategic intelligence that powers your RAG agents.
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
                            <SheetTrigger asChild>
                                <Button variant="outline" className="gap-2">
                                    <Plus className="w-4 h-4" />
                                    Add Knowledge
                                </Button>
                            </SheetTrigger>
                            <SheetContent>
                                <SheetHeader>
                                    <SheetTitle>Ingest New Asset</SheetTitle>
                                    <SheetDescription>
                                        Add a markdown file to your strategic knowledge base.
                                    </SheetDescription>
                                </SheetHeader>
                                <div className="grid gap-4 py-8">
                                    <div className="grid gap-2">
                                        <Label htmlFor="path">File Path (Relative to root)</Label>
                                        <Input 
                                            id="path" 
                                            placeholder="market_validation/innovize-ai/example.md" 
                                            value={newFilePath}
                                            onChange={(e) => setNewFilePath(e.target.value)}
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <Label htmlFor="namespace">Target Namespace</Label>
                                        <Select value={newNamespace} onValueChange={setNewNamespace}>
                                            <SelectTrigger id="namespace">
                                                <SelectValue placeholder="Select namespace" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="playbooks">Playbooks</SelectItem>
                                                <SelectItem value="solutions">Solutions</SelectItem>
                                                <SelectItem value="case-studies">Case Studies</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                                <SheetFooter>
                                    <Button onClick={handleIngest} disabled={isIngesting || !newFilePath} className="w-full">
                                        {isIngesting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                                        Start Ingestion
                                    </Button>
                                </SheetFooter>
                            </SheetContent>
                        </Sheet>
                        <Button 
                            variant="default" 
                            onClick={handleSync} 
                            disabled={isSyncing}
                            className="gap-2"
                        >
                            <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
                            Sync All Defaults
                        </Button>
                    </div>
                </div>

                {/* Categories Grid */}
                <div className="grid gap-6 md:grid-cols-3">
                    {namespaces.map((ns) => (
                        <Card key={ns.name} className="relative overflow-hidden group hover:shadow-lg transition-all border-primary/10 cursor-pointer" onClick={() => setActiveTab(ns.name)}>
                            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                                {ns.name === 'playbooks' && <Book className="w-16 h-16" />}
                                {ns.name === 'solutions' && <Terminal className="w-16 h-16" />}
                                {ns.name === 'case-studies' && <Award className="w-16 h-16" />}
                            </div>
                            <CardHeader>
                                <div className="flex items-center gap-2 mb-2">
                                    <div className={`p-2 rounded-lg ${
                                        ns.name === 'playbooks' ? 'bg-blue-500/10 text-blue-500' :
                                        ns.name === 'solutions' ? 'bg-purple-500/10 text-purple-500' :
                                        'bg-orange-500/10 text-orange-500'
                                    }`}>
                                        {ns.name === 'playbooks' && <Book className="w-4 h-4" />}
                                        {ns.name === 'solutions' && <Terminal className="w-4 h-4" />}
                                        {ns.name === 'case-studies' && <Award className="w-4 h-4" />}
                                    </div>
                                    <Badge variant="secondary" className="ml-auto bg-primary/5 text-primary border-none">
                                        {ns.count} Vectors
                                    </Badge>
                                </div>
                                <CardTitle className="capitalize">{ns.name.replace('-', ' ')}</CardTitle>
                                <CardDescription>{ns.description}</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <Button variant="ghost" size="sm" className="w-full justify-between group-hover:bg-primary/5" onClick={(e) => { e.stopPropagation(); setActiveTab(ns.name); }}>
                                    Browse Documents
                                    <ArrowUpRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                                </Button>
                            </CardContent>
                        </Card>
                    ))}
                </div>

                {/* Detail View */}
                <Card className="border-primary/5">
                    <CardHeader>
                        <CardTitle>Continuous Intelligence Loop</CardTitle>
                        <CardDescription>
                            The items listed below are currently available in your strategic directory.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                            <TabsList className="grid w-full grid-cols-3 max-w-md mb-8">
                                <TabsTrigger value="playbooks">Playbooks</TabsTrigger>
                                <TabsTrigger value="solutions">Solutions</TabsTrigger>
                                <TabsTrigger value="case-studies">Case Studies</TabsTrigger>
                            </TabsList>
                            
                            <TabsContent value="playbooks" className="space-y-4">
                                <div className="grid gap-4">
                                    {playbooks.length > 0 ? playbooks.map(f => (
                                        <DocumentItem 
                                            key={f.path}
                                            name={f.name} 
                                            status="Available" 
                                            date={`Size: ${(f.size / 1024).toFixed(1)} KB`}
                                        />
                                    )) : (
                                        <EmptyState message="No Playbooks listed in strategic directory." />
                                    )}
                                </div>
                            </TabsContent>
                            
                            <TabsContent value="solutions" className="space-y-4">
                                <div className="grid gap-4">
                                    {solutions.length > 0 ? solutions.map(f => (
                                        <DocumentItem 
                                            key={f.path}
                                            name={f.name} 
                                            status="Available" 
                                            date={`Size: ${(f.size / 1024).toFixed(1)} KB`}
                                        />
                                    )) : (
                                        <EmptyState message="No Solutions listed in strategic directory." />
                                    )}
                                </div>
                            </TabsContent>

                            <TabsContent value="case-studies" className="space-y-4">
                                <div className="grid gap-4">
                                    {caseStudies.length > 0 ? caseStudies.map(f => (
                                        <DocumentItem 
                                            key={f.path}
                                            name={f.name} 
                                            status="Available" 
                                            date={`Size: ${(f.size / 1024).toFixed(1)} KB`}
                                        />
                                    )) : (
                                        <div className="flex flex-col items-center justify-center py-12 text-center border-2 border-dashed rounded-xl bg-muted/30">
                                            <AlertCircle className="w-12 h-12 text-muted-foreground mb-4 opacity-20" />
                                            <h3 className="font-medium text-lg">No Case Studies Found</h3>
                                            <p className="text-sm text-muted-foreground mb-4">Upload industry-specific ROI documents to grounding AI outreach in hard numbers.</p>
                                            <Button variant="outline" size="sm" onClick={() => { setIsSheetOpen(true); setNewNamespace("case-studies"); }}>Add Case Study</Button>
                                        </div>
                                    )}
                                </div>
                            </TabsContent>
                        </Tabs>
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}

function DocumentItem({ name, status, date }: { name: string, status: string, date: string }) {
    return (
        <div className="flex items-center justify-between p-4 rounded-xl border bg-card hover:bg-muted/50 transition-colors cursor-pointer group">
            <div className="flex items-center gap-4">
                <div className="p-2 rounded-lg bg-primary/10 text-primary">
                    <FileText className="w-5 h-5" />
                </div>
                <div>
                    <h4 className="font-medium group-hover:text-primary transition-colors">{name}</h4>
                    <p className="text-xs text-muted-foreground">{date}</p>
                </div>
            </div>
            <div className="flex items-center gap-3">
                <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/20 gap-1 px-2 py-0">
                    <CheckCircle2 className="w-3 h-3" />
                    {status}
                </Badge>
                <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
                    <ArrowUpRight className="w-4 h-4" />
                </Button>
            </div>
        </div>
    );
}

function EmptyState({ message }: { message: string }) {
    return (
        <div className="flex flex-col items-center justify-center py-8 text-center border-2 border-dashed rounded-xl bg-muted/20">
            <FolderOpen className="w-8 h-8 text-muted-foreground mb-2 opacity-20" />
            <p className="text-sm text-muted-foreground">{message}</p>
        </div>
    )
}
