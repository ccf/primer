import { render, screen } from "@testing-library/react"
import { PostMergeOutcomesSection } from "@/components/quality/post-merge-outcomes-section"

describe("PostMergeOutcomesSection", () => {
  it("renders summary metrics and recent stabilization PRs", () => {
    render(
      <PostMergeOutcomesSection
        summary={{
          merged_prs_analyzed: 8,
          revert_prs: 1,
          hotfix_prs: 2,
          follow_up_fix_prs: 1,
          affected_repositories: 3,
          post_merge_issue_rate: 0.5,
        }}
        prs={[
          {
            repository: "acme/api",
            pr_number: 412,
            title: 'Revert "Feature rollout"',
            head_branch: "revert/feature-rollout",
            author: "Casey",
            outcome_type: "revert",
            detection_signal: "title contains 'revert'",
            linked_sessions: 2,
            merged_at: "2026-03-30T00:00:00Z",
          },
        ]}
      />,
    )

    expect(screen.getByText("Merged PRs")).toBeInTheDocument()
    expect(screen.getByText("8")).toBeInTheDocument()
    expect(screen.getByText("Issue Rate")).toBeInTheDocument()
    expect(screen.getByText("50%")).toBeInTheDocument()
    expect(screen.getByText("Revert")).toBeInTheDocument()
    expect(screen.getByText('Revert "Feature rollout"')).toBeInTheDocument()
    expect(screen.getByText("title contains 'revert'")).toBeInTheDocument()
  })

  it("renders the empty merged-pr state", () => {
    render(
      <PostMergeOutcomesSection
        summary={{
          merged_prs_analyzed: 0,
          revert_prs: 0,
          hotfix_prs: 0,
          follow_up_fix_prs: 0,
          affected_repositories: 0,
          post_merge_issue_rate: null,
        }}
        prs={[]}
      />,
    )

    expect(screen.getByText("No merged pull requests were in scope for this window yet.")).toBeInTheDocument()
  })
})
