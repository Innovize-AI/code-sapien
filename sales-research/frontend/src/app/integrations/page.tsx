"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { getIntegrations, saveIntegrations, IntegrationSettings, fetchKitForms } from "@/lib/api"
import { CheckCircle2, Circle, Copy, ExternalLink, Mail, Calendar, Layout, FileText, Globe, RefreshCw, Loader2 } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface IntegrationMetadata {
    id: string;
    name: string;
    description: string;
    icon: any;
    webhookPath: string;
    docsUrl: string;
    category: "Form" | "Scheduler" | "Email" | "Other";
}

const INTEGRATIONS: IntegrationMetadata[] = [
    {
        id: "generic",
        name: "Website Form",
        description: "Connect any custom HTML form on your website.",
        icon: Globe,
        webhookPath: "/api/webhooks/generic",
        docsUrl: "#",
        category: "Form"
    },
    {
        id: "calendly",
        name: "Calendly",
        description: "Trigger research when a new meeting is booked.",
        icon: Calendar,
        webhookPath: "/api/webhooks/calendly",
        docsUrl: "https://help.calendly.com/hc/en-us/articles/223195488-Webhooks",
        category: "Scheduler"
    },
    {
        id: "typeform",
        name: "Typeform",
        description: "Run analysis on Typeform survey responses.",
        icon: Layout,
        webhookPath: "/api/webhooks/typeform",
        docsUrl: "https://www.typeform.com/help/a/webhooks-360029581471/",
        category: "Form"
    },
    {
        id: "convertkit",
        name: "ConvertKit",
        description: "Analyze new subscribers automatically.",
        icon: Mail,
        webhookPath: "/api/webhooks/convertkit",
        docsUrl: "https://developers.convertkit.com/#webhooks",
        category: "Email"
    },
    {
        id: "cal",
        name: "Cal.com",
        description: "Integrate with open-source scheduling.",
        icon: Calendar,
        webhookPath: "/api/webhooks/cal",
        docsUrl: "https://docs.cal.com/core-features/webhooks",
        category: "Scheduler"
    },
    {
        id: "hubspot",
        name: "HubSpot",
        description: "Sync deals, past champions, and web visits.",
        icon: Layout, // Or find a more suitable icon if available
        webhookPath: "/api/webhooks/hubspot",
        docsUrl: "https://developers.hubspot.com/docs/api/overview",
        category: "Other"
    }
];

