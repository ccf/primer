import { cn } from "@/lib/utils"
import type { ChatMessage as ChatMessageType } from "@/hooks/use-explorer-stream"

const TOOL_LABELS: Record<string, string> = {
  get_overview_stats: "Overview",
  get_friction_report: "Friction",
  get_cost_breakdown: "Costs",
  get_tool_rankings: "Tools",
  get_engineer_leaderboard: "Engineers",
  get_daily_trends: "Trends",
  get_session_health: "Health",
  get_productivity: "Productivity",
  search_sessions: "Sessions",
  get_session_detail: "Session Detail",
}

interface ChatMessageProps {
  message: ChatMessageType
  isStreaming?: boolean
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const isUser = message.role === "user"

  return (
    <div className={cn("flex w-full gap-3", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[80%] rounded-xl px-4 py-3",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-card border border-border",
        )}
      >
        {/* Tool call indicators */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {message.toolCalls.map((tc, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 rounded-md bg-accent px-2 py-0.5 text-xs text-muted-foreground"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-primary/50" />
                {TOOL_LABELS[tc.name] ?? tc.name}
              </span>
            ))}
          </div>
        )}

        {/* Message content */}
        <div
          className={cn(
            "text-sm leading-relaxed",
            !isUser && "prose prose-sm dark:prose-invert max-w-none",
            !isUser &&
              "[&_table]:text-xs [&_table]:w-full [&_th]:text-left [&_th]:pb-1 [&_td]:py-0.5",
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : message.content ? (
            <MarkdownContent content={message.content} />
          ) : isStreaming ? (
            <span className="inline-flex items-center gap-1.5 text-muted-foreground">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary/60" />
              Analyzing...
            </span>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function MarkdownContent({ content }: { content: string }) {
  // Simple markdown rendering: bold, italic, code, headers, lists, tables
  // We use dangerouslySetInnerHTML with a safe transform (no user HTML)
  const html = markdownToHtml(content)
  return <div dangerouslySetInnerHTML={{ __html: html }} />
}

function markdownToHtml(md: string): string {
  let html = md
    // Code blocks
    .replace(/```(\w*)\n([\s\S]*?)```/g, "<pre><code>$2</code></pre>")
    // Inline code
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    // Headers
    .replace(/^### (.+)$/gm, "<h4>$1</h4>")
    .replace(/^## (.+)$/gm, "<h3>$1</h3>")
    .replace(/^# (.+)$/gm, "<h2>$1</h2>")
    // Bold
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    // Italic
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    // Tables
    .replace(/^\|(.+)\|$/gm, (match) => {
      const cells = match
        .split("|")
        .filter((c) => c.trim())
        .map((c) => c.trim())
      // Check if separator row
      if (cells.every((c) => /^[-:]+$/.test(c))) {
        return "<!--sep-->"
      }
      return `<tr>${cells.map((c) => `<td>${c}</td>`).join("")}</tr>`
    })

  // Wrap table rows
  html = html.replace(
    /(<tr>[\s\S]*?<\/tr>)\n<!--sep-->\n([\s\S]*?)(?=\n(?!<tr>)|$)/g,
    (_, header, body) => {
      const headerRow = header.replace(/<td>/g, "<th>").replace(/<\/td>/g, "</th>")
      return `<table>${headerRow}${body}</table>`
    },
  )

  // Unordered lists
  html = html.replace(/^- (.+)$/gm, "<li>$1</li>")
  html = html.replace(/(<li>[\s\S]*?<\/li>)/g, (match) => {
    if (!match.startsWith("<ul>")) return `<ul>${match}</ul>`
    return match
  })
  // Merge adjacent <ul> tags
  html = html.replace(/<\/ul>\s*<ul>/g, "")

  // Paragraphs: double newlines
  html = html
    .split("\n\n")
    .map((block) => {
      const trimmed = block.trim()
      if (
        !trimmed ||
        trimmed.startsWith("<h") ||
        trimmed.startsWith("<ul") ||
        trimmed.startsWith("<table") ||
        trimmed.startsWith("<pre")
      ) {
        return trimmed
      }
      return `<p>${trimmed.replace(/\n/g, "<br/>")}</p>`
    })
    .join("\n")

  return html
}
