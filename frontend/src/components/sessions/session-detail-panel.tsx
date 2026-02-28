import { format, parseISO } from "date-fns"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { SessionToolChart } from "@/components/sessions/session-tool-chart"
import { SessionCostChart } from "@/components/sessions/session-cost-chart"
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

export function SessionDetailPanel({ session }: SessionDetailPanelProps) {
  const { facets } = session
  const outcomeBadge = facets?.outcome ? OUTCOME_BADGE[facets.outcome] : null

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
    </div>
  )
}
