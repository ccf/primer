import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"

import { RecoveryPatternList } from "@/components/bottlenecks/recovery-pattern-list"

describe("RecoveryPatternList", () => {
  it("renders overview and strategy cards when recovery data exists", () => {
    render(
      <RecoveryPatternList
        overview={{
          sessions_with_recovery_paths: 4,
          recovered_sessions: 3,
          abandoned_sessions: 1,
          unresolved_sessions: 0,
          recovery_rate: 0.75,
          avg_recovery_steps: 2.5,
        }}
        patterns={[
          {
            strategy: "rerun_verification",
            session_count: 3,
            recovered_sessions: 3,
            abandoned_sessions: 0,
            unresolved_sessions: 0,
            recovery_rate: 1,
            avg_recovery_steps: 2,
            sample_commands: ["pytest -q"],
          },
        ]}
      />,
    )

    expect(screen.getByText("Recovery Paths")).toBeInTheDocument()
    expect(screen.getByText("Recovered")).toBeInTheDocument()
    expect(screen.getByText("Rerun Verification")).toBeInTheDocument()
    expect(screen.getByText("pytest -q")).toBeInTheDocument()
  })

  it("renders nothing when no recovery paths are available", () => {
    const { container } = render(
      <RecoveryPatternList
        overview={{
          sessions_with_recovery_paths: 0,
          recovered_sessions: 0,
          abandoned_sessions: 0,
          unresolved_sessions: 0,
          recovery_rate: 0,
          avg_recovery_steps: 0,
        }}
        patterns={[]}
      />,
    )

    expect(container.firstChild).toBeNull()
  })
})
