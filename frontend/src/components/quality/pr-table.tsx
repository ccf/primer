import { useState } from "react"
import type { PRSummary } from "@/types/api"

interface Props {
  prs: PRSummary[]
}

type SortKey = "pr_number" | "additions" | "review_comments_count" | "linked_sessions"

export function PRTable({ prs }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("pr_number")
  const [sortDesc, setSortDesc] = useState(true)

  if (prs.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No pull requests linked to sessions yet.
      </div>
    )
  }

  const sorted = [...prs].sort((a, b) => {
    const av = a[sortKey] ?? 0
    const bv = b[sortKey] ?? 0
    return sortDesc ? (bv as number) - (av as number) : (av as number) - (bv as number)
  })

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDesc(!sortDesc)
    else { setSortKey(key); setSortDesc(true) }
  }

  const stateColor: Record<string, string> = {
    merged: "text-purple-600 dark:text-purple-400",
    closed: "text-red-600 dark:text-red-400",
    open: "text-emerald-600 dark:text-emerald-400",
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border/60">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50 text-left text-xs font-medium text-muted-foreground">
            <th className="px-3 py-2">Repository</th>
            <th className="cursor-pointer px-3 py-2" onClick={() => toggleSort("pr_number")}>
              PR #{sortKey === "pr_number" ? (sortDesc ? " ↓" : " ↑") : ""}
            </th>
            <th className="px-3 py-2">Title</th>
            <th className="px-3 py-2">State</th>
            <th className="px-3 py-2">Branch</th>
            <th className="cursor-pointer px-3 py-2" onClick={() => toggleSort("additions")}>
              Changes{sortKey === "additions" ? (sortDesc ? " ↓" : " ↑") : ""}
            </th>
            <th className="cursor-pointer px-3 py-2" onClick={() => toggleSort("review_comments_count")}>
              Reviews{sortKey === "review_comments_count" ? (sortDesc ? " ↓" : " ↑") : ""}
            </th>
            <th className="px-3 py-2">Author</th>
            <th className="cursor-pointer px-3 py-2" onClick={() => toggleSort("linked_sessions")}>
              Sessions{sortKey === "linked_sessions" ? (sortDesc ? " ↓" : " ↑") : ""}
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((pr) => (
            <tr key={`${pr.repository}-${pr.pr_number}`} className="border-b border-border/40 last:border-0">
              <td className="px-3 py-2 text-xs text-muted-foreground">{pr.repository}</td>
              <td className="px-3 py-2 font-mono">#{pr.pr_number}</td>
              <td className="max-w-[200px] truncate px-3 py-2">{pr.title ?? "-"}</td>
              <td className={`px-3 py-2 font-medium ${stateColor[pr.state] ?? ""}`}>{pr.state}</td>
              <td className="px-3 py-2 font-mono text-xs">{pr.head_branch ?? "-"}</td>
              <td className="px-3 py-2 text-xs">
                <span className="text-emerald-600 dark:text-emerald-400">+{pr.additions}</span>{" "}
                <span className="text-red-600 dark:text-red-400">-{pr.deletions}</span>
              </td>
              <td className="px-3 py-2 text-center">{pr.review_comments_count}</td>
              <td className="px-3 py-2 text-xs">{pr.author ?? "-"}</td>
              <td className="px-3 py-2 text-center">{pr.linked_sessions}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
