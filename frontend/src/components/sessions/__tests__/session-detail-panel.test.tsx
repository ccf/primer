import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SessionDetailPanel } from "../session-detail-panel"
import type { SessionDetailResponse } from "@/types/api"

const baseSession: SessionDetailResponse = {
  id: "s1",
  engineer_id: "e1",
  project_path: "/home/user/my-project",
  project_name: "my-project",
  git_branch: "main",
  claude_version: "1.0.0",
  permission_mode: "auto",
  end_reason: "user_exit",
  started_at: "2025-01-15T10:00:00",
  ended_at: "2025-01-15T10:30:00",
  duration_seconds: 1800,
  message_count: 25,
  user_message_count: 12,
  assistant_message_count: 13,
  tool_call_count: 8,
  input_tokens: 5000,
  output_tokens: 3000,
  cache_read_tokens: 200,
  cache_creation_tokens: 100,
  primary_model: "claude-sonnet-4-5-20250929",
  first_prompt: "Help me refactor the auth module",
  summary: "Refactored auth module",
  has_facets: true,
  created_at: "2025-01-15T10:00:00",
  facets: {
    underlying_goal: "Improve auth module",
    goal_categories: ["refactoring"],
    outcome: "success",
    session_type: "code_modification",
    primary_success: "Completed refactoring",
    claude_helpfulness: "very_helpful",
    brief_summary: "Successfully refactored the authentication module with improved error handling.",
    user_satisfaction_counts: null,
    friction_counts: null,
    friction_detail: null,
    created_at: "2025-01-15T10:00:00",
  },
  tool_usages: [
    { tool_name: "Read", call_count: 5 },
    { tool_name: "Edit", call_count: 3 },
  ],
  model_usages: [
    {
      model_name: "claude-sonnet-4-5-20250929",
      input_tokens: 5000,
      output_tokens: 3000,
      cache_read_tokens: 200,
      cache_creation_tokens: 100,
    },
  ],
}

describe("SessionDetailPanel", () => {
  it("renders project name", () => {
    render(<SessionDetailPanel session={baseSession} />)

    expect(screen.getByText("my-project")).toBeInTheDocument()
  })

  it("renders metrics", () => {
    render(<SessionDetailPanel session={baseSession} />)

    expect(screen.getByText("Duration")).toBeInTheDocument()
    expect(screen.getByText("Messages")).toBeInTheDocument()
    expect(screen.getByText("Tool Calls")).toBeInTheDocument()
  })

  it("renders first prompt when present", () => {
    render(<SessionDetailPanel session={baseSession} />)

    expect(screen.getByText("First Prompt")).toBeInTheDocument()
    expect(screen.getByText("Help me refactor the auth module")).toBeInTheDocument()
  })

  it("renders facets when present", () => {
    render(<SessionDetailPanel session={baseSession} />)

    expect(screen.getByText("Facets")).toBeInTheDocument()
    expect(screen.getByText("success")).toBeInTheDocument()
    expect(screen.getByText("code_modification")).toBeInTheDocument()
    expect(
      screen.getByText("Successfully refactored the authentication module with improved error handling."),
    ).toBeInTheDocument()
  })

  it("renders tool usage table", () => {
    render(<SessionDetailPanel session={baseSession} />)

    expect(screen.getByText("Tool Usage")).toBeInTheDocument()
    expect(screen.getByText("Read")).toBeInTheDocument()
    expect(screen.getByText("Edit")).toBeInTheDocument()
    expect(screen.getByText("5")).toBeInTheDocument()
    expect(screen.getByText("3")).toBeInTheDocument()
  })

  it("renders model usage table", () => {
    render(<SessionDetailPanel session={baseSession} />)

    expect(screen.getByText("Model Usage")).toBeInTheDocument()
    expect(screen.getByText("claude-sonnet-4-5-20250929")).toBeInTheDocument()
  })

  it("does not render first prompt card when null", () => {
    const sessionNoPrompt: SessionDetailResponse = {
      ...baseSession,
      first_prompt: null,
    }
    render(<SessionDetailPanel session={sessionNoPrompt} />)

    expect(screen.queryByText("First Prompt")).not.toBeInTheDocument()
  })

  it("does not render facets card when null", () => {
    const sessionNoFacets: SessionDetailResponse = {
      ...baseSession,
      facets: null,
    }
    render(<SessionDetailPanel session={sessionNoFacets} />)

    expect(screen.queryByText("Facets")).not.toBeInTheDocument()
  })
})
