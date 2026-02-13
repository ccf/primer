import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { EmptyState } from "../empty-state"

describe("EmptyState", () => {
  it("renders default message", () => {
    render(<EmptyState />)
    expect(screen.getByText("No data available")).toBeInTheDocument()
  })

  it("renders custom message", () => {
    render(<EmptyState message="Nothing to show" />)
    expect(screen.getByText("Nothing to show")).toBeInTheDocument()
    expect(screen.queryByText("No data available")).not.toBeInTheDocument()
  })
})
