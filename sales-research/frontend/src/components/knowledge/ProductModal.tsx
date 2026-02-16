import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Book, Award } from "lucide-react";

interface ProductModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (config: ProductConfig) => Promise<void>;
    initialConfig?: ProductConfig;
    availableFiles: { name: string; path: string; type: 'playbooks' | 'case-studies' | 'solutions' }[];
}

export interface ProductConfig {
    product_name: string;
    description: string;
    is_strategic_pivot: boolean;
    target_roles: string[];
    relevant_files: string[];
}

const COMMON_ROLES = ["Founder", "CEO", "CRO", "VP Sales", "Head of Growth", "CTO", "COO", "Director of Sales"];

export function ProductModal({ isOpen, onClose, onSave, initialConfig, availableFiles }: ProductModalProps) {
    const [isSaving, setIsSaving] = useState(false);
    
    // Form State
    const [name, setName] = useState(initialConfig?.product_name || "");
    const [description, setDescription] = useState(initialConfig?.description || "");
    const [isPivot, setIsPivot] = useState(initialConfig?.is_strategic_pivot || false);
    const [selectedRoles, setSelectedRoles] = useState<string[]>(initialConfig?.target_roles || []);
    const [selectedFiles, setSelectedFiles] = useState<string[]>(initialConfig?.relevant_files || []);

    // Filter files for selection
    const playbooks = availableFiles.filter(f => f.type === 'playbooks');
    const caseStudies = availableFiles.filter(f => f.type === 'case-studies');

    const handleRoleToggle = (role: string) => {
        setSelectedRoles(prev => 
            prev.includes(role) ? prev.filter(r => r !== role) : [...prev, role]
        );
    };

    const handleFileToggle = (fname: string) => {
        setSelectedFiles(prev => 
            prev.includes(fname) ? prev.filter(f => f !== fname) : [...prev, fname]
        );
    };

    const handleSave = async () => {
        if (!name) return;
        setIsSaving(true);
        try {
            await onSave({
                product_name: name,
                description,
                is_strategic_pivot: isPivot,
                target_roles: selectedRoles,
                relevant_files: selectedFiles
            });
            onClose();
        } catch (e) {
            console.error(e);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{initialConfig ? "Edit Product" : "Agile Product Definition"}</DialogTitle>
                    <DialogDescription>
                        Define a product or service offering and attach the relevant knowledge assets.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 py-4">
                    {/* Basic Info */}
                    <div className="grid gap-4">
                        <div className="grid gap-2">
                            <Label htmlFor="name">Product / Service Name</Label>
                            <Input 
                                id="name" 
                                value={name} 
                                onChange={(e) => setName(e.target.value)} 
                                placeholder="e.g. Glial Enterprise, Sales Audit"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="desc">Short Description</Label>
                            <Textarea 
                                id="desc" 
                                value={description} 
                                onChange={(e) => setDescription(e.target.value)} 
                                placeholder="Briefly describe the value proposition..."
                                className="h-20"
                            />
                        </div>
                    </div>

                    {/* Strategic Pivot Config */}
                    <div className="flex items-center justify-between space-x-2 border p-4 rounded-lg bg-amber-500/5 border-amber-500/20">
                        <div className="flex flex-col space-y-1">
                            <Label htmlFor="pivot-mode" className="font-semibold text-amber-700">Strategic Pivot (Hero Mode)</Label>
                            <span className="text-xs text-amber-600/80">
                                If enabled, this will be the primary "Option B" pitch for qualified leads.
                            </span>
                        </div>
                        <Switch id="pivot-mode" checked={isPivot} onCheckedChange={setIsPivot} />
                    </div>

                    {isPivot && (
                        <div className="grid gap-2 animate-in fade-in slide-in-from-top-2">
                            <Label className="mb-2">Target Roles (Who buys this?)</Label>
                            <div className="grid grid-cols-2 gap-2">
                                {COMMON_ROLES.map(role => (
                                    <div key={role} className="flex items-center space-x-2">
                                        <Checkbox 
                                            id={`role-${role}`} 
                                            checked={selectedRoles.includes(role)}
                                            onCheckedChange={() => handleRoleToggle(role)}
                                        />
                                        <label 
                                            htmlFor={`role-${role}`} 
                                            className="text-sm cursor-pointer"
                                        >
                                            {role}
                                        </label>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Asset Linking */}
                    <div className="space-y-4">
                        <h3 className="font-medium text-sm text-foreground/80 border-b pb-2">Knowledge Assets</h3>
                        
                        {/* Playbooks */}
                        <div className="grid gap-2">
                            <Label className="flex items-center gap-2 text-blue-600">
                                <Book className="w-4 h-4" /> Attached Playbooks
                            </Label>
                            <div className="border rounded-md p-2 h-32 overflow-y-auto space-y-2 bg-background/50">
                                {playbooks.length > 0 ? playbooks.map(file => (
                                    <div key={file.path} className="flex items-center space-x-2">
                                        <Checkbox 
                                            id={`pb-${file.name}`} 
                                            checked={selectedFiles.includes(file.name)}
                                            onCheckedChange={() => handleFileToggle(file.name)}
                                        />
                                        <label htmlFor={`pb-${file.name}`} className="text-sm truncate w-full cursor-pointer" title={file.name}>
                                            {file.name}
                                        </label>
                                    </div>
                                )) : <p className="text-xs text-muted-foreground p-2">No playbooks available.</p>}
                            </div>
                        </div>

                        {/* Case Studies */}
                        <div className="grid gap-2">
                            <Label className="flex items-center gap-2 text-orange-600">
                                <Award className="w-4 h-4" /> Attached Case Studies
                            </Label>
                            <div className="border rounded-md p-2 h-32 overflow-y-auto space-y-2 bg-background/50">
                                {caseStudies.length > 0 ? caseStudies.map(file => (
                                    <div key={file.path} className="flex items-center space-x-2">
                                        <Checkbox 
                                            id={`cs-${file.name}`} 
                                            checked={selectedFiles.includes(file.name)}
                                            onCheckedChange={() => handleFileToggle(file.name)}
                                        />
                                        <label htmlFor={`cs-${file.name}`} className="text-sm truncate w-full cursor-pointer" title={file.name}>
                                            {file.name}
                                        </label>
                                    </div>
                                )) : <p className="text-xs text-muted-foreground p-2">No case studies available.</p>}
                            </div>
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={onClose} disabled={isSaving}>Cancel</Button>
                    <Button onClick={handleSave} disabled={isSaving || !name}>
                        {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Save Product
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
