import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatNumber } from "@/lib/utils"
import { RecommendationCard } from "@/components/dashboard/recommendation-card"
import { InterventionFormModal } from "@/components/interventions/intervention-form-modal"
import type { ProjectEnablementSummary, Recommendation } from "@/types/api"

interface ProjectEnablementCardProps {
  enablement: ProjectEnablementSummary
  teamId: string | null
  projectName: string
  startDate?: string
  endDate?: string
}

function renderCountPills(items: Record<string, number>, emptyLabel: string) {
  const entries = Object.entries(items).sort((a, b) => b[1] - a[1])
  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyLabel}</p>
  }
  return (
    <div className="flex flex-wrap gap-2">
      {entries.map(([label, count]) => (
        <Badge key={label} variant="secondary" className="gap-1">
          <span className="capitalize">{label.replaceAll("_", " ")}</span>
          <span className="text-muted-foreground">{formatNumber(count)}</span>
        </Badge>
      ))}
    </div>
  )
}

function renderTopList(items: string[], emptyLabel: string) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyLabel}</p>
  }
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <Badge key={item} variant="outline">
          {item}
        </Badge>
      ))}
    </div>
  )
}

function renderPlaybookTemplates(
  templates: ProjectEnablementSummary["playbook_templates"],
) {
  if (templates.length === 0) {
    return <p className="text-sm text-muted-foreground">No project playbook templates yet.</p>
  }

  return (
    <div className="space-y-3">
      {templates.map((template) => (
        <div
          key={`${template.template_type}-${template.title}`}
          className="rounded-xl border border-border/60 bg-muted/20 p-4"
        >
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{template.template_type.replaceAll("_", " ")}</Badge>
            {template.recommended_workflow && (
              <Badge variant="secondary">{template.recommended_workflow}</Badge>
            )}
          </div>
          <p className="mt-3 text-sm font-semibold">{template.title}</p>
          <p className="mt-1 text-sm text-muted-foreground">{template.summary}</p>

          {template.initial_steps.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                First Steps
              </p>
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                {template.initial_steps.map((step) => (
                  <li key={step}>- {step}</li>
                ))}
              </ul>
            </div>
          )}

          {template.guardrails.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Guardrails
              </p>
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                {template.guardrails.map((guardrail) => (
                  <li key={guardrail}>- {guardrail}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export function ProjectEnablementCard({
  enablement,
  teamId,
  projectName,
  startDate,
  endDate,
}: ProjectEnablementCardProps) {
  const [selectedRecommendation, setSelectedRecommendation] = useState<Recommendation | null>(null)

  return (
    <>
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="text-sm font-medium">Enablement</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Linked Repositories</p>
              <p className="mt-1 font-display text-2xl">{formatNumber(enablement.linked_repository_count)}</p>
            </div>
            <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Top Tools</p>
              <p className="mt-1 font-display text-2xl">{formatNumber(enablement.top_tools.length)}</p>
            </div>
          </div>

          <section className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Agent Mix
            </h3>
            {renderCountPills(enablement.agent_type_counts, "No agent mix yet.")}
          </section>

          <section className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Session Types
            </h3>
            {renderCountPills(enablement.session_type_counts, "No session type telemetry yet.")}
          </section>

          <section className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Permission Modes
            </h3>
            {renderCountPills(enablement.permission_mode_counts, "No permission modes recorded yet.")}
          </section>

          <section className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Top Tools
            </h3>
            {renderTopList(enablement.top_tools, "No tool telemetry yet.")}
          </section>

          <section className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Top Models
            </h3>
            {renderTopList(enablement.top_models, "No model usage telemetry yet.")}
          </section>

          <section className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Playbook Templates
            </h3>
            {renderPlaybookTemplates(enablement.playbook_templates)}
          </section>

          <section className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Enablement Recommendations
            </h3>
            {enablement.recommendations.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No project-specific enablement recommendations yet.
              </p>
            ) : (
              <div className="space-y-3">
                {enablement.recommendations.map((recommendation) => (
                  <RecommendationCard
                    key={`${recommendation.category}-${recommendation.title}`}
                    rec={recommendation}
                    onCreateIntervention={() => setSelectedRecommendation(recommendation)}
                  />
                ))}
              </div>
            )}
          </section>
        </CardContent>
      </Card>

      <InterventionFormModal
        open={selectedRecommendation != null}
        onClose={() => setSelectedRecommendation(null)}
        recommendation={selectedRecommendation}
        teamId={teamId}
        projectName={projectName}
        startDate={startDate}
        endDate={endDate}
      />
    </>
  )
}
