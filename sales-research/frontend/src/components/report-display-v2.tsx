import React, { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import axios from "axios";
import {
  User, Target, Globe, FileText, BarChart3, TrendingUp, Copy, Check,
  Info, Calendar, ShieldCheck, ShieldAlert, ShieldQuestion, ExternalLink,
  LayoutDashboard, Mail, Linkedin, Zap, MessageSquareQuote, MessageSquare,
  ArrowRight, X, Search, BookOpen, Edit2, Save, RotateCcw, Plus, ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import {
  API_URL, updateOutreachStatus, updateExecutiveBlueprint,
  updateIntentAnalysis, updateBuyerJourney,
} from "@/lib/api";
import { ensureProtocol } from "@/lib/utils";
import { CSOCommandCard } from "./cso-command-card";
import { VerificationBadge } from "./verification-badge";


interface ReportDisplayV2Props {
  data: {
    fullname?: string;
    email?: string;
    email_verification_status?: string;
    profile_picture_url?: string;
    linkedin_url?: string;
    website?: string;
    lead_score?: number;
    sales_research_report: any;
    lead_score_analysis: any;
    user_profile_analysis: any;
    website_analysis: any;
    intent_analysis?: {
      intent: string;
      summary: string;
      next_steps: string;
      sentiment: string;
      post_topic_depth?: string;
      recommended_email?: string;
    };
    email_history?: Array<{
      id?: string; subject: string; from: string; to?: string[];
      date: string; text: string; direction: string;
    }>;
    viability_analysis?: string;
    target_pain_points?: string;
    strategic_solutions?: string;
    personalized_outreach?: Array<{
      hook: string; linkedin_message: string; email_subject: string;
      email_body: string; variant_name?: string; _edit_depths?: Record<string, number>;
    }> | { hook: string; linkedin_message: string; email_subject: string; email_body: string; _edit_depths?: Record<string, number>; } | string;
    outreach_sequences?: Array<{
      variant_name: string; primary_pain_point: string; sequence_theme: string;
      steps: Array<{
        step_number: number; step_type: string; narrative_angle: string; draft: string;
        email_subject?: string; engagement_type: string; delay_days: number;
        trigger: string; internal_note: string; reference_signal?: string;
      }>;
      exit_strategy: string;
    }>;
    buyer_journey_analysis?: {
      journey_stage: string; optimal_play: string; strategic_reasoning: string;
      sentiment_score: number; urgency_level: string;
    } | any;
    meeting_notes?: string;
    post_engagements?: Array<{
      type: string; target: string; post_id: string; post_url?: string;
      content: string; reaction_type?: string; comment_text?: string;
    }>;
    company_news?: Array<{ title: string; source: string; date: string }>;
    hiring_data?: Array<{ role: string; location: string }>;
    extra_metadata?: {
      lead_source?: string;
      lead_extracted_data?: { discovery_insights?: string; [key: string]: any };
      discovery_source?: string;
      discovery_context?: any;
      download_marketing_material?: boolean;
      demo_requested?: boolean;
      referral_partner_introduction?: boolean;
      [key: string]: any;
    };
    cso_strategic_briefing?: {
      unified_command: {
        verdict: string; framework_selected: string; timing_advice: string;
        strategic_reasoning: string; objection_preemption: string[];
        sources: Array<{ source: string; snippet: string }>;
      };
      executive_blueprint_summary: string;
      refined_linkedin_message?: string;
      refined_email_body?: string;
      strategic_proof_points?: string[];
      advanced_strategic_pivots?: string[];
      _edit_depths?: Record<string, number>;
    };
    [key: string]: any;
  } | null;
  onRerun?: () => void;
}

// ─── Small copy-button with transient "Copied" state ─────────────────────────
function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const handle = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };
  return (
    <Button size="sm" variant="outline"
      className="h-7 px-2.5 gap-1.5 text-[10px] font-black uppercase tracking-tight shrink-0"
      onClick={handle}
    >
      {copied ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
      {copied ? "Copied" : label}
    </Button>
  );
}

// ─── Expandable email history row ────────────────────────────────────────────
function EmailHistoryRow({ email }: { email: { subject: string; from: string; to?: string[]; date: string; text: string; direction: string } }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="px-5 py-4 hover:bg-zinc-50 dark:hover:bg-zinc-800/40 transition-all cursor-pointer" onClick={() => setExpanded(!expanded)}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div className={cn("mt-0.5 h-6 w-6 rounded-full flex items-center justify-center shrink-0 text-white text-[10px] font-black",
            email.direction === "received" ? "bg-emerald-500" : "bg-zinc-400 dark:bg-zinc-600")}>
            {email.direction === "received" ? <ArrowRight className="h-3 w-3 rotate-180" /> : <ArrowRight className="h-3 w-3" />}
          </div>
          <div className="min-w-0">
            <p className="text-[12px] font-black text-zinc-900 dark:text-zinc-100 truncate">{email.subject}</p>
            <p className="text-[11px] text-zinc-500 mt-0.5">{email.from}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[10px] text-zinc-400 font-bold">{new Date(email.date).toLocaleDateString()}</span>
          <Badge variant="secondary" className={cn("text-[9px] uppercase font-black h-4 px-1.5 border-none",
            email.direction === "received" ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" : "bg-zinc-100 dark:bg-zinc-800 text-zinc-500")}>
            {email.direction}
          </Badge>
          <ChevronRight className={cn("h-3.5 w-3.5 text-zinc-400 transition-transform", expanded && "rotate-90")} />
        </div>
      </div>
      {expanded && (
        <div className="mt-3 ml-9 p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
          <p className="text-[12px] text-zinc-600 dark:text-zinc-400 leading-relaxed whitespace-pre-line">{email.text}</p>
        </div>
      )}
    </div>
  );
}

// ─── Lightweight content renderer for Intel sections ─────────────────────────
const INTEL_EXCLUDE_KEYS = [
  "personalized_outreach", "outreach_sequences", "final_outreach_sequences",
  "campaign_outreach_variants", "cso_strategic_briefing", "intent_analysis",
  "buyer_journey_analysis", "lead_score_analysis", "refined_linkedin_message",
  "refined_email_body", "refined_hook", "fit_reasoning",
  "name", "fullname", "headline", "recent_posts", "posts",
];

function FieldValue({ value }: { value: any }) {
  if (Array.isArray(value)) {
    return (
      <ul className="space-y-1.5 pl-3">
        {value.map((item, i) => (
          <li key={i} className="flex gap-2 text-[13px] text-zinc-700 dark:text-zinc-300 leading-relaxed">
            <span className="text-primary/60 mt-1 text-[10px]">▸</span>
            {typeof item === "object" && item !== null ? (
              <div className="flex-1 my-2 overflow-hidden rounded-2xl border border-zinc-100 dark:border-zinc-800 bg-white dark:bg-zinc-900/50 shadow-sm">
                {/* Special Case: Solution Object with Logical Gap Mapping */}
                {item.logical_gap_mapping ? (
                  <div className="grid grid-cols-1 md:grid-cols-2">
                    <div className="p-5 bg-rose-500/[0.02] space-y-3">
                      <div className="flex items-center gap-2">
                         <div className="h-1 w-3 rounded-full bg-rose-500/30" />
                         <span className="text-[9px] font-black text-rose-500 uppercase tracking-widest">Silent Friction / Logical Gapping</span>
                      </div>
                      <div className="text-[13px] text-zinc-700 dark:text-zinc-300 font-bold italic leading-relaxed">
                        <ReactMarkdown>{String(item.logical_gap_mapping)}</ReactMarkdown>
                      </div>
                    </div>
                    <div className="p-5 border-l border-zinc-100 dark:border-zinc-800 bg-emerald-500/[0.02] space-y-3">
                      <div className="flex items-center gap-2">
                         <div className="h-1 w-3 rounded-full bg-emerald-500/30" />
                         <span className="text-[9px] font-black text-emerald-500 uppercase tracking-widest">The Bridge / How it Helps</span>
                      </div>
                      <div className="space-y-2">
                        <div className="text-[13px] text-zinc-800 dark:text-zinc-100 font-bold leading-relaxed">
                          <ReactMarkdown>{String(item.description)}</ReactMarkdown>
                        </div>
                        {item.expected_roi && (
                          <div className="pt-2 flex flex-col gap-1">
                            <span className="text-[8px] font-black text-zinc-400 uppercase tracking-[0.2em]">Expected ROI / Impact</span>
                            <div className="text-[12px] text-emerald-600 dark:text-emerald-400 font-black italic">
                              {String(item.expected_roi)}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                    {item.title && (
                      <div className="col-span-full px-5 py-2.5 bg-zinc-50 dark:bg-zinc-800/50 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
                        <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">Targeted Solution</span>
                        <span className="text-[11px] font-black text-primary italic uppercase tracking-wider">{item.title}</span>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-5 space-y-3">
                    {Object.entries(item).map(([k, v]) => {
                      const labelMap: Record<string, string> = {
                        logical_gap_mapping: "Silent Friction / Logical Gapping",
                        description: "How it helps",
                        expected_roi: "Expected ROI / Impact",
                        title: "Solution Title"
                      };
                      const displayLabel = labelMap[k] || k.replace(/_/g, " ");
                      return (
                        <div key={k} className="flex flex-col gap-1">
                          <span className="text-[9px] font-black text-zinc-400 uppercase tracking-widest">{displayLabel}</span>
                          <div className="text-[13px] text-zinc-700 dark:text-zinc-300 font-medium leading-relaxed">
                            {typeof v === "object" ? JSON.stringify(v) : <ReactMarkdown>{String(v)}</ReactMarkdown>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ) : <ReactMarkdown>{String(item)}</ReactMarkdown>}
          </li>
        ))}
      </ul>
    );
  }

  if (typeof value === "object" && value !== null) {
    return (
      <div className="pl-3 border-l border-zinc-100 dark:border-zinc-800 space-y-3">
        {Object.entries(value).map(([k, v]) => {
          const labelMap: Record<string, string> = {
            logical_gap_mapping: "Silent Friction / Logical Gapping",
            description: "How it helps",
            expected_roi: "Expected ROI / Impact",
            title: "Solution Title"
          };
          const displayLabel = labelMap[k] || k.replace(/_/g, " ");
          
          return (
            <div key={k} className="flex flex-col gap-1">
              <span className="text-[9px] font-black text-primary/60 uppercase tracking-widest">{displayLabel}</span>
              <div className="text-[13px] text-zinc-700 dark:text-zinc-300 font-medium leading-relaxed">
                {typeof v === "object" ? JSON.stringify(v) : <ReactMarkdown>{String(v)}</ReactMarkdown>}
              </div>
            </div>
          );
        })}
      </div>
    );
  }
  return (
    <div className="prose prose-zinc dark:prose-invert max-w-none text-[14px] leading-relaxed font-medium">
      <ReactMarkdown>{String(value ?? "")}</ReactMarkdown>
    </div>
  );
}

function IntelContent({ content, excludeKeys = [] }: { content: any; excludeKeys?: string[] }) {
  if (!content) return <p className="text-sm text-zinc-400 italic">No data available.</p>;

  let displayContent = content;
  if (typeof content === "string") {
    try {
      // Try to parse if it's a JSON string
      if (content.trim().startsWith("{") || content.trim().startsWith("[")) {
        displayContent = JSON.parse(content);
      }
    } catch (e) {
      // Keep as string if parsing fails
    }
  }

  if (typeof displayContent === "string") {
    return (
      <div className="prose prose-zinc dark:prose-invert max-w-none text-[15px] leading-[1.8]">
        <ReactMarkdown>{displayContent}</ReactMarkdown>
      </div>
    );
  }

  if (typeof displayContent === "object" && !Array.isArray(displayContent)) {
    const allExclude = [...INTEL_EXCLUDE_KEYS, ...excludeKeys];
    return (
      <div className="space-y-8">
        {Object.entries(displayContent)
          .filter(([key]) => !allExclude.map(k => k.toLowerCase()).includes(key.toLowerCase()))
          .map(([key, value]) => {
            const display = key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
            
            // Special rendering for section containers
            if (key === "solutions" && Array.isArray(value)) {
               return (
                 <div key={key} className="space-y-4">
                   <div className="flex items-center gap-3">
                     <div className="h-px flex-1 bg-zinc-100 dark:bg-zinc-800" />
                     <h4 className="text-[10px] font-black text-zinc-400 dark:text-zinc-500 uppercase tracking-[0.3em]">{display}</h4>
                     <div className="h-px flex-1 bg-zinc-100 dark:bg-zinc-800" />
                   </div>
                   <FieldValue value={value} />
                 </div>
               );
            }

            if (key === "fit_assessment") {
              const isPoor = String(value).includes("STOP") || String(value).includes("POOR");
              return (
                <div key={key} className={cn("p-4 rounded-xl flex items-center gap-3 border",
                  isPoor ? "bg-rose-500/5 border-rose-500/20 text-rose-600 dark:text-rose-400"
                         : "bg-emerald-500/5 border-emerald-500/20 text-emerald-600 dark:text-emerald-400")}>
                  {isPoor ? <ShieldAlert className="h-5 w-5" /> : <ShieldCheck className="h-5 w-5" />}
                  <span className="font-black text-lg italic uppercase">{String(value)}</span>
                </div>
              );
            }
            return (
              <div key={key} className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-primary/40 shrink-0" />
                  <h4 className="text-[10px] font-black text-zinc-400 dark:text-zinc-500 uppercase tracking-[0.2em]">{display}</h4>
                </div>
                <div className="pl-4">
                  <FieldValue value={value} />
                </div>
              </div>
            );
          })}
      </div>
    );
  }
  return null;
}


// ─── Main component ───────────────────────────────────────────────────────────
export function ReportDisplayV2({ data, onRerun }: ReportDisplayV2Props) {
  const [activeTab, setActiveTab] = useState<"actions" | "intel" | "signals">("actions");
  const [activeIntelSection, setActiveIntelSection] = useState("synthesis");
  const [isProofOpen, setIsProofOpen] = useState(false);
  const [selectedVariantIndex, setSelectedVariantIndex] = useState(0);
  const [outreachStatus, setOutreachStatus] = useState<string>(data?.outreach_status || "not_started");
  const [isOutreachEdited, setIsOutreachEdited] = useState<boolean>(data?.is_outreach_edited || false);
  const [editDepthPercentage, setEditDepthPercentage] = useState<number>(data?.edit_depth_percentage || 0);

  useEffect(() => {
    if (data) {
      setOutreachStatus(data.outreach_status || "not_started");
      setIsOutreachEdited(data.is_outreach_edited || false);
      setEditDepthPercentage(data.edit_depth_percentage || 0);
    }
  }, [data]);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [isEditingOutreach, setIsEditingOutreach] = useState(false);
  const [isSavingOutreach, setIsSavingOutreach] = useState(false);
  const [activeOutreachTab, setActiveOutreachTab] = useState<"tactical" | "strategic">("tactical");
  const [editedOutreach, setEditedOutreach] = useState<any>({ linkedin_message: "", email_subject: "", email_body: "", hook: "", steps: [] });
  const [editedStrategicOutreach, setEditedStrategicOutreach] = useState({ linkedin_message: "", email_body: "" });
  const [isEditingJourney, setIsEditingJourney] = useState(false);
  const [isSavingJourney, setIsSavingJourney] = useState(false);
  const [editedJourney, setEditedJourney] = useState<any>(null);
  const [isEditingIntent, setIsEditingIntent] = useState(false);
  const [isSavingIntent, setIsSavingIntent] = useState(false);
  const [editedIntent, setEditedIntent] = useState<any>(null);
  const [isEditingIntentEmail, setIsEditingIntentEmail] = useState(false);
  const [isSavingIntentEmail, setIsSavingIntentEmail] = useState(false);
  const [editedIntentEmail, setEditedIntentEmail] = useState("");
  const [isEditingStrategicCommand, setIsEditingStrategicCommand] = useState(false);
  const [isSavingStrategic, setIsSavingStrategic] = useState(false);
  const [editedStrategicCommand, setEditedStrategicCommand] = useState<any[]>([]);
  const [selectedSubjectVariants, setSelectedSubjectVariants] = useState<Record<string, string>>({});
  const { toast } = useToast();

  React.useEffect(() => {
    if (!data) return;

    // Normalize variants for initial state
    const rawV = (() => {
      const p = data.personalized_outreach;
      if (Array.isArray(p) && p.length > 0) return p;
      if (p && typeof p === "object" && !Array.isArray(p)) return [p];
      const seqs = data.final_outreach_sequences || data.outreach_sequences || data.sales_research_report?.outreach_sequences;
      if (Array.isArray(seqs) && seqs.length > 0) return seqs;
      const legacy = data.campaign_outreach_variants || data.sales_research_report?.campaign_variants;
      if (Array.isArray(legacy) && legacy.length > 0) return legacy;
      if (p) return [p];
      return [];
    })();

    const campaignV = rawV.map((v: any) => {
      if (Array.isArray(v.steps) && v.steps.length > 0) return v;
      const steps: any[] = [];
      if (v.linkedin_message || v.hook) steps.push({ step_number: 1, engagement_type: "LI_DM", narrative_angle: "LinkedIn Request", draft: v.linkedin_message || v.hook, delay_days: 0, internal_note: "" });
      if (v.email_body) steps.push({ step_number: steps.length + 1, engagement_type: "EMAIL_DIRECT", narrative_angle: "Email Outreach", draft: v.email_body, email_subject: v.email_subject, delay_days: 2, internal_note: "" });
      return { ...v, steps };
    });

    const p = campaignV[selectedVariantIndex] || {};
    if (p) {
      setEditedOutreach({
        ...p,
        email_subject: p.email_subject || "",
        linkedin_message: p.linkedin_message || "",
        email_body: p.email_body || "",
        hook: p.hook || p.strategic_hook || "",
        steps: p.steps || []
      });
    }
    if (data.cso_strategic_briefing) {
      setEditedStrategicOutreach({ linkedin_message: data.cso_strategic_briefing.refined_linkedin_message || "", email_body: data.cso_strategic_briefing.refined_email_body || "" });
    }
    if (data.intent_analysis) {
      setEditedIntentEmail(data.intent_analysis.recommended_email || "");
      setEditedIntent({ ...data.intent_analysis });
    }
    if (data.buyer_journey_analysis) setEditedJourney({ ...data.buyer_journey_analysis });
    if (data.sales_research_report) setEditedStrategicCommand(data.sales_research_report.advanced_next_steps || []);
    setOutreachStatus(data.outreach_status || "not_started");
  }, [data, selectedVariantIndex, selectedSubjectVariants]);

  const handleUpdateStatus = async (newStatus: string) => {
    if (!data?.id) return;
    setIsUpdatingStatus(true);
    try {
      await updateOutreachStatus(data.id, newStatus);
      setOutreachStatus(newStatus);
      toast({ title: "Status Updated", description: `Changed to ${newStatus.replace(/_/g, " ")}` });
    } catch {
      toast({ variant: "destructive", title: "Error", description: "Failed to update status" });
    } finally { setIsUpdatingStatus(false); }
  };

  const handleSaveOutreach = async () => {
    if (!data?.id) return;
    setIsSavingOutreach(true);
    try {
      const isStrategic = activeOutreachTab === "strategic";
      const hasVariantsLocal = Array.isArray(data?.personalized_outreach) && (data.personalized_outreach as any[]).length > 0;
      const body = isStrategic
        ? { refined_linkedin_message: editedStrategicOutreach.linkedin_message, refined_email_body: editedStrategicOutreach.email_body }
        : { ...editedOutreach, ...(hasVariantsLocal ? { variant_index: selectedVariantIndex } : {}) };
      const endpoint = isStrategic ? "cso-outreach" : "outreach";
      const res = await axios.put(`${API_URL}/sales-research/reports/${data.id}/${endpoint}`, body);
      
      // Update local data to reflect changes immediately and include calculated metadata (like edit_depth_percentage)
      const respData = res.data?.data;
      if (respData) {
        // Sync the most important fields back to the prop object
        Object.assign(data, respData);
        
        // Also update local state derived from data
        if (respData.outreach_status) setOutreachStatus(respData.outreach_status);
        setIsOutreachEdited(respData.is_outreach_edited ?? data.is_outreach_edited);
        setEditDepthPercentage(respData.edit_depth_percentage ?? data.edit_depth_percentage);
      }

      toast({ title: "Saved", description: `${isStrategic ? "Strategic" : "Tactical"} outreach updated` });
      setIsEditingOutreach(false);
    } catch {
      toast({ variant: "destructive", title: "Error", description: "Failed to save outreach" });
    } finally { setIsSavingOutreach(false); }
  };

  const handleSaveStrategicCommand = async () => {
    if (!data?.id) return;
    setIsSavingStrategic(true);
    try {
      const res = await updateExecutiveBlueprint(data.id, { advanced_next_steps: editedStrategicCommand });
      const respData = res.data?.data || res.data;
      if (respData) Object.assign(data, respData);
      toast({ title: "Saved", description: "Strategic Command updated" });
      setIsEditingStrategicCommand(false);
    } catch {
      toast({ variant: "destructive", title: "Error", description: "Failed to save" });
    } finally { setIsSavingStrategic(false); }
  };

  const handleSaveIntent = async () => {
    if (!data?.id) return;
    setIsSavingIntent(true);
    try {
      const res = await updateIntentAnalysis(data.id, editedIntent);
      const respData = res.data?.data || res.data;
      if (respData) Object.assign(data, respData);
      toast({ title: "Saved", description: "Intent Analysis updated" });
      setIsEditingIntent(false);
    } catch {
      toast({ variant: "destructive", title: "Error", description: "Failed to save" });
    } finally { setIsSavingIntent(false); }
  };

  const handleSaveIntentEmail = async () => {
    if (!data?.id) return;
    setIsSavingIntentEmail(true);
    try {
      const res = await axios.put(`${API_URL}/sales-research/reports/${data.id}/intent-email`, { email_text: editedIntentEmail });
      const respData = res.data?.data;
      if (respData) Object.assign(data, respData);
      toast({ title: "Saved", description: "Follow-up email updated" });
      setIsEditingIntentEmail(false);
    } catch {
      toast({ variant: "destructive", title: "Error", description: "Failed to save email" });
    } finally { setIsSavingIntentEmail(false); }
  };

  const handleSaveJourney = async () => {
    if (!data?.id) return;
    setIsSavingJourney(true);
    try {
      const res = await updateBuyerJourney(data.id, editedJourney);
      const respData = res.data?.data || res.data;
      if (respData) Object.assign(data, respData);
      toast({ title: "Saved", description: "Buyer Journey updated" });
      setIsEditingJourney(false);
    } catch {
      toast({ variant: "destructive", title: "Error", description: "Failed to save" });
    } finally { setIsSavingJourney(false); }
  };

  if (!data) return null;

  // ── Identity ──────────────────────────────────────────────────────────────
  const getIdentity = () => {
    if (data.fullname) {
      const analysis = data.user_profile_analysis;
      let headline = "Target Profile";
      if (typeof analysis === "string") {
        const m = analysis.match(/(?:Headline|Title|Role):\s*\**([^\n\*]+)\**/i);
        if (m) headline = m[1].trim();
      } else if (analysis?.profile_summary || analysis?.headline) {
        headline = analysis.profile_summary || analysis.headline || headline;
      }
      return { name: data.fullname, headline };
    }
    const a = data.user_profile_analysis;
    if (a && typeof a === "object") return { name: a.name || a.fullname || "Prospect", headline: a.profile_summary || a.headline || "Target Profile" };
    const s = String(a || "");
    const nm = s.match(/(?:Name|Full Name):\s*\**([^\n\*]+)\**/i);
    const hm = s.match(/(?:Headline|Title|Role):\s*\**([^\n\*]+)\**/i);
    return { name: nm ? nm[1].trim() : "Prospect", headline: hm ? hm[1].trim() : "Target Profile" };
  };
  const identity = getIdentity();

  // ── Variant / outreach normalization (same logic as v1) ───────────────────
  const getRawVariants = () => {
    const p = data.personalized_outreach;
    if (Array.isArray(p) && p.length > 0) return p;
    if (p && typeof p === "object" && !Array.isArray(p)) return [p];
    const seqs = data.final_outreach_sequences || data.outreach_sequences || data.sales_research_report?.outreach_sequences;
    if (Array.isArray(seqs) && seqs.length > 0) return seqs;
    const legacy = data.campaign_outreach_variants || data.sales_research_report?.campaign_variants;
    if (Array.isArray(legacy) && legacy.length > 0) return legacy;
    if (p) return [p];
    return [];
  };

  // Derive effective contact fields — checks all possible locations in the data shape
  const effectiveEmail =
    data.email ||
    (data as any).email_id ||
    (data as any).input_lead_data?.email ||
    (data as any).extra_metadata?.email ||
    (typeof data.user_profile_analysis === "object" ? data.user_profile_analysis?.email : null) ||
    null;

  const rawVerificationStatus =
    data.email_verification_status ||
    (data as any).email_id_verification_status ||
    (data as any).input_lead_data?.email_verification_status ||
    (data as any).extra_metadata?.email_verification_status ||
    (typeof data.user_profile_analysis === "object" ? data.user_profile_analysis?.email_verification_status : null) ||
    null;
  // Normalize to lowercase so "Verified", "VERIFIED", "verified" all match
  const effectiveVerificationStatus = rawVerificationStatus?.toString().toLowerCase() || null;

  const effectiveLinkedin =
    data.linkedin_url ||
    (data as any).input_lead_data?.linkedin_url ||
    (typeof data.user_profile_analysis === "object" ? data.user_profile_analysis?.linkedin_url : null) ||
    null;

  const effectiveWebsite =
    data.website ||
    (data as any).input_lead_data?.website ||
    (typeof data.user_profile_analysis === "object" ? data.user_profile_analysis?.website : null) ||
    null;

  const rawVariants = getRawVariants();
  const campaignVariants = rawVariants.map((v: any) => {
    if (Array.isArray(v.steps) && v.steps.length > 0) return v;
    const steps: any[] = [];
    if (v.linkedin_message || v.hook) steps.push({ step_number: 1, engagement_type: "LI_DM", narrative_angle: "LinkedIn Request", draft: v.linkedin_message || v.hook, delay_days: 0, internal_note: "" });
    if (v.email_body) steps.push({ step_number: steps.length + 1, engagement_type: "EMAIL_DIRECT", narrative_angle: "Email Outreach", draft: v.email_body, email_subject: v.email_subject, delay_days: 2, internal_note: "" });
    return { ...v, steps, primary_pain_point: v.primary_pain_point || "Strategic Outreach", sequence_theme: v.sequence_theme || "Unified Touchpoints", exit_strategy: v.exit_strategy || v.fit_reasoning || "" };
  });

  const hasVariants = campaignVariants.length > 0;
  const isSequence = hasVariants && Array.isArray(campaignVariants[0]?.steps);
  const activeOutreach: any = hasVariants ? campaignVariants[selectedVariantIndex] : data.personalized_outreach;

  const tacticalActions = isSequence && activeOutreach
    ? (activeOutreach as any).steps.map((s: any) => ({
        type: s.engagement_type?.includes("EMAIL") ? "email" : "linkedin",
        title: `Step ${s.step_number || 1}: ${(s.narrative_angle || "").replace(/_/g, " ").toUpperCase()}`,
        content: s.draft || s.internal_note || "",
        icon: s.engagement_type?.includes("EMAIL") ? <Mail className="h-3.5 w-3.5" /> : <Linkedin className="h-3.5 w-3.5" />,
        ...s,
      }))
    : activeOutreach && typeof activeOutreach === "object"
      ? [
          activeOutreach.linkedin_message && { type: "linkedin", title: "LinkedIn Request", content: activeOutreach.linkedin_message || activeOutreach.hook || "", icon: <Linkedin className="h-3.5 w-3.5" /> },
          activeOutreach.email_subject && { type: "email", title: "Email Subject", content: activeOutreach.email_subject || "", icon: <Mail className="h-3.5 w-3.5" /> },
          activeOutreach.email_body && { type: "email", title: "Email Body", content: activeOutreach.email_body || "", icon: <FileText className="h-3.5 w-3.5" /> },
        ].filter(Boolean)
      : [];

  const briefing = data.cso_strategic_briefing;
  const strategicActions = briefing
    ? [
        briefing.refined_linkedin_message && { 
          type: "linkedin", 
          title: "LinkedIn Message", 
          content: briefing.refined_linkedin_message, 
          icon: <Linkedin className="h-3.5 w-3.5" />,
          _edit_depth: briefing._edit_depths?.refined_linkedin_message || 0
        },
        briefing.refined_email_body && { 
          type: "email", 
          title: "Refined Email", 
          content: briefing.refined_email_body, 
          icon: <FileText className="h-3.5 w-3.5" />,
          _edit_depth: briefing._edit_depths?.refined_email_body || 0
        },
      ].filter(Boolean)
    : [];

  const hook = activeOutreach?.hook || activeOutreach?.strategic_hook;

  // ── Intel sections config ─────────────────────────────────────────────────
  const extraMeta = data.extra_metadata || {};
  const inputLead = (data as any).input_lead_data || {};
  const discoverySource = extraMeta.discovery_source || inputLead.discovery_source;

  const INTEL_GROUPS = [
    {
      label: "Deal Context",
      sections: [
        { id: "synthesis", title: "Executive Blueprint", icon: <LayoutDashboard className="h-3.5 w-3.5" /> },
        { id: "cso-verdict", title: "CSO Verdict", icon: <ShieldCheck className="h-3.5 w-3.5" /> },
        ...(discoverySource === "competitor_comment" || discoverySource === "keyword_search" || discoverySource === "apollo_discovery"
          ? [{ id: "discovery", title: "Discovery Intelligence", icon: <Search className="h-3.5 w-3.5" /> }]
          : []),

      ],
    },
    {
      label: "Person & Company",
      sections: [
        { id: "profile", title: "Profile Intelligence", icon: <User className="h-3.5 w-3.5" /> },
        { id: "website", title: "Digital Footprint", icon: <Globe className="h-3.5 w-3.5" /> },
        { id: "viability", title: "ICP Viability", icon: <ShieldCheck className="h-3.5 w-3.5" /> },
      ],
    },
    {
      label: "Strategic Fit",
      sections: [
        { id: "pain-points", title: "Lead Pain Points", icon: <Zap className="h-3.5 w-3.5" /> },
        { id: "solutions", title: "Strategic Solutions", icon: <ArrowRight className="h-3.5 w-3.5" /> },
      ],
    },
    {
      label: "Scoring",
      sections: [
        { id: "lead-score", title: "Qualification", icon: <BarChart3 className="h-3.5 w-3.5" /> },
      ],
    },
  ];

  // ── Status helpers ────────────────────────────────────────────────────────
  const statusConfig: Record<string, { label: string; className: string }> = {
    not_started: { label: "Not Started", className: "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400" },
    in_progress: { label: "In Progress", className: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" },
    completed: { label: "Completed", className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" },
  };
  const currentStatus = statusConfig[outreachStatus] || statusConfig.not_started;

  // ═════════════════════════════════════════════════════════════════════════
  // RENDER
  // ═════════════════════════════════════════════════════════════════════════
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">

      {/* ── PROFILE HERO ──────────────────────────────────────────────────── */}
      <div className="relative bg-zinc-900 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(37,99,235,0.18),transparent_60%)]" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/30 pointer-events-none" />

        <div className="relative max-w-7xl mx-auto px-4 md:px-8 pt-8 pb-6">
          <div className="flex flex-col sm:flex-row sm:items-start gap-5">
            {/* Avatar */}
            <div className="relative shrink-0">
              {data.profile_picture_url ? (
                <img src={data.profile_picture_url} alt={identity.name}
                  className="h-20 w-20 rounded-2xl object-cover ring-2 ring-white/10 shadow-2xl" />
              ) : (
                <div className="h-20 w-20 rounded-2xl bg-zinc-800 border border-white/5 flex items-center justify-center shadow-xl">
                  <User className="h-9 w-9 text-zinc-500" />
                </div>
              )}
              <div className={cn(
                "absolute -bottom-1.5 -right-1.5 h-5 px-1.5 rounded-full border-2 border-zinc-900 flex items-center text-[8px] font-black uppercase tracking-wide",
                (data.lead_score || 0) >= 75 ? "bg-emerald-500 text-white" :
                (data.lead_score || 0) >= 50 ? "bg-amber-500 text-white" : "bg-zinc-600 text-white",
              )}>
                {(data.lead_score || 0) >= 75 ? "Hot" : (data.lead_score || 0) >= 50 ? "Warm" : "Cold"}
              </div>
            </div>

            {/* Name + headline + links */}
            <div className="flex-1 min-w-0 space-y-2.5">
              <div>
                <div className="flex flex-wrap items-center gap-2.5 mb-1">
                  <h1 className="text-2xl md:text-3xl font-black text-white tracking-tight leading-tight">{identity.name}</h1>
                </div>

                <p className="text-zinc-400 text-sm leading-relaxed max-w-2xl">{identity.headline}</p>
              </div>
              <div className="flex flex-wrap items-center gap-4">
                {data.linkedin_url && (
                  <a href={data.linkedin_url} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors group">
                    <div className="p-1.5 rounded-lg bg-zinc-800 group-hover:bg-[#0077B5]/30 transition-all">
                      <Linkedin className="h-3.5 w-3.5" />
                    </div>
                    <span className="text-xs font-bold">LinkedIn</span>
                    <ExternalLink className="h-2.5 w-2.5 opacity-0 group-hover:opacity-60 transition-all" />
                  </a>
                )}
                {data.website && (
                  <a href={ensureProtocol(data.website)} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors group">
                    <div className="p-1.5 rounded-lg bg-zinc-800 group-hover:bg-primary/20 transition-all">
                      <Globe className="h-3.5 w-3.5" />
                    </div>
                    <span className="text-xs font-bold truncate max-w-[160px]">{data.website}</span>
                    <ExternalLink className="h-2.5 w-2.5 opacity-0 group-hover:opacity-60 transition-all" />
                  </a>
                )}
                {effectiveEmail && (
                  <div className="flex items-center gap-2 text-zinc-400">
                    <div className="p-1.5 rounded-lg bg-zinc-800">
                      <Mail className="h-3.5 w-3.5" />
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-white/90 leading-none">{effectiveEmail}</span>
                      <div className="mt-1">
                        <VerificationBadge status={effectiveVerificationStatus} size="sm" />
                      </div>
                    </div>
                  </div>
                )}

              </div>
            </div>

            {onRerun && (
              <Button variant="outline" size="sm" onClick={onRerun}
                className="h-8 px-3 text-[10px] font-black uppercase bg-white/5 border-white/10 text-white hover:bg-white/10 gap-1.5 shrink-0 self-start">
                <RotateCcw className="h-3 w-3" /> Re-run
              </Button>
            )}
          </div>
        </div>

        {/* Metrics strip */}
        <div className="relative border-t border-white/[0.07] bg-black/30">
          <div className="max-w-7xl mx-auto px-4 md:px-8 py-3 flex items-center gap-5 overflow-x-auto scrollbar-none">
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[9px] font-black uppercase text-white/40 tracking-widest">Lead Score</span>
              <span className="text-xl font-black text-blue-400 leading-none">
                {data.lead_score || (typeof data.lead_score_analysis === "object" ? data.lead_score_analysis?.total_lead_score : "—")}
              </span>
            </div>
            <div className="h-4 w-px bg-white/10 shrink-0" />
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[9px] font-black uppercase text-white/40 tracking-widest">Heat</span>
              <span className="text-xl font-black text-amber-400 leading-none">{data.buyer_journey_analysis?.sentiment_score || "—"}</span>
            </div>
            <div className="h-4 w-px bg-white/10 shrink-0" />
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[9px] font-black uppercase text-white/40 tracking-widest">Journey</span>
              <span className="text-[11px] font-black text-white uppercase tracking-tight">
                {data.buyer_journey_analysis?.journey_stage || (data.post_engagements?.length ? "Consideration" : "Awareness")}
              </span>
            </div>
            <div className="h-4 w-px bg-white/10 shrink-0" />
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[9px] font-black uppercase text-white/40 tracking-widest">Status</span>
              <span className={cn("text-[10px] font-black uppercase",
                outreachStatus === "completed" ? "text-emerald-400" :
                outreachStatus === "in_progress" ? "text-amber-400" : "text-white/60"
              )}>
                {currentStatus.label}
              </span>
            </div>
            {(data.extra_metadata?.lead_source || (data as any).input_lead_data?.lead_source) && (
              <>
                <div className="h-4 w-px bg-white/10 shrink-0" />
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[9px] font-black uppercase text-white/40 tracking-widest">Source</span>
                  <span className="text-[10px] font-black text-white/80 uppercase">
                    {(data.extra_metadata?.lead_source || (data as any).input_lead_data?.lead_source || "").replace(/_/g, " ")}
                  </span>
                </div>
              </>
            )}
            {discoverySource && (
              <>
                <div className="h-4 w-px bg-white/10 shrink-0" />
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[9px] font-black uppercase text-white/40 tracking-widest">Discovery</span>
                  <span className="text-[10px] font-black text-amber-400 uppercase">
                    {discoverySource.replace(/_/g, " ")}
                  </span>
                </div>
              </>
            )}
            {isOutreachEdited && (
              <>
                <div className="h-4 w-px bg-white/10 shrink-0" />
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[9px] font-black uppercase text-white/40 tracking-widest">Edited</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xl font-black text-amber-400 leading-none">{editDepthPercentage}%</span>
                    <Edit2 className="h-3 w-3 text-amber-400/60" />
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── TAB BAR ───────────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-30 bg-white/90 dark:bg-zinc-950/90 backdrop-blur-md border-b border-zinc-200 dark:border-zinc-800">
        <div className="max-w-7xl mx-auto px-4 md:px-6 flex items-center justify-between">
          <div className="flex">
            {([
              { id: "actions", label: "Actions", icon: <Zap className="h-3.5 w-3.5" /> },
              { id: "intel", label: "Intel", icon: <Search className="h-3.5 w-3.5" /> },
              { id: "signals", label: "Signals", icon: <BarChart3 className="h-3.5 w-3.5" /> },
            ] as const).map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-2 px-4 py-3.5 text-[11px] font-black uppercase tracking-widest border-b-2 transition-all",
                  activeTab === tab.id
                    ? "border-primary text-primary"
                    : "border-transparent text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-300",
                )}>
                {tab.icon}{tab.label}
              </button>
            ))}
          </div>
          {/* Status pill always visible */}
          <div className="flex items-center gap-2">
            <Badge className={cn("text-[9px] font-black uppercase tracking-widest border-none px-2.5 h-6", currentStatus.className)}>
              {currentStatus.label}
            </Badge>
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════════
          ACTIONS TAB
         ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === "actions" && (
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 space-y-6">

          {/* Status action bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
            <div className="flex items-center gap-2">
              <div className={cn("h-2 w-2 rounded-full", outreachStatus === "completed" ? "bg-emerald-500" : outreachStatus === "in_progress" ? "bg-amber-500 animate-pulse" : "bg-zinc-400")} />
              <span className="text-[11px] font-black uppercase text-zinc-600 dark:text-zinc-400 tracking-widest">{currentStatus.label}</span>
            </div>
            <div className="flex items-center gap-2">
              {outreachStatus === "not_started" && (
                <Button size="sm" onClick={() => handleUpdateStatus("in_progress")} disabled={isUpdatingStatus}
                  className="h-8 gap-1.5 text-[10px] font-black uppercase shadow-sm shadow-primary/20">
                  <Zap className="h-3 w-3" /> Start Outreach
                </Button>
              )}
              {outreachStatus === "in_progress" && (
                <Button size="sm" onClick={() => handleUpdateStatus("completed")} disabled={isUpdatingStatus}
                  className="h-8 gap-1.5 text-[10px] font-black uppercase bg-emerald-600 hover:bg-emerald-700 shadow-sm shadow-emerald-500/20">
                  <Check className="h-3 w-3" /> Mark Completed
                </Button>
              )}
              {outreachStatus === "completed" && (
                <Button size="sm" variant="outline" onClick={() => handleUpdateStatus("in_progress")} disabled={isUpdatingStatus}
                  className="h-8 gap-1.5 text-[10px] font-black uppercase">
                  <RotateCcw className="h-3 w-3" /> Re-open
                </Button>
              )}
            </div>
          </div>

          {/* CSO Strategic Command */}
          {briefing && (
            <div className="space-y-4">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2.5">
                  <div className="h-7 w-7 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                    <ShieldCheck className="h-3.5 w-3.5 text-amber-500" />
                  </div>
                  <span className="text-sm font-black uppercase tracking-tight text-zinc-900 dark:text-zinc-100">CSO Strategic Command</span>
                  <Badge variant="outline" className="border-amber-500/30 text-amber-600 dark:text-amber-500 bg-amber-500/5 text-[9px] font-black uppercase h-5 px-2">Unified Verdict</Badge>
                </div>
                <Button size="sm" variant="ghost" onClick={() => setIsProofOpen(true)}
                  className="h-7 px-2.5 text-[10px] font-black uppercase text-zinc-400 hover:text-primary gap-1.5">
                  <BookOpen className="h-3 w-3" /> View Proofs
                </Button>
              </div>
              <div className="cursor-pointer" onClick={() => setIsProofOpen(true)}>
                <CSOCommandCard data={briefing.unified_command} />
              </div>
              {briefing.advanced_strategic_pivots && briefing.advanced_strategic_pivots.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {briefing.advanced_strategic_pivots.map((pivot: string, i: number) => (
                    <div key={i} className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/10 hover:border-amber-500/25 transition-all">
                      <div className="text-[13px] font-bold text-zinc-700 dark:text-zinc-300 italic leading-relaxed">
                        <ReactMarkdown>{pivot}</ReactMarkdown>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Outreach section */}
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
            {/* Header */}
            <div className="px-5 py-4 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10 text-primary"><Target className="h-4 w-4" /></div>
                <div>
                  <h2 className="text-sm font-black uppercase tracking-tight text-zinc-900 dark:text-zinc-100">Outreach Playbook</h2>
                  <p className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider">
                    {isSequence ? "Multi-touch Sequence" : "Campaign Drafts"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {isOutreachEdited && (
                  <Badge variant="outline" className="h-7 px-2.5 gap-1.5 border-amber-500/30 text-amber-600 bg-amber-500/5 text-[9px] font-black uppercase">
                    <Edit2 className="h-2.5 w-2.5" /> Edited · {editDepthPercentage}%
                  </Badge>
                )}
                {isEditingOutreach ? (
                  <div className="flex gap-2">
                    <Button size="sm" variant="ghost" onClick={() => setIsEditingOutreach(false)} disabled={isSavingOutreach}
                      className="h-8 gap-1.5 text-[10px] font-black uppercase">
                      <X className="h-3 w-3" /> Cancel
                    </Button>
                    <Button size="sm" onClick={handleSaveOutreach} disabled={isSavingOutreach}
                      className="h-8 gap-1.5 text-[10px] font-black uppercase">
                      {isSavingOutreach ? <RotateCcw className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
                      Save Draft
                    </Button>
                  </div>
                ) : (
                  <Button size="sm" variant="outline" onClick={() => setIsEditingOutreach(true)}
                    className="h-8 gap-1.5 text-[10px] font-black uppercase border-dashed">
                    <Edit2 className="h-3 w-3" /> Edit
                  </Button>
                )}
              </div>
            </div>

            {/* Variant selector */}
            {hasVariants && campaignVariants.length > 1 && (
              <div className="px-5 py-3 border-b border-zinc-100 dark:border-zinc-800 flex flex-wrap items-center gap-2">
                <span className="text-[9px] font-black uppercase text-zinc-400 tracking-widest mr-1">Variant</span>
                {campaignVariants.map((v: any, i: number) => (
                  <button key={i} onClick={() => setSelectedVariantIndex(i)}
                    className={cn("px-3 py-1 rounded-md text-[10px] font-black uppercase tracking-tight transition-all flex items-center gap-1.5",
                      selectedVariantIndex === i
                        ? "bg-primary text-white"
                        : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700")}>
                    {v.variant_name || `Variant ${i + 1}`}
                    {v._edit_depth > 0 && (
                        <span className="text-[8px] opacity-70">· {v._edit_depth}%</span>
                    )}
                  </button>
                ))}
                {activeOutreach?.primary_pain_point && (
                  <span className="ml-2 text-[11px] text-zinc-500 italic truncate hidden md:inline">
                    "{activeOutreach.primary_pain_point}"
                  </span>
                )}
              </div>
            )}

            {/* Tactical / Strategic tabs (only show strategic tab if CSO content exists) */}
            {strategicActions.length > 0 && (
              <div className="px-5 pt-3 flex gap-4 border-b border-zinc-100 dark:border-zinc-800">
                {(["tactical", "strategic"] as const).map(t => (
                  <button key={t} onClick={() => setActiveOutreachTab(t)}
                    className={cn("pb-2.5 text-[10px] font-black uppercase tracking-widest border-b-2 transition-all",
                      activeOutreachTab === t ? "border-primary text-primary" : "border-transparent text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300")}>
                    {t === "tactical" ? (isSequence ? "Full Sequence" : "Rapid Execution") : "CSO Strategic"}
                  </button>
                ))}
              </div>
            )}

            {/* Outreach content */}
            <div className="p-5">
              {/* Exit strategy / fit reasoning note */}
              {(activeOutreach?.exit_strategy || activeOutreach?.fit_reasoning) && (
                <div className="mb-4 flex items-start gap-2.5 p-3 rounded-lg bg-amber-500/5 border border-amber-500/10">
                  <Zap className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
                  <p className="text-[12px] font-medium text-zinc-700 dark:text-zinc-300 italic leading-relaxed">
                    "{activeOutreach.exit_strategy || activeOutreach.fit_reasoning}"
                  </p>
                </div>
              )}

              {/* Sequence steps (timeline) */}
              {activeOutreachTab === "tactical" && isSequence && (
                <div className="relative ml-3 pl-7 border-l-2 border-zinc-100 dark:border-zinc-800 space-y-4">
                  {tacticalActions.map((action: any, i: number) => (
                    <div key={i} className="relative">
                      {/* Timeline node */}
                      <div className={cn(
                        "absolute -left-[35px] top-3 h-6 w-6 rounded-full border-2 border-white dark:border-zinc-950 flex items-center justify-center z-10 text-white text-[9px] font-black shadow-sm",
                        action.type === "email" ? "bg-zinc-800" : "bg-primary",
                      )}>
                        {action.type === "email" ? <Mail className="h-2.5 w-2.5" /> : <Linkedin className="h-2.5 w-2.5" />}
                      </div>

                      <div className="bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700 rounded-xl p-4 hover:border-primary/30 transition-all">
                        <div className="flex items-center justify-between gap-2 mb-3">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[10px] font-black text-zinc-500 uppercase tracking-tight">{action.title}</span>
                            <Badge className="bg-primary/10 text-primary border-none text-[8px] font-black uppercase h-4 px-1.5">
                              {action.narrative_angle || (action.type === "email" ? "Email" : "LinkedIn")}
                            </Badge>
                            {action.delay_days !== undefined && (
                              <Badge variant="outline" className="text-[8px] font-black text-zinc-400 h-4 px-1.5">
                                Day {action.delay_days}
                              </Badge>
                            )}
                            {action.trigger === "if_no_reply" && (
                              <Badge variant="outline" className="text-[8px] font-black text-amber-500 border-amber-500/30 h-4 px-1.5">
                                If No Reply
                              </Badge>
                            )}
                            {action.cta_type && (
                              <Badge variant="outline" className="text-[8px] font-black text-indigo-500 border-indigo-500/30 h-4 px-1.5 uppercase">
                                {action.cta_type.replace(/_/g, " ")}
                              </Badge>
                            )}
                            {/* Per-step edited indicator */}
                            {action._edit_depth > 0 && (
                                <Badge variant="outline" className="text-[8px] font-black text-emerald-500 border-emerald-500/30 h-4 px-1.5 gap-1">
                                    <Edit2 className="h-2 w-2" /> {action._edit_depth}% Edited
                                </Badge>
                            )}
                          </div>
                          <CopyButton text={isEditingOutreach ? (editedOutreach.steps?.[i]?.draft || action.content) : action.content} label="Copy" />
                        </div>
                        {(action.email_subject || (isEditingOutreach && action.type === "email")) && (
                          <div className="flex flex-col gap-1.5 mb-3 py-2 px-3 rounded-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700">
                            <span className="text-[9px] font-black text-zinc-400 uppercase">Subject:</span>
                            {isEditingOutreach ? (
                              <div className="space-y-2">
                                <Input
                                  value={editedOutreach.steps?.[i]?.email_subject || ""}
                                  onChange={(e) => {
                                    const newSteps = [...(editedOutreach.steps || [])];
                                    if (newSteps[i]) newSteps[i] = { ...newSteps[i], email_subject: e.target.value };
                                    setEditedOutreach((p: any) => ({ ...p, steps: newSteps }));
                                  }}
                                  className="h-8 text-[12px] font-bold bg-transparent border-primary/20 focus:border-primary/50"
                                  placeholder="Enter email subject..."
                                />
                                <Input
                                  value={editedOutreach.steps?.[i]?.preview_text || ""}
                                  onChange={(e) => {
                                    const newSteps = [...(editedOutreach.steps || [])];
                                    if (newSteps[i]) newSteps[i] = { ...newSteps[i], preview_text: e.target.value };
                                    setEditedOutreach((p: any) => ({ ...p, steps: newSteps }));
                                  }}
                                  className="h-7 text-[10px] bg-transparent border-primary/10 focus:border-primary/30 italic"
                                  placeholder="Mobile preview text..."
                                />
                                {action.subject_line_variants?.length > 0 && (
                                  <div className="pt-1 flex flex-wrap gap-2">
                                    {action.subject_line_variants.map((v: string, idx: number) => (
                                      <TooltipProvider key={idx}>
                                        <Tooltip>
                                          <TooltipTrigger asChild>
                                            <Badge 
                                              variant="secondary" 
                                              className="cursor-pointer bg-primary/10 text-primary border-primary/20 hover:bg-primary/20 text-[8px] font-bold transition-colors"
                                              onClick={() => {
                                                const newSteps = [...(editedOutreach.steps || [])];
                                                if (newSteps[i]) newSteps[i] = { ...newSteps[i], email_subject: v };
                                                setEditedOutreach((p: any) => ({ ...p, steps: newSteps }));
                                              }}
                                            >
                                              Use Alt {idx + 1}
                                            </Badge>
                                          </TooltipTrigger>
                                          <TooltipContent>
                                            <p className="text-[11px]">{v}</p>
                                          </TooltipContent>
                                        </Tooltip>
                                      </TooltipProvider>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ) : (
                              <div className="space-y-1.5">
                                <span className="text-[12px] font-bold text-zinc-900 dark:text-zinc-100">
                                  {selectedSubjectVariants[`var_${selectedVariantIndex}_step_${i}`] || action.email_subject}
                                </span>
                                {action.preview_text && (
                                  <p className="text-[10px] text-zinc-400 font-medium italic truncate">
                                    Preview: {action.preview_text}
                                  </p>
                                )}
                                {action.subject_line_variants?.length > 0 && (
                                  <div className="pt-1 flex flex-wrap gap-2">
                                    {action.subject_line_variants.map((v: string, idx: number) => {
                                      const isSelected = selectedSubjectVariants[`var_${selectedVariantIndex}_step_${i}`] === v;
                                      return (
                                        <TooltipProvider key={idx}>
                                          <Tooltip>
                                            <TooltipTrigger asChild>
                                              <Badge 
                                                variant="secondary" 
                                                className={cn(
                                                  "cursor-pointer text-[8px] font-bold transition-colors",
                                                  isSelected 
                                                    ? "bg-primary/20 text-primary border border-primary/30" 
                                                    : "bg-zinc-50 dark:bg-zinc-800 hover:bg-zinc-100"
                                                )}
                                                onClick={() => {
                                                  setSelectedSubjectVariants(prev => ({ 
                                                    ...prev, 
                                                    [`var_${selectedVariantIndex}_step_${i}`]: v 
                                                  }));
                                                  toast({
                                                    title: "Subject Swapped",
                                                    description: `Swapped to variant ${idx + 1}.`,
                                                  });
                                                }}
                                              >
                                                {isSelected ? `Active: Alt ${idx + 1}` : `Swap to Alt ${idx + 1}`}
                                              </Badge>
                                            </TooltipTrigger>
                                            <TooltipContent>
                                              <p className="text-[11px]">{v}</p>
                                            </TooltipContent>
                                          </Tooltip>
                                        </TooltipProvider>
                                      );
                                    })}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                        {action.internal_note && (
                          <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-tight mb-2">Note: {action.internal_note}</p>
                        )}
                        <div className="prose prose-zinc dark:prose-invert max-w-none text-[13px] leading-relaxed font-medium text-zinc-700 dark:text-zinc-300 italic border-l-2 border-primary/10 pl-3">
                          {isEditingOutreach ? (
                            <div className="space-y-3">
                              <Textarea
                                value={editedOutreach.steps?.[i]?.draft || ""}
                                onChange={(e) => {
                                  const newSteps = [...(editedOutreach.steps || [])];
                                  if (newSteps[i]) newSteps[i] = { ...newSteps[i], draft: e.target.value };
                                  setEditedOutreach((p: any) => ({ ...p, steps: newSteps }));
                                }}
                                className="min-h-[120px] text-[13px] leading-relaxed resize-none bg-transparent border-primary/20 focus:border-primary/50"
                                placeholder="Enter draft content..."
                              />
                              <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800">
                                <span className="text-[9px] font-black text-zinc-400 uppercase mb-1 block">P.S. Line:</span>
                                <Input
                                  value={editedOutreach.steps?.[i]?.ps_line || ""}
                                  onChange={(e) => {
                                    const newSteps = [...(editedOutreach.steps || [])];
                                    if (newSteps[i]) newSteps[i] = { ...newSteps[i], ps_line: e.target.value };
                                    setEditedOutreach((p: any) => ({ ...p, steps: newSteps }));
                                  }}
                                  className="h-8 text-[11px] bg-transparent border-primary/10 focus:border-primary/30 italic text-primary"
                                  placeholder="Add a P.S. line..."
                                />
                              </div>
                            </div>
                          ) : (
                            <div className="space-y-3">
                              <ReactMarkdown>{action.draft || action.content || ""}</ReactMarkdown>
                              {action.ps_line && (
                                <div className="mt-4 pt-3 border-t border-zinc-100 dark:border-zinc-700/50">
                                  <p className="text-[12px] font-bold text-primary italic">
                                    <span className="text-[10px] uppercase tracking-widest mr-2 opacity-50">P.S.</span>
                                    {action.ps_line}
                                  </p>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Legacy non-sequence outreach (LinkedIn + Email cards) */}
              {activeOutreachTab === "tactical" && !isSequence && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {tacticalActions.map((action: any, i: number) => (
                    <div key={i} className={cn("rounded-xl p-5 space-y-3 border", action.type === "email" ? "bg-zinc-900 border-zinc-800" : "bg-zinc-50 dark:bg-zinc-800/50 border-zinc-200 dark:border-zinc-700")}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className={cn("p-1.5 rounded-lg", action.type === "email" ? "bg-primary/20 text-primary" : "bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 text-primary shadow-sm")}>
                            {action.icon}
                          </div>
                          <span className={cn("text-[10px] font-black uppercase tracking-widest", action.type === "email" ? "text-zinc-400" : "text-zinc-500")}>
                            {action.title}
                          </span>
                        </div>
                        <CopyButton text={action.type === "linkedin" && isEditingOutreach ? editedOutreach.linkedin_message : action.type === "email" && action.title.includes("Subject") && isEditingOutreach ? editedOutreach.email_subject : action.type === "email" && isEditingOutreach ? editedOutreach.email_body : action.content} />
                      </div>
                      {isEditingOutreach ? (
                        <Textarea
                          value={action.title.toLowerCase().includes("subject") ? editedOutreach.email_subject : action.title.toLowerCase().includes("linkedin") ? editedOutreach.linkedin_message : editedOutreach.email_body}
                          onChange={(e) => {
                            const val = e.target.value;
                            if (action.title.toLowerCase().includes("subject")) setEditedOutreach((p: any) => ({ ...p, email_subject: val }));
                            else if (action.title.toLowerCase().includes("linkedin")) setEditedOutreach((p: any) => ({ ...p, linkedin_message: val }));
                            else setEditedOutreach((p: any) => ({ ...p, email_body: val }));
                          }}
                          className={cn("min-h-[100px] text-[13px] leading-relaxed resize-none", action.type === "email" ? "bg-zinc-800 border-zinc-700 text-zinc-100" : "")}
                        />
                      ) : (
                        <div className={cn("prose prose-zinc dark:prose-invert max-w-none text-[13px] leading-relaxed font-medium italic border-l-2 pl-3", action.type === "email" ? "text-zinc-200 border-primary/20" : "text-zinc-800 dark:text-zinc-200 border-primary/10")}>
                          <ReactMarkdown>{action.content}</ReactMarkdown>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Strategic (CSO) tab */}
              {activeOutreachTab === "strategic" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {strategicActions.map((action: any, i: number) => (
                    <div key={i} className={cn("rounded-xl p-5 space-y-3 border", action.type === "email" ? "bg-zinc-900 border-zinc-800" : "bg-zinc-50 dark:bg-zinc-800/50 border-zinc-200 dark:border-zinc-700")}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className={cn("p-1.5 rounded-lg", action.type === "email" ? "bg-primary/20 text-primary" : "bg-white dark:bg-zinc-900 border border-zinc-200 text-primary shadow-sm")}>
                            {action.icon}
                          </div>
                          <span className={cn("text-[10px] font-black uppercase tracking-widest", action.type === "email" ? "text-zinc-400" : "text-zinc-500")}>{action.title}</span>
                          <Badge variant="outline" className="text-[8px] font-black text-amber-500 border-amber-500/30 h-4 px-1.5">CSO</Badge>
                          {action._edit_depth > 0 && (
                            <Badge variant="outline" className="text-[8px] font-black text-emerald-500 border-emerald-500/30 h-4 px-1.5 gap-1">
                                <Edit2 className="h-2 w-2" /> {action._edit_depth}% Edited
                            </Badge>
                          )}
                        </div>
                        <CopyButton text={isEditingOutreach ? (action.type === "linkedin" ? editedStrategicOutreach.linkedin_message : editedStrategicOutreach.email_body) : action.content} />
                      </div>
                      {isEditingOutreach ? (
                        <Textarea
                          value={action.type === "linkedin" ? editedStrategicOutreach.linkedin_message : editedStrategicOutreach.email_body}
                          onChange={(e) => {
                            const val = e.target.value;
                            if (action.type === "linkedin") setEditedStrategicOutreach((p: any) => ({ ...p, linkedin_message: val }));
                            else setEditedStrategicOutreach((p: any) => ({ ...p, email_body: val }));
                          }}
                          className={cn("min-h-[100px] text-[13px] leading-relaxed resize-none", action.type === "email" ? "bg-zinc-800 border-zinc-700 text-zinc-100" : "")}
                        />
                      ) : (
                        <div className={cn("prose prose-zinc dark:prose-invert max-w-none text-[13px] leading-relaxed font-medium italic border-l-2 pl-3", action.type === "email" ? "text-zinc-200 border-primary/20" : "text-zinc-800 dark:text-zinc-200 border-primary/10")}>
                          <ReactMarkdown>{action.content}</ReactMarkdown>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Hook / strategic angle */}
              {hook && activeOutreachTab === "tactical" && (
                <div className="mt-4 flex items-start gap-3 p-4 rounded-xl bg-zinc-100 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-700">
                  <div className="p-2 rounded-lg bg-white dark:bg-zinc-900 text-amber-500 border border-amber-100 dark:border-amber-900/30 shrink-0">
                    <Zap className="h-4 w-4" />
                  </div>
                  <div className="space-y-1 flex-1 min-w-0">
                    <span className="text-[9px] font-black uppercase tracking-widest text-zinc-500">Psychological Hook</span>
                    {isEditingOutreach ? (
                      <Textarea value={editedOutreach.hook} onChange={(e) => setEditedOutreach((p: any) => ({ ...p, hook: e.target.value }))}
                        className="min-h-[60px] text-[13px] italic resize-none" placeholder="Strategic hook..." />
                    ) : (
                      <p className="text-[14px] font-black text-zinc-900 dark:text-white italic leading-snug">"{hook}"</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Buyer Journey */}
          {data.buyer_journey_analysis && (
              <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
                <div className="px-5 py-3.5 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-primary" />
                    <span className="text-sm font-black uppercase tracking-tight">Buyer Journey</span>
                  </div>
                  {isEditingJourney ? (
                    <div className="flex gap-1.5">
                      <Button size="sm" variant="ghost" onClick={() => { setIsEditingJourney(false); setEditedJourney({ ...data.buyer_journey_analysis }); }} disabled={isSavingJourney} className="h-7 px-2.5 text-[10px] font-black uppercase gap-1">
                        <X className="h-2.5 w-2.5" /> Cancel
                      </Button>
                      <Button size="sm" onClick={handleSaveJourney} disabled={isSavingJourney} className="h-7 px-2.5 text-[10px] font-black uppercase gap-1">
                        {isSavingJourney ? <RotateCcw className="h-2.5 w-2.5 animate-spin" /> : <Save className="h-2.5 w-2.5" />} Save
                      </Button>
                    </div>
                  ) : (
                    <Button size="sm" variant="ghost" onClick={() => setIsEditingJourney(true)}
                      className="h-7 px-2.5 text-[10px] font-black uppercase text-zinc-400 gap-1.5">
                      <Edit2 className="h-3 w-3" /> Edit
                    </Button>
                  )}
                </div>
                <div className="p-4 space-y-3">
                  <div className="grid grid-cols-3 gap-3">
                    {/* Stage */}
                    <div className="p-3 rounded-xl bg-zinc-900 text-white col-span-1 space-y-2">
                      <div className="text-[9px] font-black uppercase text-zinc-500 tracking-widest">Stage</div>
                      {isEditingJourney ? (
                        <Input value={editedJourney?.journey_stage || ""} onChange={(e) => setEditedJourney((p: any) => ({ ...p, journey_stage: e.target.value }))} className="h-7 text-xs bg-white/10 border-white/20 text-white uppercase" />
                      ) : (
                        <div className="text-sm font-black italic text-white uppercase leading-tight">{data.buyer_journey_analysis.journey_stage || "Discovery"}</div>
                      )}
                      <div className="h-1 w-full bg-white/10 rounded-full overflow-hidden">
                        <div className="h-full bg-primary" style={{ width: `${(isEditingJourney ? editedJourney?.sentiment_score : data.buyer_journey_analysis.sentiment_score) || 50}%` }} />
                      </div>
                    </div>
                    {/* Heat */}
                    <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 space-y-2">
                      <div className="text-[9px] font-black uppercase text-zinc-500 tracking-widest">Heat</div>
                      {isEditingJourney ? (
                        <Input type="number" min="0" max="100" value={editedJourney?.sentiment_score || 50}
                          onChange={(e) => setEditedJourney((p: any) => ({ ...p, sentiment_score: parseInt(e.target.value) }))}
                          className="h-7 text-lg font-black text-amber-500 bg-amber-500/5 border-amber-500/20 w-full" />
                      ) : (
                        <div className="text-2xl font-black text-amber-500 italic">{data.buyer_journey_analysis.sentiment_score || 50}</div>
                      )}
                      {isEditingJourney ? (
                        <select value={editedJourney?.urgency_level} onChange={(e) => setEditedJourney((p: any) => ({ ...p, urgency_level: e.target.value }))}
                          className="w-full text-[9px] font-black uppercase border rounded px-1 py-0.5 bg-white dark:bg-zinc-900">
                          {["Low", "Medium", "High", "Critical"].map(u => <option key={u} value={u}>{u}</option>)}
                        </select>
                      ) : (
                        <Badge className={cn("text-[9px] font-black uppercase border-none px-1.5 h-4",
                          data.buyer_journey_analysis.urgency_level === "High" || data.buyer_journey_analysis.urgency_level === "Critical" ? "bg-rose-500 text-white" : "bg-zinc-200 dark:bg-zinc-700 text-zinc-600 dark:text-zinc-400")}>
                          {data.buyer_journey_analysis.urgency_level || "Normal"}
                        </Badge>
                      )}
                    </div>
                    {/* Optimal play */}
                    <div className="p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/10 space-y-1.5">
                      <div className="text-[9px] font-black uppercase text-emerald-600/70 tracking-widest">Play</div>
                      {isEditingJourney ? (
                        <Textarea value={editedJourney?.optimal_play || ""} onChange={(e) => setEditedJourney((p: any) => ({ ...p, optimal_play: e.target.value }))} className="min-h-[60px] text-[11px] bg-emerald-500/5 border-emerald-500/20 resize-none" />
                      ) : (
                        <p className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-400 italic leading-relaxed">"{data.buyer_journey_analysis.optimal_play}"</p>
                      )}
                    </div>
                  </div>
                  {/* Strategic reasoning */}
                  <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
                    <div className="text-[9px] font-black uppercase text-zinc-400 tracking-widest mb-1.5 flex items-center gap-1.5">
                      <MessageSquareQuote className="h-3 w-3" /> Strategic Reasoning
                    </div>
                    {isEditingJourney ? (
                      <Textarea value={editedJourney?.strategic_reasoning || ""} onChange={(e) => setEditedJourney((p: any) => ({ ...p, strategic_reasoning: e.target.value }))} className="min-h-[60px] text-[12px] italic resize-none" />
                    ) : (
                      <p className="text-[13px] text-zinc-600 dark:text-zinc-400 italic leading-relaxed">{data.buyer_journey_analysis.strategic_reasoning}</p>
                    )}
                  </div>
                </div>
              </div>
            )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          INTEL TAB
         ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === "intel" && (
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 flex gap-6 items-start">
          {/* Left nav */}
          <aside className="w-52 shrink-0 sticky top-[106px]">
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
              {INTEL_GROUPS.map((group) => (
                <div key={group.label} className="border-b border-zinc-100 dark:border-zinc-800 last:border-0">
                  <div className="px-3 py-2 text-[9px] font-black uppercase tracking-widest text-zinc-400 bg-zinc-50 dark:bg-zinc-800/50">
                    {group.label}
                  </div>
                  {group.sections.map((s) => (
                    <button key={s.id} onClick={() => setActiveIntelSection(s.id)}
                      className={cn(
                        "w-full flex items-center gap-2.5 px-3 py-2.5 text-[11px] font-bold text-left transition-all",
                        activeIntelSection === s.id
                          ? "bg-primary/5 text-primary border-l-2 border-primary"
                          : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800 border-l-2 border-transparent",
                      )}>
                      <span className={activeIntelSection === s.id ? "text-primary" : "text-zinc-400"}>{s.icon}</span>
                      {s.title}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </aside>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">

              {/* Section header */}
              <div className="px-6 py-4 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
                <div>
                  {INTEL_GROUPS.flatMap(g => g.sections).find(s => s.id === activeIntelSection) && (
                    <div className="flex items-center gap-2.5">
                      <span className="text-primary">{INTEL_GROUPS.flatMap(g => g.sections).find(s => s.id === activeIntelSection)!.icon}</span>
                      <h2 className="text-sm font-black uppercase tracking-tight text-zinc-900 dark:text-zinc-100">
                        {INTEL_GROUPS.flatMap(g => g.sections).find(s => s.id === activeIntelSection)!.title}
                      </h2>
                    </div>
                  )}
                </div>
                {/* Edit button for strategic command */}
                {activeIntelSection === "synthesis" && data.sales_research_report?.advanced_next_steps && (
                  isEditingStrategicCommand ? (
                    <div className="flex gap-2">
                      <Button size="sm" variant="ghost" onClick={() => setIsEditingStrategicCommand(false)} disabled={isSavingStrategic}
                        className="h-7 px-2.5 text-[10px] font-black uppercase gap-1">
                        <X className="h-2.5 w-2.5" /> Cancel
                      </Button>
                      <Button size="sm" onClick={handleSaveStrategicCommand} disabled={isSavingStrategic}
                        className="h-7 px-2.5 text-[10px] font-black uppercase gap-1">
                        {isSavingStrategic ? <RotateCcw className="h-2.5 w-2.5 animate-spin" /> : <Save className="h-2.5 w-2.5" />} Save
                      </Button>
                    </div>
                  ) : (
                    <Button size="sm" variant="outline" onClick={() => { setEditedStrategicCommand(data.sales_research_report.advanced_next_steps); setIsEditingStrategicCommand(true); }}
                      className="h-7 px-2.5 text-[10px] font-black uppercase border-dashed gap-1">
                      <Edit2 className="h-2.5 w-2.5" /> Edit Steps
                    </Button>
                  )
                )}
              </div>

              {/* Section content */}
              <div className="p-6">
                {/* CSO Verdict */}
                {activeIntelSection === "cso-verdict" && briefing && (
                  <div className="space-y-6">
                    <div className="cursor-pointer" onClick={() => setIsProofOpen(true)}>
                      <CSOCommandCard data={briefing.unified_command} />
                    </div>
                    {briefing.executive_blueprint_summary && (
                      <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 space-y-2">
                        <h4 className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Executive Summary</h4>
                        <p className="text-[14px] text-zinc-700 dark:text-zinc-300 leading-relaxed">{briefing.executive_blueprint_summary}</p>
                      </div>
                    )}
                    {briefing.advanced_strategic_pivots?.length && (
                      <div className="space-y-3">
                        <h4 className="text-[10px] font-black uppercase tracking-widest text-zinc-400 flex items-center gap-2">
                          <Zap className="h-3 w-3 text-amber-500" /> Advanced Strategic Pivots
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {briefing.advanced_strategic_pivots.map((pivot, i) => (
                            <div key={i} className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/10 text-[13px] font-bold text-zinc-700 dark:text-zinc-300 italic leading-relaxed">
                              <ReactMarkdown>{pivot}</ReactMarkdown>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Executive Blueprint */}
                {activeIntelSection === "synthesis" && (
                  <div className="space-y-6">
                    {/* Advanced next steps with editing */}
                    {(data.sales_research_report?.advanced_next_steps || editedStrategicCommand.length > 0) && (
                      <div className="space-y-3 pb-6 border-b border-zinc-100 dark:border-zinc-800">
                        <h3 className="text-[10px] font-black uppercase tracking-widest text-zinc-400 flex items-center gap-2">
                          <Zap className="h-3 w-3 text-primary" /> Advanced Next Steps
                        </h3>
                        <div className="relative pl-5 border-l-2 border-primary/20 space-y-3">
                          {(isEditingStrategicCommand ? editedStrategicCommand : data.sales_research_report?.advanced_next_steps || []).map((step: any, i: number) => (
                            <div key={i} className="relative">
                              <div className="absolute -left-[22px] top-3 h-4 w-4 rounded-full bg-white dark:bg-zinc-900 border-2 border-primary flex items-center justify-center text-[8px] font-black text-primary">{i + 1}</div>
                              {isEditingStrategicCommand ? (
                                <div className="space-y-1">
                                  <Textarea value={step} onChange={(e) => { const ns = [...editedStrategicCommand]; ns[i] = e.target.value; setEditedStrategicCommand(ns); }}
                                    className="min-h-[80px] text-[13px] font-bold italic resize-none" />
                                  <Button size="sm" variant="ghost" onClick={() => setEditedStrategicCommand(editedStrategicCommand.filter((_, idx) => idx !== i))}
                                    className="h-5 text-[9px] text-rose-500 hover:text-rose-600 uppercase">Remove</Button>
                                </div>
                              ) : (
                                <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-[13px] font-bold text-zinc-900 dark:text-zinc-100 italic leading-relaxed">
                                  <ReactMarkdown>{String(step)}</ReactMarkdown>
                                </div>
                              )}
                            </div>
                          ))}
                          {isEditingStrategicCommand && (
                            <Button size="sm" variant="outline" onClick={() => setEditedStrategicCommand([...editedStrategicCommand, ""])}
                              className="h-7 text-[10px] font-black uppercase border-dashed gap-1 w-full">
                              <Plus className="h-3 w-3" /> Add Step
                            </Button>
                          )}
                        </div>
                      </div>
                    )}
                    <IntelContent content={data.sales_research_report} excludeKeys={["advanced_next_steps"]} />
                  </div>
                )}

                {/* Discovery Intelligence */}
                {activeIntelSection === "discovery" && (
                  <div className="space-y-6">
                    <div className="p-5 rounded-xl bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 shadow-sm">
                      <div className="flex items-center gap-2 mb-3">
                        <Badge className="bg-primary/10 text-primary border-none text-[9px] font-black uppercase">{discoverySource}</Badge>
                      </div>
                      <div className="prose prose-zinc dark:prose-invert max-w-none text-[14px] leading-[1.8] italic">
                        <ReactMarkdown>{extraMeta.lead_extracted_data?.discovery_insights || inputLead.lead_extracted_data?.discovery_insights || "No discovery insights."}</ReactMarkdown>
                      </div>
                    </div>
                    {(extraMeta.discovery_context?.comments || inputLead.discovery_context?.comments) && (
                      <div className="space-y-2">
                        <h4 className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Original Context</h4>
                        <ul className="space-y-2">
                          {((extraMeta.discovery_context?.comments || inputLead.discovery_context?.comments) as string[]).map((c, i) => (
                            <li key={i} className="text-[13px] text-zinc-600 dark:text-zinc-400 italic border-l-2 border-primary/20 pl-3 py-1">"{c}"</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Profile */}
                {activeIntelSection === "profile" && <IntelContent content={data.user_profile_analysis} />}

                {/* Website */}
                {activeIntelSection === "website" && <IntelContent content={data.website_analysis} />}

                {/* Viability */}
                {activeIntelSection === "viability" && (
                  <IntelContent content={data.viability_analysis || "No viability analysis available."} />
                )}

                {/* Pain Points */}
                {activeIntelSection === "pain-points" && (
                  <IntelContent content={data.target_pain_points || "No pain point analysis available."} />
                )}

                {/* Strategic Solutions */}
                {activeIntelSection === "solutions" && (
                  <IntelContent content={data.strategic_solutions || "No strategic solutions available."} />
                )}

                {/* Lead Score */}
                {activeIntelSection === "lead-score" && data.lead_score_analysis && (
                  <div className="space-y-6">
                    {typeof data.lead_score_analysis === "object" ? (
                      <>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          {[
                            { label: "Firmographic", score: data.lead_score_analysis.score_breakdown?.firmographic_fit?.score || 0, color: "text-blue-500", bg: "bg-blue-500/5 border-blue-500/10" },
                            { label: "Persona", score: data.lead_score_analysis.score_breakdown?.persona_alignment?.score || 0, color: "text-emerald-500", bg: "bg-emerald-500/5 border-emerald-500/10" },
                            { label: "Behavioral", score: data.lead_score_analysis.score_breakdown?.behavioral_engagement?.score || 0, color: "text-orange-500", bg: "bg-orange-500/5 border-orange-500/10" },
                            { label: "Intent", score: data.lead_score_analysis.score_breakdown?.strategic_intent?.score || 0, color: "text-rose-500", bg: "bg-rose-500/5 border-rose-500/10" },
                          ].map((item) => (
                            <div key={item.label} className={cn("p-4 rounded-xl border flex flex-col items-center text-center", item.bg)}>
                              <div className={cn("text-2xl font-black", item.color)}>{item.score}</div>
                              <div className="text-[9px] font-black uppercase tracking-widest text-zinc-400 mt-1">{item.label}</div>
                            </div>
                          ))}
                        </div>
                        {data.lead_score_analysis.analysis && (
                          <div className="p-5 rounded-xl bg-zinc-900 text-zinc-300 border border-zinc-800 text-[14px] leading-relaxed italic">
                            {data.lead_score_analysis.analysis}
                          </div>
                        )}
                        {data.lead_score_analysis.lead_score_recommendations?.length > 0 && (
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {data.lead_score_analysis.lead_score_recommendations.map((rec: string, i: number) => (
                              <div key={i} className="flex items-start gap-2.5 p-3.5 rounded-xl bg-primary/5 border border-primary/10">
                                <div className="h-1.5 w-1.5 rounded-full bg-primary mt-1.5 shrink-0" />
                                <span className="text-[13px] font-bold text-zinc-700 dark:text-zinc-300 italic">{rec}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    ) : (
                      <IntelContent content={data.lead_score_analysis} />
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          SIGNALS TAB
         ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === "signals" && (() => {
        const prospectPosts = (() => {
          const pa = data.user_profile_analysis;
          if (pa && typeof pa === "object" && Array.isArray(pa.posts_analysis)) return pa.posts_analysis;
          return [];
        })();
        const conversionCount = [
          data.extra_metadata?.download_marketing_material,
          data.extra_metadata?.demo_requested,
          data.extra_metadata?.referral_partner_introduction,
        ].filter(Boolean).length;
        const hasTriggers = (data.company_news?.length || 0) + (data.hiring_data?.length || 0) > 0;

        return (
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 space-y-6">

          {/* Signal overview stats */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { label: "Social Signals", value: data.post_engagements?.length || 0, color: "text-primary", bg: "border-primary/10 bg-primary/5" },
              { label: "Emails Tracked", value: data.email_history?.length || 0, color: "text-emerald-500", bg: "border-emerald-500/10 bg-emerald-500/5" },
              { label: "Conversions", value: conversionCount, color: "text-amber-500", bg: "border-amber-500/10 bg-amber-500/5" },
              { label: "News Triggers", value: data.company_news?.length || 0, color: "text-blue-500", bg: "border-blue-500/10 bg-blue-500/5" },
              { label: "Hiring Signals", value: data.hiring_data?.length || 0, color: "text-purple-500", bg: "border-purple-500/10 bg-purple-500/5" },
              { label: "Prospect Posts", value: prospectPosts.length, color: "text-rose-500", bg: "border-rose-500/10 bg-rose-500/5" },
            ].map(stat => (
              <div key={stat.label} className={cn("rounded-xl p-3.5 border", stat.bg)}>
                <div className="text-[8px] font-black uppercase tracking-widest text-zinc-400 mb-1">{stat.label}</div>
                <div className={cn("text-2xl font-black leading-none", stat.color)}>{stat.value}</div>
              </div>
            ))}
          </div>

          {/* Contact Readiness */}
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-zinc-100 dark:border-zinc-800">
              <span className="text-sm font-black uppercase tracking-tight flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-500" /> Contact Readiness
              </span>
            </div>
            <div className="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {/* Email */}
              <div className={cn("p-3 rounded-xl border space-y-1.5 sm:col-span-2 lg:col-span-1",
                effectiveVerificationStatus === "verified" ? "bg-emerald-500/5 border-emerald-500/15" :
                effectiveVerificationStatus === "invalid" ? "bg-rose-500/5 border-rose-500/15" :
                effectiveEmail ? "bg-amber-500/5 border-amber-500/15" : "bg-zinc-50 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700")}>
                <div className="flex items-center justify-between">
                  <Mail className="h-4 w-4 text-zinc-400" />
                  {effectiveVerificationStatus === "verified" && <ShieldCheck className="h-3 w-3 text-emerald-500" />}
                  {effectiveVerificationStatus === "invalid" && <ShieldAlert className="h-3 w-3 text-rose-500" />}
                  {effectiveEmail && !["verified","invalid"].includes(effectiveVerificationStatus || "") && <ShieldQuestion className="h-3 w-3 text-amber-500" />}
                </div>
                <div className="text-[9px] font-black uppercase text-zinc-400 tracking-widest">Email</div>
                {effectiveEmail ? (
                  <>
                    <div className="text-[12px] font-bold text-zinc-800 dark:text-zinc-200 break-all leading-tight">
                      {effectiveEmail}
                    </div>
                    <div className="mt-1">
                      <VerificationBadge status={effectiveVerificationStatus} />
                    </div>
                  </>

                ) : (
                  <div className="text-[10px] font-black uppercase text-zinc-400">Not Found</div>
                )}
              </div>
              {/* LinkedIn */}
              <div className={cn("p-3 rounded-xl border space-y-1.5",
                effectiveLinkedin ? "bg-[#0077B5]/5 border-[#0077B5]/15" : "bg-zinc-50 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700")}>
                <div className="flex items-center justify-between">
                  <Linkedin className="h-4 w-4 text-zinc-400" />
                  {effectiveLinkedin && <Check className="h-3 w-3 text-[#0077B5]" />}
                </div>
                <div className="text-[9px] font-black uppercase text-zinc-400 tracking-widest">LinkedIn</div>
                <div className={cn("text-[10px] font-black uppercase", effectiveLinkedin ? "text-[#0077B5]" : "text-zinc-400")}>
                  {effectiveLinkedin ? "Profile Found" : "Not Found"}
                </div>
              </div>
              {/* Website */}
              <div className={cn("p-3 rounded-xl border space-y-1.5",
                effectiveWebsite ? "bg-primary/5 border-primary/15" : "bg-zinc-50 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700")}>
                <div className="flex items-center justify-between">
                  <Globe className="h-4 w-4 text-zinc-400" />
                  {effectiveWebsite && <Check className="h-3 w-3 text-primary" />}
                </div>
                <div className="text-[9px] font-black uppercase text-zinc-400 tracking-widest">Website</div>
                <div className={cn("text-[10px] font-black uppercase", effectiveWebsite ? "text-primary" : "text-zinc-400")}>
                  {effectiveWebsite ? "Tracked" : "Not Found"}
                </div>
              </div>
              {/* Overall readiness score */}
              {(() => {
                const score = Math.round([effectiveEmail, effectiveLinkedin, effectiveWebsite].filter(Boolean).length / 3 * 100);
                return (
                  <div className={cn("p-3 rounded-xl border space-y-1.5",
                    score === 100 ? "bg-emerald-500/5 border-emerald-500/15" :
                    score >= 60 ? "bg-amber-500/5 border-amber-500/15" :
                    "bg-zinc-50 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700")}>
                    <div className="text-[9px] font-black uppercase text-zinc-400 tracking-widest">Reachability</div>
                    <div className={cn("text-2xl font-black leading-none",
                      score === 100 ? "text-emerald-600 dark:text-emerald-400" :
                      score >= 60 ? "text-amber-600 dark:text-amber-400" : "text-zinc-500")}>
                      {score}%
                    </div>
                    <div className="h-1 w-full bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                      <div className={cn("h-full transition-all rounded-full",
                        score === 100 ? "bg-emerald-500" : score >= 60 ? "bg-amber-500" : "bg-zinc-400")}
                        style={{ width: `${score}%` }} />
                    </div>
                  </div>
                );
              })()}
            </div>
          </div>

          {/* Lead Origin */}
          {(discoverySource || data.extra_metadata?.lead_source || (data as any).input_lead_data?.lead_source) && (
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-zinc-100 dark:border-zinc-800">
                <span className="text-sm font-black uppercase tracking-tight flex items-center gap-2">
                  <Search className="h-4 w-4 text-amber-500" /> Lead Origin
                </span>
              </div>
              <div className="p-4 flex flex-wrap gap-4">
                {(data.extra_metadata?.lead_source || (data as any).input_lead_data?.lead_source) && (
                  <div className="space-y-1">
                    <div className="text-[9px] font-black uppercase text-zinc-400 tracking-widest">Source Channel</div>
                    <Badge className="bg-amber-500/10 text-amber-600 border-none text-[10px] font-black uppercase px-3 h-6">
                      {(data.extra_metadata?.lead_source || (data as any).input_lead_data?.lead_source || "").replace(/_/g, " ")}
                    </Badge>
                  </div>
                )}
                {discoverySource && (
                  <div className="space-y-1">
                    <div className="text-[9px] font-black uppercase text-zinc-400 tracking-widest">Discovery Method</div>
                    <Badge className="bg-primary/10 text-primary border-none text-[10px] font-black uppercase px-3 h-6">
                      {discoverySource.replace(/_/g, " ")}
                    </Badge>
                  </div>
                )}
                {(data.extra_metadata?.discovery_context || (data as any).input_lead_data?.discovery_context) && (
                  <div className="flex-1 min-w-[200px] space-y-1">
                    <div className="text-[9px] font-black uppercase text-zinc-400 tracking-widest">Original Signal</div>
                    <p className="text-[12px] text-zinc-600 dark:text-zinc-400 italic leading-relaxed border-l-2 border-primary/20 pl-3">
                      {typeof (data.extra_metadata?.discovery_context || (data as any).input_lead_data?.discovery_context) === "string"
                        ? (data.extra_metadata?.discovery_context || (data as any).input_lead_data?.discovery_context)
                        : (data.extra_metadata?.discovery_context?.comments?.[0] || (data as any).input_lead_data?.discovery_context?.comments?.[0] || "Signal captured")}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Intent analysis (if exists) */}
          {data.intent_analysis && (
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Target className="h-4 w-4 text-primary" />
                  <span className="text-sm font-black uppercase tracking-tight">Access & Intent</span>
                </div>
                {isEditingIntent ? (
                  <div className="flex gap-1.5">
                    <Button size="sm" variant="ghost" onClick={() => { setIsEditingIntent(false); setEditedIntent({ ...data.intent_analysis }); }} disabled={isSavingIntent} className="h-7 px-2.5 text-[10px] font-black uppercase gap-1"><X className="h-2.5 w-2.5" /> Cancel</Button>
                    <Button size="sm" onClick={handleSaveIntent} disabled={isSavingIntent} className="h-7 px-2.5 text-[10px] font-black uppercase gap-1">{isSavingIntent ? <RotateCcw className="h-2.5 w-2.5 animate-spin" /> : <Save className="h-2.5 w-2.5" />} Save</Button>
                  </div>
                ) : (
                  <Button size="sm" variant="ghost" onClick={() => setIsEditingIntent(true)} className="h-7 px-2.5 text-[10px] font-black uppercase text-zinc-400 gap-1"><Edit2 className="h-3 w-3" /> Edit</Button>
                )}
              </div>
              <div className="p-5 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-primary/5 border border-primary/10 space-y-2">
                    <span className="text-[9px] font-black uppercase tracking-widest text-primary/70">Detected Intent</span>
                    {isEditingIntent ? (
                      <Input value={editedIntent?.intent || ""} onChange={(e) => setEditedIntent((p: any) => ({ ...p, intent: e.target.value }))} className="bg-primary/10 border-primary/20 text-primary uppercase h-9" />
                    ) : (
                      <div className="text-xl font-black text-primary capitalize">{data.intent_analysis.intent.replace(/_/g, " ")}</div>
                    )}
                    <div className="flex flex-wrap gap-2">
                      {isEditingIntent ? (
                        <select value={editedIntent?.sentiment} onChange={(e) => setEditedIntent((p: any) => ({ ...p, sentiment: e.target.value }))}
                          className="border rounded px-2 py-0.5 text-[10px] uppercase font-bold bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-700">
                          {["positive", "neutral", "negative"].map(s => <option key={s} value={s}>{s}</option>)}
                        </select>
                      ) : (
                        <Badge variant="outline" className="text-[10px] uppercase font-bold">{data.intent_analysis.sentiment}</Badge>
                      )}
                      {data.intent_analysis.post_topic_depth && (
                        <Badge className="bg-primary/10 text-primary border-none text-[9px] font-black uppercase">{data.intent_analysis.post_topic_depth.replace(/_/g, " ")}</Badge>
                      )}
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/10 space-y-2">
                    <span className="text-[9px] font-black uppercase tracking-widest text-emerald-600/70">Next Best Action</span>
                    {isEditingIntent ? (
                      <Textarea value={editedIntent?.next_steps || ""} onChange={(e) => setEditedIntent((p: any) => ({ ...p, next_steps: e.target.value }))} className="min-h-[60px] bg-emerald-500/5 border-emerald-500/20 text-sm italic resize-none" />
                    ) : (
                      <p className="text-[13px] font-semibold text-emerald-700 dark:text-emerald-400 italic leading-relaxed">"{data.intent_analysis.next_steps}"</p>
                    )}
                  </div>
                </div>

                {/* Follow-up email — rendered separately below intent block */}
                {data.intent_analysis.recommended_email && (
                  <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/10 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[9px] font-black uppercase tracking-widest text-emerald-600/70 flex items-center gap-1.5"><Mail className="h-3 w-3" /> Recommended Follow-up</span>
                      {isEditingIntentEmail ? (
                        <div className="flex gap-1.5">
                          <Button size="sm" variant="ghost" onClick={() => { setIsEditingIntentEmail(false); setEditedIntentEmail(data.intent_analysis?.recommended_email ?? ""); }} disabled={isSavingIntentEmail} className="h-6 px-2 text-[9px] font-black uppercase gap-1">Cancel</Button>
                          <Button size="sm" onClick={handleSaveIntentEmail} disabled={isSavingIntentEmail} className="h-6 px-2 text-[9px] font-black uppercase gap-1">{isSavingIntentEmail ? "Saving..." : "Save"}</Button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <Button size="sm" variant="ghost" onClick={() => setIsEditingIntentEmail(true)} className="h-6 px-2 text-[9px] font-black uppercase text-zinc-400 gap-1"><Edit2 className="h-2.5 w-2.5" /> Edit</Button>
                          <CopyButton text={data.intent_analysis.recommended_email} />
                        </div>
                      )}
                    </div>
                    {isEditingIntentEmail ? (
                      <Textarea
                        value={editedIntentEmail}
                        onChange={(e) => setEditedIntentEmail(e.target.value)}
                        className="min-h-[150px] text-[13px] leading-relaxed resize-none bg-emerald-500/10 border-emerald-500/20"
                      />
                    ) : (
                      <div className="prose prose-zinc dark:prose-invert max-w-none text-[13px] leading-relaxed font-medium text-zinc-700 dark:text-zinc-300 italic border-l-2 border-emerald-500/20 pl-3">
                        <ReactMarkdown>{data.intent_analysis.recommended_email}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                )}

                {/* Summary */}
                {data.intent_analysis.summary && (
                  <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
                    <div className="text-[9px] font-black uppercase tracking-widest text-zinc-400 mb-2 flex items-center gap-1.5"><Info className="h-3 w-3" /> Conversation Summary</div>
                    {isEditingIntent ? (
                      <Textarea value={editedIntent?.summary || ""} onChange={(e) => setEditedIntent((p: any) => ({ ...p, summary: e.target.value }))} className="min-h-[80px] text-[13px] italic resize-none" />
                    ) : (
                      <p className="text-[13px] text-zinc-600 dark:text-zinc-400 leading-relaxed">{data.intent_analysis.summary}</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}


          {/* Email History */}
          {data.email_history && data.email_history.length > 0 && (
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-emerald-500/10"><Mail className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /></div>
                  <span className="text-sm font-black uppercase tracking-tight">Email History</span>
                </div>
                <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-none text-[9px] font-black">{data.email_history.length} threads</Badge>
              </div>
              <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
                {data.email_history.map((email, i) => (
                  <EmailHistoryRow key={email.id || i} email={email} />
                ))}
              </div>
            </div>
          )}

          {/* Meeting notes */}
          {data.meeting_notes && (
            <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-500/5 border border-amber-500/15">
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-500 shrink-0"><MessageSquareQuote className="h-4 w-4" /></div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-black uppercase tracking-widest text-amber-600">Human Intelligence</span>
                  <Badge className="bg-amber-500 text-white border-none text-[8px] font-black uppercase h-4 px-1.5">Meeting Notes</Badge>
                </div>
                <p className="text-[14px] text-zinc-800 dark:text-zinc-200 italic leading-relaxed border-l-2 border-amber-500/30 pl-3">{data.meeting_notes}</p>
              </div>
            </div>
          )}

          {/* Merged timeline */}
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-zinc-100 dark:border-zinc-800">
              <span className="text-sm font-black uppercase tracking-tight flex items-center gap-2">
                <Calendar className="h-4 w-4 text-zinc-400" /> Interaction Timeline
              </span>
            </div>
            <div className="p-5">
              <div className="relative pl-7 border-l-2 border-zinc-100 dark:border-zinc-800 ml-2 space-y-4">
                {[
                  ...(data.post_engagements?.map(e => ({ ...e, _type: "social", _sort: Infinity })) || []),
                  // email_history shown in dedicated section above
                  ...(data.company_news?.map(n => ({ ...n, _type: "news", _sort: n.date ? new Date(n.date).getTime() : 0 })) || []),
                  ...(data.hiring_data?.map(h => ({ ...h, _type: "hiring", _sort: 0 })) || []),
                  ...(data.extra_metadata?.demo_requested ? [{ _type: "conversion", title: "Demo Requested", _sort: 0 }] : []),
                  ...(data.extra_metadata?.download_marketing_material ? [{ _type: "conversion", title: "Marketing Download", _sort: 0 }] : []),
                ]
                  .sort((a: any, b: any) => b._sort - a._sort)
                  .map((item: any, idx: number) => {
                    const nodeConfig: Record<string, { color: string; bg: string; icon: React.ReactNode }> = {
                      social: { color: "border-primary", bg: "bg-primary text-white", icon: <Linkedin className="h-3 w-3" /> },
                      email: { color: "border-emerald-500", bg: "bg-emerald-500 text-white", icon: <Mail className="h-3 w-3" /> },
                      news: { color: "border-blue-500", bg: "bg-blue-500 text-white", icon: <Globe className="h-3 w-3" /> },
                      hiring: { color: "border-purple-500", bg: "bg-purple-500 text-white", icon: <ShieldCheck className="h-3 w-3" /> },
                      conversion: { color: "border-amber-500", bg: "bg-amber-500 text-white", icon: <Zap className="h-3 w-3" /> },
                    };
                    const cfg = nodeConfig[item._type] || nodeConfig.conversion;
                    return (
                      <div key={idx} className="relative">
                        <div className={cn("absolute -left-[33px] top-2.5 h-6 w-6 rounded-full border-2 border-white dark:border-zinc-900 flex items-center justify-center z-10 shadow-sm", cfg.bg)}>
                          {cfg.icon}
                        </div>
                        <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 hover:border-zinc-300 dark:hover:border-zinc-600 transition-all">
                          {item._type === "social" && (
                            <div className="space-y-1">
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-[11px] font-black text-zinc-900 dark:text-white capitalize">{item.type} on {item.target} post</span>
                                <Badge variant="outline" className="text-[8px] uppercase border-primary/30 text-primary h-4 px-1.5">High Intent</Badge>
                              </div>
                              <p className="text-[12px] text-zinc-600 dark:text-zinc-400">{item.reaction_type ? `Reacted: ${item.reaction_type}` : `Comment: "${item.comment_text}"`}</p>
                              {item.post_url && <a href={item.post_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-[9px] font-black uppercase text-primary hover:underline mt-1"><ExternalLink className="h-2.5 w-2.5" /> View Post</a>}
                            </div>
                          )}
                          {item._type === "email" && (
                            <div className="space-y-1">
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-[11px] font-bold text-zinc-900 dark:text-white">{item.from}</span>
                                <div className="flex items-center gap-2">
                                  <span className="text-[9px] text-zinc-400 uppercase">{new Date(item.date).toLocaleDateString()}</span>
                                  <Badge variant="secondary" className={cn("text-[9px] uppercase font-bold h-4 px-1.5", item.direction === "received" ? "bg-emerald-500/10 text-emerald-500" : "")}>{item.direction}</Badge>
                                </div>
                              </div>
                              <p className="text-[12px] font-medium text-zinc-700 dark:text-zinc-300">{item.subject}</p>
                              <p className="text-[11px] text-zinc-500 leading-relaxed line-clamp-2">{item.text}</p>
                            </div>
                          )}
                          {item._type === "news" && (
                            <div className="space-y-0.5">
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-[11px] font-black text-zinc-900 dark:text-white">Market Event: {item.source}</span>
                                <span className="text-[9px] text-zinc-400 uppercase">{item.date}</span>
                              </div>
                              <p className="text-[12px] text-zinc-600 dark:text-zinc-400">{item.title}</p>
                            </div>
                          )}
                          {item._type === "hiring" && (
                            <div className="flex items-center justify-between gap-2">
                              <div>
                                <span className="text-[11px] font-black text-zinc-900 dark:text-white">Hiring: {item.role}</span>
                                <p className="text-[11px] text-zinc-500">{item.location}</p>
                              </div>
                              <Badge variant="outline" className="text-[8px] uppercase border-purple-500/30 text-purple-500 h-4 px-1.5">Growth</Badge>
                            </div>
                          )}
                          {item._type === "conversion" && (
                            <div className="flex items-center gap-2">
                              <span className="text-[11px] font-black text-zinc-900 dark:text-white">Converted: {item.title}</span>
                              <Badge className="bg-amber-500 text-white border-none text-[8px] font-black uppercase h-4 px-1.5">High Intent</Badge>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                {!data.post_engagements?.length && !data.email_history?.length && !data.company_news?.length && !data.hiring_data?.length && (
                  <p className="text-sm text-zinc-400 italic py-4">No signals recorded yet for this lead.</p>
                )}
              </div>
            </div>
          </div>

          {/* Prospect LinkedIn Posts */}
          {prospectPosts.length > 0 && (
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
                <span className="text-sm font-black uppercase tracking-tight flex items-center gap-2">
                  <Linkedin className="h-4 w-4 text-[#0077B5]" /> Prospect's LinkedIn Posts
                </span>
                <Badge variant="outline" className="text-[9px] font-black uppercase border-rose-500/20 text-rose-500 bg-rose-500/5">Intent Signals</Badge>
              </div>
              <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                {prospectPosts.slice(0, 6).map((post: any, i: number) => (
                  <div key={i} className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 hover:border-primary/30 transition-all group space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <Badge variant="outline" className="text-[8px] font-black uppercase border-zinc-300 dark:border-zinc-600 text-zinc-500 shrink-0">
                        {post.posted_date || "Recent"}
                      </Badge>
                      {post.post_url && (
                        <a href={post.post_url} target="_blank" rel="noopener noreferrer"
                          className="opacity-0 group-hover:opacity-100 transition-all text-zinc-400 hover:text-primary">
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                    <p className="text-[12px] font-black text-zinc-900 dark:text-zinc-100 leading-snug line-clamp-2">
                      {post.post_title}
                    </p>
                    <p className="text-[11px] text-zinc-500 italic leading-relaxed line-clamp-3 border-l-2 border-primary/10 pl-2">
                      "{post.summary}"
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Trigger Events (company news + hiring) */}
          {hasTriggers && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {data.company_news && data.company_news.length > 0 && (
                <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
                  <div className="px-5 py-3.5 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
                    <span className="text-sm font-black uppercase tracking-tight flex items-center gap-2">
                      <Globe className="h-4 w-4 text-blue-500" /> Market Triggers
                    </span>
                    <Badge className="bg-blue-500/10 text-blue-500 border-none text-[9px] font-black">{data.company_news.length}</Badge>
                  </div>
                  <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
                    {data.company_news.slice(0, 5).map((news, i) => (
                      <div key={i} className="px-5 py-3 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-all">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="text-[12px] font-bold text-zinc-900 dark:text-zinc-100 leading-snug">{news.title}</p>
                            <span className="text-[10px] text-zinc-400 font-bold uppercase">{news.source}</span>
                          </div>
                          <span className="text-[9px] text-zinc-400 shrink-0 mt-0.5">{news.date}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {data.hiring_data && data.hiring_data.length > 0 && (
                <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
                  <div className="px-5 py-3.5 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
                    <span className="text-sm font-black uppercase tracking-tight flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-purple-500" /> Hiring Signals
                    </span>
                    <Badge className="bg-purple-500/10 text-purple-500 border-none text-[9px] font-black">{data.hiring_data.length} active</Badge>
                  </div>
                  <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
                    {data.hiring_data.slice(0, 5).map((job, i) => (
                      <div key={i} className="px-5 py-3 flex items-center justify-between gap-3 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-all">
                        <div>
                          <p className="text-[12px] font-bold text-zinc-900 dark:text-zinc-100">{job.role}</p>
                          <span className="text-[10px] text-zinc-400 font-bold uppercase">{job.location}</span>
                        </div>
                        <Badge variant="outline" className="text-[8px] font-black uppercase border-purple-500/20 text-purple-500 shrink-0">
                          Growth
                        </Badge>
                      </div>
                    ))}
                  </div>
                  {data.hiring_data.length > 1 && (
                    <div className="px-5 py-2 bg-purple-500/5 border-t border-purple-500/10">
                      <p className="text-[10px] font-black text-purple-600 uppercase tracking-widest">
                        {data.hiring_data.length} open roles → scaling signal
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

        </div>
        );
      })()}

      {/* Knowledge Proof Sheet */}
      <Sheet open={isProofOpen} onOpenChange={setIsProofOpen}>
        <SheetContent side="right" className="sm:max-w-xl w-full overflow-y-auto bg-white dark:bg-zinc-950 border-l border-zinc-200 dark:border-zinc-800 p-0">
          <div className="p-8 space-y-8">
            <SheetHeader className="space-y-3">
              <div className="h-12 w-12 rounded-2xl bg-amber-500/10 text-amber-500 flex items-center justify-center">
                <BookOpen className="h-6 w-6" />
              </div>
              <SheetTitle className="text-2xl font-black italic uppercase">Knowledge Proofs</SheetTitle>
              <SheetDescription className="text-zinc-500 font-medium">Strategic assets synthesized by our CSO to validate this command.</SheetDescription>
            </SheetHeader>
            <div className="space-y-6">
              {data?.cso_strategic_briefing?.unified_command?.sources?.map((source, i) => (
                <div key={i} className="p-5 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-3">
                  <Badge variant="outline" className="text-[10px] font-black uppercase tracking-widest border-primary/20 text-primary bg-primary/5">Asset: {source.source}</Badge>
                  <div className="prose prose-zinc dark:prose-invert max-w-none text-[14px] font-medium italic border-l-2 border-primary/10 pl-4 leading-relaxed">
                    <ReactMarkdown>{source.snippet}</ReactMarkdown>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
