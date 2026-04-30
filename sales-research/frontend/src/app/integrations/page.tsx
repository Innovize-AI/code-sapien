"use client";

import { useEffect, useState } from "react";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  getIntegrations,
  saveIntegrations,
  IntegrationSettings,
  fetchKitForms,
  API_URL,
} from "@/lib/api";
import {
  CheckCircle2,
  Copy,
  ExternalLink,
  Mail,
  Calendar,
  Layout,
  Globe,
  RefreshCw,
  Slack,
  UserCheck,
  Lock,
  Plug,
  FileText,
  Info,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useConfig } from "@/context/config-context";
import { Spinner } from "@/components/ui/spinner"

type Category = "All" | "Form" | "Scheduler" | "Email" | "CRM & Tools";

interface IntegrationMetadata {
  id: string;
  name: string;
  description: string;
  icon: any;
  webhookPath: string;
  docsUrl: string;
  category: Exclude<Category, "All">;
  accentColor: string;
  iconBg: string;
}

const INTEGRATIONS: IntegrationMetadata[] = [
  {
    id: "generic",
    name: "Website Form",
    description: "Connect any custom HTML form on your website to trigger AI research automatically.",
    icon: Globe,
    webhookPath: "/api/webhooks/generic",
    docsUrl: "#",
    category: "Form",
    accentColor: "bg-blue-500",
    iconBg: "bg-blue-500/10 text-blue-500",
  },
  {
    id: "typeform",
    name: "Typeform",
    description: "Run deep analysis on Typeform survey responses as they come in.",
    icon: Layout,
    webhookPath: "/api/webhooks/typeform",
    docsUrl: "https://www.typeform.com/help/a/webhooks-360029581471/",
    category: "Form",
    accentColor: "bg-zinc-700",
    iconBg: "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400",
  },
  {
    id: "calendly",
    name: "Calendly",
    description: "Trigger lead research the moment a new meeting is booked.",
    icon: Calendar,
    webhookPath: "/api/webhooks/calendly",
    docsUrl: "https://help.calendly.com/hc/en-us/articles/223195488-Webhooks",
    category: "Scheduler",
    accentColor: "bg-orange-500",
    iconBg: "bg-orange-500/10 text-orange-500",
  },
  {
    id: "cal",
    name: "Cal.com",
    description: "Integrate with open-source scheduling for automated research on bookings.",
    icon: Calendar,
    webhookPath: "/api/webhooks/cal",
    docsUrl: "https://docs.cal.com/core-features/webhooks",
    category: "Scheduler",
    accentColor: "bg-zinc-900",
    iconBg: "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400",
  },
  {
    id: "convertkit",
    name: "ConvertKit",
    description: "Analyze and score new subscribers automatically as they join your list.",
    icon: Mail,
    webhookPath: "/api/webhooks/convertkit",
    docsUrl: "https://developers.convertkit.com/#webhooks",
    category: "Email",
    accentColor: "bg-rose-500",
    iconBg: "bg-rose-500/10 text-rose-500",
  },
  {
    id: "hubspot",
    name: "HubSpot",
    description: "Sync deals, past champions, and web visits for CRM-enriched research.",
    icon: Layout,
    webhookPath: "/api/webhooks/hubspot",
    docsUrl: "https://developers.hubspot.com/docs/api/overview",
    category: "CRM & Tools",
    accentColor: "bg-orange-600",
    iconBg: "bg-orange-500/10 text-orange-600",
  },
  {
    id: "slack",
    name: "Slack",
    description: "Send research alerts and interactive lead pulses directly to your team.",
    icon: Slack,
    webhookPath: "/slack/interactions",
    docsUrl: "https://api.slack.com/messaging/webhooks",
    category: "CRM & Tools",
    accentColor: "bg-violet-500",
    iconBg: "bg-violet-500/10 text-violet-500",
  },
  {
    id: "million_verifier",
    name: "Million Verifier",
    description: "Automatically verify lead email addresses before outreach.",
    icon: UserCheck,
    webhookPath: "",
    docsUrl: "https://www.millionverifier.com/api-docs/",
    category: "CRM & Tools",
    accentColor: "bg-emerald-500",
    iconBg: "bg-emerald-500/10 text-emerald-600",
  },
];

const CATEGORIES: Category[] = ["All", "Form", "Scheduler", "Email", "CRM & Tools"];

