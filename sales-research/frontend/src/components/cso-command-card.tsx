import React from 'react';
import { ShieldCheck, Zap, Info, Clock, Target, ListChecks, BookOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
  };
}

export function CSOCommandCard({ data }: CSOCommandCardProps) {
  if (!data) return null;

  const isNegative = data.verdict.toLowerCase().includes('monitor') || 
                     data.verdict.toLowerCase().includes('deprioritize') || 
                     data.verdict.toLowerCase().includes('poor fit') ||
                     data.verdict.toLowerCase().includes('disqualif');

  const themeColor = isNegative ? 'zinc' : 'amber';
  const glowColor = isNegative ? 'via-zinc-500/10' : 'via-primary/20';
  const borderColor = isNegative ? 'border-zinc-200 dark:border-zinc-800' : 'border-amber-500/20 dark:border-amber-500/10';

  return (
    <div className="relative group mb-12">
      {/* Decorative Glow */}
      <div className={`absolute -inset-0.5 bg-gradient-to-r from-${themeColor}-500/20 ${glowColor} to-${themeColor}-500/20 rounded-[2.5rem] blur opacity-75 group-hover:opacity-100 transition duration-1000 group-hover:duration-200`} />
      
      <div className={`relative grid grid-cols-1 lg:grid-cols-3 gap-0 bg-white dark:bg-zinc-950 border ${borderColor} rounded-[2.5rem] overflow-hidden shadow-2xl`}>
        
        {/* Left Section: The Command */}
        <div className="lg:col-span-2 p-10 lg:p-12 space-y-8 border-b lg:border-b-0 lg:border-r border-zinc-100 dark:border-zinc-900">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`h-10 w-10 rounded-2xl bg-${themeColor}-500 text-white flex items-center justify-center shadow-lg shadow-${themeColor}-500/20`}>
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div className="space-y-0.5">
                <span className={`text-[10px] font-black text-${themeColor}-600 dark:text-${themeColor}-500 uppercase tracking-[0.25em]`}>Strategic Command</span>
                <h2 className="text-2xl font-black italic tracking-tight text-zinc-900 dark:text-zinc-100 uppercase">CSO Unified Verdict</h2>
              </div>
            </div>
            
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge variant="outline" className={`text-[10px] font-black border-${themeColor}-500/30 text-${themeColor}-600 bg-${themeColor}-500/5 px-3 py-1 uppercase tracking-widest cursor-help`}>
                    {data.framework_selected} Framework
                  </Badge>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs bg-zinc-950 text-white border-zinc-800">
                  <p className="text-xs font-medium">{data.framework_reasoning || "Optimized for persona engagement."}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          <div className={`p-8 rounded-3xl bg-${themeColor}-500/5 border border-${themeColor}-500/10 shadow-inner`}>
            <p className="text-2xl font-black text-zinc-900 dark:text-white leading-tight italic">
              "{data.verdict}"
            </p>
          </div>

          <div className="space-y-4">
            {data.product_selection_reasoning && (
                <div className="mb-6 pb-6 border-b border-dashed border-zinc-200 dark:border-zinc-800">
                    <div className="flex items-center gap-2 mb-2">
                    <Zap className={`h-3.5 w-3.5 text-${themeColor}-500`} />
                    <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Winning Offering Selection</span>
                    </div>
                    <p className="text-zinc-700 dark:text-zinc-300 text-sm leading-relaxed font-bold italic">
                    "{data.product_selection_reasoning}"
                    </p>
                </div>
            )}

            <div className="flex items-center gap-2 mb-2">
              <Info className="h-3.5 w-3.5 text-zinc-400" />
              <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Strategic Reasoning</span>
            </div>
            <p className="text-zinc-600 dark:text-zinc-400 text-sm leading-relaxed font-medium">
              {data.strategic_reasoning}
            </p>
          </div>
        </div>

        {/* Right Section: Tactical Advice */}
        <div className="bg-zinc-50/50 dark:bg-zinc-900/30 p-10 lg:p-12 space-y-10">
          <div>
            <div className="flex items-center gap-2 mb-4">
             <Clock className={`h-4 w-4 text-${themeColor}-500`} />
             <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Timing Advice</span>
            </div>
            <Badge className={cn(
              "text-[11px] font-black px-4 py-1.5 rounded-xl border",
              data.timing_advice.toLowerCase().includes('green') 
                ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20" 
                : (isNegative ? "bg-zinc-500/10 text-zinc-600 border-zinc-500/20" : "bg-amber-500/10 text-amber-600 border-amber-500/20")
            )}>
              {data.timing_advice}
            </Badge>
          </div>

          {data.strategic_proof_points && data.strategic_proof_points.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Target className="h-4 w-4 text-emerald-500" />
                <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Strategic Proof Points (RAG)</span>
              </div>
              <ul className="space-y-3">
                {data.strategic_proof_points.map((proof, i) => (
                  <li key={i} className="flex gap-3 text-xs font-bold text-zinc-700 dark:text-zinc-300 items-start">
                    <div className="mt-1 h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
                    {proof}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-6">
            <div className="flex items-center gap-2">
              <ListChecks className={`h-4 w-4 text-${themeColor}-500`} />
              <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">{isNegative ? 'Disqualification Reasons' : 'Objection Preemption'}</span>
            </div>
            <ul className="space-y-3">
              {data.objection_preemption.map((obj, i) => (
                <li key={i} className="flex gap-3 text-xs font-bold text-zinc-700 dark:text-zinc-300 items-start">
                  <div className={`mt-1 h-1.5 w-1.5 rounded-full bg-${themeColor}-500 shrink-0`} />
                  {obj}
                </li>
              ))}
            </ul>
          </div>

          <Button variant="outline" className="w-full justify-between h-12 rounded-2xl border-zinc-200 dark:border-zinc-800 hover:bg-white dark:hover:bg-zinc-900 shadow-sm">
             <div className="flex items-center gap-3">
               <BookOpen className={`h-4 w-4 text-${isNegative ? 'zinc-500' : 'primary'}`} />
               <span className="text-xs font-black uppercase tracking-tight">View Proofs ({data.sources.length})</span>
             </div>
             <Badge variant="secondary" className={`bg-${isNegative ? 'zinc' : 'primary'}/10 text-${isNegative ? 'zinc-500' : 'primary'} border-none text-[9px] font-black`}>RAG Verified</Badge>
          </Button>
        </div>

      </div>
    </div>
  );
}
