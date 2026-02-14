import { useState } from "react"
import { useTranscript } from "@/hooks/use-api-queries"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChevronDown, ChevronRight, MessageSquare, Terminal, Bot } from "lucide-react"
import { cn } from "@/lib/utils"
import type { SessionMessage } from "@/types/api"

interface TranscriptViewerProps {
  sessionId: string
}

function MessageBubble({ message }: { message: SessionMessage }) {
  const [expanded, setExpanded] = useState(false)
  const isHuman = message.role === "human"
  const isAssistant = message.role === "assistant"
  const isToolResult = message.role === "tool_result"

  return (
    <div
      className={cn(
        "flex gap-3",
        isHuman ? "justify-start" : "justify-start",
      )}
    >
      <div className="flex-shrink-0 mt-1">
        {isHuman && (
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-muted">
            <MessageSquare className="h-3.5 w-3.5" />
          </div>
        )}
        {isAssistant && (
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Bot className="h-3.5 w-3.5" />
          </div>
        )}
        {isToolResult && (
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400">
            <Terminal className="h-3.5 w-3.5" />
          </div>
        )}
      </div>

      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-medium">
            {isHuman ? "User" : isAssistant ? "Assistant" : "Tool Result"}
          </span>
          {message.model && (
            <span className="text-[10px] rounded bg-muted px-1.5 py-0.5">
              {message.model.replace(/^claude-/, "").split("-202")[0]}
            </span>
          )}
          {message.token_count != null && (
            <span>{message.token_count.toLocaleString()} tokens</span>
          )}
        </div>

        {message.content_text && (
          <div
            className={cn(
              "rounded-lg px-3 py-2 text-sm",
              isHuman
                ? "bg-muted"
                : isAssistant
                  ? "bg-primary/5 border border-border"
                  : "bg-amber-500/5 border border-amber-500/20",
            )}
          >
            <p className="whitespace-pre-wrap break-words">{message.content_text}</p>
          </div>
        )}

        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="space-y-1">
            {message.tool_calls.map((tc, i) => (
              <button
                key={i}
                onClick={() => setExpanded(!expanded)}
                className="flex w-full items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-left text-xs hover:bg-accent"
              >
                {expanded ? (
                  <ChevronDown className="h-3 w-3 flex-shrink-0" />
                ) : (
                  <ChevronRight className="h-3 w-3 flex-shrink-0" />
                )}
                <Terminal className="h-3 w-3 flex-shrink-0 text-muted-foreground" />
                <span className="font-medium">{tc.name}</span>
                {expanded && (
                  <pre className="mt-1 block w-full overflow-x-auto rounded bg-muted p-2 text-[11px]">
                    {tc.input_preview}
                  </pre>
                )}
              </button>
            ))}
          </div>
        )}

        {message.tool_results && message.tool_results.length > 0 && (
          <div className="space-y-1">
            {message.tool_results.map((tr, i) => (
              <div key={i}>
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                  <Terminal className="h-3 w-3" />
                  <span className="font-medium">{tr.name}</span>
                </div>
                <pre className="overflow-x-auto rounded-md bg-muted p-2 text-[11px] max-h-32 overflow-y-auto">
                  {tr.output_preview}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function TranscriptViewer({ sessionId }: TranscriptViewerProps) {
  const { data: messages, isLoading } = useTranscript(sessionId)

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Transcript</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex gap-3">
                <div className="h-7 w-7 animate-pulse rounded-full bg-muted" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-20 animate-pulse rounded bg-muted" />
                  <div className="h-12 animate-pulse rounded-lg bg-muted" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!messages || messages.length === 0) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <MessageSquare className="h-4 w-4" />
          Transcript
          <span className="text-xs font-normal text-muted-foreground">
            ({messages.length} messages)
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="max-h-[600px] space-y-4 overflow-y-auto pr-2">
          {messages.map((msg) => (
            <MessageBubble key={msg.ordinal} message={msg} />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