export default function IntegrationsPage() {
    const { toast } = useToast();
    const [settings, setSettings] = useState<IntegrationSettings | null>(null);
    const [configs, setConfigs] = useState<Record<string, { enabled: boolean }>>({});
    const [baseUrl, setBaseUrl] = useState("");
    const [kitForms, setKitForms] = useState<any[]>([]);
    const [isSavingKey, setIsSavingKey] = useState(false);
    const [isLoadingForms, setIsLoadingForms] = useState(false);

    useEffect(() => {
        setBaseUrl(window.location.origin);
        loadSettings();
    }, []);

    const loadSettings = async () => {
        const data = await getIntegrations();
        setSettings(data);
        if (data?.integrations_config) {
            try {
                setConfigs(JSON.parse(data.integrations_config));
            } catch (e) {
                console.error("Failed to parse configurations");
            }
        }
        if (data?.kit_api_key) {
            loadKitForms();
        }
    };

    const loadKitForms = async () => {
        setIsLoadingForms(true);
        try {
            const data = await fetchKitForms();
            setKitForms(data.forms || []);
        } catch (e: any) {
            const message = e.response?.data?.detail || "Failed to fetch Kit forms.";
            toast({
                title: "Integration Error",
                description: message,
                variant: "destructive"
            });
            console.error("Failed to fetch Kit forms", e);
        } finally {
            setIsLoadingForms(false);
        }
    };

    const handleSaveKitKey = async (key: string, isSecret = false) => {
        if (!settings) return;
        setIsSavingKey(true);
        try {
            const updated = { 
                ...settings, 
                [isSecret ? 'kit_api_secret' : 'kit_api_key']: key 
            };
            await saveIntegrations(updated);
            setSettings(updated);
            toast({ title: "Success", description: `${isSecret ? 'Secret' : 'Public'} Key saved.` });
            if (!isSecret && key) loadKitForms();
        } catch (e) {
            toast({ title: "Error", description: "Failed to save API Key.", variant: "destructive" });
        } finally {
            setIsSavingKey(false);
        }
    };

    const toggleIntegration = async (id: string) => {
        const newConfigs = {
            ...configs,
            [id]: { ...configs[id], enabled: !configs[id]?.enabled }
        };
        setConfigs(newConfigs);

        if (settings) {
            const updated = {
                ...settings,
                integrations_config: JSON.stringify(newConfigs)
            };
            await saveIntegrations(updated);
            toast({
                title: "Success",
                description: `${INTEGRATIONS.find(i => i.id === id)?.name} integration updated.`
            });
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        toast({
            title: "Copied!",
            description: "Webhook URL copied to clipboard."
        });
    };

    return (
        <DashboardLayout>
            <div className="space-y-8 max-w-6xl mx-auto p-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Integrations</h1>
                    <p className="text-muted-foreground mt-2">
                        Connect your favorite tools to automate lead research.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {INTEGRATIONS.map((app) => {
                        const isEnabled = configs[app.id]?.enabled;
                        const webhookUrl = `${baseUrl.replace(window.location.port, "8000")}${app.webhookPath}`;

                        return (
                            <Card key={app.id} className="relative overflow-hidden group border-2 transition-all hover:border-primary/50">
                                <CardHeader className="flex flex-row items-center gap-4 space-y-0">
                                    <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
                                        <app.icon className="w-6 h-6" />
                                    </div>
                                    <div className="flex-1">
                                        <CardTitle className="text-lg">{app.name}</CardTitle>
                                        <Badge variant="secondary" className="text-[10px] uppercase font-bold tracking-widest mt-1">
                                            {app.category}
                                        </Badge>
                                    </div>
                                    <Switch
                                        checked={isEnabled}
                                        onCheckedChange={() => toggleIntegration(app.id)}
                                    />
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <CardDescription className="min-h-[40px]">
                                        {app.description}
                                    </CardDescription>

                                    {isEnabled && (
                                        <div className="space-y-2 pt-2 animate-in fade-in slide-in-from-top-2">
                                            <Label className="text-xs text-muted-foreground uppercase font-semibold">
                                                Webhook URL
                                            </Label>
                                            <div className="flex gap-2">
                                                <Input
                                                    readOnly
                                                    value={webhookUrl}
                                                    className="bg-muted text-xs h-8 font-mono"
                                                />
                                                <Button
                                                    size="icon"
                                                    variant="ghost"
                                                    className="h-8 w-8"
                                                    onClick={() => copyToClipboard(webhookUrl)}
                                                >
                                                    <Copy className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    )}

                                    <div className="flex items-center justify-between pt-4 border-t">
                                        <Button variant="link" className="p-0 h-auto text-xs text-muted-foreground" asChild>
                                            <a href={app.docsUrl} target="_blank" rel="noreferrer">
                                                View Docs <ExternalLink className="ml-1 w-3 h-3" />
                                            </a>
                                        </Button>
                                        <div className="flex items-center gap-2">
                                            {isEnabled ? (
                                                <span className="flex items-center gap-1 text-[10px] text-green-500 font-bold uppercase">
                                                    <CheckCircle2 className="w-3 h-3" /> Active
                                                </span>
                                            ) : (
                                                <span className="flex items-center gap-1 text-[10px] text-muted-foreground font-bold uppercase">
                                                    <Circle className="w-3 h-3" /> Inactive
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {app.id === "convertkit" && isEnabled && (
                                        <div className="pt-6 border-t space-y-6 animate-in fade-in slide-in-from-top-4 duration-500">
                                            {/* API Configuration Section */}
                                            <div className="space-y-3 bg-muted/30 p-4 rounded-xl border border-border/50">
                                                <div className="flex items-center justify-between">
                                                    <Label className="text-[11px] uppercase font-bold tracking-wider text-muted-foreground">
                                                        API Configuration
                                                    </Label>
                                                    {settings?.kit_api_key && (
                                                        <Badge variant="outline" className="text-[9px] h-4 bg-green-500/10 text-green-500 border-green-500/20 px-1.5">
                                                            Connected
                                                        </Badge>
                                                    )}
                                                </div>
                                                <div className="space-y-3">
                                                    <Label className="text-xs font-medium">Public API Key (v3)</Label>
                                                    <Input
                                                        type="password"
                                                        placeholder="Paste your Public API key..."
                                                        className="text-xs h-9 bg-background focus-visible:ring-primary/30"
                                                        defaultValue={settings?.kit_api_key || ""}
                                                        onBlur={(e) => handleSaveKitKey(e.target.value, false)}
                                                    />
                                                </div>
                                                <div className="space-y-1.5 pt-2">
                                                    <Label className="text-xs font-medium">API Secret (v3)</Label>
                                                    <Input
                                                        type="password"
                                                        placeholder="Paste your Secret Key..."
                                                        className="text-xs h-9 bg-background focus-visible:ring-primary/30"
                                                        defaultValue={settings?.kit_api_secret || ""}
                                                        onBlur={(e) => handleSaveKitKey(e.target.value, true)}
                                                    />
                                                    <p className="text-[10px] text-muted-foreground">
                                                        Public Key is for listing forms. Secret Key is for tracking activity.
                                                    </p>
                                                </div>
                                            </div>

                                            {/* Forms Activity Section */}
                                            {settings?.kit_api_key && (
                                                <div className="space-y-4">
                                                    <div className="flex items-center justify-between px-1">
                                                        <div className="flex items-center gap-2">
                                                            <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                                                            <Label className="text-[11px] uppercase font-bold tracking-wider text-muted-foreground">
                                                                Active Forms
                                                            </Label>
                                                        </div>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            className="h-7 text-[10px] hover:bg-primary/5 hover:text-primary transition-colors"
                                                            onClick={loadKitForms}
                                                            disabled={isLoadingForms}
                                                        >
                                                            {isLoadingForms ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <RefreshCw className="w-3 h-3 mr-1" />}
                                                            Sync
                                                        </Button>
                                                    </div>

                                                    <div className="grid gap-2 max-h-[300px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent">
                                                        {isLoadingForms && kitForms.length === 0 ? (
                                                            <div className="flex flex-col items-center justify-center py-8 space-y-2 bg-muted/20 rounded-xl border border-dashed border-border/60">
                                                                <Loader2 className="h-5 w-5 animate-spin text-primary/40" />
                                                                <span className="text-[11px] text-muted-foreground">Fetching your forms...</span>
                                                            </div>
                                                        ) : kitForms.length > 0 ? (
                                                            kitForms.slice(0, 10).map((form) => (
                                                                <div
                                                                    key={form.id}
                                                                    className="group/form relative flex flex-col p-3 bg-muted/40 hover:bg-background border border-border/40 hover:border-primary/30 rounded-xl transition-all duration-300 hover:shadow-sm"
                                                                >
                                                                    <div className="flex items-center justify-between mb-1">
                                                                        <span className="text-[12px] font-semibold text-foreground/90 truncate max-w-[140px]">
                                                                            {form.name}
                                                                        </span>
                                                                        <Badge variant="outline" className="text-[9px] h-4 bg-primary/5 text-primary border-primary/20 hover:bg-primary/10 transition-colors">
                                                                            {form.type}
                                                                        </Badge>
                                                                    </div>
                                                                    <div className="flex items-center gap-4 mt-auto">
                                                                        <div className="flex flex-col">
                                                                            <span className="text-[9px] text-muted-foreground/60 uppercase font-bold tracking-tighter">Activity</span>
                                                                            <span className="text-[10px] font-medium text-foreground/70">
                                                                                {new Date(form.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                                                                            </span>
                                                                        </div>
                                                                        <div className="flex flex-col">
                                                                            <span className="text-[9px] text-muted-foreground/60 uppercase font-bold tracking-tighter">Status</span>
                                                                            <span className="text-[10px] font-medium text-green-500/80 flex items-center gap-1">
                                                                                <div className="w-1 h-1 rounded-full bg-green-500" /> Live
                                                                            </span>
                                                                        </div>
                                                                    </div>
                                                                    <div className="absolute right-3 bottom-3 opacity-0 group-hover/form:opacity-100 transition-opacity">
                                                                        <div className="text-[9px] text-primary font-bold uppercase tracking-widest flex items-center gap-1">
                                                                            Ready <CheckCircle2 className="w-2.5 h-2.5" />
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            ))
                                                        ) : (
                                                            <div className="flex flex-col items-center justify-center py-6 space-y-2 bg-muted/10 rounded-xl border border-dashed">
                                                                <p className="text-[10px] text-muted-foreground italic text-balance text-center px-4">
                                                                    No active forms found. Make sure you have created forms in your Kit account.
                                                                </p>
                                                            </div>
                                                        )}
                                                    </div>

                                                    {kitForms.length > 5 && (
                                                        <p className="text-[9px] text-muted-foreground text-center italic">
                                                            Showing {Math.min(kitForms.length, 10)} of {kitForms.length} forms
                                                        </p>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {app.id === "hubspot" && isEnabled && (
                                        <div className="pt-6 border-t space-y-4 animate-in fade-in slide-in-from-top-4 duration-500">
                                            <div className="space-y-3 bg-muted/30 p-4 rounded-xl border border-border/50">
                                                <Label className="text-[11px] uppercase font-bold tracking-wider text-muted-foreground transition-all duration-300 group-hover:text-primary/70">
                                                    HubSpot CRM Configuration
                                                </Label>
                                                <div className="space-y-3 pt-1">
                                                    <div className="space-y-2">
                                                        <Label className="text-[11px] font-semibold text-foreground/80">Private App Access Token</Label>
                                                        <Input
                                                            type="password"
                                                            placeholder="pat-na1-..."
                                                            className="text-xs h-9 bg-background/50 hover:bg-background border-border/40 focus:border-primary/30 focus:ring-primary/5 transition-all duration-200"
                                                            defaultValue={settings?.hubspot_access_token || ""}
                                                            onBlur={(e) => {
                                                                if (settings) {
                                                                    const updated = { ...settings, hubspot_access_token: e.target.value };
                                                                    saveIntegrations(updated).then(() => {
                                                                        setSettings(updated);
                                                                        toast({ title: "Configuration Updated", description: "HubSpot access token has been saved." });
                                                                    });
                                                                }
                                                            }}
                                                        />
                                                    </div>
                                                    <div className="flex items-center justify-between py-2 border-t border-border/20 mt-2">
                                                        <div className="space-y-0.5">
                                                            <Label className="text-[11px] font-semibold">Automated CRM Sync</Label>
                                                            <p className="text-[10px] text-muted-foreground leading-tight">
                                                                Sync deals, champions & visits every 12h.
                                                            </p>
                                                        </div>
                                                        <Switch
                                                            checked={settings?.hubspot_sync_enabled}
                                                            onCheckedChange={(checked) => {
                                                                if (settings) {
                                                                    const updated = { ...settings, hubspot_sync_enabled: checked };
                                                                    saveIntegrations(updated).then(() => {
                                                                        setSettings(updated);
                                                                        toast({ 
                                                                            title: checked ? "Sync Enabled" : "Sync Disabled", 
                                                                            description: `HubSpot background synchronization is now ${checked ? 'active' : 'paused'}.` 
                                                                        });
                                                                    });
                                                                }
                                                            }}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>

                <Card className="bg-primary/5 border-primary/20">
                    <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                            <FileText className="w-4 h-4" /> Pro Tip
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm text-balance leading-relaxed">
                            Most integrations listed here work by sending research data to our AI engine.
                            Ensure your external forms have at least an <strong>email</strong> or <strong>linkedin_url</strong> field
                            to trigger the analysis. Extra fields like "Job Title" or "Use Case" will automatically be detected
                            and used to improve the recommendation quality.
                        </p>
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    )
}
