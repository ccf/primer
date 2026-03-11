import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { ProjectRepositoriesCard } from "@/components/projects/project-repositories-card"

describe("ProjectRepositoriesCard", () => {
  it("renders repository context metrics and per-repository details", () => {
    render(
      <ProjectRepositoriesCard
        repositoryContext={{
          repositories_with_context: 1,
          avg_repo_size_kb: 12500,
          avg_test_maturity_score: 1,
          repositories_with_test_harness: 1,
          repositories_with_ci_pipeline: 1,
          language_mix: [
            { language: "Python", share_pct: 0.7 },
            { language: "TypeScript", share_pct: 0.3 },
          ],
          size_distribution: { medium: 1 },
        }}
        repositories={[
          {
            repository: "acme/workspace",
            session_count: 2,
            default_branch: "main",
            readiness_checked: true,
            ai_readiness_score: 45,
            has_claude_md: false,
            has_agents_md: false,
            has_claude_dir: false,
            primary_language: "Python",
            language_mix: [
              { language: "Python", share_pct: 0.7 },
              { language: "TypeScript", share_pct: 0.3 },
            ],
            repo_size_kb: 12500,
            repo_size_bucket: "medium",
            has_test_harness: true,
            has_ci_pipeline: true,
            test_maturity_score: 100,
          },
        ]}
      />,
    )

    expect(screen.getByText("Repository Context")).toBeInTheDocument()
    expect(screen.getAllByText("Python 70% / TypeScript 30%")).toHaveLength(2)
    expect(screen.getAllByText("12.2 MB")).toHaveLength(2)
    expect(screen.getAllByText("1/1 repos")).toHaveLength(2)
    expect(screen.getByText("100%")).toBeInTheDocument()
    expect(screen.getByText("45%")).toBeInTheDocument()
    expect(screen.getByText("Branch main • medium")).toBeInTheDocument()
  })
})
