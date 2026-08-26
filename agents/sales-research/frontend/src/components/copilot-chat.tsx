import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { 
  Send, Bot, User, X, Sparkles, Copy, Check, 
  Globe, ArrowUpRight, HelpCircle 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { fetchCopilotHistory, sendCopilotMessage } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  text: string;
  sources?: Array<{ title: string; uri: string }>;
}

interface CopilotChatProps {
  reportId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function CopilotChat({ reportId, isOpen, onClose }: CopilotChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) {
      loadChatHistory();
    }
  }, [isOpen, reportId]);

  useEffect(scrollToBottom, [messages, loading]);

  const loadChatHistory = async () => {
    try {
      const data = await fetchCopilotHistory(reportId);
      setMessages(data.messages || []);
    } catch (e) {
      console.error("Failed to load chat history", e);
    }
  };

  const handleSend = async (messageText = input) => {
    if (!messageText.trim() || loading) return;
    
    const userMsg = messageText.trim();
    setInput("");
    setLoading(true);

    // Append user message instantly to UI
    setMessages(prev => [...prev, { role: "user", text: userMsg }]);

    try {
      const data = await sendCopilotMessage(reportId, userMsg);
      setMessages(prev => [
        ...prev,
        { 
          role: "assistant", 
          text: data.answer, 
          sources: data.sources || [] 
        }
      ]);
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to communicate with Copilot.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedId(idx);
    toast({ description: "Copied to clipboard!" });
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md border-l border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
      
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="bg-primary/10 p-1.5 rounded-lg">
            <Sparkles className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-zinc-950 dark:text-white">Glial AI Copilot</h3>
            <p className="text-[10px] text-zinc-500">Analyze lead and search web in real time</p>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full">
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Suggestion Quick Chips (when chat is empty) */}
      {messages.length === 0 && (
        <div className="p-4 space-y-2 flex-1 overflow-y-auto">
          <p className="text-xs text-zinc-500 font-medium mb-3 flex items-center gap-1.5">
            <HelpCircle className="w-3.5 h-3.5" /> Suggested Queries:
          </p>
          {[
            "Summarize the lead's main pain points & concerns.",
            "Draft a personalized email sequence based on this lead's role.",
            "Are there any recent news or press updates about this company?",
            "What solutions from our playbooks match their profile?"
          ].map((prompt, i) => (
            <button
              key={i}
              onClick={() => handleSend(prompt)}
              className="w-full text-left p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs text-zinc-700 dark:text-zinc-300 transition shadow-sm"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      {/* Messages Thread */}
      {messages.length > 0 && (
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((m, idx) => (
            <div key={idx} className={`flex items-start gap-2.5 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
              {/* Avatar */}
              <div className={`h-8 w-8 rounded-lg flex items-center justify-center shrink-0 border shadow-sm ${
                m.role === "user" 
                  ? "bg-primary text-primary-foreground border-primary/20" 
                  : "bg-white dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800"
              }`}>
                {m.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4 text-primary" />}
              </div>

              {/* Message Bubble */}
              <div className="max-w-[78%] flex flex-col space-y-1">
                <div className={`p-3 rounded-2xl text-xs shadow-sm leading-relaxed border ${
                  m.role === "user"
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-white dark:bg-zinc-900 text-zinc-800 dark:text-zinc-200 border-zinc-100 dark:border-zinc-800"
                }`}>
                  <div className="markdown-content prose prose-zinc dark:prose-invert max-w-none text-xs break-words">
                    <ReactMarkdown>
                      {m.text}
                    </ReactMarkdown>
                  </div>

                  {/* Sources Grounding section */}
                  {m.sources && m.sources.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-zinc-100 dark:border-zinc-800">
                      <p className="text-[10px] font-semibold text-zinc-400 dark:text-zinc-500 mb-1.5 flex items-center gap-1">
                        <Globe className="w-3 h-3" /> Grounded Web Sources:
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {m.sources.map((s, sidx) => (
                          <a
                            key={sidx}
                            href={s.uri}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 text-[9px] text-zinc-600 dark:text-zinc-400 font-medium truncate max-w-[130px] border border-zinc-200/50"
                          >
                            {s.title || "Source"} <ArrowUpRight className="w-2.5 h-2.5" />
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Bubble Footer Copy Action */}
                {m.role === "assistant" && (
                  <button
                    onClick={() => copyToClipboard(m.text, idx)}
                    className="self-start text-[10px] text-zinc-400 hover:text-zinc-600 flex items-center gap-1 py-1 px-2 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
                  >
                    {copiedId === idx ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                    {copiedId === idx ? "Copied" : "Copy Response"}
                  </button>
                )}
              </div>
            </div>
          ))}

          {/* Typing/Thinking Loader */}
          {loading && (
            <div className="flex items-start gap-2.5">
              <div className="h-8 w-8 rounded-lg flex items-center justify-center shrink-0 border bg-white dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800">
                <Bot className="w-4 h-4 text-primary animate-pulse" />
              </div>
              <div className="bg-white dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800 p-3.5 rounded-2xl flex items-center gap-1.5">
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]" />
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce" />
                <span className="text-[10px] text-zinc-400 ml-1.5 font-medium animate-pulse">Web Grounding...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input Tray */}
      <div className="p-3 border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex gap-2">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask about competitor products or lead insights..."
          onKeyDown={e => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          rows={1}
          className="flex-1 max-h-24 resize-none rounded-xl border border-zinc-200 dark:border-zinc-800 px-3.5 py-2.5 text-xs text-zinc-800 dark:text-zinc-200 bg-zinc-50 dark:bg-zinc-950 placeholder:text-zinc-400 focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition"
        />
        <Button 
          onClick={() => handleSend()} 
          disabled={!input.trim() || loading} 
          size="icon" 
          className="rounded-xl shrink-0 h-9 w-9 self-end"
        >
          <Send className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
