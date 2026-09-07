"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  children: string;
  className?: string;
}

export default function MarkdownView({ children, className }: Props) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ ...props }) => <h1 className="text-base font-bold text-brand-text mb-2 mt-4 first:mt-0" {...props} />,
          h2: ({ ...props }) => <h2 className="text-sm font-bold text-brand-text mb-2 mt-4 first:mt-0" {...props} />,
          h3: ({ ...props }) => <h3 className="text-sm font-semibold text-brand-text mb-1 mt-3" {...props} />,
          p:  ({ ...props }) => <p className="text-sm text-brand-text leading-7 mb-3 opacity-90" {...props} />,
          strong: ({ ...props }) => <strong className="font-semibold text-brand-text" {...props} />,
          em:     ({ ...props }) => <em className="italic text-brand-muted" {...props} />,
          ul: ({ ...props }) => <ul className="list-disc list-inside text-sm text-brand-text space-y-1 mb-3 opacity-90" {...props} />,
          ol: ({ ...props }) => <ol className="list-decimal list-inside text-sm text-brand-text space-y-1 mb-3 opacity-90" {...props} />,
          li: ({ ...props }) => <li className="leading-6" {...props} />,
          hr: () => <hr className="border-brand-border my-4" />,
          table: ({ ...props }) => (
            <div className="overflow-x-auto mb-4">
              <table className="w-full text-xs border-collapse" {...props} />
            </div>
          ),
          thead: ({ ...props }) => <thead className="border-b border-brand-border" {...props} />,
          tr:    ({ ...props }) => <tr className="border-b border-brand-border last:border-0" {...props} />,
          th: ({ ...props }) => <th className="py-2 px-3 text-left text-[10px] font-semibold text-brand-muted uppercase tracking-wider" {...props} />,
          td: ({ ...props }) => <td className="py-2.5 px-3 text-sm text-brand-text" {...props} />,
          code: ({ ...props }) => <code className="font-mono text-xs bg-brand-elevated px-1 py-0.5 rounded text-teal-400" {...props} />,
          blockquote: ({ ...props }) => <blockquote className="border-l-2 border-brand-border pl-4 text-brand-muted italic my-3" {...props} />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
