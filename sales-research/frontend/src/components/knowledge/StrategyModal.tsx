import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { } from "lucide-react";
import { MultiSelect } from "@/components/ui/multi-select";
import { LINKEDIN_INDUSTRIES, JOB_TITLE_OPTIONS } from "@/lib/constants";
import { Spinner } from "@/components/ui/spinner"

interface StrategyModalProps {
    isOpen: boolean;
    onClose: () => void;
    filename: string;
    description: string;
    onSave: (config: StrategyConfig) => Promise<void>;
    initialConfig?: StrategyConfig;
    availableFiles: { name: string; path: string; type: 'playbooks' | 'case-studies' | 'solutions' }[];
}

export interface StrategyConfig {
    filename: string;
    is_strategic_pivot: boolean;
    target_roles: string[];
    target_industries: string[];
    product_name?: string;
    attached_playbooks: string[];
    attached_case_studies: string[];
    relevant_files: string[];
}


export function StrategyModal({ isOpen, onClose, filename, description, onSave, initialConfig, availableFiles }: StrategyModalProps) {
    const [isSaving, setIsSaving] = useState(false);
    const [isPivot, setIsPivot] = useState(initialConfig?.is_strategic_pivot || false);
    const [productName, setProductName] = useState(initialConfig?.product_name || filename.replace(".md", "").replace(/-/g, " ").replace(/\b\w/g, l => l.toUpperCase()));
    const [selectedRoles, setSelectedRoles] = useState<string[]>(initialConfig?.target_roles || []);
    const [selectedIndustries, setSelectedIndustries] = useState<string[]>(initialConfig?.target_industries || []);

    // Categorized selection
    const [selectedPlaybooks, setSelectedPlaybooks] = useState<string[]>(initialConfig?.attached_playbooks || (filename && filename.includes('playbook') ? [filename] : []));
    const [selectedCaseStudies, setSelectedCaseStudies] = useState<string[]>(initialConfig?.attached_case_studies || (filename && filename.includes('case-study') ? [filename] : []));

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
        setIsSaving(true);
        try {
            await onSave({
                filename,
                is_strategic_pivot: isPivot,
                target_roles: selectedRoles,
                target_industries: selectedIndustries,
                product_name: productName,
                attached_playbooks: selectedPlaybooks,
                attached_case_studies: selectedCaseStudies,
                relevant_files: Array.from(new Set([...selectedPlaybooks, ...selectedCaseStudies, filename]))
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
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Evaluate as "Hero Product"</DialogTitle>
                    <DialogDescription>
                        Configure "{filename}" as a strategic pivot for your outreach campaigns.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 py-4 overflow-y-auto max-h-[70vh] pr-2 custom-scrollbar">
                    <div className="flex items-center justify-between space-x-2 border p-4 rounded-lg bg-muted/50">
                        <div className="flex flex-col space-y-1">
                            <Label htmlFor="pivot-mode" className="font-semibold text-primary">Strategic Pivot Mode</Label>
                            <span className="text-xs text-muted-foreground">
                                If enabled, this product will be pitched as an "Option B" to qualified leads.
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
                            usePortal={false}
                        />

                        <MultiSelect
                            label="Target Industries"
                            options={LINKEDIN_INDUSTRIES}
                            value={selectedIndustries}
                            onChange={setSelectedIndustries}
                            placeholder="Select industries..."
                            allowCustom
                            usePortal={false}
                        />
                    </div>

                    {isPivot && (
                        <>
                            <div className="grid gap-2">
                                <Label htmlFor="name">Product Name (for Outreach)</Label>
                                <Input
                                    id="name"
                                    value={productName}
                                    onChange={(e) => setProductName(e.target.value)}
                                />
                            </div>

                            <div className="space-y-4">
                                <Label className="mb-2 block font-semibold">Knowledge Mapping</Label>

                                {/* Playbooks */}
                                <div className="grid gap-2">
                                    <Label className="flex items-center gap-2 text-xs text-blue-600">
                                        Attached Playbooks
                                    </Label>
                                    <div className="border rounded-md p-2 h-32 overflow-y-auto space-y-2 bg-background">
                                        {playbooks.map(file => (
                                            <div key={file.path} className="flex items-center space-x-2">
                                                <Checkbox
                                                    id={`pb-${file.name}`}
                                                    checked={selectedPlaybooks.includes(file.name)}
                                                    onCheckedChange={() => handlePlaybookToggle(file.name)}
                                                />
                                                <label
                                                    htmlFor={`pb-${file.name}`}
                                                    className="text-xs leading-none cursor-pointer truncate w-full"
                                                    title={file.name}
                                                >
                                                    {file.name}
                                                </label>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Case Studies */}
                                <div className="grid gap-2">
                                    <Label className="flex items-center gap-2 text-xs text-orange-600">
                                        Attached Case Studies
                                    </Label>
                                    <div className="border rounded-md p-2 h-32 overflow-y-auto space-y-2 bg-background">
                                        {caseStudies.map(file => (
                                            <div key={file.path} className="flex items-center space-x-2">
                                                <Checkbox
                                                    id={`cs-${file.name}`}
                                                    checked={selectedCaseStudies.includes(file.name)}
                                                    onCheckedChange={() => handleCaseStudyToggle(file.name)}
                                                />
                                                <label
                                                    htmlFor={`cs-${file.name}`}
                                                    className="text-xs leading-none cursor-pointer truncate w-full"
                                                    title={file.name}
                                                >
                                                    {file.name}
                                                </label>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={onClose} disabled={isSaving}>Cancel</Button>
                    <Button onClick={handleSave} disabled={isSaving}>
                        {isSaving && <Spinner size="md" className="mr-2" />}
                        Save Configuration
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
