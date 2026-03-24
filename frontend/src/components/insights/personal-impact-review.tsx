import { ArrowRight, BadgeCheck, Compass, DollarSign, Sparkles, Target, TrendingUp } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost, formatDuration, formatLabel, formatPercent } from "@/lib/utils"
import type { EngineerProfileResponse } from "@/types/api"

interface PersonalImpactReviewProps {
  profile: EngineerProfileResponse
}

export function PersonalImpactReview({ profile }: PersonalImpactReviewProps) {
  const review = profile.impact_review

  if (!review) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Personal Impact Review</CardTitle>
          <CardDescription>No impact review is available yet.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const metrics = [
    {
      label: "Sessions",
      value: profile.overview.total_sessions.toLocaleString(),
      icon: Sparkles,
    },
    {
      label: "Success Rate",
      value: formatPercent(profile.overview.success_rate),
      icon: Target,
    },
    {
      label: "Effectiveness",
      value: profile.effectiveness?.score != null ? profile.effectiveness.score.toFixed(1) : "-",
      icon: BadgeCheck,
    },
    {
      label: "Leverage",
      value: profile.leverage_score != null ? profile.leverage_score.toFixed(1) : "-",
      icon: TrendingUp,
    },
    {
      label: "Est. Cost",
      value: profile.overview.estimated_cost != null ? formatCost(profile.overview.estimated_cost) : "-",
      icon: DollarSign,
    },
    {
      label: "Avg Duration",
      value: formatDuration(profile.overview.avg_session_duration),
      icon: Compass,
    },
  ]

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden">
        <div className="h-1 bg-gradient-to-r from-primary via-primary/35 to-transparent" />
        <CardHeader className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-2">
              <CardTitle className="font-display text-2xl tracking-tight">
                {review.headline}
              </CardTitle>
              <CardDescription className="max-w-3xl text-sm leading-relaxed">
                {review.summary}
              </CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              {review.workflow_maturity_label ? (
                <Badge variant="secondary">{formatLabel(review.workflow_maturity_label)}</Badge>
              ) : null}
              {review.trajectory_signal ? (
                <Badge variant="outline">{formatLabel(review.trajectory_signal)}</Badge>
              ) : null}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {metrics.map((metric) => (
              <div
                key={metric.label}
                className="rounded-2xl border border-border/60 bg-muted/20 p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                    {metric.label}
                  </p>
                  <metric.icon className="h-4 w-4 text-primary/70" />
                </div>
                <p className="mt-3 font-display text-3xl tracking-tight">{metric.value}</p>
              </div>
            ))}
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
            <Card className="border-border/60 bg-background/60 shadow-none hover:border-border/70 hover:shadow-none">
              <CardHeader>
                <CardTitle className="text-base">Top Workflows</CardTitle>
                <CardDescription>
                  The workflow archetypes showing up most often in this engineer&apos;s recent work.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {review.top_workflows.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No workflow fingerprints are available yet.
                  </p>
                ) : (
                  <div className="grid gap-3 md:grid-cols-3">
                    {review.top_workflows.map((workflow) => (
                      <div
                        key={workflow.archetype}
                        className="rounded-2xl border border-border/60 bg-muted/20 p-4"
                      >
                        <p className="text-sm font-semibold">{formatLabel(workflow.archetype)}</p>
                        <div className="mt-3 space-y-2 text-sm text-muted-foreground">
                          <div className="flex items-center justify-between gap-3">
                            <span>Sessions</span>
                            <span className="font-medium text-foreground">{workflow.session_count}</span>
                          </div>
                          <div className="flex items-center justify-between gap-3">
                            <span>Share</span>
                            <span className="font-medium text-foreground">
                              {formatPercent(workflow.share_of_sessions)}
                            </span>
                          </div>
                          <div className="flex items-center justify-between gap-3">
                            <span>Success</span>
                            <span className="font-medium text-foreground">
                              {formatPercent(workflow.success_rate)}
                            </span>
                          </div>
                          <div className="flex items-center justify-between gap-3">
                            <span>Duration</span>
                            <span className="font-medium text-foreground">
                              {formatDuration(workflow.avg_duration_seconds)}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-border/60 bg-background/60 shadow-none hover:border-border/70 hover:shadow-none">
              <CardHeader>
                <CardTitle className="text-base">Recommended Next Move</CardTitle>
                <CardDescription>
                  The clearest next action pulled from the strongest recommendation signal available.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {review.next_step_title ? (
                  <div className="rounded-2xl border border-primary/15 bg-primary/[0.05] p-4">
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 rounded-full bg-primary/10 p-2 text-primary">
                        <ArrowRight className="h-4 w-4" />
                      </div>
                      <div className="space-y-1">
                        <p className="font-medium">{review.next_step_title}</p>
                        <p className="text-sm leading-relaxed text-muted-foreground">
                          {review.next_step_description}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No recommendation is available yet. Keep building session history to sharpen the next-step guidance.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <Card className="border-border/60 bg-background/60 shadow-none hover:border-border/70 hover:shadow-none">
              <CardHeader>
                <CardTitle className="text-base">What&apos;s Working</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {review.strengths.map((item, index) => (
                    <li key={`${item}-${index}`} className="flex gap-3 text-sm leading-relaxed">
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-emerald-500" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card className="border-border/60 bg-background/60 shadow-none hover:border-border/70 hover:shadow-none">
              <CardHeader>
                <CardTitle className="text-base">Focus Next</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {review.focus_areas.map((item, index) => (
                    <li key={`${item}-${index}`} className="flex gap-3 text-sm leading-relaxed">
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-amber-500" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
