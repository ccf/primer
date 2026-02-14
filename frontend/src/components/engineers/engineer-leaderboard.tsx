import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { ArrowUpDown, Download } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { formatTokens, formatCost, formatDuration, formatPercent } from "@/lib/utils"
import { exportToCsv } from "@/lib/csv-export"
import type { EngineerStats } from "@/types/api"

interface EngineerLeaderboardProps {
  engineers: EngineerStats[]
  onSortChange: (sortBy: string) => void
  sortBy: string
}

export function EngineerLeaderboard({ engineers, onSortChange, sortBy }: EngineerLeaderboardProps) {
  const navigate = useNavigate()
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  const columns = [
    { key: "name", label: "Name" },
    { key: "total_sessions", label: "Sessions" },
    { key: "total_tokens", label: "Tokens" },
    { key: "estimated_cost", label: "Cost" },
    { key: "success_rate", label: "Success Rate" },
    { key: "avg_duration", label: "Avg Duration" },
  ] as const

  const handleExport = () => {
    exportToCsv(
      "engineers.csv",
      ["Name", "Email", "Sessions", "Tokens", "Cost", "Success Rate", "Avg Duration", "Top Tools"],
      engineers.map((e) => [
        e.name,
        e.email,
        e.total_sessions,
        e.total_tokens,
        e.estimated_cost.toFixed(2),
        e.success_rate != null ? (e.success_rate * 100).toFixed(1) + "%" : "",
        e.avg_duration != null ? e.avg_duration.toFixed(0) : "",
        e.top_tools.join(", "),
      ]),
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-medium">Engineer Leaderboard</CardTitle>
        <Button variant="outline" size="sm" onClick={handleExport}>
          <Download className="mr-1 h-4 w-4" />
          Export CSV
        </Button>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className="cursor-pointer pb-2 text-left font-medium text-muted-foreground hover:text-foreground"
                    onClick={() => onSortChange(col.key)}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {sortBy === col.key && <ArrowUpDown className="h-3 w-3" />}
                    </span>
                  </th>
                ))}
                <th className="pb-2 text-left font-medium text-muted-foreground">Top Tools</th>
              </tr>
            </thead>
            <tbody>
              {engineers.map((eng) => (
                <tr
                  key={eng.engineer_id}
                  className="cursor-pointer border-b border-border last:border-0 hover:bg-muted/50"
                  onMouseEnter={() => setHoveredId(eng.engineer_id)}
                  onMouseLeave={() => setHoveredId(null)}
                  onClick={() => navigate(`/sessions?engineer_id=${eng.engineer_id}`)}
                >
                  <td className="py-2.5">
                    <div className="flex items-center gap-2">
                      {eng.avatar_url ? (
                        <img
                          src={eng.avatar_url}
                          alt={eng.name}
                          className="h-6 w-6 rounded-full"
                        />
                      ) : (
                        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-[10px] font-medium">
                          {eng.name.charAt(0)}
                        </div>
                      )}
                      <span className={hoveredId === eng.engineer_id ? "underline" : ""}>
                        {eng.name}
                      </span>
                    </div>
                  </td>
                  <td className="py-2.5">{eng.total_sessions}</td>
                  <td className="py-2.5">{formatTokens(eng.total_tokens)}</td>
                  <td className="py-2.5">{formatCost(eng.estimated_cost)}</td>
                  <td className="py-2.5">{formatPercent(eng.success_rate)}</td>
                  <td className="py-2.5">{formatDuration(eng.avg_duration)}</td>
                  <td className="py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {eng.top_tools.slice(0, 3).map((tool) => (
                        <Badge key={tool} variant="secondary" className="text-[10px]">
                          {tool}
                        </Badge>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
