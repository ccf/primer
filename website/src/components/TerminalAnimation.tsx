import { useState, useEffect, useRef } from "react";

const LINES = [
  { text: "$ pip install primer-io", delay: 0 },
  { text: "  Installing Primer...", delay: 1200 },
  { text: "  \u2713 Server ready at http://localhost:8000", delay: 2200 },
  { text: "  \u2713 Hook installed for Claude Code", delay: 2800 },
  { text: "  \u2713 MCP sidecar connected", delay: 3400 },
  { text: "", delay: 3800 },
  { text: "$ primer doctor", delay: 4200 },
  { text: "  \u2713 Database        OK", delay: 5000 },
  { text: "  \u2713 Claude Hook     installed", delay: 5400 },
  { text: "  \u2713 MCP Server      connected", delay: 5800 },
  { text: "  All checks passed!", delay: 6200 },
];

export default function TerminalAnimation() {
  const [visibleLines, setVisibleLines] = useState(0);
  const timerRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    timerRef.current = LINES.map((line, i) =>
      setTimeout(() => setVisibleLines(i + 1), line.delay)
    );
    return () => timerRef.current.forEach(clearTimeout);
  }, []);

  return (
    <div className="w-full max-w-xl mx-auto rounded-xl overflow-hidden shadow-2xl">
      {/* Title bar */}
      <div className="flex items-center gap-2 px-4 py-3 bg-[#1a1a3e]">
        <span className="w-3 h-3 rounded-full bg-[#ff5f57]" />
        <span className="w-3 h-3 rounded-full bg-[#febc2e]" />
        <span className="w-3 h-3 rounded-full bg-[#28c840]" />
        <span className="ml-2 text-xs text-white/40 font-mono">terminal</span>
      </div>
      {/* Terminal body */}
      <div className="bg-[#0F0B2A] p-5 font-mono text-sm leading-relaxed min-h-[280px]">
        {LINES.slice(0, visibleLines).map((line, i) => (
          <div key={i} className="whitespace-pre">
            {line.text.startsWith("$") ? (
              <>
                <span className="text-[#6366F1]">$</span>
                <span className="text-white">{line.text.slice(1)}</span>
              </>
            ) : line.text.includes("\u2713") ? (
              <span className="text-emerald-400">{line.text}</span>
            ) : line.text === "" ? (
              <br />
            ) : (
              <span className="text-white/70">{line.text}</span>
            )}
          </div>
        ))}
        {visibleLines < LINES.length && (
          <span className="inline-block w-2 h-4 bg-[#6366F1] animate-pulse" />
        )}
      </div>
    </div>
  );
}
