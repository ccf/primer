import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { SessionFilters } from "../session-filters"
import type { EngineerResponse } from "@/types/api"

const engineers: EngineerResponse[] = [
  {
    id: "e1",
    name: "Alice",
    email: "a@t.com",
    team_id: "t1",
    role: "engineer",
    avatar_url: null,
    github_username: null,
    display_name: null,
    created_at: "2025-01-01T00:00:00",
  },
]

describe("SessionFilters", () => {
  it("renders 'All engineers' option", () => {
    render(
      <SessionFilters engineers={engineers} engineerId="" onEngineerChange={vi.fn()} />,
    )

    expect(screen.getByText("All engineers")).toBeInTheDocument()
  })

  it("renders engineer options", () => {
    render(
      <SessionFilters engineers={engineers} engineerId="" onEngineerChange={vi.fn()} />,
    )

    expect(screen.getByText("Alice")).toBeInTheDocument()
    const options = screen.getAllByRole("option")
    expect(options).toHaveLength(2)
    expect(options[0]).toHaveTextContent("All engineers")
    expect(options[1]).toHaveTextContent("Alice")
  })

  it("calls onEngineerChange when selection changes", () => {
    const handleChange = vi.fn()
    render(
      <SessionFilters engineers={engineers} engineerId="" onEngineerChange={handleChange} />,
    )

    const select = screen.getByRole("combobox")
    fireEvent.change(select, { target: { value: "e1" } })

    expect(handleChange).toHaveBeenCalledTimes(1)
    expect(handleChange).toHaveBeenCalledWith("e1")
  })
})
