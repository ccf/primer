import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { useClaudePRComparison } from "@/hooks/use-api-queries"
import { cn, formatMetric } from "@/lib/utils"
import { GitPullRequest } from "lucide-react"
import type { PRGroupMetrics } from "@/types/api"

interface ClaudePRComparisonProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

function formatMetricWithSuffix(value: number | null, suffix = ""): string {
  const base = formatMetric(value)
  return base === "-" ? base : `${base}${suffix}`
}

function DeltaIndicator({ value }: { value: number | null }) {
  if (value == null) return <span className="text-muted-foreground">-</span>

  const isPositive = value > 0
  const isNegative = value < 0

  return (
    <span
      className={cn(
        "text-xs font-medium",
        isPositive && "text-emerald-600 dark:text-emerald-400",
        isNegative && "text-red-600 dark:text-red-400",
        !isPositive && !isNegative && "text-muted-foreground",
      )}
    >
      {isPositive ? "+" : ""}
      {value.toFixed(1)}
    </span>
  )
}

function MetricRow({
  label,
  claudeValue,
  otherValue,
  delta,
  suffix,
  invertDelta,
}: {
  label: string
  claudeValue: number | null
  otherValue: number | null
  delta?: number | null
  suffix?: string
  invertDelta?: boolean
}) {
  const displayDelta = delta != null && invertDelta ? -delta : delta
  return (
    <div className="grid grid-cols-4 gap-4 border-b border-border py-3 last:border-0">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="text-sm font-medium">{formatMetricWithSuffix(claudeValue, suffix)}</div>
      <div className="text-sm font-medium">{formatMetricWithSuffix(otherValue, suffix)}</div>
      <div className="flex items-center">
        <DeltaIndicator value={displayDelta ?? null} />
      </div>
    </div>
  )
}

function ColumnGroup({ title, metrics }: { title: string; metrics: PRGroupMetrics }) {
  return (
    <div>
      <p className="mb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {title}
      </p>
      <p className="text-2xl font-bold">{metrics.pr_count}</p>
      <p className="text-xs text-muted-foreground">pull requests</p>
    </div>
  )
}

export function ClaudePRComparison({ teamId, startDate, endDate }: ClaudePRComparisonProps) {
  const { data, isLoading } = useClaudePRComparison(teamId, startDate, endDate)

  if (isLoading) {
    return <CardSkeleton />
  }

  if (!data || data.total_prs_analyzed === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Claude PR Comparison</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <div className="rounded-lg bg-muted p-3">
            <GitPullRequest className="h-8 w-8 text-muted-foreground" />
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            No PR data available. Connect your GitHub repository to enable PR analysis.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Claude PR Comparison</CardTitle>
        <p className="text-xs text-muted-foreground">
          {data.total_prs_analyzed} PRs analyzed
        </p>
      </CardHeader>
      <CardContent>
        {/* Summary row */}
        <div className="mb-6 grid grid-cols-2 gap-6">
          <ColumnGroup title="Claude-Assisted" metrics={data.claude_assisted} />
          <ColumnGroup title="Other PRs" metrics={data.non_claude} />
        </div>

        {/* Metric rows */}
        <div className="rounded-lg border border-border">
          <div className="grid grid-cols-4 gap-4 border-b border-border bg-muted/50 px-4 py-2 text-xs font-medium text-muted-foreground">
            <div>Metric</div>
            <div>Claude</div>
            <div>Other</div>
            <div>Delta</div>
          </div>
          <div className="px-4">
            <MetricRow
              label="Merge Rate"
              claudeValue={data.claude_assisted.merge_rate != null ? data.claude_assisted.merge_rate * 100 : null}
              otherValue={data.non_claude.merge_rate != null ? data.non_claude.merge_rate * 100 : null}
              delta={data.delta_merge_rate != null ? data.delta_merge_rate * 100 : null}
              suffix="%"
            />
            <MetricRow
              label="Review Comments"
              claudeValue={data.claude_assisted.avg_review_comments}
              otherValue={data.non_claude.avg_review_comments}
              delta={data.delta_review_comments}
              invertDelta
            />
            <MetricRow
              label="Time to Merge"
              claudeValue={data.claude_assisted.avg_time_to_merge_hours}
              otherValue={data.non_claude.avg_time_to_merge_hours}
              delta={data.delta_merge_time_hours}
              suffix="h"
              invertDelta
            />
            <MetricRow
              label="Avg Additions"
              claudeValue={data.claude_assisted.avg_additions}
              otherValue={data.non_claude.avg_additions}
            />
            <MetricRow
              label="Avg Deletions"
              claudeValue={data.claude_assisted.avg_deletions}
              otherValue={data.non_claude.avg_deletions}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
