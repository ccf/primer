import { useState } from "react"
import type { EngineerQuality } from "@/types/api"

interface Props {
  engineers: EngineerQuality[]
}

type SortKey = "total_commits" | "total_lines_added" | "pr_count" | "sessions_with_commits"

export function EngineerQualityTable({ engineers }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("total_commits")
  const [sortDesc, setSortDesc] = useState(true)

  if (engineers.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No engineer quality data available.
      </div>
    )
  }

  const sorted = [...engineers].sort((a, b) => {
    const av = a[sortKey]
    const bv = b[sortKey]
    return sortDesc ? bv - av : av - bv
  })

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDesc(!sortDesc)
    else { setSortKey(key); setSortDesc(true) }
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50 text-left text-xs font-medium text-muted-foreground">
            <th className="px-3 py-2">Engineer</th>
            <th className="cursor-pointer px-3 py-2" onClick={() => toggleSort("sessions_with_commits")}>
              Sessions{sortKey === "sessions_with_commits" ? (sortDesc ? " ↓" : " ↑") : ""}
            </th>
            <th className="cursor-pointer px-3 py-2" onClick={() => toggleSort("total_commits")}>
              Commits{sortKey === "total_commits" ? (sortDesc ? " ↓" : " ↑") : ""}
            </th>
            <th className="cursor-pointer px-3 py-2" onClick={() => toggleSort("total_lines_added")}>
              Lines Added{sortKey === "total_lines_added" ? (sortDesc ? " ↓" : " ↑") : ""}
            </th>
            <th className="px-3 py-2">Lines Deleted</th>
            <th className="cursor-pointer px-3 py-2" onClick={() => toggleSort("pr_count")}>
              PRs{sortKey === "pr_count" ? (sortDesc ? " ↓" : " ↑") : ""}
            </th>
            <th className="px-3 py-2">Merge Rate</th>
            <th className="px-3 py-2">Avg Reviews</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((eng) => (
            <tr key={eng.engineer_id} className="border-b border-border last:border-0">
              <td className="px-3 py-2 font-medium">{eng.name}</td>
              <td className="px-3 py-2">{eng.sessions_with_commits}</td>
              <td className="px-3 py-2">{eng.total_commits}</td>
              <td className="px-3 py-2 text-emerald-600 dark:text-emerald-400">+{eng.total_lines_added.toLocaleString()}</td>
              <td className="px-3 py-2 text-red-600 dark:text-red-400">-{eng.total_lines_deleted.toLocaleString()}</td>
              <td className="px-3 py-2">{eng.pr_count}</td>
              <td className="px-3 py-2">{eng.merge_rate != null ? `${(eng.merge_rate * 100).toFixed(0)}%` : "-"}</td>
              <td className="px-3 py-2">{eng.avg_review_comments != null ? eng.avg_review_comments.toFixed(1) : "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
