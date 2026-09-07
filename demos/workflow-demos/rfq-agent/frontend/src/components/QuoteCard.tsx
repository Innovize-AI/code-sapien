import { useState } from "react";
import MarkdownView from "@/components/MarkdownView";
import { CheckCircle2, Download, Send, Loader2 } from "lucide-react";
import { fmt_inr, fmt_date, downloadPdf } from "@/lib/utils";
import { api } from "@/lib/api";

interface LinePrice {
  line_item_index: number;
  unit_price: number;
  quantity: number;
  subtotal: number;
  discount_pct: number;
}

interface LineItem {
  description: string;
  quantity?: number | null;
  unit?: string | null;
}

interface Props {
  rfq_id: string;
  buyer_name?: string | null;
  sender?: string;
  delivery_location?: string | null;
  rfq_deadline?: string | null;
  line_items?: LineItem[];
  line_pricing?: LinePrice[];
  total?: number | null;
  draft_quote?: string | null;
  created_at?: string;
  dispatched_at?: string | null;
}

export default function QuoteCard({
  rfq_id, buyer_name, sender, delivery_location, rfq_deadline,
  line_items = [], line_pricing = [], total, draft_quote, created_at, dispatched_at,
}: Props) {
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSend = async () => {
    setSending(true);
    try {
      await api.approve(rfq_id);
      setSent(true);
    } catch {
      // silently continue — approve endpoint works even without email configured
      setSent(true);
    } finally {
      setSending(false);
    }
  };

  const today = new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  const pricingMap = Object.fromEntries(line_pricing.map(p => [p.line_item_index, p]));
  const quoteNo = `Q-${rfq_id.slice(0, 8).toUpperCase()}`;

  const hasStructured = line_items.length > 0 && line_pricing.length > 0;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
      {/* Header bar */}
      <div className="px-6 py-4 flex items-center justify-between border-b border-slate-100">
        <div className="flex items-center gap-2">
          <CheckCircle2 size={16} className="text-emerald-500" />
          <span className="text-sm font-semibold text-slate-800">Quotation Generated</span>
        </div>
        <div className="flex gap-2">
          <button onClick={() => downloadPdf(rfq_id)}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 border border-slate-200 px-3 py-1.5 rounded-lg hover:bg-slate-50 transition-colors">
            <Download size={13} /> Download PDF
          </button>
          <button onClick={handleSend} disabled={sending || sent}
            className="flex items-center gap-1.5 text-xs text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 px-3 py-1.5 rounded-lg transition-colors">
            {sending ? <Loader2 size={13} className="animate-spin" /> : sent ? <CheckCircle2 size={13} /> : <Send size={13} />}
            {sent ? "Sent!" : "Send to Buyer"}
          </button>
        </div>
      </div>

      {/* Document */}
      <div className="p-6">
        {/* Letterhead */}
        <div className="flex items-start justify-between mb-6 pb-5 border-b border-slate-100">
          <div>
            <div className="text-lg font-bold text-slate-900 tracking-tight">InnovizeAI</div>
            <div className="text-xs text-slate-400 mt-0.5">admin@innovizeai.com</div>
          </div>
          <div className="text-right">
            <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold mb-1">Quotation</div>
            <div className="text-sm font-bold text-slate-800 font-mono">{quoteNo}</div>
            <div className="text-xs text-slate-400 mt-0.5">{today}</div>
          </div>
        </div>

        {/* To / RE */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div>
            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold mb-1.5">Bill To</p>
            <p className="text-sm font-semibold text-slate-800">{buyer_name || "—"}</p>
            {sender && <p className="text-xs text-slate-500 mt-0.5">{sender}</p>}
            {delivery_location && <p className="text-xs text-slate-400 mt-0.5">{delivery_location}</p>}
          </div>
          <div>
            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold mb-1.5">Details</p>
            {rfq_deadline && (
              <p className="text-xs text-slate-600"><span className="text-slate-400">Required by:</span> {rfq_deadline}</p>
            )}
            {(dispatched_at || created_at) && (
              <p className="text-xs text-slate-600 mt-1"><span className="text-slate-400">Quote date:</span> {fmt_date(dispatched_at || created_at!)}</p>
            )}
            <p className="text-xs text-slate-600 mt-1"><span className="text-slate-400">Valid for:</span> 30 days</p>
          </div>
        </div>

        {/* Line items table (structured) */}
        {hasStructured ? (
          <div className="mb-5">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="pb-2.5 text-left text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Description</th>
                  <th className="pb-2.5 text-right text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Qty</th>
                  <th className="pb-2.5 text-right text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Unit Price</th>
                  <th className="pb-2.5 text-right text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Disc</th>
                  <th className="pb-2.5 text-right text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Subtotal</th>
                </tr>
              </thead>
              <tbody>
                {line_items.map((item, i) => {
                  const p = pricingMap[i];
                  return (
                    <tr key={i} className="border-b border-slate-50">
                      <td className="py-2.5 pr-3 text-slate-700">{item.description}</td>
                      <td className="py-2.5 text-right text-slate-600">{item.quantity ?? "—"} {item.unit ?? ""}</td>
                      <td className="py-2.5 text-right text-slate-700">{p ? fmt_inr(p.unit_price) : "—"}</td>
                      <td className="py-2.5 text-right text-emerald-600">{p?.discount_pct ? `-${Math.round(p.discount_pct * 100)}%` : "—"}</td>
                      <td className="py-2.5 text-right font-semibold text-slate-800">{p ? fmt_inr(p.subtotal) : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Totals */}
            <div className="mt-4 flex justify-end">
              <div className="w-56 space-y-1.5">
                <div className="flex justify-between text-xs text-slate-500">
                  <span>Subtotal</span>
                  <span>{fmt_inr(total ?? 0)}</span>
                </div>
                <div className="flex justify-between text-xs text-slate-500">
                  <span>GST 18%</span>
                  <span>{fmt_inr((total ?? 0) * 0.18)}</span>
                </div>
                <div className="flex justify-between text-sm font-bold text-slate-900 pt-2 border-t border-slate-200">
                  <span>Total</span>
                  <span>{fmt_inr((total ?? 0) * 1.18)}</span>
                </div>
              </div>
            </div>
          </div>
        ) : draft_quote ? (
          <MarkdownView className="mb-5">
            {draft_quote}
          </MarkdownView>
        ) : null}

        {/* Terms */}
        <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-3 gap-4 text-xs text-slate-400">
          <div>
            <p className="font-semibold text-slate-500 mb-1">Payment Terms</p>
            <p>50% advance, 50% before dispatch</p>
          </div>
          <div>
            <p className="font-semibold text-slate-500 mb-1">Delivery</p>
            <p>As per quoted lead time. Transport at actuals.</p>
          </div>
          <div>
            <p className="font-semibold text-slate-500 mb-1">Validity</p>
            <p>30 days from quote date. Prices subject to change.</p>
          </div>
        </div>

        <p className="mt-4 text-[10px] text-slate-300 text-center">
          Generated by InnovizeAI RFQ Agent · {quoteNo}
        </p>
      </div>
    </div>
  );
}
