"use client";
import { CheckCircle2, Circle, XCircle, Loader2 } from "lucide-react";
import clsx from "clsx";

export interface TraceStep {
  node: string;
  label: string;
  detail: string;
  status: "waiting" | "running" | "done" | "error";
  result?: string;
}

const DEFAULT_STEPS: TraceStep[] = [
  { node: "parse_node",      label: "Parsing RFQ",       detail: "Extracting line items, buyer info, and requirements", status: "waiting" },
  { node: "classify_node",   label: "Classifying",        detail: "Determining urgency and complexity",                  status: "waiting" },
  { node: "retrieve_node",   label: "Catalog search",     detail: "Finding matching products",                           status: "waiting" },
  { node: "feasibility_node",label: "Feasibility check",  detail: "Verifying supply availability",                       status: "waiting" },
  { node: "pricing_node",    label: "Pricing",            detail: "Calculating unit prices and totals",                  status: "waiting" },
  { node: "drafter_node",    label: "Drafting quote",     detail: "Generating professional quotation",                   status: "waiting" },
  { node: "dispatch_node",   label: "Dispatching",        detail: "Sending quote to buyer",                              status: "waiting" },
];

interface Props {
  steps?: TraceStep[];
  active?: boolean;
}

export function buildSteps(completedNodes: Set<string>, currentNode?: string): TraceStep[] {
  return DEFAULT_STEPS.map(step => {
    if (completedNodes.has(step.node)) return { ...step, status: "done" };
    if (step.node === currentNode) return { ...step, status: "running" };
    return step;
  });
}

export default function AgentTrace({ steps = DEFAULT_STEPS, active = false }: Props) {
  return (
    <div className="bg-slate-900 rounded-2xl p-5 h-full min-h-[320px]">
      <div className="flex items-center gap-2 mb-5">
        <div className="flex gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
          <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/70" />
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/70" />
        </div>
        <span className="text-slate-400 text-xs font-mono ml-1">agent.trace</span>
        {active && <span className="ml-auto flex items-center gap-1.5 text-emerald-400 text-xs"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-dot" />running</span>}
      </div>

      <div className="space-y-1">
        {steps.map((step, i) => (
          <div key={step.node} className={clsx("flex items-start gap-3 py-2.5 px-3 rounded-lg transition-all",
            step.status === "running" && "bg-indigo-500/10",
            step.status === "done"    && "opacity-70",
            step.status === "error"   && "bg-red-500/10",
          )}>
            {/* Icon */}
            <div className="flex-shrink-0 mt-0.5">
              {step.status === "done"    && <CheckCircle2 size={15} className="text-emerald-400" />}
              {step.status === "running" && <Loader2 size={15} className="text-indigo-400 animate-spin" />}
              {step.status === "error"   && <XCircle size={15} className="text-red-400" />}
              {step.status === "waiting" && <Circle size={15} className="text-slate-600" />}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={clsx("text-xs font-semibold",
                  step.status === "done"    && "text-slate-300",
                  step.status === "running" && "text-indigo-300",
                  step.status === "error"   && "text-red-300",
                  step.status === "waiting" && "text-slate-600",
                )}>{step.label}</span>
                {step.status === "running" && (
                  <span className="text-indigo-400/60 text-[10px] font-mono">...</span>
                )}
              </div>
              {step.status !== "waiting" && (
                <p className={clsx("text-[11px] mt-0.5 leading-relaxed",
                  step.status === "done" ? "text-slate-500" : "text-slate-400"
                )}>
                  {step.result || step.detail}
                </p>
              )}
            </div>

            {/* Step number */}
            <span className="text-slate-700 text-[10px] font-mono flex-shrink-0">{String(i + 1).padStart(2, "0")}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
