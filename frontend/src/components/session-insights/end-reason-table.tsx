import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatDuration, formatPercent } from "@/lib/utils"
import type { EndReasonBreakdown } from "@/types/api"

interface Props {
  data: EndReasonBreakdown[]
}

type SortKey = "end_reason" | "count" | "avg_duration" | "success_rate"

export function EndReasonTable({ data }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("count")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc")
    } else {
      setSortKey(key)
      setSortDir("desc")
    }
  }

  const sorted = [...data].sort((a, b) => {
    const av = a[sortKey] ?? 0
    const bv = b[sortKey] ?? 0
    if (typeof av === "string" && typeof bv === "string")
      return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av)
    return sortDir === "asc" ? Number(av) - Number(bv) : Number(bv) - Number(av)
  })

  const header = (label: string, key: SortKey) => (
    <th
      className="cursor-pointer px-4 py-2 text-left text-xs font-medium text-muted-foreground hover:text-foreground"
      onClick={() => toggleSort(key)}
    >
      {label} {sortKey === key ? (sortDir === "asc" ? "\u2191" : "\u2193") : ""}
    </th>
  )

  if (data.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>End Reasons</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {header("Reason", "end_reason")}
                {header("Count", "count")}
                {header("Avg Duration", "avg_duration")}
                {header("Success Rate", "success_rate")}
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr key={row.end_reason} className="border-b border-border last:border-0">
                  <td className="px-4 py-2 font-medium">{row.end_reason}</td>
                  <td className="px-4 py-2">{row.count}</td>
                  <td className="px-4 py-2">{formatDuration(row.avg_duration)}</td>
                  <td className="px-4 py-2">{formatPercent(row.success_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
