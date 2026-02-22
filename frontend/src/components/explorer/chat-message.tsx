import ReactMarkdown from "react-markdown"
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
            <ReactMarkdown>{message.content}</ReactMarkdown>
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

