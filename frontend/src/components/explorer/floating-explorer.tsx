import { useRef, useState, useSyncExternalStore, type KeyboardEvent } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { Sparkles, Send, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { SIDEBAR_KEY } from "@/lib/constants"

function subscribeSidebarState(callback: () => void) {
  window.addEventListener("storage", callback)
  window.addEventListener("sidebar-toggle", callback)
  return () => {
    window.removeEventListener("storage", callback)
    window.removeEventListener("sidebar-toggle", callback)
  }
}

function getSidebarCollapsed() {
  try { return localStorage.getItem(SIDEBAR_KEY) === "true" } catch { return false }
}

export function FloatingExplorer() {
  const location = useLocation()
  const navigate = useNavigate()
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [dismissedPath, setDismissedPath] = useState<string | null>(null)
  const sidebarCollapsed = useSyncExternalStore(subscribeSidebarState, getSidebarCollapsed)

  // Don't show on the explorer page itself or login
  if (location.pathname === "/explorer") return null
  if (location.pathname === "/login") return null
  if (location.pathname === "/auth/callback") return null
  if (dismissedPath === location.pathname) return null

  function handleInput() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleSend() {
    const value = textareaRef.current?.value.trim()
    if (!value) return
    navigate("/explorer", { state: { initialMessage: value } })
  }

  return (
    <div className={cn("fixed bottom-6 right-0 z-40 flex justify-center px-6 animate-slide-up pointer-events-none", sidebarCollapsed ? "left-16" : "left-60")}>
      <div
        className={cn(
          "pointer-events-auto w-full max-w-xl",
          "rounded-2xl border border-border/50 bg-card/80 backdrop-blur-sm shadow-elevated",
          "flex items-end gap-2 p-2",
        )}
      >
        <Sparkles className="mb-2 ml-1.5 h-4 w-4 shrink-0 text-primary" />
        <textarea
          ref={textareaRef}
          rows={1}
          placeholder="Ask about your data..."
          onInput={handleInput}
          onKeyDown={handleKeyDown}
          className="flex-1 resize-none bg-transparent px-1 py-1.5 text-sm outline-none placeholder:text-muted-foreground"
        />
        <button
          onClick={handleSend}
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors",
            "bg-primary text-primary-foreground hover:bg-primary/90",
          )}
        >
          <Send className="h-4 w-4" />
        </button>
        <button
          onClick={() => setDismissedPath(location.pathname)}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}
