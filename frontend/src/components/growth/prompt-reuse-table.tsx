import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCost, formatLabel, formatPercent } from "@/lib/utils"
import type { PromptReusePattern } from "@/types/api"

interface PromptReuseTableProps {
  patterns: PromptReusePattern[]
}

export function PromptReuseTable({ patterns }: PromptReuseTableProps) {
  if (patterns.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Prompt Reuse Patterns</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No reusable prompt patterns detected yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Prompt Reuse Patterns</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Prompt Pattern</th>
                <th className="pb-2 text-right font-medium">Adoption</th>
                <th className="pb-2 text-right font-medium">Success</th>
                <th className="pb-2 text-right font-medium">Cost / Success</th>
                <th className="pb-2 font-medium">Workflow Fit</th>
                <th className="pb-2 font-medium">Projects</th>
              </tr>
            </thead>
            <tbody>
              {patterns.map((pattern) => (
                <tr key={pattern.prompt_pattern_id} className="border-b border-border/40">
                  <td className="py-2">
                    <div className="space-y-1">
                      <p className="font-medium">{pattern.prompt_preview}</p>
                      <p className="font-mono text-[10px] text-muted-foreground">
                        {pattern.normalized_prompt}
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <div>
                      <p>{formatPercent(pattern.adoption_rate)}</p>
                      <p className="text-xs text-muted-foreground">
                        {pattern.engineer_count} engineers · {pattern.session_count} sessions
                      </p>
                    </div>
                  </td>
                  <td className="py-2 text-right">{formatPercent(pattern.success_rate)}</td>
                  <td className="py-2 text-right">
                    {pattern.cost_per_successful_outcome != null
                      ? formatCost(pattern.cost_per_successful_outcome)
                      : pattern.avg_session_cost != null
                        ? formatCost(pattern.avg_session_cost)
                        : "-"}
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      {pattern.workflow_archetypes.length === 0 ? (
                        <span className="text-xs text-muted-foreground">No workflow signal yet</span>
                      ) : (
                        pattern.workflow_archetypes.map((workflow) => (
                          <Badge key={`${pattern.prompt_pattern_id}:${workflow}`} variant="outline">
                            {formatLabel(workflow)}
                          </Badge>
                        ))
                      )}
                    </div>
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      {pattern.top_projects.length === 0 ? (
                        <span className="text-xs text-muted-foreground">No project signal yet</span>
                      ) : (
                        pattern.top_projects.map((project) => (
                          <Badge key={`${pattern.prompt_pattern_id}:${project}`} variant="outline">
                            {project}
                          </Badge>
                        ))
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
