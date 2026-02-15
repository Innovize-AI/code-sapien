"use client"

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Book, FileText, Award, Terminal, RefreshCw, CheckCircle2, AlertCircle, Loader2, ArrowUpRight, Plus, FolderOpen, Star, UploadCloud } from "lucide-react";
import { useEffect, useState, useRef } from "react";
import { StrategyModal, StrategyConfig } from "@/components/knowledge/StrategyModal";
import { ProductModal, ProductConfig } from "@/components/knowledge/ProductModal";
import { fetchKnowledgeNamespaces, syncKnowledgeBase, fetchKnowledgeFiles, ingestKnowledgeFile, NamespaceInfo, KnowledgeFile } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger, SheetFooter } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";


// Add API function placeholders (assuming these are in @/lib/api or will be added)
// import { configureStrategy, fetchStrategy, uploadKnowledgeFile } from "@/lib/api";

// Helper to simulate API call if not exists yet
const configureStrategy = async (config: StrategyConfig) => {
    const res = await fetch('/api/knowledge/configure-strategy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    });
    if (!res.ok) throw new Error('Failed to save strategy');
    return res.json();
};

const fetchStrategy = async () => {
   const res = await fetch('/api/knowledge/strategy');
    if (!res.ok) return { products: [] };
    return res.json();
};

const uploadKnowledgeFile = async (file: File, namespace: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('namespace', namespace);
    
    const res = await fetch('/api/knowledge/upload', {
        method: 'POST',
        body: formData
    });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
};

export default function KnowledgeBasePage() {
    const [namespaces, setNamespaces] = useState<NamespaceInfo[]>([]);
    const [knowledgeFiles, setKnowledgeFiles] = useState<KnowledgeFile[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSyncing, setIsSyncing] = useState(false);
    const [activeTab, setActiveTab] = useState("playbooks");
    const { toast } = useToast();

    // Strategy State
    const [strategyProfile, setStrategyProfile] = useState<any>(null);
    const [selectedFileForStrategy, setSelectedFileForStrategy] = useState<KnowledgeFile | null>(null);
    const [isProductModalOpen, setIsProductModalOpen] = useState(false);
    const [editingProduct, setEditingProduct] = useState<ProductConfig | undefined>(undefined);

    // Form state for ingestion
    const [newFilePath, setNewFilePath] = useState("");
    const [newNamespace, setNewNamespace] = useState("playbooks");
    const [isIngesting, setIsIngesting] = useState(false);
    const [isSheetOpen, setIsSheetOpen] = useState(false);
    
    // Upload State
    const fileInputRef = useRef<HTMLInputElement>(null);

    const loadData = async () => {
        try {
            const [nsData, filesData, strategyData] = await Promise.all([
                fetchKnowledgeNamespaces(),
                fetchKnowledgeFiles(),
                fetchStrategy()
            ]);
            setNamespaces(nsData);
            setKnowledgeFiles(filesData);
            setStrategyProfile(strategyData);
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

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files?.length) return;
        const file = e.target.files[0];
        setIsIngesting(true);
        try {
            await uploadKnowledgeFile(file, newNamespace);
            toast({ title: "File Uploaded", description: "Successfully added and ingested." });
            setIsSheetOpen(false);
            loadData();
        } catch (e) {
            toast({ title: "Upload Failed", description: "Something went wrong.", variant: "destructive" });
        } finally {
            setIsIngesting(false);
        }
    };

    const handleSaveStrategy = async (config: StrategyConfig) => {
        try {
            await configureStrategy(config);
            toast({ title: "Strategy Updated", description: "Pivot configuration saved." });
            loadData();
        } catch (e) {
            toast({ title: "Error", description: "Failed to save strategy.", variant: "destructive" });
        }
    };

    const handleSaveProduct = async (config: ProductConfig) => {
        try {
            // Adapt ProductConfig to StrategyConfig for backend compatibility
            const strategyConfig: StrategyConfig = {
                filename: config.relevant_files[0] || "", // Backend uses this as ID if no product name, but we have product name
                is_strategic_pivot: config.is_strategic_pivot,
                target_roles: config.target_roles,
                product_name: config.product_name,
                relevant_files: config.relevant_files
            };

            await configureStrategy(strategyConfig);
            toast({ title: "Product Saved", description: `${config.product_name} configuration updated.` });
            loadData();
        } catch (e) {
            toast({ title: "Error", description: "Failed to save product.", variant: "destructive" });
        }
    };

    const handleStrategyClick = (file: KnowledgeFile) => {
        setSelectedFileForStrategy(file);
    };

    const getPivotInfo = (filename: string) => {
        if (!strategyProfile?.products) return null;
        return strategyProfile.products.find((p: any) => p.rag_context === filename && p.is_strategic_pivot);
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
    // Solutions are now driven by DB products, not files
    const products = strategyProfile?.products || [];
    const caseStudies = knowledgeFiles.filter(f => f.name.includes("case-study"));
    
    // Categorize files for modal selection
    const availableFilesForModal = knowledgeFiles.map(f => ({
        name: f.name,
        path: f.path,
        type: f.name.includes("case-study") ? 'case-studies' : 'playbooks' as 'playbooks' | 'case-studies'
    }));

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
                                    <SheetTitle>Add Knowledge Asset</SheetTitle>
                                    <SheetDescription>
                                        Upload a markdown file or provide a server path.
                                    </SheetDescription>
                                </SheetHeader>
                                <div className="grid gap-6 py-8">
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
                                    
                                    <div className="border-2 border-dashed rounded-lg p-6 flex flex-col items-center justify-center text-center hover:bg-muted/50 transition-colors cursor-pointer" onClick={() => fileInputRef.current?.click()}>
                                        <UploadCloud className="w-8 h-8 text-muted-foreground mb-2" />
                                        <p className="text-sm font-medium">Click to Upload File</p>
                                        <p className="text-xs text-muted-foreground">Markdown files (.md) supported</p>
                                        <input 
                                            type="file" 
                                            ref={fileInputRef} 
                                            className="hidden" 
                                            accept=".md" 
                                            onChange={handleFileUpload}
                                        />
                                    </div>

                                    <div className="relative">
                                        <div className="absolute inset-0 flex items-center">
                                            <span className="w-full border-t" />
                                        </div>
                                        <div className="relative flex justify-center text-xs uppercase">
                                            <span className="bg-background px-2 text-muted-foreground">Or ingets from path</span>
                                        </div>
                                    </div>

                                    <div className="grid gap-2">
                                        <Label htmlFor="path">Server File Path</Label>
                                        <Input 
                                            id="path" 
                                            placeholder="market_validation/innovize-ai/example.md" 
                                            value={newFilePath}
                                            onChange={(e) => setNewFilePath(e.target.value)}
                                        />
                                    </div>
                                </div>
                                <SheetFooter>
                                    <Button onClick={handleIngest} disabled={isIngesting || !newFilePath} className="w-full">
                                        {isIngesting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                                        Run Ingestion
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
                                <CardTitle className="capitalize">{ns.name === 'solutions' ? 'Products & Services' : ns.name.replace('-', ' ')}</CardTitle>
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
                                <TabsTrigger value="solutions">Products & Services</TabsTrigger>
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
                                <div className="flex justify-between items-center bg-muted/20 p-4 rounded-lg border border-dashed">
                                    <div className="space-y-1">
                                        <h3 className="font-semibold text-primary">Define Your Offerings</h3>
                                        <p className="text-sm text-muted-foreground">Create products/services and link them to your knowledge assets.</p>
                                    </div>
                                    <Button onClick={() => { setEditingProduct(undefined); setIsProductModalOpen(true); }} className="gap-2">
                                        <Plus className="w-4 h-4" /> New Product
                                    </Button>
                                </div>

                                <div className="grid gap-4 md:grid-cols-2">
                                    {products.length > 0 ? products.map((p: any) => (
                                        <Card key={p.name} className="relative overflow-hidden hover:border-primary/50 transition-colors group cursor-pointer" onClick={() => {
                                             setEditingProduct({
                                                product_name: p.name,
                                                description: p.description,
                                                is_strategic_pivot: p.is_strategic_pivot,
                                                target_roles: p.target_roles,
                                                relevant_files: p.relevant_files || []
                                             });
                                             setIsProductModalOpen(true);
                                        }}>
                                            <CardHeader className="pb-2">
                                                <div className="flex justify-between items-start">
                                                    <CardTitle className="text-lg">{p.name}</CardTitle>
                                                    {p.is_strategic_pivot && (
                                                        <Badge className="bg-amber-500/10 text-amber-600 border-amber-500/20 hover:bg-amber-500/20">
                                                            <Star className="w-3 h-3 mr-1 fill-amber-600" /> Hero Product
                                                        </Badge>
                                                    )}
                                                </div>
                                                <CardDescription className="line-clamp-2">{p.description}</CardDescription>
                                            </CardHeader>
                                            <CardContent>
                                                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                                    <span className="flex items-center gap-1">
                                                        <FileText className="w-3 h-3" /> {(p.relevant_files || []).length} Linked Assets
                                                    </span>
                                                    {(p.target_roles || []).length > 0 && (
                                                        <span className="flex items-center gap-1">
                                                            <CheckCircle2 className="w-3 h-3" /> {(p.target_roles || []).length} Roles
                                                        </span>
                                                    )}
                                                </div>
                                            </CardContent>
                                        </Card>
                                    )) : (
                                        <div className="col-span-2">
                                            <EmptyState message="No products defined. Create one to organize your knowledge." />
                                        </div>
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

                {isProductModalOpen && (
                    <ProductModal 
                        isOpen={isProductModalOpen}
                        onClose={() => setIsProductModalOpen(false)}
                        onSave={handleSaveProduct}
                        initialConfig={editingProduct}
                        availableFiles={availableFilesForModal}
                    />
                )}

            </div>
        </DashboardLayout>
    );
}

function DocumentItem({ name, status, date, onStrategyClick, pivotInfo }: { name: string, status: string, date: string, onStrategyClick?: () => void, pivotInfo?: any }) {
    return (
        <div className="flex items-center justify-between p-4 rounded-xl border bg-card hover:bg-muted/50 transition-colors cursor-pointer group">
            <div className="flex items-center gap-4">
                <div className="p-2 rounded-lg bg-primary/10 text-primary">
                    <FileText className="w-5 h-5" />
                </div>
                <div>
                    <h4 className="font-medium group-hover:text-primary transition-colors flex items-center gap-2">
                        {name}
                        {pivotInfo && (
                            <Badge variant="default" className="bg-amber-500/10 text-amber-600 hover:bg-amber-500/20 border-amber-500/20 text-[10px] px-1 py-0 h-5">
                                <Star className="w-3 h-3 mr-1 fill-amber-600" />
                                Hero Product
                            </Badge>
                        )}
                    </h4>
                    <p className="text-xs text-muted-foreground">{date}</p>
                </div>
            </div>
            <div className="flex items-center gap-3">
                <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/20 gap-1 px-2 py-0">
                    <CheckCircle2 className="w-3 h-3" />
                    {status}
                </Badge>
                
                {onStrategyClick && (
                    <Button 
                        variant="ghost" 
                        size="icon" 
                        className={`h-8 w-8 transition-all ${pivotInfo ? 'text-amber-500 opacity-100' : 'text-muted-foreground opacity-20 group-hover:opacity-100'}`}
                        onClick={(e) => { e.stopPropagation(); onStrategyClick(); }}
                        title="Configure Strategic Pivot"
                    >
                        <Star className={`w-4 h-4 ${pivotInfo ? 'fill-current' : ''}`} />
                    </Button>
                )}

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
