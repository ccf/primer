import { useState } from "react"
import type { ReviewFindingSummary } from "@/types/api"

const SEVERITY_BADGE: Record<string, string> = {
  high: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  low: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  info: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
}

const STATUS_BADGE: Record<string, string> = {
  open: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  fixed: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  dismissed: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
}

type SortKey = "severity" | "detected_at"

const SEVERITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2, info: 3 }

interface Props {
  findings: ReviewFindingSummary[]
}

export function FindingsTable({ findings }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("detected_at")
  const [sortAsc, setSortAsc] = useState(false)

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(key === "severity")
    }
  }

  if (findings.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-8 text-center text-sm text-muted-foreground">
        No automated review findings detected yet.
      </div>
    )
  }

  const sorted = [...findings].sort((a, b) => {
    let cmp = 0
    if (sortKey === "severity") {
      cmp = (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9)
    } else {
      cmp = a.detected_at.localeCompare(b.detected_at)
    }
    return sortAsc ? cmp : -cmp
  })

  const sortArrow = (key: SortKey) => {
    if (sortKey !== key) return null
    return <span className="ml-1">{sortAsc ? "\u2191" : "\u2193"}</span>
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50 text-left text-xs font-medium text-muted-foreground">
            <th
              className="cursor-pointer px-4 py-2.5"
              onClick={() => handleSort("severity")}
            >
              Severity{sortArrow("severity")}
            </th>
            <th className="px-4 py-2.5">Title</th>
            <th className="px-4 py-2.5">Source</th>
            <th className="px-4 py-2.5">File</th>
            <th className="px-4 py-2.5">Status</th>
            <th className="px-4 py-2.5">PR</th>
            <th
              className="cursor-pointer px-4 py-2.5"
              onClick={() => handleSort("detected_at")}
            >
              Date{sortArrow("detected_at")}
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((f) => (
            <tr key={f.id} className="border-b border-border last:border-0">
              <td className="px-4 py-2.5">
                <span
                  className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_BADGE[f.severity] || SEVERITY_BADGE.info}`}
                >
                  {f.severity}
                </span>
              </td>
              <td className="max-w-xs truncate px-4 py-2.5 font-medium" title={f.title}>
                {f.title}
              </td>
              <td className="px-4 py-2.5 text-muted-foreground">{f.source}</td>
              <td
                className="max-w-[200px] truncate px-4 py-2.5 font-mono text-xs text-muted-foreground"
                title={f.file_path || undefined}
              >
                {f.file_path ? `${f.file_path}${f.line_number ? `:${f.line_number}` : ""}` : "-"}
              </td>
              <td className="px-4 py-2.5">
                <span
                  className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[f.status] || STATUS_BADGE.open}`}
                >
                  {f.status}
                </span>
              </td>
              <td className="px-4 py-2.5 text-muted-foreground">
                {f.pr_number ? `#${f.pr_number}` : "-"}
              </td>
              <td className="whitespace-nowrap px-4 py-2.5 text-muted-foreground">
                {new Date(f.detected_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
