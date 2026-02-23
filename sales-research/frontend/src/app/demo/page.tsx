"use client";

import React, { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Zap,
  Search,
  UserCheck,
  BarChart3,
  ArrowRight,
  MousePointer2,
  MessageSquare,
  Loader2,
  Sparkles,
  ShieldCheck,
  Target,
  TrendingUp,
  Linkedin,
  Mail,
} from "lucide-react";
import { ReportDisplay } from "@/components/report-display";
import demoPosts from "@/lib/demo-data.json";
import demoReport from "@/lib/demo-report.json";
import { cn } from "@/lib/utils";

type DemoStage = "signals" | "sifting" | "analyzing" | "briefing";

const STAGES: {
  id: DemoStage;
  title: string;
  description: string;
  icon: any;
}[] = [
  {
    id: "signals",
    title: "Global Signal Interception",
    description: "Monitoring LinkedIn for high-intent activity.",
    icon: Search,
  },
  {
    id: "sifting",
    title: "Neural Sifting",
    description: "AI-driven lead qualification and ICP alignment.",
    icon: UserCheck,
  },
  {
    id: "analyzing",
    title: "Deep Analysis",
    description: "Synthesizing strategic hooks and pain points.",
    icon: Zap,
  },
  {
    id: "briefing",
    title: "Strategic Command",
    description: "The final executive briefing for your sales team.",
    icon: Sparkles,
  },
];

