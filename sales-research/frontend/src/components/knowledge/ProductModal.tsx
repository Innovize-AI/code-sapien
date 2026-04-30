import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { Book, Award } from "lucide-react";
import { MultiSelect } from "@/components/ui/multi-select";
import { LINKEDIN_INDUSTRIES, JOB_TITLE_OPTIONS } from "@/lib/constants";
import { Spinner } from "@/components/ui/spinner"

interface ProductModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (config: ProductConfig) => Promise<void>;
    initialConfig?: ProductConfig;
    availableFiles: { name: string; path: string; type: 'playbooks' | 'case-studies' | 'solutions' }[];
    isAdmin?: boolean;
}

export interface ProductConfig {
    product_name: string;
    description: string;
    is_strategic_pivot: boolean;
    target_roles: string[];
    target_industries: string[];
    attached_playbooks: string[];
    attached_case_studies: string[];
    relevant_files?: string[];
}


export function ProductModal({ isOpen, onClose, onSave, initialConfig, availableFiles, isAdmin }: ProductModalProps) {
    const [isSaving, setIsSaving] = useState(false);

    // Form State
    const [name, setName] = useState(initialConfig?.product_name || "");
    const [description, setDescription] = useState(initialConfig?.description || "");
    const [isPivot, setIsPivot] = useState(initialConfig?.is_strategic_pivot || false);
    const [selectedRoles, setSelectedRoles] = useState<string[]>(initialConfig?.target_roles || []);
    const [selectedIndustries, setSelectedIndustries] = useState<string[]>(initialConfig?.target_industries || []);
    const [selectedPlaybooks, setSelectedPlaybooks] = useState<string[]>(initialConfig?.attached_playbooks || []);
    const [selectedCaseStudies, setSelectedCaseStudies] = useState<string[]>(initialConfig?.attached_case_studies || []);

    // Filter files for selection
    const playbooks = availableFiles.filter(f => f.type === 'playbooks');
    const caseStudies = availableFiles.filter(f => f.type === 'case-studies');


    const handlePlaybookToggle = (fname: string) => {
        setSelectedPlaybooks(prev =>
            prev.includes(fname) ? prev.filter(f => f !== fname) : [...prev, fname]
        );
    };

    const handleCaseStudyToggle = (fname: string) => {
        setSelectedCaseStudies(prev =>
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
                target_industries: selectedIndustries,
                attached_playbooks: selectedPlaybooks,
                attached_case_studies: selectedCaseStudies,
                relevant_files: [...selectedPlaybooks, ...selectedCaseStudies] // Sync for legacy
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

                    <div className="grid gap-4">
                        <MultiSelect
                            label="Target Roles"
                            options={JOB_TITLE_OPTIONS}
                            value={selectedRoles}
                            onChange={setSelectedRoles}
                            placeholder="Select roles..."
                            allowCustom
                        />

                        <MultiSelect
                            label="Target Industries"
                            options={LINKEDIN_INDUSTRIES}
                            value={selectedIndustries}
                            onChange={setSelectedIndustries}
                            placeholder="Select industries..."
                            allowCustom
                        />
                    </div>

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
                                            checked={selectedPlaybooks.includes(file.name)}
                                            onCheckedChange={() => handlePlaybookToggle(file.name)}
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
                                            checked={selectedCaseStudies.includes(file.name)}
                                            onCheckedChange={() => handleCaseStudyToggle(file.name)}
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
                    <Button onClick={handleSave} disabled={isSaving || !name || !isAdmin}>
                        {isSaving && <Spinner size="md" className="mr-2" />}
                        Save Product
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
