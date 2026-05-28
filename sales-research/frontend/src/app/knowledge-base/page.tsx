"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Book,
  FileText,
  Award,
  Terminal,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  ArrowUpRight,
  Plus,
  FolderOpen,
  Star,
  UploadCloud,
  Target,
  ChevronRight,
  ChevronDown,
} from "lucide-react";
import { useEffect, useState, useRef } from "react";
import {
  StrategyModal,
  StrategyConfig,
} from "@/components/knowledge/StrategyModal";
import {
  ProductModal,
  ProductConfig,
} from "@/components/knowledge/ProductModal";
import {
  fetchKnowledgeNamespaces,
  syncKnowledgeBase,
  fetchKnowledgeFiles,
  ingestKnowledgeFile,
  NamespaceInfo,
  KnowledgeFile,
  fetchStrategy,
  configureStrategy,
  uploadKnowledgeFile,
  deleteKnowledgeFile,
  getKnowledgeFileContent,
} from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetFooter,
} from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { useAuth } from "@/context/auth-context";
import { Spinner } from "@/components/ui/spinner"

export default function KnowledgeBasePage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [namespaces, setNamespaces] = useState<NamespaceInfo[]>([]);
  const [knowledgeFiles, setKnowledgeFiles] = useState<KnowledgeFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [activeTab, setActiveTab] = useState("playbooks");
  const { toast } = useToast();

  // Strategy State
  const [strategyProfile, setStrategyProfile] = useState<any>(null);
  const [selectedFileForStrategy, setSelectedFileForStrategy] =
    useState<KnowledgeFile | null>(null);
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<
    ProductConfig | undefined
  >(undefined);

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
        fetchStrategy(),
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
        variant: "destructive",
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
        variant: "destructive",
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
      toast({
        title: "File Uploaded",
        description: "Successfully added and ingested.",
      });
      setIsSheetOpen(false);
      loadData();
    } catch (e) {
      toast({
        title: "Upload Failed",
        description: "Something went wrong.",
        variant: "destructive",
      });
    } finally {
      setIsIngesting(false);
    }
  };

  const handleDelete = async (assetId: string) => {
    try {
      await deleteKnowledgeFile(assetId);
      toast({
        title: "Asset Deleted",
        description: "Removed from database, storage, and index.",
      });
      loadData();
    } catch (e) {
      toast({
        title: "Delete Failed",
        description: "An error occurred while deleting the asset.",
        variant: "destructive",
      });
    }
  };

  const handleSaveStrategy = async (config: StrategyConfig) => {
    try {
      await configureStrategy(config);
      toast({
        title: "Strategy Updated",
        description: "Pivot configuration saved.",
      });
      loadData();
    } catch (e) {
      toast({
        title: "Error",
        description: "Failed to save strategy.",
        variant: "destructive",
      });
    }
  };

  const handleSaveProduct = async (config: ProductConfig) => {
    try {
      // Adapt ProductConfig to StrategyConfig for backend compatibility
      const strategyConfig: StrategyConfig = {
        filename: config.relevant_files?.[0] || "", // Backend uses this as ID if no product name, but we have product name
        is_strategic_pivot: config.is_strategic_pivot,
        target_roles: config.target_roles,
        target_industries: config.target_industries,
        product_name: config.product_name,
        relevant_files: config.relevant_files || [],
        attached_playbooks: config.attached_playbooks || [],
        attached_case_studies: config.attached_case_studies || [],
      };

      await configureStrategy(strategyConfig);
      toast({
        title: "Product Saved",
        description: `${config.product_name} configuration updated.`,
      });
      loadData();
    } catch (e) {
      toast({
        title: "Error",
        description: "Failed to save product.",
        variant: "destructive",
      });
    }
  };

  const handleStrategyClick = (file: KnowledgeFile) => {
    setSelectedFileForStrategy(file);
  };

  const getPivotInfo = (filename: string) => {
    if (!strategyProfile?.products) return null;
    return strategyProfile.products.find(
      (p: any) => p.rag_context === filename && p.is_strategic_pivot,
    );
  };

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex h-full items-center justify-center min-h-[50vh]">
          <Spinner size="lg" />
        </div>
      </DashboardLayout>
    );
  }

  // Solutions are now driven by DB products, not files
  const products = strategyProfile?.products || [];

  const caseStudies = knowledgeFiles.filter(
    (f) => f.namespace === "case-studies" || f.namespace === "casestudies"
  );

  const playbooks = knowledgeFiles.filter(
    (f) => f.namespace === "playbooks" || !f.namespace // fallback for old data if any
  );

  // Categorize files for modal selection
  const availableFilesForModal = knowledgeFiles.map((f) => ({
    name: f.name,
    path: f.path || f.name,
    type: (f.namespace === "case-studies" || f.namespace === "casestudies")
      ? "case-studies"
      : ("playbooks" as "playbooks" | "case-studies"),
  }));

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-primary">
              Knowledge Base
            </h1>
            <p className="text-muted-foreground mt-1">
              Manage the strategic intelligence that powers your RAG agents.
            </p>
          </div>
          {isAdmin && (
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
                      <Select
                        value={newNamespace}
                        onValueChange={setNewNamespace}
                      >
                        <SelectTrigger id="namespace">
                          <SelectValue placeholder="Select namespace" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="playbooks">Playbooks</SelectItem>
                          <SelectItem value="solutions">Solutions</SelectItem>
                          <SelectItem value="case-studies">
                            Case Studies
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div
                      className="border-2 border-dashed rounded-lg p-6 flex flex-col items-center justify-center text-center hover:bg-muted/50 transition-colors cursor-pointer"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <UploadCloud className="w-8 h-8 text-muted-foreground mb-2" />
                      <p className="text-sm font-medium">
                        Click to Upload File
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Markdown files (.md) supported
                      </p>
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
                        <span className="bg-background px-2 text-muted-foreground">
                          Or ingets from path
                        </span>
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
                    <Button
                      onClick={handleIngest}
                      disabled={isIngesting || !newFilePath}
                      className="w-full"
                    >
                      {isIngesting && (
                        <Spinner size="md" className="mr-2" />
                      )}
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
                <RefreshCw
                  className={`w-4 h-4 ${isSyncing ? "animate-spin" : ""}`}
                />
                Sync All Defaults
              </Button>
            </div>
          )}
        </div>

        {/* Categories Grid */}
        <div className="grid gap-6 md:grid-cols-3">
          {namespaces.map((ns) => (
            <Card
              key={ns.name}
              className="relative overflow-hidden group hover:shadow-lg transition-all border-primary/10 cursor-pointer"
              onClick={() => setActiveTab(ns.name)}
            >
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                {ns.name === "playbooks" && <Book className="w-16 h-16" />}
                {ns.name === "solutions" && <Terminal className="w-16 h-16" />}
                {ns.name === "case-studies" && <Award className="w-16 h-16" />}
              </div>
              <CardHeader>
                <div className="flex items-center gap-2 mb-2">
                  <div
                    className={`p-2 rounded-lg ${
                      ns.name === "playbooks"
                        ? "bg-blue-500/10 text-blue-500"
                        : ns.name === "solutions"
                          ? "bg-purple-500/10 text-purple-500"
                          : "bg-orange-500/10 text-orange-500"
                    }`}
                  >
                    {ns.name === "playbooks" && <Book className="w-4 h-4" />}
                    {ns.name === "solutions" && (
                      <Terminal className="w-4 h-4" />
                    )}
                    {ns.name === "case-studies" && (
                      <Award className="w-4 h-4" />
                    )}
                  </div>
                  <Badge
                    variant="secondary"
                    className="ml-auto bg-primary/5 text-primary border-none"
                  >
                    {ns.count} Vectors
                  </Badge>
                </div>
                <CardTitle className="capitalize">
                  {ns.name === "solutions"
                    ? "Products & Services"
                    : ns.name.replace("-", " ")}
                </CardTitle>
                <CardDescription>{ns.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-between group-hover:bg-primary/5"
                  onClick={(e) => {
                    e.stopPropagation();
                    setActiveTab(ns.name);
                  }}
                >
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
              The items listed below are currently available in your strategic
              directory.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs
              value={activeTab}
              onValueChange={setActiveTab}
              className="w-full"
            >
              <TabsList className="grid w-full grid-cols-3 max-w-md mb-8">
                <TabsTrigger value="playbooks">Playbooks</TabsTrigger>
                <TabsTrigger value="solutions">Products & Services</TabsTrigger>
                <TabsTrigger value="case-studies">Case Studies</TabsTrigger>
              </TabsList>

              <TabsContent value="playbooks" className="space-y-4">
                <div className="grid gap-4">
                  {playbooks.length > 0 ? (
                    playbooks.map((f) => (
                      <DocumentItem
                        key={f.id || f.path || f.name}
                        name={f.name}
                        status="Available"
                        date={f.storage_path || (typeof f.modified === 'string' ? new Date(f.modified).toLocaleDateString() : `Size: ${(f.size / 1024).toFixed(1)} KB`)}
                        onStrategyClick={() => {
                          setSelectedFileForStrategy(f);
                        }}
                        pivotInfo={strategyProfile?.products?.find((p: any) => p.relevant_files?.includes(f.name))?.is_strategic_pivot}
                        isAdmin={isAdmin}
                        assetMetadata={f.asset_metadata}
                        onDelete={f.id ? () => handleDelete(f.id!) : undefined}
                        assetId={f.id}
                      />
                    ))
                  ) : (
                    <EmptyState message="No Playbooks listed in strategic directory." />
                  )}
                </div>
              </TabsContent>

              <TabsContent value="solutions" className="space-y-4">
                <div className="flex justify-between items-center bg-muted/20 p-4 rounded-lg border border-dashed">
                  <div className="space-y-1">
                    <h3 className="font-semibold text-primary">
                      Define Your Offerings
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      Create products/services and link them to your knowledge
                      assets.
                    </p>
                  </div>
                  {isAdmin && (
                    <Button
                      onClick={() => {
                        setEditingProduct(undefined);
                        setIsProductModalOpen(true);
                      }}
                      className="gap-2"
                    >
                      <Plus className="w-4 h-4" /> New Product
                    </Button>
                  )}
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  {products.length > 0 ? (
                    products.map((p: any) => (
                      <Card
                        key={p.name}
                        className="relative overflow-hidden hover:border-primary/50 transition-colors group cursor-pointer"
                        onClick={() => {
                          if (!isAdmin) return;
                          setEditingProduct({
                            product_name: p.name,
                            description: p.description,
                            is_strategic_pivot: p.is_strategic_pivot,
                            target_roles: p.target_roles,
                            target_industries: p.target_industries || [],
                            attached_playbooks: p.attached_playbooks || [],
                            attached_case_studies:
                              p.attached_case_studies || [],
                            relevant_files: p.relevant_files || [],
                          });
                          setIsProductModalOpen(true);
                        }}
                      >
                        <CardHeader className="pb-2">
                          <div className="flex justify-between items-start">
                            <CardTitle className="text-lg">{p.name}</CardTitle>
                            {p.is_strategic_pivot && (
                              <Badge className="bg-amber-500/10 text-amber-600 border-amber-500/20 hover:bg-amber-500/20">
                                <Star className="w-3 h-3 mr-1 fill-amber-600" />{" "}
                                Hero Product
                              </Badge>
                            )}
                          </div>
                          <CardDescription className="line-clamp-2">
                            {p.description}
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="flex items-center gap-4 text-xs text-muted-foreground">
                            <span
                              className="flex items-center gap-1"
                              title="Playbooks"
                            >
                              <Book className="w-3 h-3 text-blue-500" />{" "}
                              {(p.attached_playbooks || []).length}
                            </span>
                            <span
                              className="flex items-center gap-1"
                              title="Case Studies"
                            >
                              <Award className="w-3 h-3 text-orange-500" />{" "}
                              {(p.attached_case_studies || []).length}
                            </span>
                            {(p.target_roles || []).length > 0 && (
                              <span className="flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3" />{" "}
                                {(p.target_roles || []).length} Roles
                              </span>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    ))
                  ) : (
                    <div className="col-span-2">
                      <EmptyState message="No products defined. Create one to organize your knowledge." />
                    </div>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="case-studies" className="space-y-4">
                <div className="grid gap-4">
                  {caseStudies.length > 0 ? (
                    caseStudies.map((f) => (
                      <DocumentItem
                        key={f.id || f.path || f.name}
                        name={f.name}
                        status="Available"
                        date={f.storage_path || (typeof f.modified === 'string' ? new Date(f.modified).toLocaleDateString() : `Size: ${(f.size / 1024).toFixed(1)} KB`)}
                        onStrategyClick={() => {
                          setSelectedFileForStrategy(f);
                        }}
                        pivotInfo={strategyProfile?.products?.find((p: any) => p.relevant_files?.includes(f.name))?.is_strategic_pivot}
                        isAdmin={isAdmin}
                        assetMetadata={f.asset_metadata}
                        onDelete={f.id ? () => handleDelete(f.id!) : undefined}
                        assetId={f.id}
                      />
                    ))
                  ) : (
                    <div className="flex flex-col items-center justify-center py-12 text-center border-2 border-dashed rounded-xl bg-muted/30">
                      <AlertCircle className="w-12 h-12 text-muted-foreground mb-4 opacity-20" />
                      <h3 className="font-medium text-lg">
                        No Case Studies Found
                      </h3>
                      <p className="text-sm text-muted-foreground mb-4">
                        Upload industry-specific ROI documents to grounding AI
                        outreach in hard numbers.
                      </p>
                      {isAdmin && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setIsSheetOpen(true);
                            setNewNamespace("case-studies");
                          }}
                        >
                          Add Case Study
                        </Button>
                      )}
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
            isAdmin={isAdmin}
          />
        )}

        {selectedFileForStrategy && (
          <StrategyModal
            isOpen={!!selectedFileForStrategy}
            onClose={() => setSelectedFileForStrategy(null)}
            filename={selectedFileForStrategy.name}
            description={selectedFileForStrategy.description || ""}
            onSave={handleSaveStrategy}
            initialConfig={strategyProfile?.products?.find((p: any) => 
                p.filename === selectedFileForStrategy.name || 
                p.relevant_files?.includes(selectedFileForStrategy.name)
            )}
            availableFiles={availableFilesForModal}
          />
        )}
      </div>
    </DashboardLayout>
  );
}

function DocumentItem({
  name,
  status,
  date,
  onStrategyClick,
  pivotInfo,
  isAdmin,
  assetMetadata,
  onDelete,
  isDeleting,
  assetId,
}: {
  name: string;
  status: string;
  date: string;
  onStrategyClick?: () => void;
  pivotInfo?: any;
  isAdmin?: boolean;
  assetMetadata?: Record<string, any>;
  onDelete?: () => void;
  isDeleting?: boolean;
  assetId?: string;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [content, setContent] = useState<string | null>(null);
  const [isLoadingContent, setIsLoadingContent] = useState(false);

  const toggleExpand = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!isExpanded && !content && assetId) {
      setIsLoadingContent(true);
      try {
        const res = await getKnowledgeFileContent(assetId);
        setContent(res.content);
      } catch (e) {
        console.error("Failed to fetch content", e);
      } finally {
        setIsLoadingContent(false);
      }
    }
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="space-y-2">
      <div 
        className={`flex items-center justify-between p-4 rounded-xl border bg-card hover:bg-muted/50 transition-colors cursor-pointer group ${isExpanded ? 'border-primary/30 bg-muted/20' : ''}`}
        onClick={toggleExpand}
      >
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 p-0 hover:bg-transparent"
              onClick={toggleExpand}
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              )}
            </Button>
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <div>
            <h4 className="font-medium group-hover:text-primary transition-colors flex items-center gap-2">
              {name}
              {pivotInfo && (
                <Badge
                  variant="default"
                  className="bg-amber-500/10 text-amber-600 hover:bg-amber-500/20 border-amber-500/20 text-[10px] px-1 py-0 h-5"
                >
                  <Star className="w-3 h-3 mr-1 fill-amber-600" />
                  Hero Product
                </Badge>
              )}
            </h4>
            <div className="flex items-center gap-2 mt-1">
              <p className="text-xs text-muted-foreground">{date}</p>
              {assetMetadata?.product && (
                <>
                  <span className="text-muted-foreground/30">•</span>
                  <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 border-primary/10 bg-primary/5">
                    {assetMetadata.product}
                  </Badge>
                </>
              )}
              {assetMetadata?.industry && (
                <>
                  <span className="text-muted-foreground/30">•</span>
                  <span className="text-[10px] text-muted-foreground italic">
                    {assetMetadata.industry}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {onDelete && isAdmin && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={(e) => {
                e.stopPropagation();
                if (confirm(`Are you sure you want to delete ${name}? This will remove it from the DB, Storage, and Pinecone.`)) {
                  onDelete();
                }
              }}
              disabled={isDeleting}
            >
              {isDeleting ? <Spinner size="md" /> : <Plus className="w-4 h-4 rotate-45" />}
            </Button>
          )}
          
          <Badge
            variant="outline"
            className="bg-green-500/10 text-green-600 border-green-500/20 gap-1 px-2 py-0"
          >
            <CheckCircle2 className="w-3 h-3" />
            {status}
          </Badge>
          
          {onStrategyClick && (
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onStrategyClick();
              }}
              className="h-8 gap-1.5"
            >
              <Target className="w-3.5 h-3.5" />
              Strategy
            </Button>
          )}
        </div>
      </div>
      
      {isExpanded && (
        <div className="mx-6 p-6 rounded-xl border bg-muted/30 animate-in slide-in-from-top-2 duration-200">
          {isLoadingContent ? (
            <div className="flex items-center justify-center py-8 gap-2 text-muted-foreground text-sm">
              <Spinner size="md" />
              Fetching content from storage...
            </div>
          ) : content ? (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <pre className="whitespace-pre-wrap font-sans text-xs leading-relaxed text-muted-foreground overflow-auto max-h-[400px]">
                {content}
              </pre>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground text-sm">
              No content available for this file.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center border-2 border-dashed rounded-xl bg-muted/20">
      <FolderOpen className="w-8 h-8 text-muted-foreground mb-2 opacity-20" />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}
