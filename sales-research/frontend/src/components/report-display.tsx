import React from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Target, Globe, FileText, BarChart3, TrendingUp, Copy, Check, Info, Calendar, ShieldCheck, ExternalLink, ChevronRight, LayoutDashboard, Mail, Linkedin, Zap, MessageSquareQuote, MousePointer2, MessageSquare, ArrowRight, ArrowDown, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface ReportDisplayProps {
    data: {
        fullname?: string;
        profile_picture_url?: string;
        linkedin_url?: string;
        website?: string;
        lead_score?: number;
        sales_research_report: string;
        lead_score_analysis: any; // Can be string or structured object
        user_profile_analysis: any;
        website_analysis: any;
        intent_analysis?: {
            intent: string;
            summary: string;
            next_steps: string;
            sentiment: string;
            recommended_email?: string;
        };
        email_history?: Array<{
            id?: string;
            subject: string;
            from: string;
            to?: string[];
            date: string;
            text: string;
            direction: string;
        }>;
        // Modular Nodules
        viability_analysis?: string;
        target_pain_points?: string;
        strategic_solutions?: string;
        personalized_outreach?: {
            hook: string;
            linkedin_message: string;
            email_subject: string;
            email_body: string;
        } | string;
        buyer_journey_analysis?: {
            journey_stage: string;
            optimal_play: string;
            strategic_reasoning: string;
            sentiment_score: number;
            urgency_level: string;
        } | any;
        meeting_notes?: string;
        // LinkedIn Subgraph
        post_engagements?: Array<{
            type: string;
            target: string;
            post_id: string;
            content: string;
            reaction_type?: string;
            comment_text?: string;
        }>;
        company_news?: Array<{
            title: string;
            source: string;
            date: string;
        }>;
        hiring_data?: Array<{
            role: string;
            location: string;
        }>;
        extra_metadata?: {
            lead_source?: string;
            download_marketing_material?: boolean;
            demo_requested?: boolean;
            referral_partner_introduction?: boolean;
            [key: string]: any;
        };
        [key: string]: any;
    } | null;

    onRerun?: () => void;
}

type ActivityType = 'email' | 'linkedin_reaction' | 'linkedin_comment' | 'conversion' | 'discovery';

interface Activity {
    id: string;
    type: ActivityType;
    title: string;
    description: string;
    date: string;
    status?: string;
    meta?: any;
}


