import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { SavedExplorerItems } from "@/components/explorer/saved-explorer-items"

describe("SavedExplorerItems", () => {
  it("renders prompts and report cards and calls run/delete handlers", async () => {
    const user = userEvent.setup()
    const onRun = vi.fn()
    const onDelete = vi.fn()

    render(
      <SavedExplorerItems
        items={[
          {
            id: "prompt-1",
            engineer_id: "eng-1",
            owner_role: "engineer",
            item_type: "prompt",
            title: "Weekly check-in",
            prompt_text: "How am I trending this week?",
            result_preview: null,
            scope_team_id: null,
            scope_start_date: null,
            scope_end_date: null,
            created_at: "2026-04-05T12:00:00Z",
            updated_at: "2026-04-05T12:00:00Z",
          },
          {
            id: "report-1",
            engineer_id: "eng-1",
            owner_role: "engineer",
            item_type: "report_card",
            title: "Friction snapshot",
            prompt_text: "What is costing us the most time?",
            result_preview: "Permission issues and timeouts dominate the week.",
            scope_team_id: "team-1",
            scope_start_date: "2026-04-01T00:00:00Z",
            scope_end_date: "2026-04-07T00:00:00Z",
            created_at: "2026-04-05T12:00:00Z",
            updated_at: "2026-04-05T12:00:00Z",
          },
        ]}
        onRun={onRun}
        onDelete={onDelete}
      />,
    )

    expect(screen.getByText("Saved Prompts")).toBeInTheDocument()
    expect(screen.getByText("Weekly check-in")).toBeInTheDocument()
    expect(screen.getByText("Report Cards")).toBeInTheDocument()
    expect(screen.getByText("Friction snapshot")).toBeInTheDocument()
    expect(screen.getByText("Team scope · Saved date range")).toBeInTheDocument()

    const buttons = screen.getAllByRole("button")
    await user.click(buttons[0])
    expect(onRun).toHaveBeenCalledWith(
      expect.objectContaining({ id: "prompt-1", item_type: "prompt" }),
    )

    await user.click(buttons[1])
    expect(onDelete).toHaveBeenCalledWith("prompt-1")
  })
})
