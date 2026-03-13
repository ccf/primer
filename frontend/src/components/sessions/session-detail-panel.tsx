import { format, parseISO } from "date-fns"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { SessionToolChart } from "@/components/sessions/session-tool-chart"
import { SessionCostChart } from "@/components/sessions/session-cost-chart"
import { RECOVERY_STRATEGY_LABELS } from "@/lib/recovery"
import type { SessionDetailResponse } from "@/types/api"
import { formatDuration, formatTokens } from "@/lib/utils"

interface SessionDetailPanelProps {
  session: SessionDetailResponse
}

const OUTCOME_BADGE: Record<string, { variant: "success" | "destructive" | "warning" | "secondary"; label: string }> = {
  success: { variant: "success", label: "Success" },
  failure: { variant: "destructive", label: "Failure" },
  partial: { variant: "warning", label: "Partial" },
  abandoned: { variant: "secondary", label: "Abandoned" },
}

const EXECUTION_EVIDENCE_LABELS = {
  test: "Tests",
  lint: "Lint",
  build: "Build",
  verification: "Verification",
} as const

const RECOVERY_RESULT_BADGE: Record<
  string,
  { variant: "success" | "destructive" | "warning"; label: string }
> = {
  recovered: { variant: "success", label: "Recovered" },
  abandoned: { variant: "destructive", label: "Abandoned" },
  unresolved: { variant: "warning", label: "Unresolved" },
}

const EXECUTION_STATUS_BADGE: Record<
  string,
  "success" | "destructive" | "secondary"
> = {
  passed: "success",
  failed: "destructive",
  unknown: "secondary",
}

const WORKFLOW_ARCHETYPE_LABELS: Record<string, string> = {
  debugging: "Debugging",
  feature_delivery: "Feature Delivery",
  refactor: "Refactor",
  migration: "Migration",
  docs: "Docs",
  investigation: "Investigation",
}

