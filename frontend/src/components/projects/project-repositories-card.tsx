import { Check, X } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatPercent } from "@/lib/utils"
import type { ProjectRepositorySummary } from "@/types/api"

interface ProjectRepositoriesCardProps {
  repositories: ProjectRepositorySummary[]
}

function StatusIcon({ value }: { value: boolean | null }) {
  if (value == null) {
    return <span className="text-xs text-muted-foreground">-</span>
  }
  return value ? (
    <Check className="h-4 w-4 text-emerald-500" />
  ) : (
    <X className="h-4 w-4 text-muted-foreground/50" />
  )
}

export function ProjectRepositoriesCard({ repositories }: ProjectRepositoriesCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Repository Readiness</CardTitle>
      </CardHeader>
      <CardContent>
        {repositories.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No linked repositories yet for this project.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="pb-2 font-medium">Repository</th>
                  <th className="pb-2 text-right font-medium">Sessions</th>
                  <th className="pb-2 text-center font-medium">CLAUDE.md</th>
                  <th className="pb-2 text-center font-medium">AGENTS.md</th>
                  <th className="pb-2 text-center font-medium">.claude/</th>
                  <th className="pb-2 text-right font-medium">Readiness</th>
                  <th className="pb-2 text-left font-medium">Default Branch</th>
                </tr>
              </thead>
              <tbody>
                {repositories.map((repo) => (
                  <tr key={repo.repository} className="border-b border-border/40 last:border-0">
                    <td className="py-2 font-mono text-xs">{repo.repository}</td>
                    <td className="py-2 text-right">{repo.session_count}</td>
                    <td className="py-2 text-center">
                      <div className="flex justify-center">
                        <StatusIcon value={repo.has_claude_md} />
                      </div>
                    </td>
                    <td className="py-2 text-center">
                      <div className="flex justify-center">
                        <StatusIcon value={repo.has_agents_md} />
                      </div>
                    </td>
                    <td className="py-2 text-center">
                      <div className="flex justify-center">
                        <StatusIcon value={repo.has_claude_dir} />
                      </div>
                    </td>
                    <td className="py-2 text-right">
                      {repo.readiness_checked
                        ? formatPercent(
                            repo.ai_readiness_score != null ? repo.ai_readiness_score / 100 : null,
                          )
                        : "-"}
                    </td>
                    <td className="py-2 text-muted-foreground">{repo.default_branch ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
