import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { Badge } from "../badge"

describe("Badge", () => {
  it("renders children text", () => {
    render(<Badge>Active</Badge>)
    expect(screen.getByText("Active")).toBeInTheDocument()
  })

  it("applies base classes", () => {
    const { container } = render(<Badge>Test</Badge>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("inline-flex")
    expect(el.className).toContain("rounded-full")
    expect(el.className).toContain("text-xs")
    expect(el.className).toContain("font-medium")
  })

  it("applies default variant classes", () => {
    const { container } = render(<Badge>Default</Badge>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("bg-primary")
    expect(el.className).toContain("text-primary-foreground")
  })

  it("applies secondary variant classes", () => {
    const { container } = render(<Badge variant="secondary">Secondary</Badge>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("bg-secondary")
    expect(el.className).toContain("text-secondary-foreground")
  })

  it("applies destructive variant classes", () => {
    const { container } = render(<Badge variant="destructive">Error</Badge>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("bg-destructive")
    expect(el.className).toContain("text-destructive-foreground")
  })

  it("applies outline variant classes", () => {
    const { container } = render(<Badge variant="outline">Outline</Badge>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("border")
    expect(el.className).toContain("text-foreground")
  })

  it("applies success variant classes", () => {
    const { container } = render(<Badge variant="success">OK</Badge>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("text-success")
    expect(el.className).toContain("bg-success/10")
  })

  it("applies warning variant classes", () => {
    const { container } = render(<Badge variant="warning">Warn</Badge>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("text-warning")
    expect(el.className).toContain("bg-warning/10")
  })
})
