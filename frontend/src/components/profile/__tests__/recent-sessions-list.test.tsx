import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

import { RecentSessionsList } from "@/components/profile/recent-sessions-list"
import type { SessionResponse } from "@/types/api"

const baseSession: SessionResponse = {
  id: "s1",
  engineer_id: "e1",
  project_path: null,
  project_name: "primer",
  git_branch: null,
  agent_type: "claude_code",
  agent_version: null,
  permission_mode: null,
  end_reason: null,
  started_at: "2025-01-15T10:00:00",
  ended_at: null,
  duration_seconds: 120,
  message_count: 10,
  user_message_count: 5,
  assistant_message_count: 5,
  tool_call_count: 3,
  input_tokens: 1000,
  output_tokens: 500,
  cache_read_tokens: 0,
  cache_creation_tokens: 0,
  primary_model: "claude-sonnet-4-5-20250929",
  first_prompt: null,
  summary: null,
  has_facets: false,
  has_workflow_profile: true,
  created_at: "2025-01-15T10:00:00",
}

describe("RecentSessionsList", () => {
  it("shows workflow status when workflow analysis exists without facets", () => {
    render(
      <MemoryRouter>
        <RecentSessionsList sessions={[baseSession]} />
      </MemoryRouter>,
    )

    expect(screen.getByText("Workflow")).toBeInTheDocument()
  })
})
