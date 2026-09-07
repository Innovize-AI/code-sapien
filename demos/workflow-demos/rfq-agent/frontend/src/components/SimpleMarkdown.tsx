import React from "react";

function inlineFormat(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**")
      ? <strong key={i} className="font-semibold text-slate-800">{p.slice(2, -2)}</strong>
      : <span key={i}>{p}</span>
  );
}

export default function SimpleMarkdown({ children }: { children: string }) {
  const lines = children.split("\n");
  const nodes: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Table block: starts with |
    if (line.trim().startsWith("|")) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }
      // Parse header, separator, rows
      const rows = tableLines
        .filter(l => !l.replace(/[\s|:-]/g, "").length === false) // keep non-separator rows
        .filter(l => !/^\s*\|[\s|:-]+\|\s*$/.test(l)); // drop separator rows like |---|---|

      if (rows.length > 0) {
        const header = rows[0].split("|").filter((_, ci) => ci > 0 && ci < rows[0].split("|").length - 1).map(c => c.trim());
        const body = rows.slice(1);
        nodes.push(
          <div key={i} className="overflow-x-auto mb-4">
            <table className="w-full text-xs border-collapse">
              <thead className="bg-slate-50">
                <tr>
                  {header.map((h, hi) => (
                    <th key={hi} className="border border-slate-200 px-3 py-2 text-left text-[10px] uppercase tracking-wider font-semibold text-slate-500">
                      {inlineFormat(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {body.map((row, ri) => {
                  const cells = row.split("|").filter((_, ci) => ci > 0 && ci < row.split("|").length - 1).map(c => c.trim());
                  return (
                    <tr key={ri} className="border-b border-slate-100 hover:bg-slate-50/50">
                      {cells.map((cell, ci) => (
                        <td key={ci} className="border border-slate-100 px-3 py-1.5 text-slate-700">
                          {inlineFormat(cell)}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        );
      }
      continue;
    }

    // Heading
    if (line.startsWith("### ")) {
      nodes.push(<h3 key={i} className="text-xs font-semibold text-slate-700 uppercase tracking-wide mt-3 mb-1">{inlineFormat(line.slice(4))}</h3>);
      i++; continue;
    }
    if (line.startsWith("## ")) {
      nodes.push(<h2 key={i} className="text-sm font-semibold text-slate-800 mt-3 mb-1.5">{inlineFormat(line.slice(3))}</h2>);
      i++; continue;
    }
    if (line.startsWith("# ")) {
      nodes.push(<h1 key={i} className="text-base font-bold text-slate-900 mt-3 mb-2">{inlineFormat(line.slice(2))}</h1>);
      i++; continue;
    }

    // Horizontal rule
    if (/^[-*_]{3,}$/.test(line.trim())) {
      nodes.push(<hr key={i} className="border-slate-100 my-4" />);
      i++; continue;
    }

    // List item
    if (/^[-*+] /.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*+] /.test(lines[i])) {
        items.push(lines[i].slice(2));
        i++;
      }
      nodes.push(
        <ul key={i} className="list-disc list-inside text-sm text-slate-600 mb-2 space-y-0.5">
          {items.map((it, ii) => <li key={ii}>{inlineFormat(it)}</li>)}
        </ul>
      );
      continue;
    }

    // Empty line
    if (!line.trim()) { i++; continue; }

    // Regular paragraph
    nodes.push(<p key={i} className="text-sm text-slate-600 mb-2 leading-relaxed">{inlineFormat(line)}</p>);
    i++;
  }

  return <div>{nodes}</div>;
}
