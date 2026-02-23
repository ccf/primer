import { useCallback, useEffect, useRef, useState } from "react"
import { getApiKey } from "@/lib/api"
import type { DateRange } from "@/components/layout/date-range-picker"

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  toolCalls?: { name: string; input: Record<string, unknown> }[]
}

interface UseExplorerStreamReturn {
  messages: ChatMessage[]
  sendMessage: (content: string) => void
  isStreaming: boolean
  error: string | null
  clearMessages: () => void
}

export function useExplorerStream(
  teamId: string | null,
  dateRange: DateRange | null,
): UseExplorerStreamReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
  }, [])

  const sendMessage = useCallback(
    (content: string) => {
      if (isStreaming || !content.trim()) return

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: content.trim(),
      }

      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        toolCalls: [],
      }

      setMessages((prev) => [...prev, userMsg, assistantMsg])
      setIsStreaming(true)
      setError(null)

      // Build conversation history for the API
      const allMessages = [...messages, userMsg]
      const apiMessages = allMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }))

      const apiKey = getApiKey()
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...(apiKey ? { "x-admin-key": apiKey } : {}),
      }

      const body: Record<string, unknown> = {
        messages: apiMessages,
        team_id: teamId,
      }
      if (dateRange) {
        body.start_date = dateRange.startDate
        body.end_date = dateRange.endDate
      }

      const assistantId = assistantMsg.id

      function handleSSEEvent(
        eventType: string,
        data: Record<string, unknown>,
      ) {
        if (eventType === "text") {
          const textContent = (data.content as string) ?? ""
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content + textContent }
                : m,
            ),
          )
        } else if (eventType === "tool_call") {
          const name = (data.name as string) ?? ""
          const input = (data.input as Record<string, unknown>) ?? {}
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    toolCalls: [...(m.toolCalls ?? []), { name, input }],
                  }
                : m,
            ),
          )
        } else if (eventType === "error") {
          setError((data.message as string) ?? "Unknown error")
        }
      }

      const controller = new AbortController()
      abortRef.current = controller

      fetch("/api/v1/explorer/chat", {
        method: "POST",
        headers,
        credentials: "include",
        body: JSON.stringify(body),
        signal: controller.signal,
      })
        .then(async (res) => {
          if (!res.ok) {
            const text = await res.text()
            throw new Error(text || `HTTP ${res.status}`)
          }

          const reader = res.body?.getReader()
          if (!reader) throw new Error("No response body")

          const decoder = new TextDecoder()
          let buffer = ""
          let eventType = ""

          while (true) {
            const { done, value } = await reader.read()
            if (done) break

            buffer += decoder.decode(value, { stream: true })

            // Process complete SSE events
            const lines = buffer.split("\n")
            buffer = lines.pop() ?? ""

            for (const line of lines) {
              if (line.startsWith("event: ")) {
                eventType = line.slice(7).trim()
              } else if (line.startsWith("data: ") && eventType) {
                try {
                  const data = JSON.parse(line.slice(6))
                  handleSSEEvent(eventType, data)
                } catch {
                  // Skip malformed JSON
                }
                eventType = ""
              }
            }
          }
        })
        .catch((err) => {
          if (err.name !== "AbortError") {
            setError(err.message || "Failed to connect")
          }
        })
        .finally(() => {
          setIsStreaming(false)
          abortRef.current = null
        })
    },
    [isStreaming, messages, teamId, dateRange],
  )

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  return { messages, sendMessage, isStreaming, error, clearMessages }
}
