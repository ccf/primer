import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import userEvent from "@testing-library/user-event"
import { FrictionList } from "../friction-list"
import type { FrictionReport } from "@/types/api"

const frictionData: FrictionReport[] = [
  {
    friction_type: "tool_error",
    count: 5,
    details: ["Failed on large files", "Timeout"],
  },
]

describe("FrictionList", () => {
  it("shows 'No friction detected' when empty", () => {
    render(
      <MemoryRouter>
        <FrictionList data={[]} />
      </MemoryRouter>,
    )

    expect(screen.getByText("No friction detected")).toBeInTheDocument()
  })

  it("renders friction types and counts", () => {
    render(
      <MemoryRouter>
        <FrictionList data={frictionData} />
      </MemoryRouter>,
    )

    expect(screen.getByText("tool_error")).toBeInTheDocument()
    expect(screen.getByText("5")).toBeInTheDocument()
  })

  it("expands details when clicked", async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <FrictionList data={frictionData} />
      </MemoryRouter>,
    )

    expect(screen.queryByText("Failed on large files")).not.toBeInTheDocument()

    const button = screen.getByRole("button", { name: /tool_error/i })
    await user.click(button)

    expect(screen.getByText("Failed on large files")).toBeInTheDocument()
    expect(screen.getByText("Timeout")).toBeInTheDocument()
  })

  it("collapses when clicked again", async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <FrictionList data={frictionData} />
      </MemoryRouter>,
    )

    const button = screen.getByRole("button", { name: /tool_error/i })
    await user.click(button)
    expect(screen.getByText("Failed on large files")).toBeInTheDocument()

    await user.click(button)
    expect(screen.queryByText("Failed on large files")).not.toBeInTheDocument()
  })
})
