import { render, screen } from "@testing-library/react"

import { RootCauseClusterList } from "@/components/bottlenecks/root-cause-cluster-list"

describe("RootCauseClusterList", () => {
  it("renders clustered root-cause evidence", () => {
    render(
      <RootCauseClusterList
        data={[
          {
            cluster_id: "permission_boundary::execute",
            title: "Permission boundaries during execute work",
            cause_category: "permission_boundary",
            workflow_stage: "execute",
            session_count: 3,
            occurrence_count: 5,
            success_rate: 0.333,
            avg_impact_score: 0.25,
            top_friction_types: ["permission_denied"],
            common_tools: ["Bash", "Edit"],
            transcript_cues: ["permission", "access denied"],
            sample_details: ["Permission was denied on file write."],
          },
        ]}
      />,
    )

    expect(screen.getByText("Root-Cause Clusters")).toBeInTheDocument()
    expect(screen.getByText("Permission boundaries during execute work")).toBeInTheDocument()
    expect(screen.getByText("3 sessions • 5 occurrences")).toBeInTheDocument()
    expect(screen.getByText("Success 33%")).toBeInTheDocument()
    expect(screen.getByText("Avg impact 25.0pp")).toBeInTheDocument()
    expect(screen.getByText("Bash")).toBeInTheDocument()
    expect(screen.getByText("permission")).toBeInTheDocument()
    expect(screen.getByText("Permission was denied on file write.")).toBeInTheDocument()
  })
})
