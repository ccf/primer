import { useEffect, useRef } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { ChatMessage } from "@/components/explorer/chat-message"
import { ChatInput } from "@/components/explorer/chat-input"
import { useExplorerStream } from "@/hooks/use-explorer-stream"
import type { DateRange } from "@/components/layout/date-range-picker"

const SUGGESTED_QUESTIONS = [
  "How am I trending this month?",
  "What's causing the most friction?",
  "Break down my costs by model",
  "Which tools am I using most?",
]

interface ExplorerPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function ExplorerPage({ teamId, dateRange }: ExplorerPageProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { messages, sendMessage, isStreaming, error } = useExplorerStream(
    teamId,
    dateRange,
  )
  const scrollRef = useRef<HTMLDivElement>(null)
  const sendMessageRef = useRef(sendMessage)
  useEffect(() => { sendMessageRef.current = sendMessage })

  // Auto-send initial message passed from floating explorer.
  // navigate must happen inside the timeout — if called before, the state
  // change triggers a re-render whose cleanup clears the timer.
  // setTimeout also survives StrictMode's cleanup/re-run cycle.
  useEffect(() => {
    const initialMessage = (location.state as { initialMessage?: string })?.initialMessage
    if (!initialMessage) return

    const timer = setTimeout(() => {
      sendMessageRef.current(initialMessage)
      navigate(location.pathname, { replace: true, state: {} })
    }, 0)
    return () => clearTimeout(timer)
  }, [location.state, location.pathname, navigate])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    const el = scrollRef.current
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }, [messages])

  const isEmpty = messages.length === 0

  return (
    <div className="flex h-full flex-col">
      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4">
        {isEmpty ? (
          <div className="flex h-full flex-col items-center justify-center gap-6">
            <div className="text-center">
              <h2 className="text-xl font-semibold">Explore your data</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Ask questions about your Claude Code usage in natural language
              </p>
            </div>

            {/* Suggested questions */}
            <div className="grid w-full max-w-lg gap-2">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  disabled={isStreaming}
                  className="rounded-lg border border-border bg-card px-4 py-3 text-left text-sm transition-colors hover:bg-accent disabled:opacity-50"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.map((msg, i) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                isStreaming={
                  isStreaming &&
                  msg.role === "assistant" &&
                  i === messages.length - 1
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mx-6 mb-2 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="border-t border-border px-6 py-3">
        <div className="mx-auto max-w-3xl">
          <ChatInput
            onSend={sendMessage}
            disabled={isStreaming}
            placeholder="Ask about your Claude Code usage..."
          />
          <p className="mt-1.5 text-center text-xs text-muted-foreground">
            Press Enter to send, Shift+Enter for newline
          </p>
        </div>
      </div>
    </div>
  )
}
