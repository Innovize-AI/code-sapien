"use client";
import { useState, useRef, useEffect, DragEvent } from "react";
import { Upload, FileText, Send, CheckCircle2, AlertTriangle, Loader2, X } from "lucide-react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import AgentTrace, { buildSteps } from "@/components/AgentTrace";
import type { UploadResponse } from "@/lib/types";
import { fmt_inr, fmt_pct } from "@/lib/utils";

type Tab = "file" | "text";

export default function SubmitPage() {
  const [tab, setTab] = useState<Tab>("text");
  const [sender, setSender] = useState("");
  const [rawText, setRawText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [traceSteps, setTraceSteps] = useState(buildSteps(new Set()));
  const [tracing, setTracing] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  };

  useEffect(() => () => stopPolling(), []);

  const startTracePolling = (rfqId: string) => {
    setTracing(true);
    setTraceSteps(buildSteps(new Set()));
    let attempts = 0;

    pollRef.current = setInterval(async () => {
      attempts++;
      try {
        const [traceData, statusData] = await Promise.all([
          api.getTrace(rfqId),
          api.getStatus(rfqId),
        ]);

        const done = new Set<string>();
        let running: string | undefined;
        for (const s of traceData.steps) {
          if (s.status === "done" || s.status === "error") done.add(s.node);
          else if (s.status === "running") running = s.node;
        }
        setTraceSteps(buildSteps(done, running));

        const finished = ["dispatched", "pending_review", "failed"].includes(statusData.status);
        if (finished || attempts > 60) {
          stopPolling();
          setTracing(false);
          // Mark all completed nodes as done on finish
          setTraceSteps(buildSteps(done));
        }
      } catch {
        // ignore transient errors
      }
    }, 800);
  };

  const reset = () => { setResult(null); setError(null); setTraceSteps(buildSteps(new Set())); setTracing(false); stopPolling(); };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  };

  const submit = async () => {
    setError(null);
    setResult(null);
    if (!sender.trim()) { setError("Sender email is required"); return; }

    setLoading(true);
    setTraceSteps(buildSteps(new Set()));
    try {
      let res: UploadResponse;
      if (tab === "file") {
        if (!file) { setError("Please select a file"); setLoading(false); return; }
        res = await api.uploadFile(file, sender);
      } else {
        if (!rawText.trim()) { setError("RFQ text is required"); setLoading(false); return; }
        res = await api.submitText(rawText, sender);
      }
      startTracePolling(res.rfq_id);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Submission failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Submit RFQ</h1>
        <p className="text-slate-500 text-sm mt-0.5">Upload a PDF/document or paste raw RFQ text. Works for both product orders and freight requests.</p>
      </div>

      <div className="grid grid-cols-5 gap-6">
        {/* Form — left 3 cols */}
        <div className="col-span-3">
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
            {/* Tabs */}
            <div className="flex gap-1 bg-slate-100 rounded-lg p-1 mb-6 w-fit">
              {([["text", "Paste Text"], ["file", "Upload File"]] as [Tab, string][]).map(([t, label]) => (
                <button key={t} onClick={() => { setTab(t); reset(); }}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === t ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}>
                  {label}
                </button>
              ))}
            </div>

            {/* Sender */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Sender Email</label>
              <input type="email" value={sender} onChange={e => setSender(e.target.value)}
                placeholder="buyer@company.com"
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent" />
            </div>

            {/* Text input */}
            {tab === "text" && (
              <div className="mb-5">
                <label className="block text-sm font-medium text-slate-700 mb-1.5">RFQ Content</label>
                <textarea value={rawText} onChange={e => setRawText(e.target.value)} rows={10}
                  placeholder={`Paste the full RFQ here. For example:\n\nHi, we need 500 M8 bolts and 200 M10 nuts delivered to Pune by 25 July.\n\nOr for freight:\nNeed a 10-ton truck from Mumbai to Delhi, cargo is steel parts, delivery in 3 days.`}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none" />
              </div>
            )}

            {/* File drop */}
            {tab === "file" && (
              <div className={`mb-5 border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer ${
                dragging ? "border-indigo-400 bg-indigo-50" : "border-slate-200 hover:border-indigo-300 hover:bg-slate-50"
              }`}
                onDragOver={e => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileRef.current?.click()}>
                <input ref={fileRef} type="file" accept=".pdf,.doc,.docx,.txt" className="hidden"
                  onChange={e => setFile(e.target.files?.[0] ?? null)} />
                {file ? (
                  <div className="flex items-center justify-center gap-3">
                    <FileText size={22} className="text-indigo-500" />
                    <span className="font-medium text-slate-700">{file.name}</span>
                    <button onClick={e => { e.stopPropagation(); setFile(null); }} className="text-slate-400 hover:text-red-500">
                      <X size={16} />
                    </button>
                  </div>
                ) : (
                  <>
                    <Upload size={28} className="mx-auto text-slate-400 mb-3" />
                    <p className="text-slate-600 font-medium">Drop your file here or click to browse</p>
                    <p className="text-slate-400 text-sm mt-1">PDF, Word, or TXT — up to 10 MB</p>
                  </>
                )}
              </div>
            )}

            {error && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
                <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" /> {error}
              </div>
            )}

            <button onClick={submit} disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-medium py-2.5 rounded-xl flex items-center justify-center gap-2 transition-colors">
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              {loading ? "Processing RFQ…" : "Submit RFQ"}
            </button>
          </div>

          {/* Result card */}
          {result && (
            <div className="mt-5 bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
              <div className="flex items-center gap-3 mb-5">
                <CheckCircle2 size={18} className="text-emerald-500" />
                <h2 className="font-semibold text-slate-900">RFQ Processed</h2>
                <StatusBadge status={result.status} />
                {result.rfq_type && (
                  <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full capitalize">{result.rfq_type}</span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3 mb-5">
                {[
                  ["RFQ ID", <span key="id" className="font-mono text-sm text-slate-800">{result.rfq_id.slice(0,8).toUpperCase()}</span>],
                  ["Total Value", <span key="val" className="font-semibold text-slate-900">{fmt_inr(result.total)}</span>],
                  ["Confidence", <span key="conf" className="font-semibold text-slate-900">{fmt_pct(result.pricing_confidence)}</span>],
                  ["Line Items", <span key="li" className="font-semibold text-slate-900">{result.line_items_count}</span>],
                ].map(([label, val]) => (
                  <div key={String(label)} className="bg-slate-50 rounded-xl p-3">
                    <p className="text-xs text-slate-400 mb-0.5">{label}</p>
                    {val}
                  </div>
                ))}
              </div>

              {result.review_notes && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 mb-4 text-sm text-amber-800">
                  {result.review_notes}
                </div>
              )}

              {result.draft_quote && (
                <details className="mb-4" open>
                  <summary className="text-sm font-medium text-indigo-600 cursor-pointer hover:underline mb-3">View Draft Quotation</summary>
                  <div className="mt-3 bg-slate-50 rounded-xl p-4 border border-slate-100 text-sm">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        table: ({ ...props }) => <table className="w-full text-xs border-collapse mb-3" {...props} />,
                        thead: ({ ...props }) => <thead className="bg-white" {...props} />,
                        th: ({ ...props }) => <th className="border border-slate-200 px-3 py-2 text-left text-[10px] uppercase tracking-wider font-semibold text-slate-500" {...props} />,
                        td: ({ ...props }) => <td className="border border-slate-100 px-3 py-1.5 text-slate-700 text-xs" {...props} />,
                        tr: ({ ...props }) => <tr className="border-b border-slate-100" {...props} />,
                        p: ({ ...props }) => <p className="text-sm text-slate-600 mb-2 leading-relaxed" {...props} />,
                        strong: ({ ...props }) => <strong className="font-semibold text-slate-800" {...props} />,
                        h2: ({ ...props }) => <h2 className="text-sm font-semibold text-slate-800 mb-1.5 mt-3" {...props} />,
                        h3: ({ ...props }) => <h3 className="text-xs font-semibold text-slate-600 mb-1 mt-2 uppercase tracking-wide" {...props} />,
                        ul: ({ ...props }) => <ul className="list-disc list-inside text-sm text-slate-600 mb-2 space-y-0.5" {...props} />,
                        li: ({ ...props }) => <li className="text-slate-600" {...props} />,
                      }}
                    >
                      {result.draft_quote}
                    </ReactMarkdown>
                  </div>
                </details>
              )}

              <Link href={`/rfqs/${result.rfq_id}`}
                className="inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:underline font-medium">
                View full details →
              </Link>
            </div>
          )}
        </div>

        {/* Agent trace — right 2 cols */}
        <div className="col-span-2">
          <div className="sticky top-6">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Agent Processing</p>
            <AgentTrace steps={traceSteps} active={tracing} />
            {!tracing && !result && (
              <p className="text-xs text-slate-400 text-center mt-3">Submit an RFQ to see the agent work in real time</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
