import { useState, type FormEvent } from "react"
import { X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useCreateIntervention } from "@/hooks/use-api-mutations"
import { useEngineers } from "@/hooks/use-api-queries"
import type { Recommendation } from "@/types/api"

interface InterventionFormModalProps {
  open: boolean
  onClose: () => void
  recommendation?: Recommendation | null
  teamId: string | null
  engineerId?: string | null
  projectName?: string | null
  startDate?: string
  endDate?: string
  defaultOwnerEngineerId?: string | null
}

interface FormState {
  title: string
  description: string
  category: string
  severity: string
  dueDate: string
  ownerEngineerId: string
  trackExperiment: boolean
  experimentType: string
  experimentHypothesis: string
  experimentTargetCohort: string
  experimentSuccessCriteria: string
}

function buildInitialState(
  recommendation: Recommendation | null | undefined,
  defaultOwnerEngineerId?: string | null,
): FormState {
  return {
    title: recommendation?.title ?? "",
    description: recommendation?.description ?? "",
    category: recommendation?.category ?? "workflow",
    severity: recommendation?.severity ?? "info",
    dueDate: "",
    ownerEngineerId: defaultOwnerEngineerId ?? "",
    trackExperiment: false,
    experimentType: "training_rollout",
    experimentHypothesis: "",
    experimentTargetCohort: "",
    experimentSuccessCriteria: "",
  }
}

export function InterventionFormModal({
  open,
  onClose,
  recommendation,
  teamId,
  engineerId,
  projectName,
  startDate,
  endDate,
  defaultOwnerEngineerId,
}: InterventionFormModalProps) {
  if (!open) return null

  const formKey = [
    recommendation?.title ?? "manual",
    recommendation?.description ?? "",
    defaultOwnerEngineerId ?? "",
    teamId ?? "",
    engineerId ?? "",
    projectName ?? "",
  ].join("::")

  return (
    <InterventionFormBody
      key={formKey}
      onClose={onClose}
      recommendation={recommendation}
      teamId={teamId}
      engineerId={engineerId}
      projectName={projectName}
      startDate={startDate}
      endDate={endDate}
      defaultOwnerEngineerId={defaultOwnerEngineerId}
    />
  )
}

function InterventionFormBody({
  onClose,
  recommendation,
  teamId,
  engineerId,
  projectName,
  startDate,
  endDate,
  defaultOwnerEngineerId,
}: Omit<InterventionFormModalProps, "open">) {
  const createIntervention = useCreateIntervention()
  const { data: engineers } = useEngineers()
  const [form, setForm] = useState<FormState>(() =>
    buildInitialState(recommendation, defaultOwnerEngineerId),
  )

  const visibleEngineers = (engineers ?? []).filter((engineer) =>
    teamId ? engineer.team_id === teamId : true,
  )

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    createIntervention.mutate(
      {
        title: form.title,
        description: form.description,
        category: form.category,
        severity: form.severity,
        team_id: teamId,
        engineer_id: engineerId,
        owner_engineer_id: form.ownerEngineerId || undefined,
        project_name: projectName,
        due_date: form.dueDate || undefined,
        source_type: recommendation ? "recommendation" : "manual",
        source_title: recommendation?.title,
        evidence: recommendation?.evidence ?? null,
        experiment: form.trackExperiment
          ? {
              experiment_type: form.experimentType,
              hypothesis: form.experimentHypothesis,
              target_cohort: form.experimentTargetCohort || null,
              success_criteria: form.experimentSuccessCriteria || null,
            }
          : null,
        baseline_start_at: startDate,
        baseline_end_at: endDate,
      },
      { onSuccess: () => onClose() },
    )
  }

  const scopeLabel = projectName
    ? `Project: ${projectName}`
    : engineerId
      ? "Engineer-scoped"
      : teamId
        ? "Team-scoped"
        : "Organization-scoped"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative z-10 w-full max-w-xl rounded-2xl border border-border bg-card p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">Create Intervention</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Turn a recommendation into a tracked action with a measurable baseline.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label="Close intervention form"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-3 inline-flex rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
          {scopeLabel}
        </div>

        <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="text-sm font-medium">Title</label>
            <input
              value={form.title}
              onChange={(event) => updateField("title", event.target.value)}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none ring-0 transition-colors focus:border-primary"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <textarea
              value={form.description}
              onChange={(event) => updateField("description", event.target.value)}
              className="min-h-28 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none ring-0 transition-colors focus:border-primary"
              required
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Category</label>
              <input
                value={form.category}
                onChange={(event) => updateField("category", event.target.value)}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none ring-0 transition-colors focus:border-primary"
                required
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Severity</label>
              <select
                value={form.severity}
                onChange={(event) => updateField("severity", event.target.value)}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none ring-0 transition-colors focus:border-primary"
              >
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="critical">Critical</option>
              </select>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Owner</label>
              <select
                value={form.ownerEngineerId}
                onChange={(event) => updateField("ownerEngineerId", event.target.value)}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none ring-0 transition-colors focus:border-primary"
              >
                <option value="">Unassigned</option>
                {visibleEngineers.map((engineer) => (
                  <option key={engineer.id} value={engineer.id}>
                    {engineer.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Due Date</label>
              <input
                type="date"
                value={form.dueDate}
                onChange={(event) => updateField("dueDate", event.target.value)}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none ring-0 transition-colors focus:border-primary"
              />
            </div>
          </div>

          <div className="space-y-4 rounded-xl border border-border/60 bg-muted/20 p-4">
            <label className="flex items-center gap-2 text-sm font-medium">
              <input
                type="checkbox"
                checked={form.trackExperiment}
                onChange={(event) => updateField("trackExperiment", event.target.checked)}
              />
              Track this as an experiment
            </label>

            {form.trackExperiment && (
              <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Experiment Type</label>
                    <select
                      value={form.experimentType}
                      onChange={(event) => updateField("experimentType", event.target.value)}
                      className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none ring-0 transition-colors focus:border-primary"
                    >
                      <option value="training_rollout">Training Rollout</option>
                      <option value="tool_change">Tool Change</option>
                      <option value="enablement_playbook">Enablement Playbook</option>
                      <option value="prompt_standardization">Prompt Standardization</option>
                      <option value="model_rollout">Model Rollout</option>
                      <option value="workflow_playbook">Workflow Playbook</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Target Cohort</label>
                    <input
                      value={form.experimentTargetCohort}
                      onChange={(event) =>
                        updateField("experimentTargetCohort", event.target.value)
                      }
                      placeholder="New hires, Team A, API engineers..."
                      className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none ring-0 transition-colors focus:border-primary"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Hypothesis</label>
                  <textarea
                    value={form.experimentHypothesis}
                    onChange={(event) =>
                      updateField("experimentHypothesis", event.target.value)
                    }
                    className="min-h-20 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none ring-0 transition-colors focus:border-primary"
                    placeholder="What change do you expect and why?"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Success Criteria</label>
                  <textarea
                    value={form.experimentSuccessCriteria}
                    onChange={(event) =>
                      updateField("experimentSuccessCriteria", event.target.value)
                    }
                    className="min-h-20 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none ring-0 transition-colors focus:border-primary"
                    placeholder="What metric change will count as success?"
                  />
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={createIntervention.isPending}>
              {createIntervention.isPending ? "Creating..." : "Create intervention"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