export default function DemoPage() {
  const [currentStage, setCurrentStage] = useState<DemoStage>("signals");
  const [progress, setProgress] = useState(0);
  const [visiblePosts, setVisiblePosts] = useState<any[]>([]);
  const [siftedLeads, setSiftedLeads] = useState<any[]>([]);
  const [scanningIndex, setScanningIndex] = useState(-1);
  const [analyzingStep, setAnalyzingStep] = useState(0);

  // Initial Stage: Signal Feeding
  useEffect(() => {
    if (currentStage === "signals") {
      const timer = setInterval(() => {
        setVisiblePosts((prev) => {
          if (prev.length >= 10) return prev;
          const nextPost =
            demoPosts.data && Array.isArray(demoPosts.data.posts)
              ? demoPosts.data.posts[prev.length]
              : null;
          return nextPost ? [...prev, nextPost] : prev;
        });
      }, 800);
      return () => clearInterval(timer);
    }
  }, [currentStage]);

  // Stage 2: Sifting Simulation
  useEffect(() => {
    if (currentStage === "sifting") {
      const timer = setInterval(() => {
        setScanningIndex((prev) => {
          const next = prev + 1;
          if (next >= visiblePosts.length) {
            clearInterval(timer);
            return prev;
          }
          // Simulate classification
          const isFit = next % 3 === 0; // Just for demo
          setSiftedLeads((s) => [...s, { ...visiblePosts[next], isFit }]);
          return next;
        });
      }, 600);
      return () => clearInterval(timer);
    }
  }, [currentStage, visiblePosts]);

  // Stage 3: Analyzing Simulation
  useEffect(() => {
    if (currentStage === "analyzing") {
      const timer = setInterval(() => {
        setAnalyzingStep((prev) => {
          if (prev >= 4) {
            clearInterval(timer);
            return prev;
          }
          return prev + 1;
        });
      }, 1500);
      return () => clearInterval(timer);
    }
  }, [currentStage]);

  const nextStage = () => {
    const currentIndex = STAGES.findIndex((s) => s.id === currentStage);
    if (currentIndex < STAGES.length - 1) {
      setCurrentStage(STAGES[currentIndex + 1].id);
      setProgress(((currentIndex + 1) / (STAGES.length - 1)) * 100);
    }
  };

  const renderSignals = () => (
    <div className="space-y-4 animate-in fade-in duration-700">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-2xl font-bold text-primary flex items-center gap-2">
            <Search className="w-6 h-6" /> Signal Interception
          </h2>
          <p className="text-muted-foreground">
            Monitoring active discussions on LinkedIn for buyer intent.
          </p>
        </div>
        <Button onClick={nextStage} className="group">
          Start Sifting{" "}
          <ArrowRight className="ml-2 group-hover:translate-x-1 transition-transform" />
        </Button>
      </div>

      <div className="grid gap-3 max-h-[60vh] overflow-hidden relative">
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent z-10" />
        {visiblePosts.map((post, i) => (
          <Card
            key={i}
            className="bg-muted/30 border-dashed border-muted-foreground/20 animate-in slide-in-from-bottom-4 duration-500"
          >
            <CardContent className="p-4 flex gap-4 items-start">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                <Linkedin className="w-4 h-4 text-primary" />
              </div>
              <div className="space-y-1 overflow-hidden">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm truncate">
                    {post.author?.first_name} {post.author?.last_name}
                  </span>
                  <Badge variant="outline" className="text-[10px] py-0">
                    {post.posted_at?.relative || "Just now"}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground line-clamp-2 italic">
                  "{post.text}"
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );

  const renderSifting = () => (
    <div className="space-y-6 animate-in fade-in duration-700">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-2xl font-bold text-primary flex items-center gap-2">
            <UserCheck className="w-6 h-6" /> Neural Sifting Layer
          </h2>
          <p className="text-muted-foreground">
            Filtering competitors, noise, and non-ICP leads in real-time.
          </p>
        </div>
        <Button
          onClick={nextStage}
          disabled={scanningIndex < visiblePosts.length - 1}
          className="group"
        >
          Run Deep Analysis{" "}
          <ArrowRight className="ml-2 group-hover:translate-x-1 transition-transform" />
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {siftedLeads.map((lead, i) => (
          <Card
            key={i}
            className={cn(
              "transition-all duration-500",
              lead.isFit
                ? "border-emerald-500/50 bg-emerald-500/5"
                : "opacity-40 scale-95 border-rose-500/20",
            )}
          >
            <CardContent className="p-4 space-y-3">
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-muted overflow-hidden">
                    {lead.isFit ? (
                      <Sparkles className="w-4 h-4 m-2 text-primary" />
                    ) : (
                      <div />
                    )}
                  </div>
                  <span className="font-bold text-sm truncate w-24">
                    {lead.author?.first_name} {lead.author?.last_name}
                  </span>
                </div>
                <Badge
                  variant={lead.isFit ? "default" : "outline"}
                  className={lead.isFit ? "bg-emerald-600" : "text-rose-600"}
                >
                  {lead.isFit ? "Target ICP" : "Non-Fit"}
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground line-clamp-2">
                "{lead.text}"
              </p>
              {lead.isFit && (
                <div className="pt-2 border-t border-emerald-500/20 flex items-center gap-1 text-[10px] font-bold text-emerald-600 uppercase">
                  <Target className="w-3 h-3" /> Decision Maker Identified
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );

  const renderAnalyzing = () => (
    <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-8 animate-in zoom-in-95 duration-700">
      <div className="relative">
        <div className="absolute inset-0 bg-primary/20 blur-3xl animate-pulse rounded-full" />
        <div className="relative w-32 h-32 bg-primary/10 rounded-3xl border border-primary/20 flex items-center justify-center">
          <Zap className="w-16 h-16 text-primary animate-bounce" />
        </div>
        <div className="absolute -top-2 -right-2 w-8 h-8 bg-emerald-500 rounded-full border-4 border-background flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
      </div>

      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <h3 className="text-xl font-bold">Sales Brain in Action</h3>
          <p className="text-sm text-muted-foreground">
            Architecting the strategic narrative for {demoReport.fullname}...
          </p>
        </div>

        <div className="space-y-3">
          {[
            "Ingesting ICP Playbooks & ROI Stories",
            "Extracting Post Intent & Pain Signals",
            "Mapping Website Context to Strategic Pillars",
            "Synthesizing CSO Verdict & Outreach Design",
          ].map((step, i) => (
            <div
              key={i}
              className={cn(
                "flex items-center gap-3 text-sm transition-all duration-300",
                analyzingStep > i
                  ? "text-emerald-500 font-medium"
                  : analyzingStep === i
                    ? "text-primary animate-pulse"
                    : "text-muted-foreground opacity-30",
              )}
            >
              <div
                className={cn(
                  "w-5 h-5 rounded-full border flex items-center justify-center text-[10px]",
                  analyzingStep > i
                    ? "bg-emerald-500 border-emerald-500 text-white"
                    : "border-muted-foreground",
                )}
              >
                {analyzingStep > i ? (
                  <ShieldCheck className="w-3 h-3" />
                ) : (
                  i + 1
                )}
              </div>
              {step}
            </div>
          ))}
        </div>

        <Progress value={(analyzingStep / 4) * 100} className="h-2" />

        {analyzingStep === 4 && (
          <Button
            onClick={nextStage}
            className="w-full animate-in fade-in slide-in-from-top-2 duration-500"
          >
            View Strategic Briefing <ArrowRight className="ml-2" />
          </Button>
        )}
      </div>
    </div>
  );

  const renderBriefing = () => (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-1000">
      <div className="flex items-center gap-4 bg-primary/5 p-4 rounded-2xl border border-primary/20 mb-8">
        <div className="p-3 bg-primary rounded-xl text-white shadow-lg shadow-primary/20">
          <TrendingUp className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-xl font-black text-primary uppercase tracking-tight">
            Strategic Intelligence Ready
          </h2>
          <p className="text-sm text-muted-foreground">
            High-grade account intelligence synthesized into 1 click.
          </p>
        </div>
      </div>

      <ReportDisplay data={demoReport as any} />
    </div>
  );

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto space-y-12 pb-20">
        {/* Demo Stepper */}
        <div className="grid grid-cols-4 gap-4">
          {STAGES.map((s, i) => (
            <div key={s.id} className="relative group">
              <div
                className={cn(
                  "flex flex-col items-center gap-2 p-4 rounded-2xl border transition-all duration-500",
                  currentStage === s.id
                    ? "bg-primary/5 border-primary shadow-sm"
                    : "border-transparent opacity-40 hover:opacity-60",
                )}
              >
                <div
                  className={cn(
                    "w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-500",
                    currentStage === s.id
                      ? "bg-primary text-white scale-110"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  <s.icon className="w-5 h-5" />
                </div>
                <div className="text-center hidden md:block">
                  <p className="text-xs font-black uppercase tracking-widest">
                    {s.title}
                  </p>
                </div>
              </div>
              {i < STAGES.length - 1 && (
                <div className="absolute top-1/2 -right-2 w-4 h-px bg-muted-foreground/20 hidden md:block" />
              )}
            </div>
          ))}
        </div>

        {/* Content Area */}
        <div className="min-h-[50vh]">
          {currentStage === "signals" && renderSignals()}
          {currentStage === "sifting" && renderSifting()}
          {currentStage === "analyzing" && renderAnalyzing()}
          {currentStage === "briefing" && renderBriefing()}
        </div>
      </div>
    </DashboardLayout>
  );
}
