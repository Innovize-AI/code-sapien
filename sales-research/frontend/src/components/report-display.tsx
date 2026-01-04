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
        sales_research_report: string;
        lead_score_analysis: string;
        user_profile_analysis: string;
        website_analysis: string;
        intent_analysis?: {
            intent: string;
            summary: string;
            next_steps: string;
            sentiment: string;
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
        [key: string]: any;
    } | null;
    onRerun?: () => void;
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

    const tacticalActions = extractTacticalItems(data.sales_research_report);

    // Extract basic profile details from analysis string
    const getIdentity = () => {
        // Prioritize explicit database fields if available
        if (data.fullname) {
            const analysis = data.user_profile_analysis || "";
            const headlineMatch = analysis.match(/(?:Headline|Title|Role):\s*\**([^\n\*]+)\**/i);
            return {
                name: data.fullname,
                headline: headlineMatch ? headlineMatch[1].trim() : "Target Profile Analysis"
            };
        }

        const analysis = data.user_profile_analysis || "";
        // Look for "Name: " or "**Name:**" or similar
        const nameMatch = analysis.match(/(?:Name|Full Name):\s*\**([^\n\*]+)\**/i);
        // Look for "Headline: " or "Title: " or similar
        const headlineMatch = analysis.match(/(?:Headline|Title|Role):\s*\**([^\n\*]+)\**/i);

        return {
            name: nameMatch ? nameMatch[1].trim() : "Prospect Identity",
            headline: headlineMatch ? headlineMatch[1].trim() : "Target Profile Analysis"
        };
    };

    const identity = getIdentity();

    const sections = [
        { id: "profile", title: "Profile Intelligence", icon: <User className="h-4 w-4" />, content: data.user_profile_analysis, badge: "Intelligence", isPrimary: true },
        { id: "lead-score", title: "Qualification", icon: <TrendingUp className="h-4 w-4" />, content: data.lead_score_analysis, badge: "AI Score" },
        { id: "strategy", title: "Outreach Strategy", icon: <Target className="h-4 w-4" />, content: data.sales_research_report, badge: "Tactical", tactical: tacticalActions },
        { id: "website-analysis", title: "Digital Footprint", icon: <Globe className="h-4 w-4" />, content: data.website_analysis, badge: "Technical" },
        // New Section for Intent & History
        ...(data.email_history && data.email_history.length > 0 ? [{
            id: "intent-history",
            title: "Access & Intent",
            icon: <MessageSquare className="h-4 w-4" />,
            content: "", // Content handled by custom renderer
            badge: "Interaction",
            isIntent: true
        }] : [])
    ];

    // Helper to render content based on its type (JSON or Markdown) with support for "sloppy" and fragmented formats
    const DynamicContent = ({ content, title, isSocial = false, className = "" }: { content: string, title?: string, isSocial?: boolean, className?: string }) => {
        const [copied, setCopied] = React.useState(false);

        const handleCopy = () => {
            navigator.clipboard.writeText(content);
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

        let processedContent = content.trim();
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

    return (
        <div className="flex flex-col gap-10 max-w-[1400px] mx-auto px-4 py-8">
            <div className="relative overflow-hidden rounded-2xl bg-zinc-900 text-white p-10 md:p-12 border border-zinc-800">
                <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/10 blur-[130px] rounded-full -mr-32 -mt-32 pointer-events-none" />

                <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
                    <div className="flex flex-col md:flex-row items-start md:items-center gap-8">
                        {data.profile_picture_url ? (
                            <div className="relative group">
                                <div className="absolute -inset-1 bg-gradient-to-r from-primary/50 to-emerald-500/50 rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200" />
                                <div className="relative h-28 w-28 rounded-2xl overflow-hidden border-2 border-primary/20 bg-zinc-800">
                                    <img
                                        src={data.profile_picture_url}
                                        alt={identity.name}
                                        className="h-full w-full object-cover grayscale-[20%] hover:grayscale-0 transition-all duration-500"
                                    />
                                </div>
                            </div>
                        ) : (
                            <div className="p-6 rounded-2xl bg-primary/10 border border-primary/20 text-primary">
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

                    <div className="flex items-center gap-4 bg-white/5 p-4 rounded-2xl border border-white/10 backdrop-blur-md">
                        <div className="text-right pr-4 border-r border-white/10">
                            <div className="text-zinc-400 text-[10px] font-black uppercase tracking-widest mb-1">Lead Score</div>
                            <div className="text-3xl font-black text-primary leading-none">85</div>
                        </div>
                        <div className="pl-2">
                            <div className="text-zinc-400 text-[10px] font-black uppercase tracking-widest mb-1">Status</div>
                            <Badge className="bg-emerald-500/20 text-emerald-400 border-none hover:bg-emerald-500/30 text-[10px] uppercase font-black">Ready to Outreach</Badge>
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
                                <CardHeader className="px-12 pt-12 pb-8 flex flex-row items-center justify-between border-none">
                                    <div className="flex items-center gap-6">
                                        <div className={cn(
                                            "p-5 rounded-2xl border transition-transform hover:rotate-6",
                                            section.isPrimary ? "bg-primary text-white border-primary" : "bg-primary/5 text-primary border-primary/10"
                                        )}>
                                            {React.isValidElement(section.icon) && React.cloneElement(section.icon as React.ReactElement<any>, { className: "h-8 w-8" })}
                                        </div>
                                        <div className="space-y-1">
                                            <Badge variant="outline" className="text-[10px] uppercase font-black tracking-[0.25em] text-primary border-primary/20 h-6 px-3 rounded-full mb-1">{section.badge}</Badge>
                                            <CardTitle className="text-3xl md:text-4xl font-black tracking-tighter text-zinc-950 dark:text-zinc-50 uppercase italic">
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
                                    {section.id === 'strategy' && section.tactical && section.tactical.length > 0 && (
                                        <div className="mb-12 grid grid-cols-1 md:grid-cols-2 gap-6">
                                            {/* Action Cards for tactical extraction */}
                                            {section.tactical.map((action, i) => (
                                                <div key={i} className="group relative p-8 rounded-2xl bg-zinc-900 text-white border border-zinc-800 overflow-hidden hover:scale-[1.01] transition-transform">
                                                    <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity">
                                                        <Button
                                                            variant="secondary"
                                                            size="icon"
                                                            className="h-10 w-10 rounded-xl bg-white/10 hover:bg-white/20 border-white/10 text-white"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                navigator.clipboard.writeText(action.content);
                                                            }}
                                                        >
                                                            <Copy className="h-4 w-4" />
                                                        </Button>
                                                    </div>
                                                    <div className="flex items-center gap-4 mb-4 font-black">
                                                        <div className="p-3 rounded-2xl bg-primary/20 text-primary border border-primary/20">
                                                            {action.icon}
                                                        </div>
                                                        <span className="text-xs uppercase tracking-widest text-zinc-300">{action.title}</span>
                                                    </div>
                                                    <div className="text-[15px] font-medium leading-relaxed italic text-zinc-100">
                                                        "{action.content}"
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {/* Custom Intent Rendering */}
                                    {/* @ts-ignore */}
                                    {section.isIntent && data.intent_analysis && (
                                        <div className="space-y-12">
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