export function SessionDetailPanel({ session }: SessionDetailPanelProps) {
  const { facets } = session
  const changeShape = session.change_shape
  const recoveryPath = session.recovery_path
  const workflowProfile = session.workflow_profile
  const visibleNamedFiles = changeShape?.named_touched_files?.slice(0, 8) ?? []
  const hiddenChangeShapeFiles = changeShape
    ? changeShape.files_touched_count - visibleNamedFiles.length
    : 0
  const outcomeBadge = facets?.outcome ? OUTCOME_BADGE[facets.outcome] : null
  const recoveryBadge = recoveryPath ? RECOVERY_RESULT_BADGE[recoveryPath.recovery_result] : null
  const executionEvidenceCounts = session.execution_evidence.reduce<Record<string, number>>(
    (acc, evidence) => {
      acc[evidence.evidence_type] = (acc[evidence.evidence_type] || 0) + 1
      return acc
    },
    {},
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold">
            {session.project_name || session.project_path?.split("/").pop() || "Session"}
          </h1>
          <p className="text-sm text-muted-foreground">
            {session.started_at ? format(parseISO(session.started_at), "PPpp") : "Unknown date"}
            {session.git_branch && ` · ${session.git_branch}`}
          </p>
        </div>
        {outcomeBadge && (
          <Badge variant={outcomeBadge.variant} className="text-xs">
            {outcomeBadge.label}
          </Badge>
        )}
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-6">
        {[
          { label: "Duration", value: formatDuration(session.duration_seconds) },
          { label: "Messages", value: session.message_count },
          { label: "Tool Calls", value: session.tool_call_count },
          { label: "Input Tokens", value: formatTokens(session.input_tokens) },
          { label: "Output Tokens", value: formatTokens(session.output_tokens) },
          { label: "Model", value: session.primary_model?.replace(/^claude-/, "").split("-202")[0] || "-" },
        ].map((m) => (
          <Card key={m.label}>
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">{m.label}</p>
              <p className="mt-1 text-lg font-semibold">{m.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Session metadata */}
      {(session.end_reason || session.permission_mode || session.agent_version) && (
        <div className="flex flex-wrap gap-4 text-sm">
          {session.agent_version && (
            <div>
              <span className="text-muted-foreground">Agent Version: </span>
              <span className="font-medium">{session.agent_version}</span>
            </div>
          )}
          {session.permission_mode && (
            <div>
              <span className="text-muted-foreground">Permission Mode: </span>
              <span className="font-medium">{session.permission_mode}</span>
            </div>
          )}
          {session.end_reason && (
            <div>
              <span className="text-muted-foreground">End Reason: </span>
              <span className="font-medium">{session.end_reason}</span>
            </div>
          )}
        </div>
      )}

      {/* First prompt */}
      {session.first_prompt && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">First Prompt</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm">{session.first_prompt}</p>
          </CardContent>
        </Card>
      )}

      {/* Facets */}
      {facets && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Facets</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {facets.outcome && (
                <div>
                  <p className="text-xs text-muted-foreground">Outcome</p>
                  <Badge variant={facets.outcome === "success" ? "success" : facets.outcome === "failure" ? "destructive" : "warning"}>
                    {facets.outcome}
                  </Badge>
                </div>
              )}
              {facets.session_type && (
                <div>
                  <p className="text-xs text-muted-foreground">Session Type</p>
                  <p className="text-sm font-medium">{facets.session_type}</p>
                </div>
              )}
              {facets.agent_helpfulness && (
                <div>
                  <p className="text-xs text-muted-foreground">Helpfulness</p>
                  <p className="text-sm font-medium">{facets.agent_helpfulness}</p>
                </div>
              )}
              {facets.primary_success && (
                <div>
                  <p className="text-xs text-muted-foreground">Primary Success</p>
                  <p className="text-sm font-medium">{facets.primary_success}</p>
                </div>
              )}
              {facets.underlying_goal && (
                <div className="sm:col-span-2">
                  <p className="text-xs text-muted-foreground">Goal</p>
                  <p className="text-sm">{facets.underlying_goal}</p>
                </div>
              )}
              {facets.brief_summary && (
                <div className="sm:col-span-2 lg:col-span-3">
                  <p className="text-xs text-muted-foreground">Summary</p>
                  <p className="text-sm">{facets.brief_summary}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <Separator />

      {/* Tool & Cost Charts */}
      <div className="grid gap-4 lg:grid-cols-2">
        {session.tool_usages.length > 0 && (
          <SessionToolChart data={session.tool_usages} />
        )}
        {session.model_usages.length > 0 && (
          <SessionCostChart data={session.model_usages} />
        )}
      </div>

      {/* Model usages table */}
      {session.model_usages.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Model Usage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="pb-2 text-left font-medium text-muted-foreground">Model</th>
                    <th className="pb-2 text-right font-medium text-muted-foreground">Input</th>
                    <th className="pb-2 text-right font-medium text-muted-foreground">Output</th>
                    <th className="pb-2 text-right font-medium text-muted-foreground">Cache Read</th>
                    <th className="pb-2 text-right font-medium text-muted-foreground">Cache Create</th>
                  </tr>
                </thead>
                <tbody>
                  {session.model_usages.map((m) => (
                    <tr key={m.model_name} className="border-b border-border last:border-0">
                      <td className="py-2">{m.model_name}</td>
                      <td className="py-2 text-right">{formatTokens(m.input_tokens)}</td>
                      <td className="py-2 text-right">{formatTokens(m.output_tokens)}</td>
                      <td className="py-2 text-right">{formatTokens(m.cache_read_tokens)}</td>
                      <td className="py-2 text-right">{formatTokens(m.cache_creation_tokens)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {workflowProfile && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Workflow Profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-border/70 px-3 py-2">
                <p className="text-xs text-muted-foreground">Archetype</p>
                <p className="mt-1 text-sm font-semibold">
                  {workflowProfile.archetype
                    ? WORKFLOW_ARCHETYPE_LABELS[workflowProfile.archetype]
                    : "-"}
                </p>
              </div>
              <div className="rounded-lg border border-border/70 px-3 py-2">
                <p className="text-xs text-muted-foreground">Fingerprint</p>
                <p className="mt-1 text-sm font-semibold">
                  {workflowProfile.label ?? "-"}
                </p>
              </div>
              <div className="rounded-lg border border-border/70 px-3 py-2">
                <p className="text-xs text-muted-foreground">Delegations</p>
                <p className="mt-1 text-sm font-semibold">
                  {workflowProfile.delegation_count}
                </p>
              </div>
              <div className="rounded-lg border border-border/70 px-3 py-2">
                <p className="text-xs text-muted-foreground">Verification Runs</p>
                <p className="mt-1 text-sm font-semibold">
                  {workflowProfile.verification_run_count}
                </p>
              </div>
            </div>
            {workflowProfile.steps && workflowProfile.steps.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Workflow Steps
                </p>
                <div className="flex flex-wrap gap-2">
                  {workflowProfile.steps.map((step) => (
                    <Badge key={step} variant="secondary">
                      {step.replace(/_/g, " ")}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {workflowProfile.top_tools && workflowProfile.top_tools.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Top Tools
                </p>
                <div className="flex flex-wrap gap-2">
                  {workflowProfile.top_tools.map((tool) => (
                    <Badge key={tool} variant="outline">
                      {tool}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {workflowProfile.archetype_reason && (
              <p className="text-sm text-muted-foreground">
                {workflowProfile.archetype_reason}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {changeShape && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Change Shape</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { label: "Files Touched", value: changeShape.files_touched_count },
                { label: "Diff Size", value: changeShape.diff_size },
                { label: "Lines Added", value: changeShape.lines_added },
                { label: "Lines Deleted", value: changeShape.lines_deleted },
              ].map((metric) => (
                <div
                  key={metric.label}
                  className="rounded-lg border border-border/70 px-3 py-2"
                >
                  <p className="text-xs text-muted-foreground">{metric.label}</p>
                  <p className="mt-1 text-sm font-semibold">{metric.value}</p>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">Edits {changeShape.edit_operations}</Badge>
              <Badge variant="secondary">Creates {changeShape.create_operations}</Badge>
              <Badge variant="secondary">Deletes {changeShape.delete_operations}</Badge>
              <Badge variant="secondary">Renames {changeShape.rename_operations}</Badge>
              {changeShape.churn_files_count > 0 && (
                <Badge variant="warning">Churn {changeShape.churn_files_count}</Badge>
              )}
              {changeShape.rewrite_indicator && (
                <Badge variant="warning">Rewrite Signal</Badge>
              )}
              {changeShape.revert_indicator && (
                <Badge variant="destructive">Revert Signal</Badge>
              )}
            </div>
            {changeShape.named_touched_files && changeShape.named_touched_files.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Named Files
                </p>
                <div className="flex flex-wrap gap-2">
                  {visibleNamedFiles.map((filePath) => (
                    <Badge key={filePath} variant="outline" className="max-w-full break-all">
                      {filePath}
                    </Badge>
                  ))}
                  {hiddenChangeShapeFiles > 0 && (
                    <Badge variant="outline">
                      +{hiddenChangeShapeFiles} more
                    </Badge>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {recoveryPath && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Recovery Path</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { label: "First Friction", value: recoveryPath.first_friction_ordinal ?? "-" },
                { label: "Recovery Steps", value: recoveryPath.recovery_step_count },
                { label: "Final Outcome", value: recoveryPath.final_outcome ?? "-" },
                { label: "Last Verification", value: recoveryPath.last_verification_status ?? "-" },
              ].map((metric) => (
                <div
                  key={metric.label}
                  className="rounded-lg border border-border/70 px-3 py-2"
                >
                  <p className="text-xs text-muted-foreground">{metric.label}</p>
                  <p className="mt-1 text-sm font-semibold">{metric.value}</p>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              {recoveryBadge && (
                <Badge variant={recoveryBadge.variant}>{recoveryBadge.label}</Badge>
              )}
              {(recoveryPath.recovery_strategies ?? []).map((strategy) => (
                <Badge key={strategy} variant="secondary">
                  {RECOVERY_STRATEGY_LABELS[strategy]}
                </Badge>
              ))}
            </div>
            {recoveryPath.sample_recovery_commands &&
              recoveryPath.sample_recovery_commands.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Sample Recovery Commands
                  </p>
                  <div className="space-y-2">
                    {recoveryPath.sample_recovery_commands.map((command) => (
                      <p
                        key={command}
                        className="break-all rounded bg-muted px-2 py-1 font-mono text-xs"
                      >
                        {command}
                      </p>
                    ))}
                  </div>
                </div>
              )}
          </CardContent>
        </Card>
      )}

      {session.execution_evidence.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Execution Evidence</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {Object.entries(EXECUTION_EVIDENCE_LABELS).map(([key, label]) => {
                const count = executionEvidenceCounts[key] || 0
                if (!count) return null
                return (
                  <Badge key={key} variant="secondary" className="gap-1">
                    <span>{label}</span>
                    <span>{count}</span>
                  </Badge>
                )
              })}
            </div>
            <div className="space-y-3">
              {session.execution_evidence.map((evidence, index) => (
                <div
                  key={`${evidence.ordinal}-${evidence.evidence_type}-${index}`}
                  className="rounded-lg border border-border/70 p-3"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">
                      {EXECUTION_EVIDENCE_LABELS[evidence.evidence_type]}
                    </Badge>
                    <Badge variant={EXECUTION_STATUS_BADGE[evidence.status]}>
                      {evidence.status}
                    </Badge>
                    {evidence.tool_name && (
                      <span className="text-xs text-muted-foreground">{evidence.tool_name}</span>
                    )}
                  </div>
                  {evidence.command && (
                    <p className="mt-2 break-all rounded bg-muted px-2 py-1 font-mono text-xs">
                      {evidence.command}
                    </p>
                  )}
                  {evidence.output_preview && (
                    <p className="mt-2 whitespace-pre-wrap text-xs text-muted-foreground">
                      {evidence.output_preview}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