export default function IntegrationsPage() {
  const { trialMode } = useConfig();
  const { toast } = useToast();
  const [settings, setSettings] = useState<IntegrationSettings | null>(null);
  const [configs, setConfigs] = useState<Record<string, { enabled: boolean }>>({});
  const [kitForms, setKitForms] = useState<any[]>([]);
  const [isSavingKey, setIsSavingKey] = useState(false);
  const [isLoadingForms, setIsLoadingForms] = useState(false);
  const [activeCategory, setActiveCategory] = useState<Category>("All");

  useEffect(() => {
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
    if (data?.kit_api_key) loadKitForms();
  };

  const loadKitForms = async () => {
    setIsLoadingForms(true);
    try {
      const data = await fetchKitForms();
      setKitForms(data.forms || []);
    } catch (e: any) {
      const message = e.response?.data?.detail || "Failed to fetch Kit forms.";
      toast({ title: "Integration Error", description: message, variant: "destructive" });
    } finally {
      setIsLoadingForms(false);
    }
  };

  const handleSaveKitKey = async (key: string, isSecret = false) => {
    if (!settings) return;
    setIsSavingKey(true);
    try {
      const updated = { ...settings, [isSecret ? "kit_api_secret" : "kit_api_key"]: key };
      await saveIntegrations(updated);
      setSettings(updated);
      toast({ title: "Saved", description: `${isSecret ? "Secret" : "Public"} key saved.` });
      if (!isSecret && key) loadKitForms();
    } catch (e) {
      toast({ title: "Error", description: "Failed to save API key.", variant: "destructive" });
    } finally {
      setIsSavingKey(false);
    }
  };

  const toggleIntegration = async (id: string) => {
    const newConfigs = { ...configs, [id]: { ...configs[id], enabled: !configs[id]?.enabled } };
    setConfigs(newConfigs);
    if (settings) {
      const updated = {
        ...settings,
        integrations_config: JSON.stringify(newConfigs),
        million_verifier_enabled: id === "million_verifier" ? newConfigs[id].enabled : settings.million_verifier_enabled,
        hubspot_sync_enabled: id === "hubspot" ? newConfigs[id].enabled : settings.hubspot_sync_enabled,
      };
      await saveIntegrations(updated);
      setSettings(updated);
      toast({
        title: newConfigs[id].enabled ? "Integration enabled" : "Integration disabled",
        description: `${INTEGRATIONS.find((i) => i.id === id)?.name} has been updated.`,
      });
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({ title: "Copied", description: "URL copied to clipboard." });
  };

  const connectedCount = INTEGRATIONS.filter((app) => configs[app.id]?.enabled).length;
  const filtered = INTEGRATIONS.filter((app) => {
    const matchesCategory = activeCategory === "All" || app.category === activeCategory;
    const isHiddenInTrial = trialMode && app.id === "million_verifier";
    return matchesCategory && !isHiddenInTrial;
  });

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <Plug className="w-4 h-4 text-primary" />
              </div>
              <h1 className="text-2xl font-black tracking-tight">Integrations</h1>
            </div>
            <p className="text-sm text-muted-foreground pl-10">
              Connect your tools to automate research and sync your pipeline.
            </p>
          </div>
          <div className="flex items-center gap-3 pl-10 md:pl-0">
            {connectedCount > 0 ? (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                  {connectedCount} connected
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
                <div className="w-1.5 h-1.5 rounded-full bg-zinc-400" />
                <span className="text-xs font-bold text-zinc-500">None connected</span>
              </div>
            )}
          </div>
        </div>

        {/* Category tabs */}
        <div className="flex items-center gap-1 p-1 bg-zinc-100 dark:bg-zinc-800/60 rounded-xl w-fit">
          {CATEGORIES.map((cat) => {
            const count = cat === "All"
              ? INTEGRATIONS.length
              : INTEGRATIONS.filter((i) => i.category === cat).length;
            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeCategory === cat
                    ? "bg-white dark:bg-zinc-700 text-zinc-900 dark:text-white shadow-sm"
                    : "text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
                }`}
              >
                {cat}
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                  activeCategory === cat
                    ? "bg-primary/10 text-primary"
                    : "bg-zinc-200 dark:bg-zinc-600 text-zinc-500 dark:text-zinc-400"
                }`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Integration cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {filtered.map((app) => {
            const isLocked = trialMode && app.id !== "slack";
            const isEnabled = configs[app.id]?.enabled;
            const webhookUrl = `${API_URL}${app.webhookPath}`;

            return (
              <div
                key={app.id}
                className={`relative rounded-2xl border bg-white dark:bg-zinc-900 overflow-hidden transition-all ${
                  isEnabled
                    ? "border-zinc-200 dark:border-zinc-700 shadow-sm"
                    : "border-zinc-100 dark:border-zinc-800"
                } ${isLocked ? "opacity-60" : ""}`}
              >
                {/* Accent bar */}
                <div className={`absolute top-0 left-0 right-0 h-0.5 ${isEnabled ? app.accentColor : "bg-zinc-200 dark:bg-zinc-700"}`} />

                {/* Trial lock overlay */}
                {isLocked && (
                  <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none">
                    <Badge className="bg-amber-500 hover:bg-amber-500 text-white border-none gap-1.5 py-1 px-3 shadow-xl text-xs">
                      <Lock className="w-3 h-3" /> Not available in trial
                    </Badge>
                  </div>
                )}

                {/* Card header */}
                <div className="p-5 flex items-start gap-4">
                  <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${app.iconBg}`}>
                    <app.icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <h3 className="font-bold text-sm text-zinc-900 dark:text-white">{app.name}</h3>
                        <span className={`text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded-md ${
                          app.category === "Form" ? "bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400" :
                          app.category === "Scheduler" ? "bg-orange-50 dark:bg-orange-950/40 text-orange-600 dark:text-orange-400" :
                          app.category === "Email" ? "bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400" :
                          "bg-violet-50 dark:bg-violet-950/40 text-violet-600 dark:text-violet-400"
                        }`}>
                          {app.category}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {isEnabled && (
                          <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-500">
                            <CheckCircle2 className="w-3 h-3" /> Active
                          </span>
                        )}
                        <Switch
                          checked={isEnabled}
                          onCheckedChange={() => toggleIntegration(app.id)}
                          disabled={isLocked}
                        />
                      </div>
                    </div>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                      {app.description}
                    </p>
                  </div>
                </div>

                {/* Expanded config */}
                {isEnabled && (
                  <div className="border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-800/30 px-5 py-4 space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">

                    {/* Webhook URL (shown for all integrations that have a path, except config-only ones) */}
                    {app.webhookPath && app.id !== "million_verifier" && (
                      <div className="space-y-1.5">
                        <Label className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">
                          {app.id === "slack" ? "Interactivity Request URL" : "Webhook URL"}
                        </Label>
                        <div className="flex gap-2">
                          <Input
                            readOnly
                            value={webhookUrl}
                            className="bg-white dark:bg-zinc-800 text-xs h-8 font-mono border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-300"
                          />
                          <Button
                            size="icon"
                            variant="outline"
                            className="h-8 w-8 flex-shrink-0"
                            onClick={() => copyToClipboard(webhookUrl)}
                          >
                            <Copy className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* ConvertKit config */}
                    {app.id === "convertkit" && (
                      <div className="space-y-4 pt-2 border-t border-zinc-200 dark:border-zinc-700">
                        <div className="flex items-center justify-between">
                          <Label className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">API Configuration</Label>
                          {settings?.kit_api_key && (
                            <Badge variant="outline" className="text-[9px] h-4 bg-emerald-500/10 text-emerald-600 border-emerald-500/20">
                              Connected
                            </Badge>
                          )}
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div className="space-y-1.5">
                            <Label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">Public API Key (v3)</Label>
                            <Input
                              type="password"
                              placeholder="Paste public key..."
                              className="h-9 text-xs bg-white dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700"
                              defaultValue={settings?.kit_api_key || ""}
                              onBlur={(e) => handleSaveKitKey(e.target.value, false)}
                            />
                          </div>
                          <div className="space-y-1.5">
                            <Label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">API Secret (v3)</Label>
                            <Input
                              type="password"
                              placeholder="Paste secret key..."
                              className="h-9 text-xs bg-white dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700"
                              defaultValue={settings?.kit_api_secret || ""}
                              onBlur={(e) => handleSaveKitKey(e.target.value, true)}
                            />
                          </div>
                        </div>
                        <p className="text-[10px] text-zinc-400">Public key lists forms · Secret key tracks activity</p>

                        {settings?.kit_api_key && (
                          <div className="space-y-3 pt-2 border-t border-zinc-200 dark:border-zinc-700">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
                                <Label className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">Active Forms</Label>
                              </div>
                              <Button variant="ghost" size="sm" className="h-7 text-[10px]" onClick={loadKitForms} disabled={isLoadingForms}>
                                {isLoadingForms ? <Spinner size="sm" className="mr-1" /> : <RefreshCw className="w-3 h-3 mr-1" />}
                                Sync
                              </Button>
                            </div>
                            <div className="grid gap-2 max-h-[200px] overflow-y-auto">
                              {isLoadingForms && kitForms.length === 0 ? (
                                <div className="flex items-center justify-center py-6 gap-2 text-zinc-400">
                                  <Spinner size="md" />
                                  <span className="text-xs">Fetching forms...</span>
                                </div>
                              ) : kitForms.length > 0 ? (
                                kitForms.slice(0, 10).map((form) => (
                                  <div key={form.id} className="flex items-center justify-between px-3 py-2 rounded-lg bg-white dark:bg-zinc-800 border border-zinc-100 dark:border-zinc-700">
                                    <div>
                                      <p className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 truncate max-w-[160px]">{form.name}</p>
                                      <p className="text-[10px] text-zinc-400">{new Date(form.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</p>
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                      <Badge variant="outline" className="text-[9px] h-4">{form.type}</Badge>
                                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                                    </div>
                                  </div>
                                ))
                              ) : (
                                <p className="text-xs text-zinc-400 text-center py-4 italic">No active forms found in your Kit account.</p>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* HubSpot config */}
                    {app.id === "hubspot" && (
                      <div className="space-y-4 pt-2 border-t border-zinc-200 dark:border-zinc-700">
                        <Label className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">HubSpot Configuration</Label>
                        <div className="space-y-1.5">
                          <Label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">Private App Access Token</Label>
                          <Input
                            type="password"
                            placeholder="pat-na1-..."
                            className="h-9 text-xs bg-white dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700"
                            defaultValue={settings?.hubspot_access_token || ""}
                            onBlur={(e) => {
                              if (settings) {
                                const updated = { ...settings, hubspot_access_token: e.target.value };
                                saveIntegrations(updated).then(() => {
                                  setSettings(updated);
                                  toast({ title: "Saved", description: "HubSpot access token updated." });
                                });
                              }
                            }}
                          />
                        </div>
                        <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-white dark:bg-zinc-800 border border-zinc-100 dark:border-zinc-700">
                          <div>
                            <p className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">Automated CRM Sync</p>
                            <p className="text-[10px] text-zinc-400 mt-0.5">Sync deals, champions and visits every 12 hours.</p>
                          </div>
                          <Switch
                            checked={settings?.hubspot_sync_enabled}
                            onCheckedChange={(checked) => {
                              if (settings) {
                                const updated = { ...settings, hubspot_sync_enabled: checked };
                                saveIntegrations(updated).then(() => {
                                  setSettings(updated);
                                  toast({ title: checked ? "Sync enabled" : "Sync disabled", description: `HubSpot sync is now ${checked ? "active" : "paused"}.` });
                                });
                              }
                            }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Slack config */}
                    {app.id === "slack" && (
                      <div className="space-y-3 pt-2 border-t border-zinc-200 dark:border-zinc-700">
                        <Label className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">Slack Configuration</Label>
                        <div className="space-y-1.5">
                          <Label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">Incoming Webhook URL</Label>
                          <Input
                            type="password"
                            placeholder="https://hooks.slack.com/services/..."
                            className="h-9 text-xs bg-white dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700"
                            defaultValue={settings?.slack_webhook_url || ""}
                            onBlur={(e) => {
                              if (settings) {
                                const updated = { ...settings, slack_webhook_url: e.target.value };
                                saveIntegrations(updated).then(() => {
                                  setSettings(updated);
                                  toast({ title: "Saved", description: "Slack webhook URL updated." });
                                });
                              }
                            }}
                          />
                          <p className="text-[10px] text-zinc-400">Found under your Slack App → Incoming Webhooks.</p>
                        </div>
                      </div>
                    )}

                    {/* Million Verifier config */}
                    {app.id === "million_verifier" && (
                      <div className="space-y-3 pt-2 border-t border-zinc-200 dark:border-zinc-700">
                        <Label className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">Million Verifier Configuration</Label>
                        <div className="space-y-1.5">
                          <Label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">API Key</Label>
                          <Input
                            type="password"
                            placeholder="mv-..."
                            className="h-9 text-xs bg-white dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700"
                            defaultValue={settings?.million_verifier_api_key || ""}
                            onBlur={(e) => {
                              if (settings) {
                                const updated = { ...settings, million_verifier_api_key: e.target.value, million_verifier_enabled: true };
                                saveIntegrations(updated).then(() => {
                                  setSettings(updated);
                                  toast({ title: "Saved", description: "Million Verifier API key updated." });
                                });
                              }
                            }}
                          />
                          <p className="text-[10px] text-zinc-400">Your API key for automated email verification.</p>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Footer */}
                <div className={`px-5 py-3 flex items-center justify-between border-t ${isEnabled ? "border-zinc-100 dark:border-zinc-800" : "border-transparent"}`}>
                  <a
                    href={app.docsUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-[11px] text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
                  >
                    <ExternalLink className="w-3 h-3" /> View docs
                  </a>
                  {!isEnabled && (
                    <span className="text-[10px] text-zinc-400 font-medium">Toggle to connect</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Pro tip */}
        <div className="flex gap-4 p-5 rounded-2xl bg-primary/5 border border-primary/15">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Info className="w-4 h-4 text-primary" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">Webhook setup tip</p>
            <p className="text-xs text-zinc-500 leading-relaxed">
              All integrations require at least an <code className="px-1 py-0.5 rounded bg-primary/10 text-primary font-mono text-[11px]">email</code> or{" "}
              <code className="px-1 py-0.5 rounded bg-primary/10 text-primary font-mono text-[11px]">linkedin_url</code> field to trigger analysis.
              Extra fields like job title or use case are automatically detected and used to improve recommendation quality.
            </p>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
