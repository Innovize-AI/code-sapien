import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Loader2 } from "lucide-react";

interface StrategyModalProps {
    isOpen: boolean;
    onClose: () => void;
    filename: string;
    description: string;
    onSave: (config: StrategyConfig) => Promise<void>;
    initialConfig?: StrategyConfig;
    availableFiles: { name: string; path: string }[];
}

export interface StrategyConfig {
    filename: string;
    is_strategic_pivot: boolean;
    target_roles: string[];
    product_name?: string;
    relevant_files: string[];
}

const COMMON_ROLES = ["Founder", "CEO", "CRO", "VP Sales", "Head of Growth", "CTO", "COO", "Director of Sales"];

export function StrategyModal({ isOpen, onClose, filename, description, onSave, initialConfig, availableFiles }: StrategyModalProps) {
    const [isSaving, setIsSaving] = useState(false);
    const [isPivot, setIsPivot] = useState(initialConfig?.is_strategic_pivot || false);
    const [productName, setProductName] = useState(initialConfig?.product_name || filename.replace(".md", "").replace(/-/g, " ").replace(/\b\w/g, l => l.toUpperCase()));
    const [selectedRoles, setSelectedRoles] = useState<string[]>(initialConfig?.target_roles || []);
    const [selectedFiles, setSelectedFiles] = useState<string[]>(initialConfig?.relevant_files || (filename ? [filename] : []));

    const handleRoleToggle = (role: string) => {
        setSelectedRoles(prev => 
            prev.includes(role) 
                ? prev.filter(r => r !== role) 
                : [...prev, role]
        );
    };

    const handleFileToggle = (fname: string) => {
        setSelectedFiles(prev => 
            prev.includes(fname)
                ? prev.filter(f => f !== fname)
                : [...prev, fname]
        );
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            await onSave({
                filename,
                is_strategic_pivot: isPivot,
                target_roles: selectedRoles,
                product_name: productName,
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
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Evaluate as "Hero Product"</DialogTitle>
                    <DialogDescription>
                        Configure "{filename}" as a strategic pivot for your outreach campaigns.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 py-4">
                    <div className="flex items-center justify-between space-x-2 border p-4 rounded-lg bg-muted/50">
                        <div className="flex flex-col space-y-1">
                            <Label htmlFor="pivot-mode" className="font-semibold text-primary">Strategic Pivot Mode</Label>
                            <span className="text-xs text-muted-foreground">
                                If enabled, this product will be pitched as an "Option B" to qualified leads.
                            </span>
                        </div>
                        <Switch id="pivot-mode" checked={isPivot} onCheckedChange={setIsPivot} />
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

                            <div className="grid gap-2">
                                <Label className="mb-2">Target Roles (Strict Filter)</Label>
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
                                                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                                            >
                                                {role}
                                            </label>
                                        </div>
                                    ))}
                                </div>
                                <p className="text-xs text-muted-foreground mt-2">
                                    The agent will ONLY pitch this product if the lead matches one of these roles.
                                </p>
                            </div>

                            <div className="grid gap-2">
                                <Label className="mb-2">Relevant Knowledge Assets</Label>
                                <div className="border rounded-md p-2 h-40 overflow-y-auto space-y-2 bg-background">
                                    {availableFiles.map(file => (
                                        <div key={file.path} className="flex items-center space-x-2">
                                            <Checkbox 
                                                id={`file-${file.name}`} 
                                                checked={selectedFiles.includes(file.name)}
                                                onCheckedChange={() => handleFileToggle(file.name)}
                                            />
                                            <label 
                                                htmlFor={`file-${file.name}`} 
                                                className="text-sm leading-none cursor-pointer truncate w-full"
                                                title={file.name}
                                            >
                                                {file.name}
                                            </label>
                                        </div>
                                    ))}
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">
                                    Select all documents (Playbooks, Case Studies, etc.) that provide context for this product.
                                </p>
                            </div>
                        </>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={onClose} disabled={isSaving}>Cancel</Button>
                    <Button onClick={handleSave} disabled={isSaving}>
                        {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Save Configuration
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
