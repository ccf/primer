import { useRef, useEffect, type KeyboardEvent } from "react"
import { Send } from "lucide-react"
import { cn } from "@/lib/utils"

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ onSend, disabled, placeholder }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  })

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleSend() {
    const value = textareaRef.current?.value.trim()
    if (!value || disabled) return
    onSend(value)
    if (textareaRef.current) {
      textareaRef.current.value = ""
      textareaRef.current.style.height = "auto"
    }
  }

  return (
    <div className="flex items-end gap-2 rounded-xl border border-border bg-card p-2">
      <textarea
        ref={textareaRef}
        rows={1}
        placeholder={placeholder ?? "Ask about your data..."}
        disabled={disabled}
        onKeyDown={handleKeyDown}
        className={cn(
          "flex-1 resize-none bg-transparent px-2 py-1.5 text-sm outline-none",
          "placeholder:text-muted-foreground",
          disabled && "opacity-50",
        )}
      />
      <button
        onClick={handleSend}
        disabled={disabled}
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-lg transition-colors",
          "bg-primary text-primary-foreground hover:bg-primary/90",
          "disabled:opacity-50 disabled:cursor-not-allowed",
        )}
      >
        <Send className="h-4 w-4" />
      </button>
    </div>
  )
}
