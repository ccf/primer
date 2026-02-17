import { Fragment, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ArrowUpDown, Download, FileText, ChevronDown, ChevronRight } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { formatCost, formatPercent } from "@/lib/utils"
import { exportToCsv } from "@/lib/csv-export"
import { exportToPdf } from "@/lib/pdf-export"
import { BenchmarkRadar } from "./benchmark-radar"
import type { EngineerBenchmark, BenchmarkContext } from "@/types/api"

export interface UnifiedEngineerRow {
  engineer_id: string
  name: string
  display_name: string | null
  email: string
  avatar_url: string | null
  total_sessions: number
  estimated_cost: number
  success_rate: number | null
  // benchmark
  percentile_sessions?: number
  vs_team_avg?: Record<string, number>
  // quality
  pr_count?: number
  merge_rate?: number | null
  // maturity
  leverage_score?: number
  // full benchmark record (for radar)
  _benchmark?: EngineerBenchmark
}

interface EngineerLeaderboardProps {
  engineers: UnifiedEngineerRow[]
  benchmark?: BenchmarkContext
  onSortChange: (sortBy: string) => void
  sortBy: string
}

function PercentileBadge({ value }: { value: number }) {
  if (value >= 90) return <Badge variant="success">Top 10%</Badge>
  if (value >= 75)
    return (
      <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
        Top 25%
      </Badge>
    )
  if (value >= 50) return <Badge variant="secondary">Top 50%</Badge>
  return <Badge variant="outline">Bottom 50%</Badge>
}

