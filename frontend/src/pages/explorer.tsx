import { useEffect, useMemo, useRef, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { BookmarkPlus, FileText, MessageSquare } from "lucide-react"
import { ChatMessage } from "@/components/explorer/chat-message"
import { ChatInput } from "@/components/explorer/chat-input"
import { SavedExplorerItems } from "@/components/explorer/saved-explorer-items"
import { Button } from "@/components/ui/button"
import { useCreateExplorerSavedItem, useDeleteExplorerSavedItem } from "@/hooks/use-api-mutations"
import { useExplorerSavedItems } from "@/hooks/use-api-queries"
import { useExplorerStream } from "@/hooks/use-explorer-stream"
import type { ExplorerSavedItemResponse } from "@/types/api"
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
  const [saveError, setSaveError] = useState<string | null>(null)
  const { messages, sendMessage, isStreaming, error } = useExplorerStream(
    teamId,
    dateRange,
  )
  const { data: savedItems } = useExplorerSavedItems()
  const createSavedItem = useCreateExplorerSavedItem()
  const deleteSavedItem = useDeleteExplorerSavedItem()
  const scrollRef = useRef<HTMLDivElement>(null)
  const sendMessageRef = useRef(sendMessage)
  useEffect(() => { sendMessageRef.current = sendMessage })

  // Auto-send initial message passed from floating explorer.
  // navigate must happen inside the timeout — if called before, the state
  // change triggers a re-render whose cleanup clears the timer.
  // setTimeout also survives StrictMode's cleanup/re-run cycle.
  useEffect(() => {
    const raw = (location.state as Record<string, unknown> | null)?.initialMessage
    if (!raw || typeof raw !== "string") return
    const initialMessage = raw

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
  const latestUserMessage = useMemo(
    () => [...messages].reverse().find((message) => message.role === "user") ?? null,
    [messages],
  )
  const latestAssistantMessage = useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant") ?? null,
    [messages],
  )

  function buildSavedItemTitle(content: string) {
    return content.length > 72 ? `${content.slice(0, 72).trimEnd()}...` : content
  }

  function handleSavePrompt() {
    if (!latestUserMessage) return
    setSaveError(null)
    createSavedItem.mutate(
      {
        item_type: "prompt",
        title: buildSavedItemTitle(latestUserMessage.content),
        prompt_text: latestUserMessage.content,
        scope_team_id: teamId,
        scope_start_date: dateRange?.startDate ?? null,
        scope_end_date: dateRange?.endDate ?? null,
      },
      {
        onError: (mutationError) => {
          setSaveError(
            mutationError instanceof Error ? mutationError.message : "Failed to save prompt",
          )
        },
      },
    )
  }

  function handleSaveReportCard() {
    if (!latestUserMessage || !latestAssistantMessage?.content) return
    setSaveError(null)
    createSavedItem.mutate(
      {
        item_type: "report_card",
        title: buildSavedItemTitle(latestUserMessage.content),
        prompt_text: latestUserMessage.content,
        result_preview: latestAssistantMessage.content.slice(0, 400),
        scope_team_id: teamId,
        scope_start_date: dateRange?.startDate ?? null,
        scope_end_date: dateRange?.endDate ?? null,
      },
      {
        onError: (mutationError) => {
          setSaveError(
            mutationError instanceof Error
              ? mutationError.message
              : "Failed to save report card",
          )
        },
      },
    )
  }

  function handleRunSavedItem(item: ExplorerSavedItemResponse) {
    sendMessage(item.prompt_text, {
      teamId: item.scope_team_id,
      startDate: item.scope_start_date ?? undefined,
      endDate: item.scope_end_date ?? undefined,
    })
  }

  return (
    <div className="grid h-full min-h-0 xl:grid-cols-[320px_minmax(0,1fr)]">
      <aside className="border-b border-border px-6 py-4 xl:border-b-0 xl:border-r xl:overflow-y-auto">
        <div className="space-y-3">
          <div>
            <h2 className="font-display text-lg">Saved Explorer</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Save recurring questions and reusable report cards.
            </p>
          </div>
          <SavedExplorerItems
            items={savedItems ?? []}
            onRun={handleRunSavedItem}
            onDelete={(itemId) => deleteSavedItem.mutate(itemId)}
            deletingId={deleteSavedItem.variables ?? null}
          />
        </div>
      </aside>

      <div className="flex min-h-0 flex-col">
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4">
        {isEmpty ? (
          <div className="flex h-full flex-col items-center justify-center gap-6">
            <div className="flex flex-col items-center gap-4 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/8">
                <MessageSquare className="h-8 w-8 text-primary" />
              </div>
              <div>
                <h2 className="font-display text-2xl">Explore your data</h2>
                <p className="mt-2 max-w-md text-sm text-muted-foreground">
                  Ask questions about your Claude Code usage in natural language.
                  Get insights about costs, productivity, tool usage, and more.
                </p>
              </div>
            </div>

            {/* Suggested questions */}
            <div className="grid w-full max-w-lg grid-cols-2 gap-2">
              {SUGGESTED_QUESTIONS.map((q, i) => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  disabled={isStreaming}
                  className="animate-stagger-in rounded-xl border border-border bg-card px-4 py-3 text-left text-sm transition-colors hover:border-primary/30 hover:bg-accent disabled:opacity-50"
                  style={{ animationDelay: `${i * 60}ms` }}
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
        {(error || saveError) && (
          <div className="mx-6 mb-2 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
            {error ?? saveError}
          </div>
        )}

        {/* Input */}
        <div className="border-t border-border px-6 py-3">
          <div className="mx-auto max-w-3xl">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={!latestUserMessage || createSavedItem.isPending}
                onClick={handleSavePrompt}
              >
                <BookmarkPlus className="mr-1 h-4 w-4" />
                Save Prompt
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={!latestUserMessage || !latestAssistantMessage?.content || createSavedItem.isPending}
                onClick={handleSaveReportCard}
              >
                <FileText className="mr-1 h-4 w-4" />
                Save Report Card
              </Button>
            </div>
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
    </div>
  )
}
