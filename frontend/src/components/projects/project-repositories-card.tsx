import { Check, X } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatPercent } from "@/lib/utils"
import type { ProjectRepositoryContextSummary, ProjectRepositorySummary } from "@/types/api"

interface ProjectRepositoriesCardProps {
  repositories: ProjectRepositorySummary[]
  repositoryContext: ProjectRepositoryContextSummary
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

function formatLanguageMix(repository: ProjectRepositorySummary) {
  if (repository.language_mix.length > 0) {
    return repository.language_mix
      .map((item) => `${item.language} ${formatPercent(item.share_pct)}`)
      .join(" / ")
  }
  return repository.primary_language ?? "-"
}

function formatRepoSize(repoSizeKb: number | null) {
  if (repoSizeKb == null) {
    return "-"
  }
  if (repoSizeKb >= 1024) {
    return `${(repoSizeKb / 1024).toFixed(1)} MB`
  }
  return `${repoSizeKb.toFixed(0)} KB`
}

export function ProjectRepositoriesCard({
  repositories,
  repositoryContext,
}: ProjectRepositoriesCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Repository Context</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {repositories.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No linked repositories yet for this project.
          </p>
        ) : (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Language Mix</p>
                <p className="mt-1 text-sm font-medium">
                  {repositoryContext.language_mix.length > 0
                    ? repositoryContext.language_mix
                        .map((item) => `${item.language} ${formatPercent(item.share_pct)}`)
                        .join(" / ")
                    : "-"}
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Avg Repo Size</p>
                <p className="mt-1 text-sm font-medium">
                  {formatRepoSize(repositoryContext.avg_repo_size_kb)}
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Test Harness</p>
                <p className="mt-1 text-sm font-medium">
                  {repositoryContext.repositories_with_test_harness}/{repositoryContext.repositories_with_context} repos
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">CI Coverage</p>
                <p className="mt-1 text-sm font-medium">
                  {repositoryContext.repositories_with_ci_pipeline}/{repositoryContext.repositories_with_context} repos
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="pb-2 font-medium">Repository</th>
                    <th className="pb-2 text-right font-medium">Sessions</th>
                    <th className="pb-2 font-medium">Languages</th>
                    <th className="pb-2 text-right font-medium">Size</th>
                    <th className="pb-2 text-right font-medium">Tests</th>
                    <th className="pb-2 text-center font-medium">CI</th>
                    <th className="pb-2 text-right font-medium">AI Readiness</th>
                  </tr>
                </thead>
                <tbody>
                  {repositories.map((repo) => (
                    <tr key={repo.repository} className="border-b border-border/40 last:border-0">
                      <td className="py-2">
                        <div className="space-y-1">
                          <p className="font-mono text-xs">{repo.repository}</p>
                          <p className="text-xs text-muted-foreground">
                            {repo.default_branch ? `Branch ${repo.default_branch}` : "Branch unknown"}
                            {repo.repo_size_bucket ? ` • ${repo.repo_size_bucket}` : ""}
                          </p>
                        </div>
                      </td>
                      <td className="py-2 text-right">{repo.session_count}</td>
                      <td className="py-2 text-xs text-muted-foreground">
                        {formatLanguageMix(repo)}
                      </td>
                      <td className="py-2 text-right">{formatRepoSize(repo.repo_size_kb)}</td>
                      <td className="py-2 text-right">
                        {repo.test_maturity_score != null
                          ? formatPercent(repo.test_maturity_score / 100)
                          : "-"}
                      </td>
                      <td className="py-2 text-center">
                        <div className="flex justify-center">
                          <StatusIcon value={repo.has_ci_pipeline} />
                        </div>
                      </td>
                      <td className="py-2 text-right">
                        {repo.readiness_checked
                          ? formatPercent(
                              repo.ai_readiness_score != null ? repo.ai_readiness_score / 100 : null,
                            )
                          : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
