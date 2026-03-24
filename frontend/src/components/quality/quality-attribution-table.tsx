import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { formatLabel, formatMetric } from "@/lib/utils"
import type { QualityAttributionRow } from "@/types/api"

interface Props {
  rows: QualityAttributionRow[]
  framed?: boolean
}

const DIMENSION_LABELS: Record<string, string> = {
  session_type: "Session Type",
  agent_type: "Agent Type",
  permission_mode: "Permission Mode",
  tool_breadth: "Tool Breadth",
  workflow_archetype: "Workflow Archetype",
  workflow_fingerprint: "Workflow Fingerprint",
}

function formatPercent(value: number | null): string {
  return value == null ? "-" : `${(value * 100).toFixed(0)}%`
}

export function QualityAttributionTable({ rows, framed = true }: Props) {
  if (rows.length === 0) {
    const emptyBody = (
      <>
        {framed ? (
          <CardHeader>
            <CardTitle>Quality Attribution</CardTitle>
            <CardDescription>No attributed PR outcomes yet.</CardDescription>
          </CardHeader>
        ) : null}
        <CardContent className={framed ? undefined : "p-0"}>
          {!framed ? (
            <p className="text-sm text-muted-foreground">No attributed PR outcomes yet.</p>
          ) : null}
        </CardContent>
      </>
    )

    return framed ? (
      <Card>
        {emptyBody}
      </Card>
    ) : (
      emptyBody
    )
  }

  const grouped = rows.reduce<Record<string, QualityAttributionRow[]>>((acc, row) => {
    acc[row.dimension] ??= []
    acc[row.dimension].push(row)
    return acc
  }, {})

  const content = (
    <>
      {framed ? (
      <CardHeader>
        <CardTitle>Quality Attribution</CardTitle>
        <CardDescription>
          Group PR outcomes by workflow and behavior so strong patterns stand out faster.
        </CardDescription>
      </CardHeader>
      ) : null}
      <CardContent className={framed ? "space-y-5" : "space-y-5 p-0"}>
      {Object.entries(grouped).map(([dimension, items]) => (
        <section key={dimension} className="space-y-3 rounded-2xl border border-border/60 bg-muted/20 p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-foreground">
            {DIMENSION_LABELS[dimension] ?? formatLabel(dimension)}
            </h3>
            <span className="text-xs text-muted-foreground">
              {items.length} behavior{items.length === 1 ? "" : "s"}
            </span>
          </div>
          <div className="overflow-x-auto rounded-xl border border-border/60 bg-background">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50 text-left text-xs font-medium text-muted-foreground">
                  <th className="px-3 py-2">Behavior</th>
                  <th className="px-3 py-2">Sessions</th>
                  <th className="px-3 py-2">PRs</th>
                  <th className="px-3 py-2">Merge Rate</th>
                  <th className="px-3 py-2">Reviews / PR</th>
                  <th className="px-3 py-2">Findings / PR</th>
                  <th className="px-3 py-2">High Sev / PR</th>
                  <th className="px-3 py-2">Fix Rate</th>
                  <th className="px-3 py-2">Merge Time (h)</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr
                    key={`${row.dimension}-${row.label}`}
                    className="border-b border-border/40 last:border-0"
                  >
                    <td className="px-3 py-2 font-medium">{formatLabel(row.label)}</td>
                    <td className="px-3 py-2">{row.linked_sessions}</td>
                    <td className="px-3 py-2">{row.linked_prs}</td>
                    <td className="px-3 py-2">{formatPercent(row.merge_rate)}</td>
                    <td className="px-3 py-2">
                      {formatMetric(row.avg_review_comments_per_pr)}
                    </td>
                    <td className="px-3 py-2">{formatMetric(row.avg_findings_per_pr)}</td>
                    <td className="px-3 py-2">
                      {formatMetric(row.high_severity_findings_per_pr)}
                    </td>
                    <td className="px-3 py-2">{formatPercent(row.findings_fix_rate)}</td>
                    <td className="px-3 py-2">
                      {formatMetric(row.avg_time_to_merge_hours)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
      </CardContent>
    </>
  )

  return framed ? (
    <Card>
      {content}
    </Card>
  ) : (
    content
  )
}
