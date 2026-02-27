import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { SessionTable } from "../session-table"
import type { SessionResponse } from "@/types/api"

const session: SessionResponse = {
  id: "s1",
  engineer_id: "e1",
  project_path: null,
  project_name: "my-project",
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
  has_facets: true,
  created_at: "2025-01-15T10:00:00",
}

function renderWithRouter(sessions: SessionResponse[]) {
  return render(
    <MemoryRouter>
      <SessionTable sessions={sessions} />
    </MemoryRouter>,
  )
}

describe("SessionTable", () => {
  it("renders table headers", () => {
    renderWithRouter([session])

    const headers = ["Project", "Model", "Started", "Duration", "Messages", "Tools", "Tokens", "Facets"]
    for (const header of headers) {
      expect(screen.getByText(header)).toBeInTheDocument()
    }
  })

  it("renders session data", () => {
    renderWithRouter([session])

    expect(screen.getByText("my-project")).toBeInTheDocument()
    expect(screen.getByText("10")).toBeInTheDocument()
  })

  it("renders 'Yes' badge when has_facets is true", () => {
    renderWithRouter([session])

    expect(screen.getByText("Yes")).toBeInTheDocument()
  })

  it("renders 'No' badge when has_facets is false", () => {
    const noFacetsSession: SessionResponse = { ...session, id: "s2", has_facets: false }
    renderWithRouter([noFacetsSession])

    expect(screen.getByText("No")).toBeInTheDocument()
  })
})
