import { Badge } from "@/components/ui/badge"
import type { PostMergeOutcomePRSummary, PostMergeOutcomeSummary } from "@/types/api"
import { formatPercent } from "@/lib/utils"

interface PostMergeOutcomesSectionProps {
  summary: PostMergeOutcomeSummary | null
  prs: PostMergeOutcomePRSummary[]
}

const outcomeLabel: Record<string, string> = {
  revert: "Revert",
  hotfix: "Hotfix",
  follow_up_fix: "Follow-up fix",
}

export function PostMergeOutcomesSection({
  summary,
  prs,
}: PostMergeOutcomesSectionProps) {
  if (!summary || summary.merged_prs_analyzed === 0) {
    return (
      <div className="rounded-2xl border border-border/70 bg-card/70 p-6">
        <p className="text-sm font-medium">Post-merge outcomes</p>
        <p className="mt-2 text-sm text-muted-foreground">
          No merged pull requests were in scope for this window yet.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4 rounded-2xl border border-border/70 bg-card/70 p-6">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Merged PRs" value={String(summary.merged_prs_analyzed)} />
        <MetricCard label="Reverts" value={String(summary.revert_prs)} />
        <MetricCard label="Hotfixes" value={String(summary.hotfix_prs)} />
        <MetricCard label="Follow-up fixes" value={String(summary.follow_up_fix_prs)} />
        <MetricCard
          label="Issue Rate"
          value={formatPercent(summary.post_merge_issue_rate)}
          subtitle={`${summary.affected_repositories} repos affected`}
        />
      </div>

      {prs.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No revert, hotfix, or follow-up fix PRs were detected in this scope.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border/60">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50 text-left text-xs font-medium text-muted-foreground">
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Repository</th>
                <th className="px-3 py-2">PR</th>
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2">Signal</th>
                <th className="px-3 py-2">Author</th>
                <th className="px-3 py-2">Sessions</th>
              </tr>
            </thead>
            <tbody>
              {prs.map((pr) => (
                <tr
                  key={`${pr.repository}-${pr.pr_number}-${pr.outcome_type}`}
                  className="border-b border-border/40 last:border-0"
                >
                  <td className="px-3 py-2">
                    <Badge variant="outline">
                      {outcomeLabel[pr.outcome_type] ?? pr.outcome_type.replaceAll("_", " ")}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">{pr.repository}</td>
                  <td className="px-3 py-2 font-mono">#{pr.pr_number}</td>
                  <td className="max-w-[260px] truncate px-3 py-2">{pr.title ?? "-"}</td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">{pr.detection_signal}</td>
                  <td className="px-3 py-2 text-xs">{pr.author ?? "-"}</td>
                  <td className="px-3 py-2 text-center">{pr.linked_sessions}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function MetricCard({
  label,
  value,
  subtitle,
}: {
  label: string
  value: string
  subtitle?: string
}) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/70 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 font-display text-2xl tracking-tight">{value}</p>
      {subtitle && <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>}
    </div>
  )
}
