import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatPercent } from "@/lib/utils"
import type { RecoveryOverview, RecoveryPattern } from "@/types/api"

interface RecoveryPatternListProps {
  overview: RecoveryOverview | null
  patterns: RecoveryPattern[]
}

const STRATEGY_LABELS: Record<RecoveryPattern["strategy"], string> = {
  inspect_context: "Inspect Context",
  edit_fix: "Edit Fix",
  revert_or_reset: "Revert or Reset",
  rerun_verification: "Rerun Verification",
  delegate_or_parallelize: "Delegate or Parallelize",
}

export function RecoveryPatternList({ overview, patterns }: RecoveryPatternListProps) {
  if (!overview || overview.sessions_with_recovery_paths === 0) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Recovery Paths</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[
            { label: "Recovered", value: overview.recovered_sessions },
            { label: "Abandoned", value: overview.abandoned_sessions },
            { label: "Recovery Rate", value: formatPercent(overview.recovery_rate) },
            { label: "Avg Steps", value: overview.avg_recovery_steps ?? "-" },
          ].map((item) => (
            <div
              key={item.label}
              className="rounded-xl border border-border/60 bg-background px-3 py-2"
            >
              <p className="text-xs text-muted-foreground">{item.label}</p>
              <p className="mt-1 text-sm font-semibold">{item.value}</p>
            </div>
          ))}
        </div>

        {patterns.length > 0 && (
          <div className="space-y-3">
            {patterns.map((pattern) => (
              <div
                key={pattern.strategy}
                className="rounded-xl border border-border/60 bg-background p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <p className="font-medium">{STRATEGY_LABELS[pattern.strategy]}</p>
                    <p className="text-sm text-muted-foreground">
                      {pattern.session_count} sessions • {pattern.recovered_sessions} recovered
                    </p>
                  </div>
                  <div className="text-right text-sm text-muted-foreground">
                    <p>Recovery {formatPercent(pattern.recovery_rate)}</p>
                    <p>Avg steps {pattern.avg_recovery_steps ?? "-"}</p>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  {pattern.abandoned_sessions > 0 && (
                    <Badge variant="destructive">Abandoned {pattern.abandoned_sessions}</Badge>
                  )}
                  {pattern.unresolved_sessions > 0 && (
                    <Badge variant="warning">Unresolved {pattern.unresolved_sessions}</Badge>
                  )}
                </div>

                {pattern.sample_commands.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Sample Commands
                    </p>
                    <div className="space-y-2">
                      {pattern.sample_commands.map((command) => (
                        <p
                          key={command}
                          className="break-all rounded-lg bg-muted/40 px-3 py-2 font-mono text-xs text-muted-foreground"
                        >
                          {command}
                        </p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
