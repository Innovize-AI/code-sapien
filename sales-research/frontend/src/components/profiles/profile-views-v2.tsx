"use client";

import React, { useState } from "react";
import {
  ExternalLink, Users, Globe, Mail, Zap, TrendingUp, UserCheck,
  CheckCircle2, FileText, Play, Loader2, Search, MessageSquare,
  ArrowUp, ArrowDown, ArrowUpDown, ChevronRight, ShieldCheck,
  ShieldAlert, ShieldQuestion, Eye, BarChart3,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn, ensureProtocol, normalizeUrl } from "@/lib/utils";
import { IdentifiedProfile } from "@/lib/api";

// ─── Shared props ─────────────────────────────────────────────────────────────
export interface ProfileViewProps {
  profiles: IdentifiedProfile[];
  selectedIds: Set<string>;
  toggleSelection: (id: string) => void;
  toggleSelectAll: () => void;
  leadsStatus: any[];
  onOpenReport: (reportId: string) => void;
  onOpenCompany: (companyId: string) => void;
  onAnalyze: (profile: IdentifiedProfile) => void;
  onEnrich: (apolloId: string) => void;
  enrichingIds: Set<string>;
  sortBy: string;
  sortOrder: "asc" | "desc";
  onSort: (column: string) => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function getInitials(name?: string) {
  if (!name) return "?";
  const parts = name.trim().split(" ");
  return parts.length >= 2
    ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

function getRelativeTime(dateStr: string) {
  try {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}d ago`;
    return `${Math.floor(days / 30)}mo ago`;
  } catch { return "—"; }
}

function parseInteractionStats(profile: IdentifiedProfile) {
  try {
    const history = JSON.parse(profile.interaction_history || "[]");
    let keyword = 0, competitor = 0;
    const allTouchpoints: { competitor: string; title: string; url: string; comments: string[] }[] = [];
    history.forEach((comp: any) => {
      comp.posts?.forEach((post: any) => {
        if (comp.type === "keyword" || comp.competitor?.toLowerCase().includes("keyword")) keyword++;
        else competitor++;
        allTouchpoints.push({ competitor: comp.competitor, title: post.title, url: post.url, comments: post.comments || [] });
      });
    });
    if (keyword === 0 && competitor === 0 && allTouchpoints.length === 0) {
      const sources = JSON.parse(profile.source_posts || "[]");
      sources.forEach((s: any) => allTouchpoints.push({ competitor: s.competitor || "Source", title: s.title, url: s.url, comments: [] }));
    }
    return { keyword, competitor, total: keyword + competitor || allTouchpoints.length, allTouchpoints, firstComment: allTouchpoints[0]?.comments?.[0] || null };
  } catch { return { keyword: 0, competitor: 0, total: 0, allTouchpoints: [], firstComment: null }; }
}

function getAccent(profile: IdentifiedProfile) {
  if (profile.is_competitor) return { bar: "bg-rose-500", badge: "bg-rose-50 text-rose-700 border-rose-200", avatar: "bg-rose-100 text-rose-700", dot: "bg-rose-500" };
  if (profile.is_fit) return { bar: "bg-emerald-500", badge: "bg-emerald-50 text-emerald-700 border-emerald-200", avatar: "bg-emerald-100 text-emerald-700", dot: "bg-emerald-500" };
  if (profile.is_buy_signal) return { bar: "bg-violet-500", badge: "bg-violet-50 text-violet-700 border-violet-200", avatar: "bg-violet-100 text-violet-700", dot: "bg-violet-500" };
  if (profile.is_decision_maker) return { bar: "bg-blue-500", badge: "bg-blue-50 text-blue-700 border-blue-200", avatar: "bg-blue-100 text-blue-700", dot: "bg-blue-500" };
  if (profile.is_strategic_seller) return { bar: "bg-zinc-400", badge: "bg-zinc-50 text-zinc-600 border-zinc-200", avatar: "bg-zinc-100 text-zinc-600", dot: "bg-zinc-400" };
  return { bar: "bg-zinc-200 dark:bg-zinc-700", badge: "bg-zinc-50 text-zinc-600 border-zinc-200", avatar: "bg-zinc-100 text-zinc-500", dot: "bg-zinc-300" };
}

function EmailVerificationIcon({ status }: { status?: string }) {
  if (!status) return null;
  const s = status.toLowerCase();
  if (["verified", "ok", "valid"].includes(s)) return <ShieldCheck className="h-3 w-3 text-emerald-500" />;
  if (["invalid", "error", "failed", "unverified"].includes(s)) return <ShieldAlert className="h-3 w-3 text-rose-500" />;
  if (["catch_all", "catchall", "risky"].includes(s)) return <ShieldAlert className="h-3 w-3 text-amber-500" />;
  return <ShieldQuestion className="h-3 w-3 text-zinc-400" />;
}

function EmailVerificationBadge({ status }: { status?: string }) {
  if (!status) return null;
  const s = status.toLowerCase();

  if (["verified", "ok", "valid"].includes(s)) {
    return (
      <Badge variant="outline" className="text-[9px] h-4 px-1.5 bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20 flex items-center gap-1 font-bold">
        <ShieldCheck className="h-2.5 w-2.5" /> Verified
      </Badge>
    );
  }
  if (["invalid", "error", "failed"].includes(s)) {
    return (
      <Badge variant="outline" className="text-[9px] h-4 px-1.5 bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/20 flex items-center gap-1 font-bold">
        <ShieldAlert className="h-2.5 w-2.5" /> Invalid
      </Badge>
    );
  }
  if (["catch_all", "catchall", "risky"].includes(s)) {
    return (
      <Badge variant="outline" className="text-[9px] h-4 px-1.5 bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20 flex items-center gap-1 font-bold">
        <ShieldAlert className="h-2.5 w-2.5" /> Risky
      </Badge>
    );
  }
  if (["unverified"].includes(s)) {
    return (
      <Badge variant="outline" className="text-[9px] h-4 px-1.5 bg-zinc-50 text-zinc-500 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700 flex items-center gap-1 font-bold">
        <ShieldQuestion className="h-2.5 w-2.5" /> Unverified
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="text-[9px] h-4 px-1.5 bg-zinc-50 text-zinc-500 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700 flex items-center gap-1 font-bold">
      <ShieldQuestion className="h-2.5 w-2.5" /> {s.charAt(0).toUpperCase() + s.slice(1)}
    </Badge>
  );
}

function StatusChips({ profile, size = "sm" }: { profile: IdentifiedProfile; size?: "sm" | "xs" }) {
  const h = size === "xs" ? "h-4 text-[8px] px-1" : "h-5 text-[9px] px-1.5";
  return (
    <div className="flex flex-wrap gap-1">
      {profile.is_competitor && <Badge variant="destructive" className={cn(h)}><span>Competitor</span></Badge>}
      {profile.is_fit && <Badge variant="outline" className={cn(h, "bg-emerald-50 text-emerald-700 border-emerald-200")}><CheckCircle2 className="w-2.5 h-2.5 mr-0.5" />Fit</Badge>}
      {profile.is_buy_signal && <Badge variant="outline" className={cn(h, "bg-violet-50 text-violet-700 border-violet-200")}><Zap className="w-2.5 h-2.5 mr-0.5" />Buy Signal</Badge>}
      {profile.is_decision_maker && <Badge variant="outline" className={cn(h, "bg-blue-50 text-blue-700 border-blue-200")}><UserCheck className="w-2.5 h-2.5 mr-0.5" />Decision Maker</Badge>}
      {profile.is_strategic_seller && <Badge variant="outline" className={cn(h, "bg-zinc-50 text-zinc-600 border-zinc-200")}><TrendingUp className="w-2.5 h-2.5 mr-0.5" />Seller</Badge>}
      {profile.outreach_status && profile.outreach_status !== "not_started" && (
        <Badge variant="outline" className={cn(h,
          profile.outreach_status === "in_progress" ? "bg-amber-50 text-amber-600 border-amber-200" : "bg-emerald-50 text-emerald-700 border-emerald-200")}>
          {profile.outreach_status.replace(/_/g, " ")}
        </Badge>
      )}
    </div>
  );
}

function TouchpointTooltip({ profile, children }: { profile: IdentifiedProfile; children: React.ReactNode }) {
  const stats = parseInteractionStats(profile);
  if (stats.allTouchpoints.length === 0) return <>{children}</>;
  return (
    <TooltipProvider>
      <Tooltip delayDuration={200}>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipContent side="left" className="w-80 p-0 shadow-xl overflow-hidden">
          <div className="px-3 py-2 bg-zinc-50 dark:bg-zinc-900 border-b flex items-center justify-between">
            <span className="text-[10px] font-black uppercase tracking-widest">All Touchpoints</span>
            <Badge variant="outline" className="text-[9px]">{stats.total} total</Badge>
          </div>
          <div className="max-h-64 overflow-y-auto p-2 space-y-2">
            {stats.allTouchpoints.slice(0, 8).map((tp, i) => (
              <div key={i} className="p-2 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-1">
                <div className="flex items-center gap-1.5">
                  <div className="h-1.5 w-1.5 rounded-full bg-primary/50" />
                  <span className="text-[9px] font-black uppercase text-primary/70">{tp.competitor}</span>
                </div>
                <a href={tp.url} target="_blank" rel="noopener noreferrer"
                  className="text-[10px] text-blue-600 hover:underline italic block pl-3 line-clamp-1">
                  "{tp.title}"
                </a>
                {tp.comments[0] && (
                  <p className="text-[10px] text-zinc-500 italic pl-3 line-clamp-2 border-l border-zinc-200 ml-1">
                    <MessageSquare className="h-2 w-2 inline mr-1 opacity-50" />
                    {tp.comments[0]}
                  </p>
                )}
              </div>
            ))}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ─── ProfileCardV2 ────────────────────────────────────────────────────────────
function ProfileCardV2({
  profile, isSelected, onSelect, isDisabled, leadStatus, onOpenReport, onOpenCompany, onAnalyze, onEnrich, enrichingIds,
}: {
  profile: IdentifiedProfile;
  isSelected: boolean;
  onSelect: () => void;
  isDisabled: boolean;
  leadStatus: any;
  onOpenReport: (id: string) => void;
  onOpenCompany: (id: string) => void;
  onAnalyze: (p: IdentifiedProfile) => void;
  onEnrich: (id: string) => void;
  enrichingIds: Set<string>;
}) {
  const accent = getAccent(profile);
  const stats = parseInteractionStats(profile);
  const status = leadStatus?.status;
  const reportId = status === "completed" && leadStatus?.result?.id ? leadStatus.result.id : profile.latest_report_id;
  const profileMeta = (() => { try { return JSON.parse(profile.profile_metadata || "{}"); } catch { return {}; } })();
  const industry = (() => { try { const i = JSON.parse(profile.company?.industries || "[]"); return Array.isArray(i) ? i[0] : i; } catch { return profile.company?.industries; } })();
  const interactionHistory: any[] = (() => { try { return JSON.parse(profile.interaction_history || "[]"); } catch { return []; } })();
  const legacyComments: string[] = (() => { try { return JSON.parse(profile.comment_history || "[]"); } catch { return []; } })();
  const legacySources: any[] = (() => { try { return JSON.parse(profile.source_posts || "[]"); } catch { return []; } })();

  return (
    <div className={cn(
      "relative bg-white dark:bg-zinc-900 rounded-xl border transition-all duration-200 flex flex-col overflow-hidden group",
      isSelected ? "border-primary shadow-md shadow-primary/10" : "border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 hover:shadow-sm",
    )}>
      {/* Left accent bar */}
      <div className={cn("absolute left-0 top-0 bottom-0 w-1.5", accent.bar)} />

      {/* Top row: checkbox + status chips */}
      <div className="pl-4 pr-4 pt-4 flex items-start justify-between gap-2">
        <Checkbox checked={isSelected} onCheckedChange={onSelect} disabled={isDisabled} className="mt-0.5 shrink-0" />
        <div className="flex-1 flex flex-wrap justify-end gap-1">
          {status === "analyzing" && (
            <Badge className="text-[8px] h-4 px-1.5 bg-blue-100 text-blue-700 border-blue-200 animate-pulse gap-1">
              <Loader2 className="h-2 w-2 animate-spin" />{leadStatus?.currentStep || "Analyzing"}
            </Badge>
          )}
          <StatusChips profile={profile} size="xs" />
        </div>
      </div>

      {/* Identity */}
      <div className="pl-4 pr-4 pt-3 pb-4 flex items-start gap-3">
        <div className={cn("h-11 w-11 rounded-xl flex items-center justify-center text-sm font-black shrink-0 shadow-sm", accent.avatar)}>
          {getInitials(profile.name)}
        </div>
        <div className="flex-1 min-w-0 space-y-0.5">
          <h3 className="text-[14px] font-black text-zinc-900 dark:text-zinc-100 leading-tight truncate">
            {profile.name || "Anonymous Profile"}
          </h3>
          {profile.headline && (
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400 line-clamp-2 leading-snug">{profile.headline}</p>
          )}
          {(profile.company?.name || profileMeta.company_name) && (
            <div className="mt-1 space-y-1">
              <div className="flex items-center gap-1.5 flex-wrap">
                <button
                  onClick={() => profile.company_id && onOpenCompany(profile.company_id)}
                  className={cn("text-[11px] font-bold text-zinc-700 dark:text-zinc-300 hover:text-primary transition-colors truncate max-w-[160px]", profile.company_id && "cursor-pointer")}
                >
                  {profile.company?.name || profileMeta.company_name}
                </button>
                {industry && <span className="text-zinc-300 dark:text-zinc-600">·</span>}
                {industry && <span className="text-[10px] text-zinc-400 truncate max-w-[100px]">{industry}</span>}
                {profile.company?.employee_count && (
                  <>
                    <span className="text-zinc-300 dark:text-zinc-600">·</span>
                    <span className="text-[10px] text-zinc-400 flex items-center gap-0.5">
                      <Users className="h-2.5 w-2.5" />{profile.company.employee_count.toLocaleString()}
                    </span>
                  </>
                )}
              </div>
              {(profile.company?.revenue_estimate || profile.company?.market_cap || profile.company?.total_funding) && (
                <div className="flex flex-wrap gap-1">
                  {profile.company.revenue_estimate && (
                    <Badge variant="secondary" className="text-[9px] h-4 px-1.5 bg-emerald-50 text-emerald-700 border-emerald-100 font-bold">
                      $ {profile.company.revenue_estimate}
                    </Badge>
                  )}
                  {profile.company.market_cap && (
                    <Badge variant="secondary" className="text-[9px] h-4 px-1.5 bg-amber-50 text-amber-700 border-amber-100 font-bold">
                      MC {profile.company.market_cap}
                    </Badge>
                  )}
                  {profile.company.total_funding && (
                    <Badge variant="secondary"
                      onClick={() => profile.company_id && onOpenCompany(profile.company_id)}
                      className="text-[9px] h-4 px-1.5 bg-blue-50 text-blue-700 border-blue-100 font-bold cursor-pointer hover:bg-blue-100">
                      Fund: {profile.company.total_funding}
                    </Badge>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Contact row */}
      <div className="px-4 py-2.5 border-t border-zinc-100 dark:border-zinc-800 flex items-center gap-3 flex-wrap">
        {profile.email && (
          <div className="flex items-center gap-1.5 min-w-0 flex-wrap">
            <Mail className="h-3 w-3 text-zinc-400 shrink-0" />
            <span className="text-[11px] text-zinc-600 dark:text-zinc-400 truncate max-w-[140px]">{profile.email}</span>
            <EmailVerificationBadge status={profile.email_verification_status} />
          </div>
        )}
        <div className="flex items-center gap-2 ml-auto shrink-0">
          <a href={profile.linkedin_url} target="_blank" rel="noopener noreferrer"
            className="p-1 rounded-md bg-[#0077B5]/10 hover:bg-[#0077B5]/20 text-[#0077B5] transition-colors">
            <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" /></svg>
          </a>
          {profile.website && (
            <a href={ensureProtocol(profile.website)} target="_blank" rel="noopener noreferrer"
              className="p-1 rounded-md bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-500 transition-colors">
              <Globe className="h-3 w-3" />
            </a>
          )}
          {profile.company?.total_funding && (
            <Badge variant="outline"
              onClick={() => profile.company_id && onOpenCompany(profile.company_id)}
              className="text-[9px] h-5 px-1.5 bg-blue-50 text-blue-700 border-blue-200 cursor-pointer hover:bg-blue-100">
              {profile.company.total_funding}
            </Badge>
          )}
        </div>
      </div>

      {/* Signal row */}
      {stats.total > 0 && (
        <div className="px-4 py-2.5 border-t border-zinc-100 dark:border-zinc-800">
          <TouchpointTooltip profile={profile}>
            <div className="flex items-center gap-2 cursor-help group/signal">
              <div className={cn("h-6 w-6 rounded-lg flex items-center justify-center shrink-0", accent.avatar)}>
                <BarChart3 className="h-3 w-3" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-black text-zinc-900 dark:text-zinc-100">{stats.total} touchpoints</span>
                  {stats.keyword > 0 && (
                    <Badge className="bg-primary/10 text-primary border-none text-[8px] h-4 px-1.5 gap-1">
                      <Search className="h-2 w-2" />{stats.keyword}
                    </Badge>
                  )}
                  {stats.competitor > 0 && (
                    <Badge className="bg-zinc-100 dark:bg-zinc-800 text-zinc-600 border-none text-[8px] h-4 px-1.5 gap-1">
                      <Users className="h-2 w-2" />{stats.competitor}
                    </Badge>
                  )}
                </div>
                {stats.firstComment && (
                  <p className="text-[10px] text-zinc-400 truncate italic mt-0.5">"{stats.firstComment}"</p>
                )}
              </div>
              <ChevronRight className="h-3 w-3 text-zinc-300 group-hover/signal:text-primary transition-colors shrink-0" />
            </div>
          </TouchpointTooltip>
        </div>
      )}

      {/* AI Reasoning */}
      {profile.fit_reasoning && (
        <div className="px-4 py-2.5 border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50/60 dark:bg-zinc-800/20">
          <p className="text-[10px] text-zinc-600 dark:text-zinc-400 italic leading-relaxed">
            <span className="text-[9px] font-black not-italic text-primary/60 uppercase tracking-widest mr-1.5">AI Reasoning</span>
            {profile.fit_reasoning}
          </p>
        </div>
      )}

      {/* Interaction History */}
      {interactionHistory.length > 0 ? (
        <div className="px-4 py-3 border-t border-zinc-100 dark:border-zinc-800 space-y-3">
          {interactionHistory.slice(0, 3).map((comp: any, ci: number) => (
            <div key={ci} className="space-y-1.5">
              <div className="flex items-center gap-2">
                <div className="p-1 rounded-md bg-primary/10 text-primary shrink-0">
                  <Users className="h-2.5 w-2.5" />
                </div>
                <span className="text-[10px] font-black uppercase tracking-tight text-zinc-700 dark:text-zinc-300 truncate">
                  {comp.competitor}
                </span>
              </div>
              <div className="pl-6 space-y-2 border-l-2 border-primary/15 ml-1">
                {comp.posts?.slice(0, 2).map((post: any, pi: number) => (
                  <div key={pi} className="space-y-1">
                    <a href={post.url} target="_blank" rel="noopener noreferrer"
                      className="text-[10px] text-blue-600 hover:underline italic line-clamp-1 flex items-center gap-1">
                      <ExternalLink className="h-2 w-2 shrink-0 opacity-60" />
                      "{post.title}"
                    </a>
                    {post.comments?.slice(0, 2).map((comment: string, comi: number) => (
                      <p key={comi} className="text-[10px] text-zinc-400 dark:text-zinc-500 italic pl-2 line-clamp-2 border-l border-zinc-200 dark:border-zinc-700">
                        "{comment}"
                      </p>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : legacyComments.length > 0 || legacySources.length > 0 ? (
        <div className="px-4 py-3 border-t border-zinc-100 dark:border-zinc-800 space-y-3">
          {legacyComments.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[9px] font-black uppercase tracking-widest text-zinc-400 flex items-center gap-1.5">
                <MessageSquare className="h-2.5 w-2.5" /> Comments
              </span>
              <div className="space-y-1 max-h-24 overflow-y-auto">
                {legacyComments.map((c, i) => (
                  <p key={i} className="text-[10px] text-zinc-400 italic bg-zinc-50 dark:bg-zinc-800 px-2 py-1 rounded border border-zinc-100 dark:border-zinc-700">
                    "{c}"
                  </p>
                ))}
              </div>
            </div>
          )}
          {legacySources.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[9px] font-black uppercase tracking-widest text-zinc-400">Sources</span>
              {legacySources.map((s, i) => (
                <a key={i} href={s.url} target="_blank" rel="noopener noreferrer"
                  className="text-[10px] text-zinc-400 hover:text-blue-600 flex items-start gap-1 italic hover:underline line-clamp-1">
                  <ExternalLink className="h-2.5 w-2.5 mt-0.5 shrink-0 opacity-40" />
                  "{s.title}" <span className="not-italic text-[9px] text-primary/40">({s.competitor})</span>
                </a>
              ))}
            </div>
          )}
        </div>
      ) : null}

      {/* Analyzing progress */}
      {status === "analyzing" && (
        <div className="px-4 py-2 border-t border-blue-100 bg-blue-50/50">
          <div className="flex items-center justify-between text-[10px] font-bold text-blue-700 mb-1">
            <span className="flex items-center gap-1.5"><Loader2 className="h-2.5 w-2.5 animate-spin" />{leadStatus?.currentStep || "Researching..."}</span>
            <span>{leadStatus?.progress || 0}%</span>
          </div>
          <Progress value={leadStatus?.progress || 0} className="h-1 bg-blue-200/50" />
        </div>
      )}

      {/* Footer: time + actions */}
      <div className="px-4 py-3 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between gap-2 mt-auto">
        <span className="text-[10px] text-zinc-400 font-medium shrink-0">
          {getRelativeTime(profile.last_interaction_at)}
        </span>
        <div className="flex items-center gap-1.5">
          {profile.linkedin_url.startsWith("apollo_id:") && (
            <Button size="sm" variant="outline"
              className="h-7 px-2 text-[10px] font-black uppercase gap-1 hover:bg-amber-50 hover:text-amber-700 hover:border-amber-200"
              disabled={profileMeta.apollo_id && enrichingIds.has(profileMeta.apollo_id)}
              onClick={() => profileMeta.apollo_id && onEnrich(profileMeta.apollo_id)}>
              {profileMeta.apollo_id && enrichingIds.has(profileMeta.apollo_id) ? <Loader2 className="h-2.5 w-2.5 animate-spin" /> : <Zap className="h-2.5 w-2.5 text-amber-500" />}
              Enrich
            </Button>
          )}
          {reportId ? (
            <Button size="sm" className="h-7 px-3 text-[10px] font-black uppercase gap-1.5"
              onClick={() => onOpenReport(reportId)}>
              <FileText className="h-2.5 w-2.5" /> Report
              <ChevronRight className="h-2.5 w-2.5" />
            </Button>
          ) : !status && !profile.linkedin_url.startsWith("apollo_id:") && (
            <Button size="sm" variant="outline" className="h-7 px-3 text-[10px] font-black uppercase gap-1.5"
              onClick={() => onAnalyze(profile)}>
              <Play className="h-2.5 w-2.5" /> Analyze
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── ProfileGridV2 ────────────────────────────────────────────────────────────
export function ProfileGridV2({
  profiles, selectedIds, toggleSelection, leadsStatus, onOpenReport, onOpenCompany, onAnalyze, onEnrich, enrichingIds,
}: ProfileViewProps) {
  if (profiles.length === 0) return (
    <div className="flex flex-col items-center justify-center py-24 border-2 border-dashed rounded-2xl">
      <Users className="h-10 w-10 text-zinc-300 mb-3" />
      <p className="text-sm font-bold text-zinc-500">No profiles found</p>
      <p className="text-xs text-zinc-400 mt-1">Try adjusting your filters</p>
    </div>
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {profiles.map(profile => {
        const profileUrl = normalizeUrl(profile.linkedin_url);
        const leadStatus = leadsStatus?.find(s => normalizeUrl(s.url) === profileUrl || s.url === profile.linkedin_url);
        return (
          <ProfileCardV2
            key={profile.id}
            profile={profile}
            isSelected={selectedIds.has(profile.id)}
            onSelect={() => toggleSelection(profile.id)}
            isDisabled={leadStatus?.status === "analyzing" || leadStatus?.status === "pending"}
            leadStatus={leadStatus}
            onOpenReport={onOpenReport}
            onOpenCompany={onOpenCompany}
            onAnalyze={onAnalyze}
            onEnrich={onEnrich}
            enrichingIds={enrichingIds}
          />
        );
      })}
    </div>
  );
}

// ─── ProfileListV2 ────────────────────────────────────────────────────────────
export function ProfileListV2({
  profiles, selectedIds, toggleSelection, toggleSelectAll, leadsStatus, onOpenReport, onOpenCompany, onAnalyze, onEnrich, enrichingIds, sortBy, sortOrder, onSort,
}: ProfileViewProps) {
  if (profiles.length === 0) return (
    <div className="flex flex-col items-center justify-center py-24 border-2 border-dashed rounded-2xl">
      <Users className="h-10 w-10 text-zinc-300 mb-3" />
      <p className="text-sm font-bold text-zinc-500">No profiles found</p>
    </div>
  );

  const SortBtn = ({ col, label }: { col: string; label: string }) => (
    <button onClick={() => onSort(col)}
      className={cn("flex items-center gap-1 text-[10px] font-black uppercase tracking-widest transition-colors", sortBy === col ? "text-primary" : "text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300")}>
      {label}
      {sortBy === col ? (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />) : <ArrowUpDown className="h-3 w-3 opacity-30" />}
    </button>
  );

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 overflow-hidden">
      {/* Legend */}
      <div className="px-4 py-2 border-b border-zinc-100 dark:border-zinc-800 flex items-center gap-4 flex-wrap bg-zinc-50/70 dark:bg-zinc-800/30">
        <span className="text-[9px] font-black uppercase tracking-widest text-zinc-400">Classification</span>
        {[
          { color: "bg-emerald-500", label: "Potential Fit" },
          { color: "bg-blue-500",    label: "Decision Maker" },
          { color: "bg-violet-500",  label: "Buy Signal" },
          { color: "bg-rose-500",    label: "Competitor" },
          { color: "bg-zinc-400",    label: "Strategic Seller" },
          { color: "bg-zinc-300",    label: "Unclassified" },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className={cn("h-3 w-1.5 rounded-full", color)} />
            <span className="text-[10px] font-semibold text-zinc-500 dark:text-zinc-400">{label}</span>
          </div>
        ))}
      </div>

      {/* Header */}
      <div className="grid grid-cols-[40px_2fr_1.2fr_1fr_80px_120px] gap-4 px-4 py-2.5 border-b border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50">
        <div className="flex items-center">
          <Checkbox
            checked={selectedIds.size === profiles.length && profiles.length > 0}
            onCheckedChange={toggleSelectAll}
          />
        </div>
        <SortBtn col="name" label="Profile" />
        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Company</span>
        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Status</span>
        <SortBtn col="touchpoint_count" label="Signals" />
        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400 text-right">Actions</span>
      </div>

      {/* Rows */}
      <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
        {profiles.map(profile => {
          const accent = getAccent(profile);
          const profileUrl = normalizeUrl(profile.linkedin_url);
          const leadStatus = leadsStatus?.find(s => normalizeUrl(s.url) === profileUrl || s.url === profile.linkedin_url);
          const status = leadStatus?.status;
          const reportId = status === "completed" && leadStatus?.result?.id ? leadStatus.result.id : profile.latest_report_id;
          const stats = parseInteractionStats(profile);
          const profileMeta = (() => { try { return JSON.parse(profile.profile_metadata || "{}"); } catch { return {}; } })();
          const industry = (() => { try { const i = JSON.parse(profile.company?.industries || "[]"); return Array.isArray(i) ? i[0] : i; } catch { return profile.company?.industries; } })();
          const listInteractionHistory: any[] = (() => { try { return JSON.parse(profile.interaction_history || "[]"); } catch { return []; } })();

          return (
            <div key={profile.id}
              className={cn("relative grid grid-cols-[40px_2fr_1.2fr_1fr_80px_120px] gap-4 px-4 py-3 items-center transition-colors",
                selectedIds.has(profile.id) ? "bg-primary/[0.03]" : "hover:bg-zinc-50 dark:hover:bg-zinc-800/30"
              )}>
              {/* Left bar */}
              <div className={cn("absolute left-0 top-0 bottom-0 w-1.5", accent.bar)} />

              {/* Checkbox */}
              <Checkbox checked={selectedIds.has(profile.id)} onCheckedChange={() => toggleSelection(profile.id)}
                disabled={status === "analyzing" || status === "pending" || profile.linkedin_url.startsWith("apollo_id:")} />

              {/* Profile */}
              <div className="flex items-center gap-3 min-w-0">
                <div className={cn("h-9 w-9 rounded-lg flex items-center justify-center text-xs font-black shrink-0", accent.avatar)}>
                  {getInitials(profile.name)}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[13px] font-bold text-zinc-900 dark:text-zinc-100 truncate">{profile.name || "Anonymous"}</span>
                    <a href={profile.linkedin_url} target="_blank" rel="noopener noreferrer"
                      className="shrink-0 text-[#0077B5] hover:opacity-70 transition-opacity">
                      <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" /></svg>
                    </a>
                  </div>
                  {profile.headline && (
                    <p className="text-[11px] text-zinc-400 truncate">{profile.headline}</p>
                  )}
                  {profile.email && (
                    <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                      <Mail className="h-2.5 w-2.5 text-zinc-400 shrink-0" />
                      <span className="text-[11px] text-zinc-500 dark:text-zinc-400 truncate max-w-[180px]">{profile.email}</span>
                      <EmailVerificationBadge status={profile.email_verification_status} />
                    </div>
                  )}
                  {(profile.website || profileMeta.website) && (
                    <a href={ensureProtocol(profile.website || profileMeta.website)} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1 mt-0.5 group/web">
                      <Globe className="h-2.5 w-2.5 text-zinc-400 shrink-0" />
                      <span className="text-[11px] text-zinc-400 group-hover/web:text-primary truncate max-w-[200px] transition-colors">
                        {(profile.website || profileMeta.website || "").replace(/^https?:\/\//, "")}
                      </span>
                    </a>
                  )}
                  {profile.fit_reasoning && (
                    <TooltipProvider>
                      <Tooltip delayDuration={200}>
                        <TooltipTrigger asChild>
                          <p className="text-[10px] text-zinc-400 italic line-clamp-1 cursor-help mt-0.5">
                            <span className="text-[9px] font-black not-italic text-primary/50 uppercase mr-1">AI:</span>
                            {profile.fit_reasoning}
                          </p>
                        </TooltipTrigger>
                        <TooltipContent side="right" className="max-w-xs">
                          <p className="text-xs font-medium leading-relaxed">{profile.fit_reasoning}</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )}
                </div>
              </div>

              {/* Company */}
              <div className="min-w-0">
                {profile.company?.name || profileMeta.company_name ? (
                  <div>
                    <button
                      onClick={() => profile.company_id && onOpenCompany(profile.company_id)}
                      className={cn("text-[12px] font-bold text-zinc-700 dark:text-zinc-300 truncate block max-w-full", profile.company_id && "hover:text-primary cursor-pointer")}
                    >
                      {profile.company?.name || profileMeta.company_name}
                    </button>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {industry && <span className="text-[10px] text-zinc-400 truncate max-w-[100px]">{industry}</span>}
                      {profile.company?.employee_count && (
                        <span className="text-[10px] text-zinc-400 flex items-center gap-0.5 shrink-0">
                          · <Users className="h-2.5 w-2.5 ml-0.5" />{profile.company.employee_count.toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                ) : <span className="text-[11px] text-zinc-300">—</span>}
              </div>

              {/* Status */}
              <div>
                {status === "analyzing" ? (
                  <Badge className="text-[8px] h-4 px-1.5 bg-blue-100 text-blue-700 border-blue-200 animate-pulse gap-1">
                    <Loader2 className="h-2 w-2 animate-spin" />Analyzing
                  </Badge>
                ) : (
                  <StatusChips profile={profile} size="xs" />
                )}
              </div>

              {/* Signals */}
              <div>
                {stats.total > 0 ? (
                  <TouchpointTooltip profile={profile}>
                    <div className="space-y-1 cursor-help">
                      <div className="flex items-center gap-1.5">
                        <div className={cn("h-5 w-5 rounded flex items-center justify-center shrink-0", accent.avatar)}>
                          <BarChart3 className="h-2.5 w-2.5" />
                        </div>
                        <span className="text-[12px] font-black text-zinc-700 dark:text-zinc-300">{stats.total}</span>
                        {stats.keyword > 0 && <Badge className="bg-primary/10 text-primary border-none text-[8px] h-4 px-1 gap-0.5"><Search className="h-2 w-2" />{stats.keyword}</Badge>}
                        {stats.competitor > 0 && <Badge className="bg-zinc-100 dark:bg-zinc-800 text-zinc-500 border-none text-[8px] h-4 px-1 gap-0.5"><Users className="h-2 w-2" />{stats.competitor}</Badge>}
                      </div>
                      {listInteractionHistory.slice(0, 2).map((comp: any, i: number) => (
                        <div key={i} className="text-[9px] font-black uppercase text-zinc-400 truncate pl-0.5">
                          {comp.competitor}
                        </div>
                      ))}
                    </div>
                  </TouchpointTooltip>
                ) : (
                  <span className="text-[11px] text-zinc-300">—</span>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-1.5">
                {profile.linkedin_url.startsWith("apollo_id:") && (
                  <Button size="sm" variant="outline"
                    className="h-7 px-2 text-[9px] font-black uppercase gap-1 hover:bg-amber-50 hover:text-amber-700 hover:border-amber-200"
                    disabled={profileMeta.apollo_id && enrichingIds.has(profileMeta.apollo_id)}
                    onClick={() => profileMeta.apollo_id && onEnrich(profileMeta.apollo_id)}>
                    {profileMeta.apollo_id && enrichingIds.has(profileMeta.apollo_id) ? <Loader2 className="h-2.5 w-2.5 animate-spin" /> : <Zap className="h-2.5 w-2.5 text-amber-500" />}
                    Enrich
                  </Button>
                )}
                {reportId ? (
                  <Button size="sm" variant="ghost"
                    className="h-7 px-2 text-[10px] font-black uppercase text-primary hover:bg-primary/10 gap-1"
                    onClick={() => onOpenReport(reportId)}>
                    <Eye className="h-3 w-3" /> Report
                  </Button>
                ) : !status && !profile.linkedin_url.startsWith("apollo_id:") && (
                  <Button size="sm" variant="outline"
                    className="h-7 px-2 text-[9px] font-black uppercase gap-1"
                    onClick={() => onAnalyze(profile)}>
                    <Play className="h-2.5 w-2.5" /> Analyze
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