function DeltaIndicator({ value }: { value: number | undefined }) {
  if (value === undefined) return null
  const positive = value > 0
  return (
    <span
      className={`ml-1 text-[10px] ${positive ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}
    >
      {positive ? "+" : ""}
      {value.toFixed(0)}%
    </span>
  )
}

function LeverageBar({ score }: { score: number }) {
  const color =
    score >= 60 ? "bg-emerald-500" : score >= 30 ? "bg-amber-500" : "bg-red-400"
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 w-14 rounded-full bg-muted">
        <div
          className={`h-1.5 rounded-full ${color}`}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
      <span className="text-xs">{score.toFixed(0)}</span>
    </div>
  )
}

export function EngineerLeaderboard({
  engineers,
  benchmark,
  onSortChange,
  sortBy,
}: EngineerLeaderboardProps) {
  const navigate = useNavigate()
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const hasBenchmarks = engineers.some((e) => e.percentile_sessions != null)
  const hasQuality = engineers.some((e) => e.pr_count != null)
  const hasLeverage = engineers.some((e) => e.leverage_score != null)

  const exportHeaders = [
    "Rank",
    "Name",
    "Email",
    "Sessions",
    "Cost",
    "Success Rate",
    ...(hasQuality ? ["PRs", "Merge Rate"] : []),
    ...(hasLeverage ? ["Leverage Score"] : []),
  ]
  const exportRows = () =>
    engineers.map((e, i) => [
      String(i + 1),
      e.display_name ?? e.name,
      e.email,
      e.total_sessions,
      e.estimated_cost.toFixed(2),
      e.success_rate != null ? (e.success_rate * 100).toFixed(1) + "%" : "",
      ...(hasQuality ? [e.pr_count ?? 0, e.merge_rate != null ? (e.merge_rate * 100).toFixed(0) + "%" : ""] : []),
      ...(hasLeverage ? [e.leverage_score?.toFixed(1) ?? ""] : []),
    ])

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-medium">Engineer Leaderboard</CardTitle>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => exportToCsv("engineers.csv", exportHeaders, exportRows())}
          >
            <Download className="mr-1 h-4 w-4" />
            CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              exportToPdf("engineers.pdf", "Engineer Leaderboard", exportHeaders, exportRows())
            }
          >
            <FileText className="mr-1 h-4 w-4" />
            PDF
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                {hasBenchmarks && (
                  <th className="w-8 px-2 py-2.5" />
                )}
                {hasBenchmarks && (
                  <th className="px-3 py-2.5 text-center font-medium text-muted-foreground">
                    Rank
                  </th>
                )}
                <th
                  className="cursor-pointer px-3 py-2.5 text-left font-medium text-muted-foreground hover:text-foreground"
                  onClick={() => onSortChange("name")}
                >
                  <span className="inline-flex items-center gap-1">
                    Engineer
                    {sortBy === "name" && <ArrowUpDown className="h-3 w-3" />}
                  </span>
                </th>
                <th
                  className="cursor-pointer px-3 py-2.5 text-right font-medium text-muted-foreground hover:text-foreground"
                  onClick={() => onSortChange("total_sessions")}
                >
                  <span className="inline-flex items-center gap-1">
                    Sessions
                    {sortBy === "total_sessions" && <ArrowUpDown className="h-3 w-3" />}
                  </span>
                </th>
                <th
                  className="cursor-pointer px-3 py-2.5 text-right font-medium text-muted-foreground hover:text-foreground"
                  onClick={() => onSortChange("estimated_cost")}
                >
                  <span className="inline-flex items-center gap-1">
                    Cost
                    {sortBy === "estimated_cost" && <ArrowUpDown className="h-3 w-3" />}
                  </span>
                </th>
                <th
                  className="cursor-pointer px-3 py-2.5 text-right font-medium text-muted-foreground hover:text-foreground"
                  onClick={() => onSortChange("success_rate")}
                >
                  <span className="inline-flex items-center gap-1">
                    Success
                    {sortBy === "success_rate" && <ArrowUpDown className="h-3 w-3" />}
                  </span>
                </th>
                {hasQuality && (
                  <th className="px-3 py-2.5 text-right font-medium text-muted-foreground">
                    PRs
                  </th>
                )}
                {hasLeverage && (
                  <th className="px-3 py-2.5 text-left font-medium text-muted-foreground">
                    Leverage
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {engineers.map((eng) => (
                <Fragment key={eng.engineer_id}>
                  <tr
                    className="cursor-pointer border-b border-border last:border-0 hover:bg-muted/30"
                    onMouseEnter={() => setHoveredId(eng.engineer_id)}
                    onMouseLeave={() => setHoveredId(null)}
                    onClick={() => navigate(`/engineers/${eng.engineer_id}`)}
                  >
                    {hasBenchmarks && (
                      <td className="w-8 px-2 py-2.5">
                        {eng._benchmark && benchmark && (
                          <button
                            className="text-muted-foreground hover:text-foreground"
                            onClick={(e) => {
                              e.stopPropagation()
                              setExpandedId(
                                expandedId === eng.engineer_id ? null : eng.engineer_id,
                              )
                            }}
                          >
                            {expandedId === eng.engineer_id ? (
                              <ChevronDown className="h-3.5 w-3.5" />
                            ) : (
                              <ChevronRight className="h-3.5 w-3.5" />
                            )}
                          </button>
                        )}
                      </td>
                    )}
                    {hasBenchmarks && (
                      <td className="px-3 py-2.5 text-center">
                        {eng.percentile_sessions != null ? (
                          <PercentileBadge value={eng.percentile_sessions} />
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </td>
                    )}
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        {eng.avatar_url ? (
                          <img
                            src={eng.avatar_url}
                            alt={eng.display_name ?? eng.name}
                            className="h-6 w-6 rounded-full"
                          />
                        ) : (
                          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-[10px] font-medium">
                            {(eng.display_name ?? eng.name).charAt(0).toUpperCase()}
                          </div>
                        )}
                        <span
                          className={
                            hoveredId === eng.engineer_id ? "font-medium underline" : "font-medium"
                          }
                        >
                          {eng.display_name ?? eng.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      {eng.total_sessions}
                      <DeltaIndicator value={eng.vs_team_avg?.sessions} />
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      {formatCost(eng.estimated_cost)}
                      <DeltaIndicator value={eng.vs_team_avg?.cost} />
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      {formatPercent(eng.success_rate)}
                    </td>
                    {hasQuality && (
                      <td className="px-3 py-2.5 text-right">
                        {eng.pr_count != null ? (
                          <span>
                            {eng.pr_count}
                            {eng.merge_rate != null && (
                              <span className="ml-1 text-[10px] text-muted-foreground">
                                ({(eng.merge_rate * 100).toFixed(0)}% merged)
                              </span>
                            )}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </td>
                    )}
                    {hasLeverage && (
                      <td className="px-3 py-2.5">
                        {eng.leverage_score != null ? (
                          <LeverageBar score={eng.leverage_score} />
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </td>
                    )}
                  </tr>
                  {hasBenchmarks &&
                    expandedId === eng.engineer_id &&
                    eng._benchmark &&
                    benchmark && (
                      <tr key={`${eng.engineer_id}-radar`}>
                        <td
                          colSpan={
                            4 +
                            (hasBenchmarks ? 2 : 0) +
                            (hasQuality ? 1 : 0) +
                            (hasLeverage ? 1 : 0)
                          }
                          className="bg-muted/20 px-4 py-4"
                        >
                          <div className="mx-auto max-w-md">
                            <BenchmarkRadar engineer={eng._benchmark} benchmark={benchmark} />
                          </div>
                        </td>
                      </tr>
                    )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