export function ReportDisplay({ data, onRerun }: ReportDisplayProps) {
    const [activeSection, setActiveSection] = React.useState<number>(0);
    const [isNavVisible, setIsNavVisible] = React.useState<boolean>(true);

    if (!data) {
        return null;
    }

    // Helper to extract specific tactical items from markdown strategy
    const extractTacticalItems = (content: string) => {
        const items: { type: 'linkedin' | 'email' | 'pain-point', title: string, content: string, icon: React.ReactNode }[] = [];

        // Extract LinkedIn Message
        const linkedinMatch = content.match(/LinkedIn Connection Message:\s*\*?\"?([\s\S]*?)\"?\*?(\n\n|(?=\d\.|$))/i);
        if (linkedinMatch) {
            items.push({
                type: 'linkedin',
                title: 'LinkedIn Connection',
                content: linkedinMatch[1].trim().replace(/^\"|\"$/g, ''),
                icon: <Linkedin className="h-4 w-4" />
            });
        }

        // Extract Email
        const emailMatch = content.match(/(Hyperpersonalized Email|Email Message):\s*\*?\"?([\s\S]*?)\"?\*?(\n\n|(?=\d\.|$))/i);
        if (emailMatch) {
            items.push({
                type: 'email',
                title: 'Personalized Email',
                content: emailMatch[2].trim().replace(/^\"|\"$/g, ''),
                icon: <Mail className="h-4 w-4" />
            });
        }

        // Extract Pain Points (Attempt to find "Pain Points" section)
        const painMatch = content.match(/Pain Points:\s*([\s\S]*?)(\n\n|(?=\d\.|$))/i);
        if (painMatch) {
            items.push({
                type: 'pain-point',
                title: 'Identified Pain point',
                content: painMatch[1].trim(),
                icon: <Zap className="h-4 w-4" />
            });
        }

        return items;
    };

    // Extract basic profile details from analysis string

    const getIdentity = () => {
        // Prioritize explicit database fields if available
        if (data.fullname) {
            const analysis = data.user_profile_analysis;
            let headline = "Target Profile Analysis";

            if (typeof analysis === 'string') {
                const headlineMatch = analysis.match(/(?:Headline|Title|Role):\s*\**([^\n\*]+)\**/i);
                if (headlineMatch) headline = headlineMatch[1].trim();
            } else if (analysis && typeof analysis === 'object') {
                headline = analysis.profile_summary || analysis.headline || analysis.role || headline;
            }

            return {
                name: data.fullname,
                headline: headline
            };
        }

        const analysis = data.user_profile_analysis;
        if (analysis && typeof analysis === 'object') {
            return {
                name: analysis.name || analysis.fullname || "Prospect Identity",
                headline: analysis.profile_summary || analysis.headline || analysis.role || "Target Profile Analysis"
            };
        }

        const analysisStr = String(analysis || "");
        const nameMatch = analysisStr.match(/(?:Name|Full Name):\s*\**([^\n\*]+)\**/i);
        const headlineMatch = analysisStr.match(/(?:Headline|Title|Role):\s*\**([^\n\*]+)\**/i);

        return {
            name: nameMatch ? nameMatch[1].trim() : "Prospect Identity",
            headline: headlineMatch ? headlineMatch[1].trim() : "Target Profile Analysis"
        };
    };

    const identity = getIdentity();

    interface Section {
        id: string;
        title: string;
        icon: React.ReactNode;
        content: any;
        badge: string;
        isPrimary?: boolean;
        isActivity?: boolean;
        isIntent?: boolean;
        isJourney?: boolean;
        isOutreach?: boolean;
        tactical?: any[];
    }

    const sections: Section[] = [
        { id: "synthesis", title: "Executive Blueprint", icon: <LayoutDashboard className="h-4 w-4" />, content: data.sales_research_report, badge: "CSO Briefing", isPrimary: true },
        { id: "journey", title: "Buyer Journey", icon: <TrendingUp className="h-4 w-4" />, content: "", badge: "Strategy", isJourney: true },
        { id: "profile", title: "Profile Intelligence", icon: <User className="h-4 w-4" />, content: data.user_profile_analysis, badge: "Intelligence" },
        { id: "activity", title: "Activity Board", icon: <BarChart3 className="h-4 w-4" />, content: "", badge: "Real-time", isActivity: true },
        { id: "viability", title: "ICP Viability", icon: <ShieldCheck className="h-4 w-4" />, content: data.viability_analysis || "", badge: "Strategic" },
        { id: "pain-points", title: "Lead Pain Points", icon: <Zap className="h-4 w-4" />, content: data.target_pain_points || "", badge: "Discovery" },
        { id: "solutions", title: "Strategic Solutions", icon: <ArrowDown className="h-4 w-4" />, content: data.strategic_solutions || "", badge: "Matching" },
        { id: "outreach", title: "Outreach Design", icon: <Target className="h-4 w-4" />, content: "", badge: "Tactical", isOutreach: true },
        { id: "lead-score", title: "Qualification", icon: <BarChart3 className="h-4 w-4" />, content: data.lead_score_analysis, badge: "AI Score" },
        { id: "website-analysis", title: "Digital Footprint", icon: <Globe className="h-4 w-4" />, content: data.website_analysis, badge: "Technical" },
        // New Section for Intent & History
        ...((data.email_history && data.email_history.length > 0) || (data.post_engagements && data.post_engagements.length > 0) ? [{
            id: "intent-history",
            title: "Access & Intent",
            icon: <MessageSquare className="h-4 w-4" />,
            content: "", // Content handled by custom renderer
            badge: "Interaction",
            isIntent: true
        }] : [])
    ];



    // Helper to render content based on its type (JSON or Markdown) with support for "sloppy" and fragmented formats
    const DynamicContent = ({ content, title, isSocial = false, className = "" }: { content: any, title?: string, isSocial?: boolean, className?: string }) => {
        const [copied, setCopied] = React.useState(false);

        const handleCopy = () => {
            const textToCopy = typeof content === 'string' ? content : JSON.stringify(content, null, 2);
            navigator.clipboard.writeText(textToCopy);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        };

        const ProseWrapper = ({ children }: { children: React.ReactNode }) => (
            <div className="prose prose-zinc dark:prose-invert max-w-none 
                text-[15px] text-zinc-600 dark:text-zinc-400 leading-[1.8] font-normal 
                prose-headings:text-zinc-900 dark:prose-headings:text-zinc-100 
                prose-headings:font-bold prose-headings:tracking-tight
                prose-strong:text-zinc-900 dark:prose-strong:text-zinc-100
                prose-a:text-primary hover:prose-a:underline">
                {children}
            </div>
        );

        if (content && typeof content === 'object' && !Array.isArray(content)) {
            return (
                <div className={cn("relative group space-y-8", className)}>
                    <div className="absolute right-0 -top-14 opacity-0 group-hover:opacity-100 transition-all duration-300">
                        <Button variant="outline" size="sm" onClick={handleCopy} className="h-9 gap-2 text-xs bg-white dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-900">
                            {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
                            {copied ? "Copied" : "Copy Section"}
                        </Button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-10 p-12 rounded-[2.5rem] bg-zinc-50/50 dark:bg-zinc-900/30 border border-zinc-200/60 dark:border-zinc-800/60 transition-all duration-500 hover:bg-zinc-50 dark:hover:bg-zinc-900/40">
                        {Object.entries(content).map(([key, value]) => {
                            if (key === 'posts_analysis' || key === 'recent_posts') return null;

                            if (Array.isArray(value)) {
                                return (
                                    <div key={key} className="md:col-span-2 space-y-3">
                                        <div className="flex items-center gap-3">
                                            <div className="h-1.5 w-1.5 rounded-full bg-primary/40 shadow-sm shadow-primary/20" />
                                            <h4 className="text-[10px] font-black text-zinc-400 dark:text-zinc-500 uppercase tracking-[0.2em]">{key.replace(/_/g, ' ')}</h4>
                                        </div>
                                        <div className="pl-6 space-y-2">
                                            {value.map((item, i) => (
                                                <div key={i} className="flex gap-2 text-[15px] font-medium text-zinc-900 dark:text-zinc-100 leading-relaxed">
                                                    <span className="text-primary mt-1.5">•</span>
                                                    <div className="prose prose-zinc dark:prose-invert max-w-none text-[15px] text-zinc-900 dark:text-zinc-100 leading-relaxed font-medium">
                                                        <ReactMarkdown>{String(item)}</ReactMarkdown>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                );
                            }

                            if (typeof value === 'object' && value !== null) {
                                return (
                                    <div key={key} className="md:col-span-2 space-y-4 pt-4 border-t border-dashed border-zinc-200 dark:border-zinc-800">
                                        <div className="flex items-center gap-3">
                                            <div className="h-1.5 w-1.5 rounded-full bg-primary/40 shadow-sm shadow-primary/20" />
                                            <h4 className="text-[10px] font-black text-zinc-400 dark:text-zinc-500 uppercase tracking-[0.2em]">{key.replace(/_/g, ' ')}</h4>
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pl-4">
                                            {Object.entries(value).map(([subKey, subValue]) => (
                                                <div key={subKey} className="space-y-2">
                                                    <h5 className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">{subKey.replace(/_/g, ' ')}</h5>
                                                    <div className="prose prose-zinc dark:prose-invert max-w-none text-[15px] font-semibold text-zinc-900 dark:text-zinc-100 leading-relaxed">
                                                        <ReactMarkdown>{String(subValue)}</ReactMarkdown>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                );
                            }

                            return (
                                <div key={key} className={cn("space-y-3", (String(value).length > 150) ? 'md:col-span-2' : '')}>
                                    <div className="flex items-center gap-3">
                                        <div className="h-1.5 w-1.5 rounded-full bg-primary/40 shadow-sm shadow-primary/20" />
                                        <h4 className="text-[10px] font-black text-zinc-400 dark:text-zinc-500 uppercase tracking-[0.2em]">{key.replace(/_/g, ' ')}</h4>
                                    </div>
                                    <div className="prose prose-zinc dark:prose-invert max-w-none text-[16px] font-bold text-zinc-900 dark:text-zinc-100 leading-relaxed pl-6 antialiased">
                                        <ReactMarkdown>{String(value)}</ReactMarkdown>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            );
        }

        let processedContent = String(content || "").trim();
        if (processedContent.startsWith('```')) {
            processedContent = processedContent.replace(/^```(markdown)?\n?/i, '').replace(/\n?```$/i, '').trim();
        }

        if (title && (processedContent.toLowerCase().startsWith(title.toLowerCase()) ||
            processedContent.toLowerCase().startsWith(`**${title.toLowerCase()}**`))) {
            processedContent = processedContent.replace(new RegExp(`^#*\\s*(\\**)?${title}(\\**)?\\s*`, 'i'), '').trim();
        }

        const segments: { type: 'markdown' | 'object', data: any }[] = [];
        let lastIndex = 0;
        const blockRegex = /\{[\s\S]*?\}/g;
        let match;

        while ((match = blockRegex.exec(processedContent)) !== null) {
            if (match.index > lastIndex) {
                let text = processedContent.substring(lastIndex, match.index).trim();
                // Strip trailing code block starts like ```json or ```
                text = text.replace(/```[a-z]*\s*$/i, '').trim();
                if (text) segments.push({ type: 'markdown', data: text });
            }

            const rawBlock = match[0];
            try {
                const parsed = JSON.parse(rawBlock);
                segments.push({ type: 'object', data: parsed });
            } catch (e) {
                const pairs: Record<string, string> = {};
                const pairRegex = /(?:(\w+)|\"([^\"]*)\"|\'([^\']*)\')\s*:\s*(?:\"([^\"]*)\"|\'([^\']*)\'|([^,}\n]+))/g;
                let pairMatch;
                let foundAny = false;

                while ((pairMatch = pairRegex.exec(rawBlock)) !== null) {
                    const key = (pairMatch[1] || pairMatch[2] || pairMatch[3] || "").trim();
                    const value = (pairMatch[4] || pairMatch[5] || pairMatch[6] || "").trim();
                    if (key) {
                        pairs[key] = value;
                        foundAny = true;
                    }
                }

                if (foundAny) {
                    segments.push({ type: 'object', data: pairs });
                } else {
                    segments.push({ type: 'markdown', data: rawBlock });
                }
            }
            lastIndex = blockRegex.lastIndex;
        }

        if (lastIndex < processedContent.length) {
            let text = processedContent.substring(lastIndex).trim();
            text = text.replace(/^\s*```/i, '').trim();
            if (text) segments.push({ type: 'markdown', data: text });
        }

        // --- BRAIN: Consolidate Social Activity ---
        const activitySegments = segments.filter(s =>
            isSocial && s.type === 'object' && Object.keys(s.data).some(k =>
                ['post', 'activity', 'recent', 'content'].some(term => k.toLowerCase().includes(term))
            )
        );

        const otherSegments = segments.filter(s => !activitySegments.includes(s));
        // --- END BRAIN ---

        return (
            <div className={cn("relative group space-y-8", className)}>
                <div className="absolute right-0 -top-14 opacity-0 group-hover:opacity-100 transition-all duration-300">
                    <Button variant="outline" size="sm" onClick={handleCopy} className="h-9 gap-2 text-xs bg-white dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-900">
                        {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
                        {copied ? "Copied" : "Copy Section"}
                    </Button>
                </div>

                {/* Render non-activity segments first */}
                {otherSegments.map((segment, idx) => (
                    segment.type === 'markdown' ? (
                        <div key={idx}>
                            <ProseWrapper>
                                <ReactMarkdown>{segment.data}</ReactMarkdown>
                            </ProseWrapper>
                        </div>
                    ) : (
                        <div key={idx} className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-8 p-10 rounded-2xl bg-zinc-50/50 dark:bg-zinc-900/30 border border-zinc-200/60 dark:border-zinc-800/60">
                            {Object.entries(segment.data).map(([key, value]) => (
                                <div key={key} className={cn("space-y-2", (String(value).length > 100) ? 'md:col-span-2' : '')}>
                                    <div className="flex items-center gap-2">
                                        <div className="h-1 w-4 bg-primary/20 rounded-full" />
                                        <h4 className="text-[11px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-[0.15em]">{key.replace(/_/g, ' ')}</h4>
                                    </div>
                                    <div className="text-[15px] font-semibold text-zinc-900 dark:text-zinc-100 leading-relaxed pl-6">
                                        {String(value)}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )
                ))}

                {/* Render Consolidated Activity Timeline */}
                {activitySegments.length > 0 && (
                    <div className="space-y-8 pt-4">
                        <div className="flex items-center gap-4 px-2">
                            <div className="h-px flex-1 bg-gradient-to-r from-transparent via-zinc-200 dark:via-zinc-800 to-transparent" />
                            <div className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/5 border border-primary/20">
                                <MessageSquareQuote className="h-3.5 w-3.5 text-primary" />
                                <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">Intelligence Feed</h4>
                            </div>
                            <div className="h-px flex-1 bg-gradient-to-r from-transparent via-zinc-200 dark:via-zinc-800 to-transparent" />
                        </div>

                        <div className="relative pl-8 space-y-10 border-l-2 border-primary/10 ml-4 py-4">
                            {activitySegments.map((segment, sIdx) => (
                                <div key={sIdx} className="relative group/item">
                                    {/* Timeline Node */}
                                    <div className="absolute -left-[41px] top-0 p-1.5 rounded-full bg-white dark:bg-zinc-950 border-2 border-primary/20 group-hover/item:border-primary transition-colors z-10 shadow-sm">
                                        <Zap className="h-3 w-3 text-primary" />
                                    </div>

                                    <div className="relative overflow-hidden p-8 rounded-2xl bg-zinc-50/50 dark:bg-zinc-900/30 border border-zinc-200/60 dark:border-zinc-800/60 hover:border-primary/20 transition-all duration-300 group/card">
                                        <div className="space-y-4">
                                            {Object.entries(segment.data).map(([key, value]) => {
                                                const isContent = ['content', 'post', 'text', 'activity'].some(t => key.toLowerCase().includes(t));
                                                return (
                                                    <div key={key} className={isContent ? "pt-2" : ""}>
                                                        {!isContent && (
                                                            <div className="flex items-center gap-2 mb-1">
                                                                <span className="text-[9px] font-black uppercase tracking-[0.2em] text-zinc-400">{key.replace(/_/g, ' ')}</span>
                                                            </div>
                                                        )}
                                                        <div className={cn(
                                                            "leading-relaxed",
                                                            isContent ? "text-[16px] font-medium text-zinc-900 dark:text-zinc-100 italic border-l-4 border-primary/20 pl-6 py-1" : "text-xs font-bold text-zinc-600 dark:text-zinc-400"
                                                        )}>
                                                            {isContent ? `"${String(value)}"` : String(value)}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        );
    };

    const outreach = data.personalized_outreach;
    const tacticalActions = (typeof outreach === 'object' && outreach !== null) ? [
        { type: 'linkedin' as const, title: 'LinkedIn Request', content: outreach.linkedin_message, icon: <Linkedin className="h-4 w-4" /> },
        { type: 'email' as const, title: 'Email Subject', content: outreach.email_subject, icon: <Mail className="h-4 w-4" /> },
        { type: 'email' as const, title: 'Email Body', content: outreach.email_body, icon: <FileText className="h-4 w-4" /> }
    ] : extractTacticalItems(data.sales_research_report);

    return (
        <div className="relative min-h-screen bg-zinc-50 dark:bg-zinc-950/50">
            {/* Header / Hero Section */}
            <div className="relative overflow-hidden bg-zinc-900 border-b border-white/5 pt-20 pb-16 px-8 md:px-12">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(37,99,235,0.1),transparent)]" />
                <div className="max-w-7xl mx-auto relative flex flex-col md:flex-row md:items-end justify-between gap-8">
                    <div className="flex items-center gap-8">
                        {data.profile_picture_url ? (
                            <img
                                src={data.profile_picture_url}
                                alt={identity.name}
                                className="h-32 w-32 rounded-3xl object-cover ring-4 ring-white/5 shadow-2xl transition-transform hover:scale-105 duration-500"
                            />
                        ) : (
                            <div className="h-32 w-32 rounded-3xl bg-zinc-800 flex items-center justify-center text-zinc-600 ring-4 ring-white/5">
                                <User className="h-12 w-12" />
                            </div>
                        )}
                        <div className="space-y-3">
                            <div className="flex flex-wrap items-center gap-3">
                                <h1 className="text-4xl md:text-5xl font-black tracking-tight text-white leading-tight">
                                    {identity.name}
                                </h1>
                                <Badge variant="secondary" className="bg-primary/20 text-primary border-none text-[10px] uppercase font-black tracking-widest px-3 py-1 rounded-full">Lead Verified</Badge>
                            </div>
                            <p className="text-zinc-200 text-lg font-medium max-w-xl leading-relaxed">
                                {identity.headline}
                            </p>
                            <div className="flex flex-wrap items-center gap-6 pt-2">
                                {data.linkedin_url && (
                                    <a href={data.linkedin_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors group">
                                        <div className="p-2 rounded-lg bg-zinc-800 group-hover:bg-primary/20 group-hover:text-primary transition-all">
                                            <Linkedin className="h-4 w-4" />
                                        </div>
                                        <span className="text-sm font-bold tracking-tight">LinkedIn Profile</span>
                                        <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0 transition-all" />
                                    </a>
                                )}
                                {data.website && (
                                    <a href={data.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors group">
                                        <div className="p-2 rounded-lg bg-zinc-800 group-hover:bg-primary/20 group-hover:text-primary transition-all">
                                            <Globe className="h-4 w-4" />
                                        </div>
                                        <span className="text-sm font-bold tracking-tight">Company Website</span>
                                        <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0 transition-all" />
                                    </a>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-6 bg-white/5 p-6 rounded-3xl border border-white/10 backdrop-blur-xl transition-all hover:bg-white/10">
                        <div className="text-right pr-6 border-r border-white/10">
                            <div className="text-zinc-400 text-[9px] font-black uppercase tracking-[0.2em] mb-1.5 opacity-60">Lead Score</div>
                            <div className="text-4xl font-black text-primary leading-none italic">{data.lead_score || (typeof data.lead_score_analysis === 'object' ? data.lead_score_analysis.total_lead_score : 85)}</div>
                        </div>
                        <div className="text-right pr-6 border-r border-white/10">
                            <div className="text-zinc-400 text-[9px] font-black uppercase tracking-[0.2em] mb-1.5 opacity-60">Heat Rating</div>
                            <div className="text-4xl font-black text-amber-500 leading-none italic">{data.buyer_journey_analysis?.sentiment_score || 50}</div>
                        </div>
                        <div className="pl-2">
                            <div className="text-zinc-400 text-[9px] font-black uppercase tracking-[0.2em] mb-1.5 opacity-60">Journey Stage</div>
                            <Badge className="bg-primary/20 text-primary border border-primary/20 hover:bg-primary/30 text-[10px] uppercase font-black px-3 py-1 rounded-lg">
                                {data.buyer_journey_analysis?.journey_stage || (data.post_engagements && data.post_engagements.length > 0 ? "Consideration" : "Awareness")}
                            </Badge>
                        </div>
                    </div>

                    {onRerun && (
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={onRerun}
                            className="bg-white/10 hover:bg-white/20 border-white/20 text-white gap-2"
                        >
                            <Zap className="h-4 w-4" />
                            Re-run Analysis
                        </Button>
                    )}
                </div>
            </div>

            <div className="flex flex-col lg:flex-row gap-12 items-start">
                <div className={cn(
                    "sticky top-24 shrink-0 space-y-8 transition-all duration-300",
                    isNavVisible ? "w-80" : "w-16"
                )}>
                    <div className={cn(
                        "rounded-2xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 flex flex-col gap-8 relative transition-all duration-300",
                        isNavVisible ? "p-8" : "p-3"
                    )}>
                        {/* Toggle Button - Top Right Corner */}
                        <button
                            onClick={() => setIsNavVisible(!isNavVisible)}
                            className="absolute -right-3 top-4 p-2 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-all shadow-sm z-10"
                            title={isNavVisible ? "Close sidebar" : "Open sidebar"}
                        >
                            {isNavVisible ? <ChevronRight className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
                        </button>

                        {isNavVisible ? (
                            <div>
                                <div>
                                    <div className="flex items-center gap-2 mb-6 px-1">
                                        <LayoutDashboard className="h-4 w-4 text-primary" />
                                        <span className="text-[10px] font-black uppercase tracking-[0.2em] opacity-50">Navigation</span>
                                    </div>
                                    <nav className="space-y-2">
                                        {sections.map((section, idx) => (
                                            <button
                                                key={idx}
                                                onClick={() => {
                                                    setActiveSection(idx);
                                                    const el = document.getElementById(section.id);
                                                    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                                }}
                                                className={cn(
                                                    "w-full flex items-center justify-between px-5 py-4 rounded-2xl text-[13px] font-black transition-all duration-500 group border border-transparent",
                                                    activeSection === idx
                                                        ? "bg-primary text-white border-primary translate-x-3"
                                                        : "text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-900 hover:text-zinc-900 dark:hover:text-zinc-100"
                                                )}
                                            >
                                                <div className="flex items-center gap-4">
                                                    {React.cloneElement(section.icon as React.ReactElement, { className: cn("h-4 w-4 transition-transform group-hover:scale-110", activeSection === idx ? "text-white" : "text-zinc-400 group-hover:text-primary") })}
                                                    {section.title}
                                                </div>
                                                <ChevronRight className={cn("h-3 w-3 transition-all duration-500", activeSection === idx ? "rotate-90" : "opacity-0 -translate-x-2")} />
                                            </button>
                                        ))}
                                    </nav>
                                </div>

                                <div className="pt-8 border-t border-zinc-100 dark:border-zinc-900">
                                    <div className="flex items-center gap-2 mb-4 px-1">
                                        <Zap className="h-4 w-4 text-emerald-500" />
                                        <span className="text-[10px] font-black uppercase tracking-[0.2em] opacity-50">Tactical actions</span>
                                    </div>
                                    <div className="space-y-4">
                                        {tacticalActions.map((action, i) => (
                                            <button
                                                key={i}
                                                onClick={() => {
                                                    const el = document.getElementById('strategy');
                                                    el?.scrollIntoView({ behavior: 'smooth' });
                                                }}
                                                className="w-full flex items-center gap-3 p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-900 border border-transparent hover:border-primary/20 transition-all text-left"
                                            >
                                                <div className="p-2 rounded-xl bg-primary/10 text-primary">
                                                    {action.icon}
                                                </div>
                                                <div className="flex-1">
                                                    <div className="text-[11px] font-black tracking-tight text-zinc-900 dark:text-zinc-100 uppercase">{action.title}</div>
                                                    <div className="text-[10px] font-bold text-zinc-500 tracking-tighter">Draft Ready</div>
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <nav className="space-y-3">
                                {sections.map((section, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => {
                                            setActiveSection(idx);
                                            const el = document.getElementById(section.id);
                                            el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                        }}
                                        className={cn(
                                            "w-full p-3 rounded-xl transition-all duration-300 group",
                                            activeSection === idx
                                                ? "bg-primary text-white"
                                                : "text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-900 hover:text-primary"
                                        )}
                                        title={section.title}
                                    >
                                        {React.cloneElement(section.icon as React.ReactElement, {
                                            className: cn("h-5 w-5 mx-auto", activeSection === idx ? "text-white" : "")
                                        })}
                                    </button>
                                ))}
                            </nav>
                        )}
                    </div>
                </div>

                <div className="flex-1 space-y-12 min-w-0 pb-32">
                    {sections.map((section, index) => (
                        <div
                            key={index}
                            id={section.id}
                            className="scroll-mt-24"
                            onMouseEnter={() => setActiveSection(index)}
                        >
                            <Card className={cn(
                                "rounded-2xl overflow-hidden border border-zinc-200/60 dark:border-zinc-800/60 transition-all duration-700",
                                section.isPrimary ? "bg-primary/[0.03]" : "bg-white dark:bg-zinc-950"
                            )}>
                                <CardHeader className="px-12 pt-14 pb-10 flex flex-row items-center justify-between border-none relative overflow-hidden">
                                    {section.id === 'synthesis' && (
                                        <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.05] via-transparent to-transparent opacity-60" />
                                    )}
                                    <div className="flex items-center gap-8 relative z-10">
                                        <div className={cn(
                                            "p-6 rounded-[2rem] border transition-all duration-500 group-hover:scale-110",
                                            section.isPrimary ? "bg-primary text-white border-primary shadow-xl shadow-primary/20" : "bg-primary/5 text-primary border-primary/10"
                                        )}>
                                            {React.isValidElement(section.icon) && React.cloneElement(section.icon as React.ReactElement<any>, { className: "h-10 w-10 stroke-[2.5]" })}
                                        </div>
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-3 mb-1">
                                                <Badge variant="outline" className="text-[10px] uppercase font-black tracking-[0.3em] text-primary border-primary/30 h-7 px-4 rounded-full bg-primary/5">{section.badge}</Badge>
                                                {section.id === 'synthesis' && (
                                                    <span className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-emerald-500">
                                                        <ShieldCheck className="h-3.5 w-3.5" /> High Stakes Analysis
                                                    </span>
                                                )}
                                            </div>
                                            <CardTitle className="text-4xl md:text-5xl font-black tracking-tighter text-zinc-950 dark:text-zinc-50 uppercase italic leading-none">
                                                {section.title}
                                            </CardTitle>
                                        </div>
                                    </div>
                                    {section.id === 'strategy' && (
                                        <div className="hidden md:flex flex-col items-end gap-1">
                                            <div className="text-[10px] font-black uppercase text-zinc-400">Total Insights</div>
                                            <div className="text-2xl font-black text-primary">14</div>
                                        </div>
                                    )}
                                </CardHeader>
                                <CardContent className="px-12 pb-16">
                                    {section.id === 'outreach' && tacticalActions.length > 0 && (
                                        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                                {/* Outreach Cards */}
                                                {tacticalActions.map((action, i) => (
                                                    <div
                                                        key={i}
                                                        className={cn(
                                                            "group relative p-10 rounded-3xl transition-all duration-500",
                                                            action.type === 'email' ? "bg-zinc-900 text-white shadow-2xl" : "bg-zinc-50 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800"
                                                        )}
                                                    >
                                                        <div className="absolute top-6 right-6 opacity-0 group-hover:opacity-100 transition-all duration-300">
                                                            <Button
                                                                size="sm"
                                                                variant={action.type === 'email' ? "secondary" : "outline"}
                                                                className="h-9 px-4 rounded-xl gap-2 font-black uppercase tracking-tighter text-[10px]"
                                                                onClick={() => {
                                                                    navigator.clipboard.writeText(action.content);
                                                                }}
                                                            >
                                                                <Copy className="h-3.5 w-3.5" />
                                                                Copy {action.title.split(' ')[1] || 'Draft'}
                                                            </Button>
                                                        </div>

                                                        <div className="flex items-center gap-4 mb-8">
                                                            <div className={cn(
                                                                "p-3 rounded-2xl border transition-transform group-hover:rotate-12",
                                                                action.type === 'email' ? "bg-primary/20 text-primary border-primary/20 shadow-lg shadow-primary/10" : "bg-white dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800 text-primary shadow-sm"
                                                            )}>
                                                                {action.icon}
                                                            </div>
                                                            <div className="space-y-1">
                                                                <span className={cn(
                                                                    "text-[10px] uppercase font-black tracking-widest block",
                                                                    action.type === 'email' ? "text-zinc-400" : "text-zinc-500"
                                                                )}>{action.title}</span>
                                                                <div className={cn(
                                                                    "h-1 w-12 rounded-full",
                                                                    action.type === 'email' ? "bg-primary" : "bg-primary/30"
                                                                )} />
                                                            </div>
                                                        </div>

                                                        <div className={cn(
                                                            "text-[16px] leading-[1.8] font-medium italic",
                                                            action.type === 'email' ? "text-zinc-100 selection:bg-primary/30" : "text-zinc-800 dark:text-zinc-200 selection:bg-primary/10"
                                                        )}>
                                                            {action.content}
                                                        </div>

                                                        {action.type === 'email' && action.title.includes('Subject') && (
                                                            <div className="mt-6 pt-6 border-t border-white/5 flex items-center gap-3">
                                                                <ShieldCheck className="h-4 w-4 text-primary" />
                                                                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">Optimized for High Open Rates</span>
                                                            </div>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>

                                            {typeof data.personalized_outreach === 'object' && data.personalized_outreach?.hook && (
                                                <div className="p-10 rounded-3xl bg-primary/[0.03] border border-primary/10 space-y-4">
                                                    <div className="flex items-center gap-3">
                                                        <Zap className="h-4 w-4 text-primary" />
                                                        <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-primary/70">Strategic Conversion Angle</h4>
                                                    </div>
                                                    <p className="text-[17px] font-bold text-zinc-900 dark:text-zinc-100 leading-relaxed italic">
                                                        "{data.personalized_outreach.hook}"
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {section.isJourney && data.buyer_journey_analysis && (
                                        <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-1000">
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                                                <div className="p-10 rounded-3xl bg-zinc-900 text-white border border-white/5 space-y-6 shadow-2xl relative overflow-hidden group">
                                                    <div className="absolute top-0 right-0 w-48 h-48 bg-primary/20 blur-[80px] rounded-full -mr-24 -mt-24 pointer-events-none group-hover:bg-primary/30 transition-all duration-700" />
                                                    <div className="flex items-center gap-4 relative">
                                                        <div className="p-3 rounded-2xl bg-white/10 border border-white/10 text-primary">
                                                            <Target className="h-6 w-6" />
                                                        </div>
                                                        <div className="space-y-1">
                                                            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">Pipeline Alpha</span>
                                                            <h4 className="text-xl font-black italic">Journey Stage</h4>
                                                        </div>
                                                    </div>
                                                    <div className="text-4xl font-black text-white tracking-tight uppercase italic relative">
                                                        {data.buyer_journey_analysis.journey_stage || "Discovery"}
                                                    </div>
                                                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden relative">
                                                        <div
                                                            className="h-full bg-primary shadow-[0_0_15px_rgba(37,99,235,0.5)] transition-all duration-1000"
                                                            style={{ width: `${(data.buyer_journey_analysis.sentiment_score || 50)}%` }}
                                                        />
                                                    </div>
                                                </div>

                                                <div className="p-10 rounded-3xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-6 shadow-sm hover:shadow-md transition-all duration-500">
                                                    <div className="flex items-center gap-4">
                                                        <div className="p-3 rounded-2xl bg-emerald-500/10 text-emerald-500 border border-emerald-500/10">
                                                            <Zap className="h-6 w-6" />
                                                        </div>
                                                        <div className="space-y-1">
                                                            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">Recommended Action</span>
                                                            <h4 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100 uppercase italic">The Optimal Play</h4>
                                                        </div>
                                                    </div>
                                                    <p className="text-[15px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/5 p-6 rounded-2xl border border-emerald-500/10 leading-relaxed italic">
                                                        "{data.buyer_journey_analysis.optimal_play || "Initiate high-value outreach sequence"}"
                                                    </p>
                                                </div>

                                                <div className="p-10 rounded-3xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-6 shadow-sm hover:shadow-md transition-all duration-500">
                                                    <div className="flex items-center gap-4">
                                                        <div className="p-3 rounded-2xl bg-amber-500/10 text-amber-500 border border-amber-500/10">
                                                            <BarChart3 className="h-6 w-6" />
                                                        </div>
                                                        <div className="space-y-1">
                                                            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">Temp Check</span>
                                                            <h4 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100 uppercase italic">Heat Rating</h4>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-end gap-3">
                                                        <span className="text-5xl font-black text-amber-500 italic">{(data.buyer_journey_analysis.sentiment_score || 50)}</span>
                                                        <span className="text-zinc-400 font-black uppercase tracking-[0.1em] text-[15px] pb-1.5 font-sans">/ 100</span>
                                                    </div>
                                                    <Badge className={cn(
                                                        "px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest border-none",
                                                        (data.buyer_journey_analysis.urgency_level === 'High' || (data.buyer_journey_analysis.sentiment_score || 0) > 70) ? "bg-rose-500 text-white" : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
                                                    )}>
                                                        {data.buyer_journey_analysis.urgency_level || "Normal"} Urgency Detected
                                                    </Badge>
                                                </div>
                                            </div>

                                            <div className="p-12 rounded-[2.5rem] bg-zinc-50 dark:bg-zinc-900/30 border border-zinc-200/60 dark:border-zinc-800/60 space-y-8 relative overflow-hidden">
                                                <div className="flex items-center gap-4 mb-2">
                                                    <MessageSquareQuote className="h-5 w-5 text-primary/60" />
                                                    <h4 className="text-[11px] font-black uppercase tracking-[0.25em] text-zinc-400">Strategic Reasoning</h4>
                                                </div>
                                                <p className="text-[19px] leading-[1.8] font-medium text-zinc-700 dark:text-zinc-300 antialiased italic max-w-4xl">
                                                    {data.buyer_journey_analysis.strategic_reasoning || "Analysis based on profile seniority, recent hiring signals, and intent data points."}
                                                </p>
                                            </div>
                                        </div>
                                    )}


                                    {/* Custom Intent Rendering */}
                                    {/* @ts-ignore */}
                                    {/* Unified Activity Board */}
                                    {section.isActivity && (
                                        <div className="space-y-8">
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                                <Card className="bg-white/5 border-white/10">
                                                    <CardHeader className="pb-2">
                                                        <CardDescription className="uppercase text-[10px] font-black">Social Intent</CardDescription>
                                                        <CardTitle className="text-2xl font-black text-primary">{data.post_engagements?.length || 0}</CardTitle>
                                                    </CardHeader>
                                                </Card>
                                                <Card className="bg-white/5 border-white/10">
                                                    <CardHeader className="pb-2">
                                                        <CardDescription className="uppercase text-[10px] font-black">Emails Scanned</CardDescription>
                                                        <CardTitle className="text-2xl font-black text-emerald-500">{data.email_history?.length || 0}</CardTitle>
                                                    </CardHeader>
                                                </Card>
                                                <Card className="bg-white/5 border-white/10">
                                                    <CardHeader className="pb-2">
                                                        <CardDescription className="uppercase text-[10px] font-black">Conversion Events</CardDescription>
                                                        <CardTitle className="text-2xl font-black text-amber-500">
                                                            {[
                                                                data.extra_metadata?.download_marketing_material,
                                                                data.extra_metadata?.demo_requested,
                                                                data.extra_metadata?.referral_partner_introduction
                                                            ].filter(Boolean).length}
                                                        </CardTitle>
                                                    </CardHeader>
                                                </Card>
                                            </div>

                                            <div className="space-y-6">
                                                <h3 className="text-sm font-black uppercase tracking-widest text-zinc-400">Interaction Timeline</h3>
                                                <div className="relative pl-8 border-l border-white/10 space-y-8 ml-4">
                                                    {/* Meeting Notes / Human Intelligence */}
                                                    {data.meeting_notes && (
                                                        <div className="relative group/note">
                                                            <div className="absolute -left-[45px] top-0 p-2 rounded-full bg-amber-500/20 border border-amber-500/30 text-amber-500 shadow-lg shadow-amber-500/10">
                                                                <MessageSquareQuote className="h-4 w-4" />
                                                            </div>
                                                            <div className="space-y-4 p-8 rounded-3xl bg-amber-500/[0.02] border border-amber-500/10 hover:border-amber-500/20 transition-all duration-300">
                                                                <div className="flex items-center gap-3">
                                                                    <span className="text-[10px] font-black tracking-[0.2em] text-amber-600 uppercase">Human Intelligence (Meeting Notes)</span>
                                                                    <Badge className="bg-amber-500 text-white border-none rounded-full px-2 py-0 text-[8px] font-black uppercase">Internal</Badge>
                                                                </div>
                                                                <p className="text-[17px] font-medium text-zinc-800 dark:text-zinc-200 leading-relaxed italic border-l-4 border-amber-500/30 pl-6">
                                                                    {data.meeting_notes}
                                                                </p>
                                                            </div>
                                                        </div>
                                                    )}

                                                    {/* LinkedIn Engagements */}
                                                    {data.post_engagements?.map((eng, idx) => (
                                                        <div key={`social-${idx}`} className="relative">
                                                            <div className="absolute -left-[45px] top-0 p-2 rounded-full bg-primary/20 border border-primary/30 text-primary">
                                                                <Linkedin className="h-4 w-4" />
                                                            </div>
                                                            <div className="space-y-1">
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-sm font-black text-white capitalize">{eng.type} on {eng.target} post</span>
                                                                    <Badge variant="outline" className="text-[9px] uppercase border-primary/30 text-primary">Intent High</Badge>
                                                                </div>
                                                                <p className="text-sm text-zinc-400 leading-relaxed">
                                                                    {eng.reaction_type ? `Reacted with ${eng.reaction_type}` : `Commented: "${eng.comment_text}"`}
                                                                </p>
                                                                <div className="text-[10px] text-zinc-500 uppercase font-bold pt-1">Recent Activity</div>
                                                            </div>
                                                        </div>
                                                    ))}

                                                    {/* Emails */}
                                                    {data.email_history?.slice(0, 5).map((email, idx) => (
                                                        <div key={`email-${idx}`} className="relative">
                                                            <div className="absolute -left-[45px] top-0 p-2 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-500">
                                                                <Mail className="h-4 w-4" />
                                                            </div>
                                                            <div className="space-y-1">
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-sm font-black text-white">Email {email.direction}</span>
                                                                    <Badge variant="outline" className="text-[9px] uppercase border-emerald-500/30 text-emerald-500">{email.direction}</Badge>
                                                                </div>
                                                                <p className="text-sm text-zinc-400 line-clamp-1">{email.subject}</p>
                                                                <div className="text-[10px] text-zinc-500 uppercase font-bold pt-1">{new Date(email.date).toLocaleDateString()}</div>
                                                            </div>
                                                        </div>
                                                    ))}

                                                    {/* Conversion Events */}
                                                    {data.extra_metadata?.download_marketing_material && (
                                                        <div className="relative">
                                                            <div className="absolute -left-[45px] top-0 p-2 rounded-full bg-amber-500/20 border border-amber-500/30 text-amber-500">
                                                                <FileText className="h-4 w-4" />
                                                            </div>
                                                            <div className="space-y-1">
                                                                <span className="text-sm font-black text-white">Converted: Marketing Download</span>
                                                                <p className="text-sm text-zinc-400">Lead downloaded resource from website/portal.</p>
                                                                <div className="text-[10px] text-zinc-500 uppercase font-bold pt-1">Historical Data</div>
                                                            </div>
                                                        </div>
                                                    )}
                                                    {data.extra_metadata?.demo_requested && (
                                                        <div className="relative">
                                                            <div className="absolute -left-[45px] top-0 p-2 rounded-full bg-rose-500/20 border border-rose-500/30 text-rose-500">
                                                                <Zap className="h-4 w-4" />
                                                            </div>
                                                            <div className="space-y-1">
                                                                <span className="text-sm font-black text-white">Converted: Demo Requested</span>
                                                                <p className="text-sm text-zinc-400">Direct high-intent request for a product demonstration.</p>
                                                                <div className="text-[10px] text-zinc-500 uppercase font-bold pt-1">Priority Event</div>
                                                            </div>
                                                        </div>
                                                    )}

                                                    {/* Company News */}
                                                    {data.company_news?.map((news, idx) => (
                                                        <div key={`news-${idx}`} className="relative">
                                                            <div className="absolute -left-[45px] top-0 p-2 rounded-full bg-blue-500/20 border border-blue-500/30 text-blue-500">
                                                                <Globe className="h-4 w-4" />
                                                            </div>
                                                            <div className="space-y-1">
                                                                <span className="text-sm font-black text-white">Market Event: {news.source}</span>
                                                                <p className="text-sm text-zinc-400 leading-relaxed">{news.title}</p>
                                                                <div className="text-[10px] text-zinc-500 uppercase font-bold pt-1">{news.date}</div>
                                                            </div>
                                                        </div>
                                                    ))}

                                                    {/* Hiring Data */}
                                                    {data.hiring_data?.map((job, idx) => (
                                                        <div key={`hiring-${idx}`} className="relative">
                                                            <div className="absolute -left-[45px] top-0 p-2 rounded-full bg-purple-500/20 border border-purple-500/30 text-purple-500">
                                                                <ShieldCheck className="h-4 w-4" />
                                                            </div>
                                                            <div className="space-y-1">
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-sm font-black text-white">Hiring Signal: {job.role}</span>
                                                                    <Badge variant="outline" className="text-[9px] uppercase border-purple-500/30 text-purple-500">Growth</Badge>
                                                                </div>
                                                                <p className="text-sm text-zinc-400">{job.location}</p>
                                                                <div className="text-[10px] text-zinc-500 uppercase font-bold pt-1">Active Listing</div>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {section.id === 'lead-score' && data.lead_score_analysis && (
                                        <div className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
                                            {typeof data.lead_score_analysis === 'object' ? (
                                                <>
                                                    <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
                                                        {[
                                                            { label: "Demographic", score: data.lead_score_analysis.demographic_fit_score, max: 25, color: "text-blue-500" },
                                                            { label: "Engagement", score: data.lead_score_analysis.engagement_score, max: 20, color: "text-emerald-500" },
                                                            { label: "Readiness", score: data.lead_score_analysis.sales_readiness_score, max: 25, color: "text-orange-500" },
                                                            { label: "Source", score: data.lead_score_analysis.lead_source_score, max: 15, color: "text-purple-500" },
                                                            { label: "Timing", score: data.lead_score_analysis.timing_score, max: 15, color: "text-rose-500" }
                                                        ].map((item, idx) => (
                                                            <div key={idx} className="p-8 rounded-[2rem] bg-zinc-50 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800 flex flex-col items-center text-center space-y-4 hover:scale-105 transition-transform duration-500">
                                                                <div className={cn("text-3xl font-black", item.color)}>
                                                                    {item.score}
                                                                </div>
                                                                <div className="space-y-1">
                                                                    <div className="text-[9px] font-black uppercase tracking-[0.2em] text-zinc-400">{item.label}</div>
                                                                    <div className="h-1 w-8 bg-zinc-200 dark:bg-zinc-800 rounded-full mx-auto" />
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>

                                                    <div className="p-10 rounded-3xl bg-zinc-900 text-white border border-zinc-800 shadow-2xl relative overflow-hidden group">
                                                        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-transparent opacity-50" />
                                                        <div className="relative z-10 space-y-6">
                                                            <div className="flex items-center gap-4">
                                                                <div className="p-3 rounded-2xl bg-white/10 border border-white/10 text-primary">
                                                                    <Info className="h-6 w-6" />
                                                                </div>
                                                                <h4 className="text-xl font-bold uppercase italic tracking-tight">Scoring Intelligence Analysis</h4>
                                                            </div>
                                                            <div className="text-[17px] leading-[1.8] font-medium text-zinc-300 italic max-w-4xl">
                                                                {data.lead_score_analysis.analysis}
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {data.lead_score_analysis.recommendations && data.lead_score_analysis.recommendations.length > 0 && (
                                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                            {data.lead_score_analysis.recommendations.map((rec: string, i: number) => (
                                                                <div key={i} className="flex items-center gap-4 p-6 rounded-2xl bg-primary/5 border border-primary/10 group hover:translate-x-2 transition-transform duration-300">
                                                                    <div className="h-2 w-2 rounded-full bg-primary" />
                                                                    <span className="text-[15px] font-bold text-zinc-700 dark:text-zinc-300 antialiased italic">{rec}</span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                </>
                                            ) : (
                                                <DynamicContent content={data.lead_score_analysis} />
                                            )}
                                        </div>
                                    )}

                                    {section.id === "intent-history" && data.intent_analysis && (
                                        <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-700">
                                            {/* Intent Cards */}
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                <div className="p-8 rounded-2xl bg-primary/5 border border-primary/10">
                                                    <div className="flex items-center gap-3 mb-4">
                                                        <Target className="h-5 w-5 text-primary" />
                                                        <span className="text-xs font-black uppercase tracking-widest text-primary/70">DETECTED INTENT</span>
                                                    </div>
                                                    <div className="text-2xl font-black text-primary capitalize mb-2">{data.intent_analysis.intent}</div>
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-xs font-bold text-zinc-500 uppercase tracking-widest">Sentiment:</span>
                                                        <Badge variant="outline" className="text-[10px] uppercase font-bold">{data.intent_analysis.sentiment}</Badge>
                                                    </div>
                                                </div>
                                                <div className="p-8 rounded-2xl bg-emerald-500/5 border border-emerald-500/10">
                                                    <div className="flex items-center gap-3 mb-4">
                                                        <ArrowRight className="h-5 w-5 text-emerald-500" />
                                                        <span className="text-xs font-black uppercase tracking-widest text-emerald-600/70">NEXT BEST ACTION</span>
                                                    </div>
                                                    <div className="text-lg font-medium text-emerald-900 dark:text-emerald-100 italic leading-relaxed">
                                                        "{data.intent_analysis.next_steps}"
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Recommended Email */}
                                            {data.intent_analysis?.recommended_email && (
                                                <div className="space-y-4">
                                                    <div className="flex items-center justify-between">
                                                        <h3 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-3">
                                                            <Mail className="h-4 w-4 text-primary" />
                                                            Recommended Follow-up Email
                                                        </h3>
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            className="h-8 gap-2 group"
                                                            onClick={() => {
                                                                navigator.clipboard.writeText(data.intent_analysis?.recommended_email || "");
                                                            }}
                                                        >
                                                            <Copy className="h-3.5 w-3.5 transition-transform group-hover:scale-110" />
                                                            Copy Email
                                                        </Button>
                                                    </div>
                                                    <div className="relative group p-8 rounded-2xl bg-zinc-900 text-white border border-zinc-800 shadow-xl overflow-hidden">
                                                        <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 blur-[50px] rounded-full -mr-16 -mt-16 pointer-events-none" />
                                                        <div className="relative z-10 text-[16px] font-medium leading-relaxed italic text-zinc-100">
                                                            {data.intent_analysis.recommended_email}
                                                        </div>
                                                        <div className="mt-6 flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-zinc-500">
                                                            <ShieldCheck className="h-3 w-3" />
                                                            AI PROMPT: AS HUMAN AS POSSIBLE
                                                        </div>
                                                    </div>
                                                </div>
                                            )}

                                            {/* Summary */}
                                            <div className="space-y-4">
                                                <h3 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-3">
                                                    <Info className="h-4 w-4 text-zinc-400" />
                                                    Conversation Summary
                                                </h3>
                                                <div className="p-6 rounded-2xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 leading-relaxed text-[15px]">
                                                    {data.intent_analysis.summary}
                                                </div>
                                            </div>

                                            {/* Timeline */}
                                            <div className="space-y-8">
                                                <h3 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-3">
                                                    <Calendar className="h-4 w-4 text-zinc-400" />
                                                    Conversation Timeline
                                                </h3>
                                                <div className="relative pl-8 border-l-2 border-zinc-200 dark:border-zinc-800 space-y-8 ml-3">
                                                    {data.email_history?.map((email, idx) => (
                                                        <div key={idx} className="relative">
                                                            <div className={cn(
                                                                "absolute -left-[41px] top-0 p-1.5 rounded-full border-2 z-10 bg-white dark:bg-zinc-950",
                                                                email.direction === 'sent' ? "border-zinc-200 dark:border-zinc-700" : "border-primary bg-primary text-white"
                                                            )}>
                                                                {email.direction === 'sent' ? <ArrowRight className="h-3 w-3 text-zinc-400" /> : <Mail className="h-3 w-3" />}
                                                            </div>
                                                            <div className="p-6 rounded-2xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 shadow-sm hover:border-primary/20 transition-all">
                                                                <div className="flex items-center justify-between mb-4">
                                                                    <div className="flex flex-col">
                                                                        <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100">{email.from}</span>
                                                                        <span className="text-[10px] text-zinc-500 uppercase tracking-wider">{new Date(email.date).toLocaleDateString()}</span>
                                                                    </div>
                                                                    <Badge variant="secondary" className="text-[10px] uppercase font-bold">{email.direction}</Badge>
                                                                </div>
                                                                <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100 mb-2">{email.subject}</div>
                                                                <div className="text-sm text-zinc-500 leading-relaxed line-clamp-3 hover:line-clamp-none transition-all">
                                                                    {email.text}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    <DynamicContent
                                        content={section.content}
                                        title={section.title}
                                        isSocial={section.id === 'profile'}
                                    />
                                </CardContent>
                            </Card>
                        </div>
                    ))}
                </div>
            </div>
        </div >
    );
}
