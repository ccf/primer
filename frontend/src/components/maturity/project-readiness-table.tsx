import { Check, X } from "lucide-react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import type { ProjectReadinessEntry } from "@/types/api"

interface ProjectReadinessTableProps {
  data: ProjectReadinessEntry[]
}

function CheckIcon({ value }: { value: boolean }) {
  return value ? (
    <Check className="h-4 w-4 text-emerald-500" />
  ) : (
    <X className="h-4 w-4 text-muted-foreground/40" />
  )
}

export function ProjectReadinessTable({ data }: ProjectReadinessTableProps) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium">Project AI Readiness</h3>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No readiness data yet. Run a GitHub sync to check repositories.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-medium">Project AI Readiness</h3>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Repository</th>
                <th className="pb-2 text-center font-medium">CLAUDE.md</th>
                <th className="pb-2 text-center font-medium">AGENTS.md</th>
                <th className="pb-2 text-center font-medium">.claude/</th>
                <th className="pb-2 text-right font-medium">Score</th>
                <th className="pb-2 text-right font-medium">Sessions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((entry) => (
                <tr key={entry.repository} className="border-b border-border/40">
                  <td className="py-2 font-mono text-xs">{entry.repository}</td>
                  <td className="py-2 text-center">
                    <div className="flex justify-center">
                      <CheckIcon value={entry.has_claude_md} />
                    </div>
                  </td>
                  <td className="py-2 text-center">
                    <div className="flex justify-center">
                      <CheckIcon value={entry.has_agents_md} />
                    </div>
                  </td>
                  <td className="py-2 text-center">
                    <div className="flex justify-center">
                      <CheckIcon value={entry.has_claude_dir} />
                    </div>
                  </td>
                  <td className="py-2 text-right font-medium">{entry.ai_readiness_score}</td>
                  <td className="py-2 text-right">{entry.session_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
