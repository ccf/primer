import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
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
          "rounded-2xl px-5 py-4",
          isUser
            ? "max-w-[75%] bg-primary text-primary-foreground"
            : "max-w-[85%] bg-card border border-border/60",
        )}
      >
        {/* Tool call indicators */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1.5">
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
            isUser && "whitespace-pre-wrap",
            !isUser && [
              "prose prose-sm dark:prose-invert max-w-none",
              // Headings
              "prose-headings:font-semibold prose-headings:tracking-tight",
              "prose-h3:text-sm prose-h3:mt-4 prose-h3:mb-2",
              "prose-h4:text-sm prose-h4:mt-3 prose-h4:mb-1",
              // Paragraphs — generous spacing so stacked items don't feel crowded
              "prose-p:my-3 prose-p:leading-relaxed",
              // Lists
              "prose-ul:my-3 prose-ol:my-3 prose-li:my-1",
              // Bold / emphasis
              "prose-strong:font-semibold prose-strong:text-foreground",
              // Code
              "prose-code:rounded prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:text-xs prose-code:font-normal prose-code:before:content-none prose-code:after:content-none",
              // Tables
              "[&_table]:my-3 [&_table]:w-full [&_table]:text-xs [&_table]:border-collapse",
              "[&_thead]:border-b [&_thead]:border-border/60",
              "[&_th]:px-3 [&_th]:py-2 [&_th]:text-left [&_th]:font-medium [&_th]:text-muted-foreground",
              "[&_td]:px-3 [&_td]:py-2 [&_td]:border-t [&_td]:border-border/40",
              "[&_tr:hover]:bg-accent/50",
              // Breathing room after tables before prose resumes
              "[&_table+*]:mt-5",
              // Horizontal rules
              "prose-hr:my-4 prose-hr:border-border/40",
              // First child flush, last child flush
              "[&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
            ],
          )}
        >
          {isUser ? (
            message.content
          ) : message.content ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
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
