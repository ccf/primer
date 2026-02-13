import { format, parseISO } from "date-fns"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import type { SessionDetailResponse } from "@/types/api"
import { formatDuration, formatTokens } from "@/lib/utils"

interface SessionDetailPanelProps {
  session: SessionDetailResponse
}

export function SessionDetailPanel({ session }: SessionDetailPanelProps) {
  const { facets } = session

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold">
          {session.project_name || session.project_path?.split("/").pop() || "Session"}
        </h1>
        <p className="text-sm text-muted-foreground">
          {session.started_at ? format(parseISO(session.started_at), "PPpp") : "Unknown date"}
          {session.git_branch && ` · ${session.git_branch}`}
        </p>
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
              {facets.claude_helpfulness && (
                <div>
                  <p className="text-xs text-muted-foreground">Helpfulness</p>
                  <p className="text-sm font-medium">{facets.claude_helpfulness}</p>
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

      {/* Tool usages */}
      {session.tool_usages.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Tool Usage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="pb-2 text-left font-medium text-muted-foreground">Tool</th>
                    <th className="pb-2 text-right font-medium text-muted-foreground">Calls</th>
                  </tr>
                </thead>
                <tbody>
                  {session.tool_usages
                    .sort((a, b) => b.call_count - a.call_count)
                    .map((t) => (
                      <tr key={t.tool_name} className="border-b border-border last:border-0">
                        <td className="py-2">{t.tool_name}</td>
                        <td className="py-2 text-right">{t.call_count}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Model usages */}
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
                  </tr>
                </thead>
                <tbody>
                  {session.model_usages.map((m) => (
                    <tr key={m.model_name} className="border-b border-border last:border-0">
                      <td className="py-2">{m.model_name}</td>
                      <td className="py-2 text-right">{formatTokens(m.input_tokens)}</td>
                      <td className="py-2 text-right">{formatTokens(m.output_tokens)}</td>
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
