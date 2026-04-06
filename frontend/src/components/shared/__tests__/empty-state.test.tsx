import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
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

  it("renders title and description", () => {
    render(<EmptyState title="No items" description="Items will appear here." />)
    expect(screen.getByText("No items")).toBeInTheDocument()
    expect(screen.getByText("Items will appear here.")).toBeInTheDocument()
  })

  it("renders action link", () => {
    render(
      <MemoryRouter>
        <EmptyState title="Empty" actionLabel="Go home" actionHref="/" />
      </MemoryRouter>,
    )
    expect(screen.getByText("Go home")).toBeInTheDocument()
    expect(screen.getByText("Go home").closest("a")).toHaveAttribute("href", "/")
  })
})
