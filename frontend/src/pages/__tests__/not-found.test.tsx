import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { NotFoundPage } from "../not-found"

describe("NotFoundPage", () => {
  const renderPage = () =>
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>,
    )

  it("renders 404 text", () => {
    renderPage()
    expect(screen.getByText("404")).toBeInTheDocument()
  })

  it("renders 'Page not found' message", () => {
    renderPage()
    expect(screen.getByText("Page not found")).toBeInTheDocument()
  })

  it("renders a link to overview", () => {
    renderPage()
    const link = screen.getByRole("link", { name: /go to overview/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute("href", "/")
  })
})
