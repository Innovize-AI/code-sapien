import React from "react";
import { ShieldCheck, ShieldAlert, Clock, Target, ListChecks, Zap, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface CSOCommandCardProps {
  data: {
    verdict: string;
    framework_selected: string;
    framework_reasoning?: string;
    timing_advice: string;
    product_selection_reasoning?: string;
    strategic_reasoning: string;
    objection_preemption: string[];
    sources: Array<{ source: string; snippet: string }>;
    strategic_proof_points?: string[];
    strategic_pivot_usecase?: string;
    selected_product_name?: string;
    selected_product_justification?: string;
    lookalike_peer?: string;
  };
}

export function CSOCommandCard({ data }: CSOCommandCardProps) {
  if (!data) return null;

  const verdictStr = data.verdict || "";
  const timingAdviceStr = data.timing_advice || "";

  const isNegative =
    verdictStr.toLowerCase().includes("monitor") ||
    verdictStr.toLowerCase().includes("deprioritize") ||
    verdictStr.toLowerCase().includes("poor fit") ||
    verdictStr.toLowerCase().includes("disqualif");

  const isGreenLight =
    timingAdviceStr.toLowerCase().includes("green") ||
    timingAdviceStr.toLowerCase().includes("ideal") ||
    timingAdviceStr.toLowerCase().includes("proceed");

  const accent = isNegative
    ? {
        bar: "bg-rose-500",
        headerBg: "bg-rose-50 dark:bg-rose-500/10",
        headerBorder: "border-rose-100 dark:border-rose-500/15",
        iconBg: "bg-rose-100 dark:bg-rose-500/20",
        iconText: "text-rose-600 dark:text-rose-400",
        label: "text-rose-600 dark:text-rose-400",
        verdictBg: "bg-rose-50 dark:bg-rose-500/5",
        verdictBorder: "border-rose-200 dark:border-rose-500/15",
        verdictText: "text-rose-900 dark:text-rose-100",
        dot: "bg-rose-500",
        timingBg: "bg-rose-50 border-rose-200 text-rose-700 dark:bg-rose-500/10 dark:border-rose-500/20 dark:text-rose-400",
        frameworkBg: "bg-rose-50 border-rose-200 text-rose-600 dark:bg-rose-500/10 dark:border-rose-500/20 dark:text-rose-400",
      }
    : isGreenLight
    ? {
        bar: "bg-emerald-500",
        headerBg: "bg-emerald-50 dark:bg-emerald-500/10",
        headerBorder: "border-emerald-100 dark:border-emerald-500/15",
        iconBg: "bg-emerald-100 dark:bg-emerald-500/20",
        iconText: "text-emerald-700 dark:text-emerald-400",
        label: "text-emerald-700 dark:text-emerald-400",
        verdictBg: "bg-emerald-50 dark:bg-emerald-500/5",
        verdictBorder: "border-emerald-200 dark:border-emerald-500/15",
        verdictText: "text-emerald-900 dark:text-emerald-100",
        dot: "bg-emerald-500",
        timingBg: "bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-500/10 dark:border-emerald-500/20 dark:text-emerald-400",
        frameworkBg: "bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-500/10 dark:border-emerald-500/20 dark:text-emerald-400",
      }
    : {
        bar: "bg-amber-500",
        headerBg: "bg-amber-50 dark:bg-amber-500/10",
        headerBorder: "border-amber-100 dark:border-amber-500/15",
        iconBg: "bg-amber-100 dark:bg-amber-500/20",
        iconText: "text-amber-700 dark:text-amber-400",
        label: "text-amber-700 dark:text-amber-400",
        verdictBg: "bg-amber-50 dark:bg-amber-500/5",
        verdictBorder: "border-amber-200 dark:border-amber-500/15",
        verdictText: "text-amber-900 dark:text-amber-100",
        dot: "bg-amber-500",
        timingBg: "bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-500/10 dark:border-amber-500/20 dark:text-amber-400",
        frameworkBg: "bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-500/10 dark:border-amber-500/20 dark:text-amber-400",
      };

  return (
    <div className="relative overflow-hidden rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm">

      {/* Left accent bar */}
      <div className={cn("absolute left-0 top-0 bottom-0 w-1 rounded-l-2xl", accent.bar)} />

      {/* ── Header ── */}
      <div className={cn("pl-6 pr-5 pt-4 pb-3.5 flex items-center justify-between gap-3 border-b", accent.headerBg, accent.headerBorder)}>
        <div className="flex items-center gap-3">
          <div className={cn("h-8 w-8 rounded-xl flex items-center justify-center", accent.iconBg)}>
            {isNegative
              ? <ShieldAlert className={cn("h-4 w-4", accent.iconText)} />
              : <ShieldCheck className={cn("h-4 w-4", accent.iconText)} />}
          </div>
          <div>
            <div className={cn("text-[9px] font-black uppercase tracking-[0.3em]", accent.label)}>
              CSO Unified Verdict
            </div>
            <div className="text-[11px] font-black text-zinc-500 dark:text-zinc-400 uppercase tracking-widest">
              Strategic Command
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
          {/* Framework */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className={cn("flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[9px] font-black uppercase tracking-widest cursor-help", accent.frameworkBg)}>
                  <div className={cn("h-1.5 w-1.5 rounded-full", accent.dot)} />
                  {data.framework_selected}
                </div>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <p className="text-xs font-medium">{data.framework_reasoning || "Optimized for this persona and engagement context."}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {/* Timing */}
          <div className={cn("flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[9px] font-black uppercase tracking-widest", accent.timingBg)}>
            <Clock className="h-2.5 w-2.5" />
            {data.timing_advice}
          </div>

          {/* Source count */}
          <div className="px-2 py-1 rounded-full bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
            <span className="text-[9px] font-black text-zinc-400 uppercase tracking-widest">{(data.sources || []).length} sources</span>
          </div>
        </div>
      </div>

      {/* ── Verdict ── */}
      <div className="pl-6 pr-6 pt-5 pb-4">
        <div className={cn("relative rounded-xl p-5 border", accent.verdictBg, accent.verdictBorder)}>
          {/* Decorative quote mark */}
          <div className={cn("absolute -top-3 left-4 text-5xl font-black leading-none select-none opacity-20", accent.label)}>"</div>
          <blockquote className={cn("text-lg md:text-xl font-black italic leading-snug tracking-tight", accent.verdictText)}>
            {data.verdict}
          </blockquote>
        </div>
      </div>

      {/* Product Selection */}
      {(data.selected_product_name || data.product_selection_reasoning || data.selected_product_justification) && (
        <div className="pl-6 pr-6 pb-4">
          <div className={cn("flex items-start gap-3 p-4 rounded-xl border", accent.verdictBg, accent.verdictBorder)}>
            <Zap className={cn("h-3.5 w-3.5 mt-0.5 shrink-0", accent.iconText)} />
            <div className="space-y-1 w-full">
              <div className="text-[9px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">Winning Offering</div>
              {data.selected_product_name && (
                <div className="text-[14px] font-black text-zinc-800 dark:text-zinc-200">
                  {data.selected_product_name}
                </div>
              )}
              {data.selected_product_justification && (
                <p className="text-[12px] font-medium text-zinc-600 dark:text-zinc-400 leading-relaxed">
                  {data.selected_product_justification}
                </p>
              )}
              {data.product_selection_reasoning && (
                <p className={cn("text-[13px] font-bold italic leading-relaxed pt-0.5", accent.iconText)}>
                  {data.product_selection_reasoning}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Lookalike Peer Social Proof */}
      {data.lookalike_peer && data.lookalike_peer !== "N/A" && (
        <div className="pl-6 pr-6 pb-4">
          <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
            <span className="text-[9px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">Lookalike Peer Proof:</span>
            <Badge className="bg-primary/10 text-primary border-none text-[10px] font-black">{data.lookalike_peer}</Badge>
          </div>
        </div>
      )}

      {/* Strategic Pivot Use Case */}
      {data.strategic_pivot_usecase && data.strategic_pivot_usecase !== "N/A" && data.strategic_pivot_usecase !== "None" && (
        <div className="pl-6 pr-6 pb-4">
          <div className="flex items-start gap-3 p-4 rounded-xl border bg-indigo-500/[0.03] border-indigo-500/15 text-indigo-900 dark:text-indigo-100">
            <Target className="h-3.5 w-3.5 mt-0.5 shrink-0 text-indigo-500" />
            <div>
              <div className="text-[9px] font-black uppercase tracking-widest text-indigo-400 dark:text-indigo-500 mb-1">Strategic Pivot Use Case</div>
              <p className="text-[13px] font-bold italic leading-relaxed text-indigo-700 dark:text-indigo-300">
                {data.strategic_pivot_usecase}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Strategic Reasoning */}
      <div className="pl-6 pr-6 pb-5">
        <div className="flex items-center gap-2 mb-2">
          <Info className="h-3 w-3 text-zinc-400" />
          <span className="text-[9px] font-black text-zinc-400 uppercase tracking-[0.2em]">Strategic Reasoning</span>
        </div>
        <p className="text-[13px] text-zinc-600 dark:text-zinc-400 leading-relaxed font-medium border-l-2 border-zinc-200 dark:border-zinc-700 pl-3">
          {data.strategic_reasoning}
        </p>
      </div>

      {/* ── Bottom: Objections + Proof Points ── */}
      <div className={cn(
        "grid border-t border-zinc-100 dark:border-zinc-800",
        data.strategic_proof_points?.length ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1",
      )}>
        {/* Objections */}
        <div className={cn("p-5", data.strategic_proof_points?.length ? "md:border-r border-zinc-100 dark:border-zinc-800" : "")}>
          <div className="flex items-center gap-2 mb-3">
            <ListChecks className={cn("h-3.5 w-3.5", accent.iconText)} />
            <span className="text-[9px] font-black text-zinc-400 uppercase tracking-[0.2em]">
              {isNegative ? "Disqualification Reasons" : "Objection Preemption"}
            </span>
          </div>
          <ul className="space-y-2">
            {(data.objection_preemption || []).slice(0, 5).map((obj, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <div className={cn("mt-1.5 h-1.5 w-1.5 rounded-full shrink-0", accent.dot)} />
                <span className="text-[12px] font-medium text-zinc-600 dark:text-zinc-400 leading-relaxed">{obj}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Proof Points */}
        {data.strategic_proof_points && data.strategic_proof_points.length > 0 && (
          <div className="p-5 bg-zinc-50 dark:bg-zinc-800/40">
            <div className="flex items-center gap-2 mb-3">
              <Target className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
              <span className="text-[9px] font-black text-zinc-400 uppercase tracking-[0.2em]">Proof Points · RAG</span>
            </div>
            <ul className="space-y-2">
              {data.strategic_proof_points.slice(0, 5).map((proof, i) => (
                <li key={i} className="flex items-start gap-2.5">
                  <div className="mt-1.5 h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
                  <span className="text-[12px] font-medium text-zinc-600 dark:text-zinc-400 leading-relaxed">{proof}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

    </div>
  );
}
