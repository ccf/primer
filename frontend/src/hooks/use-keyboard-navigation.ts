import { useState, useEffect, useCallback, useMemo } from "react"
import { useNavigate } from "react-router-dom"

interface UseKeyboardNavigationOptions {
  items: { id: string }[]
  enabled?: boolean
}

export function useKeyboardNavigation({ items, enabled = true }: UseKeyboardNavigationOptions) {
  const [selectedIndex, setSelectedIndex] = useState<number>(-1)
  const [prevItemsKey, setPrevItemsKey] = useState<string>("")
  const navigate = useNavigate()

  // Create a stable key from item IDs to detect changes
  const itemsKey = useMemo(() => items.map((i) => i.id).join(","), [items])

  // Reset selection when items change (derive during render, no effect needed)
  if (itemsKey !== prevItemsKey) {
    setPrevItemsKey(itemsKey)
    if (selectedIndex !== -1) {
      setSelectedIndex(-1)
    }
  }

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled || items.length === 0) return

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault()
          setSelectedIndex((prev) => (prev < items.length - 1 ? prev + 1 : prev))
          break
        case "ArrowUp":
          e.preventDefault()
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : prev))
          break
        case "Enter":
          if (selectedIndex >= 0 && selectedIndex < items.length) {
            e.preventDefault()
            navigate(`/sessions/${items[selectedIndex].id}`)
          }
          break
        case "Escape":
          setSelectedIndex(-1)
          break
      }
    },
    [enabled, items, selectedIndex, navigate],
  )

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [handleKeyDown])

  return { selectedIndex }
}
