import React from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Globe, Briefcase, MessageSquare, ExternalLink, TrendingUp, Calendar } from "lucide-react";

interface EvidencePanelProps {
  isOpen: boolean;
  onClose: () => void;
  data: {
    company_news?: any[];
    hiring_data?: any[];
    post_engagements?: any[];
  };
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({ isOpen, onClose, data }) => {
  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent className="sm:max-w-md overflow-y-auto bg-white dark:bg-zinc-950 border-l border-zinc-200 dark:border-zinc-800">
        <SheetHeader className="pb-6 border-b border-zinc-100 dark:border-zinc-900">
          <SheetTitle className="text-2xl font-black uppercase italic tracking-tighter text-zinc-950 dark:text-zinc-50">
            Research Evidence
          </SheetTitle>
          <SheetDescription className="text-xs font-bold text-primary uppercase tracking-[0.2em]">
            Raw signals used for analysis
          </SheetDescription>
        </SheetHeader>

        <div className="mt-8 space-y-10 pb-20">
          {/* Company News */}
          {data.company_news && data.company_news.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <Globe className="h-4 w-4 text-primary" />
                <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400">
                  Recent News Signals
                </h3>
              </div>
              <div className="space-y-3">
                {data.company_news.map((news, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-900/50 border border-zinc-100 dark:border-zinc-800/50 hover:border-primary/20 transition-all group">
                    <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 mb-2 line-clamp-2 leading-snug">
                      {news.title}
                    </h4>
                    <div className="flex items-center justify-between mt-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-[9px] h-5 uppercase tracking-tighter border-zinc-200 text-zinc-500">
                          {news.source}
                        </Badge>
                        <span className="text-[10px] font-medium text-zinc-400">{news.date}</span>
                      </div>
                      <ExternalLink className="h-3 w-3 text-zinc-400 opacity-0 group-hover:opacity-100 transition-all" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Hiring Data */}
          {data.hiring_data && data.hiring_data.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <Briefcase className="h-4 w-4 text-emerald-500" />
                <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400">
                  Expansion & Hiring
                </h3>
              </div>
              <div className="space-y-3">
                {data.hiring_data.map((job, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-emerald-500/[0.02] border border-emerald-500/10 hover:border-emerald-500/30 transition-all">
                    <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 leading-snug">
                      {job.role}
                    </h4>
                    <div className="flex items-center gap-2 mt-1">
                      <TrendingUp className="h-3 w-3 text-emerald-500" />
                      <span className="text-[11px] font-medium text-zinc-500">{job.location}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Social Engagements */}
          {data.post_engagements && data.post_engagements.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <MessageSquare className="h-4 w-4 text-blue-500" />
                <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400">
                  Social Proof & Intent
                </h3>
              </div>
              <div className="space-y-4">
                {data.post_engagements.map((post, idx) => (
                  <div key={idx} className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge className="text-[9px] uppercase font-black tracking-tighter bg-blue-500/10 text-blue-500 border-none h-5">
                        {post.type}
                      </Badge>
                      <span className="text-[10px] text-zinc-400 flex items-center gap-1">
                        <Calendar className="h-2.5 w-2.5" /> Recent
                      </span>
                    </div>
                    <div className="p-4 rounded-xl bg-blue-500/[0.02] border border-blue-500/10 italic text-[13px] leading-relaxed text-zinc-600 dark:text-zinc-400 font-medium">
                      "{post.content || post.comment_text}"
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
};
