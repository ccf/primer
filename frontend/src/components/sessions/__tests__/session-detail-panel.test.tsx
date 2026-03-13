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
  agent_type: "claude_code",
  agent_version: "1.0.0",
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
    agent_helpfulness: "very_helpful",
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
  execution_evidence: [
    {
      ordinal: 3,
      evidence_type: "test",
      status: "passed",
      tool_name: "Bash",
      command: "pytest -q",
      output_preview: "2 passed in 0.12s",
    },
  ],
  change_shape: {
    files_touched_count: 3,
    named_touched_files: ["src/auth.py", "tests/test_auth.py"],
    commit_files_changed: 3,
    lines_added: 42,
    lines_deleted: 12,
    diff_size: 54,
    edit_operations: 2,
    create_operations: 1,
    delete_operations: 0,
    rename_operations: 0,
    churn_files_count: 1,
    rewrite_indicator: false,
    revert_indicator: false,
  },
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

  it("renders tool usage chart", () => {
    render(<SessionDetailPanel session={baseSession} />)

    expect(screen.getByText("Tool Usage")).toBeInTheDocument()
  })

  it("renders model usage table", () => {
    render(<SessionDetailPanel session={baseSession} />)

    expect(screen.getByText("Model Usage")).toBeInTheDocument()
    expect(screen.getByText("claude-sonnet-4-5-20250929")).toBeInTheDocument()
  })

  it("renders execution evidence when present", () => {
    render(<SessionDetailPanel session={baseSession} />)

    expect(screen.getByText("Execution Evidence")).toBeInTheDocument()
    expect(screen.getByText("pytest -q")).toBeInTheDocument()
    expect(screen.getByText("2 passed in 0.12s")).toBeInTheDocument()
  })

  it("renders change shape when present", () => {
    render(<SessionDetailPanel session={baseSession} />)

    expect(screen.getByText("Change Shape")).toBeInTheDocument()
    expect(screen.getByText("Files Touched")).toBeInTheDocument()
    expect(screen.getByText("src/auth.py")).toBeInTheDocument()
    expect(screen.getByText("Edits 2")).toBeInTheDocument()
  })

  it("counts hidden change-shape files from both named overflow and inferred files", () => {
    render(
      <SessionDetailPanel
        session={{
          ...baseSession,
          change_shape: {
            ...baseSession.change_shape,
            files_touched_count: 12,
            named_touched_files: [
              "src/a.ts",
              "src/b.ts",
              "src/c.ts",
              "src/d.ts",
              "src/e.ts",
              "src/f.ts",
              "src/g.ts",
              "src/h.ts",
              "src/i.ts",
              "src/j.ts",
            ],
          },
        }}
      />,
    )

    expect(screen.getByText("+4 more")).toBeInTheDocument()
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
