export type CardVariant = "gold" | "green" | "red" | "blue" | "purple" | "white"

export const variantStyles: Record<CardVariant, string> = {
  gold: "bg-gradient-to-br from-amber-50 to-amber-100 border-amber-300 dark:from-amber-950/30 dark:to-amber-900/20 dark:border-amber-700",
  green:
    "bg-emerald-50 border-emerald-300 dark:bg-emerald-950/30 dark:border-emerald-700",
  red: "bg-red-50 border-red-300 dark:bg-red-950/30 dark:border-red-700",
  blue: "bg-blue-50 border-blue-300 dark:bg-blue-950/30 dark:border-blue-700",
  purple:
    "bg-gradient-to-br from-violet-50 to-purple-50 border-violet-300 dark:from-violet-950/30 dark:to-purple-950/20 dark:border-violet-700",
  white: "bg-card border-border",
}

export const proseStyles: Record<CardVariant, string> = {
  gold: "text-amber-950/80 dark:text-amber-100/80 [&_strong]:text-amber-900 dark:[&_strong]:text-amber-200",
  green:
    "text-emerald-950/80 dark:text-emerald-100/80 [&_strong]:text-emerald-900 dark:[&_strong]:text-emerald-200",
  red: "text-red-950/80 dark:text-red-100/80 [&_strong]:text-red-900 dark:[&_strong]:text-red-200",
  blue: "text-blue-950/80 dark:text-blue-100/80 [&_strong]:text-blue-900 dark:[&_strong]:text-blue-200",
  purple:
    "text-violet-950/80 dark:text-violet-100/80 [&_strong]:text-violet-900 dark:[&_strong]:text-violet-200",
  white: "text-muted-foreground",
}

export const titleStyles: Record<CardVariant, string> = {
  gold: "text-amber-900 dark:text-amber-200",
  green: "text-emerald-900 dark:text-emerald-200",
  red: "text-red-900 dark:text-red-200",
  blue: "text-blue-900 dark:text-blue-200",
  purple: "text-violet-900 dark:text-violet-200",
  white: "text-foreground",
}

/**
 * Split markdown content on `### Title` boundaries into individual items.
 * Returns an array of { title, body } where body is the content after the heading.
 * If no ### headings are found, returns the whole content as a single item.
 */
export function splitByHeadings(content: string): { title: string; body: string }[] {
  const parts = content.split(/^###\s+/m)
  // First part is text before any ### heading (section intro)
  const intro = parts[0]?.trim() ?? ""
  const items: { title: string; body: string }[] = []

  for (let i = 1; i < parts.length; i++) {
    const lines = parts[i].split("\n")
    const title = lines[0]?.trim() ?? ""
    const body = lines.slice(1).join("\n").trim()
    if (title) {
      items.push({ title, body })
    }
  }

  // If no headings found, return everything as one item
  if (items.length === 0 && content.trim()) {
    return [{ title: "", body: content.trim() }]
  }

  // Prepend intro text to first item if present
  if (intro && items.length > 0) {
    items[0].body = intro + "\n\n" + items[0].body
  }

  return items
}

/**
 * Parse "At a Glance" content into labeled paragraphs.
 * Expects markdown with bold labels like **What's working:** followed by text.
 */
export function parseGlanceSections(
  content: string,
): { label: string; text: string }[] {
  // Split on bold labels: **Label:** pattern
  const regex = /\*\*([^*]+?):\*\*\s*/g
  const sections: { label: string; text: string }[] = []
  let match: RegExpExecArray | null

  const matches: { label: string; start: number; end: number }[] = []
  while ((match = regex.exec(content)) !== null) {
    matches.push({ label: match[1], start: match.index, end: regex.lastIndex })
  }

  for (let i = 0; i < matches.length; i++) {
    const textStart = matches[i].end
    const textEnd = i + 1 < matches.length ? matches[i + 1].start : content.length
    const text = content.slice(textStart, textEnd).trim()
    sections.push({ label: matches[i].label, text })
  }

  // Fallback: if no bold labels found, return the whole thing
  if (sections.length === 0 && content.trim()) {
    return [{ label: "", text: content.trim() }]
  }

  return sections
}
