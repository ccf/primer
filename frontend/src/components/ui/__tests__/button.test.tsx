import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { Button } from "../button"

describe("Button", () => {
  it("renders children", () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole("button", { name: "Click me" })).toBeInTheDocument()
  })

  it("applies default variant classes", () => {
    render(<Button>Default</Button>)
    const btn = screen.getByRole("button")
    expect(btn.className).toContain("bg-primary")
    expect(btn.className).toContain("text-primary-foreground")
  })

  it("applies outline variant classes", () => {
    render(<Button variant="outline">Outline</Button>)
    const btn = screen.getByRole("button")
    expect(btn.className).toContain("border")
    expect(btn.className).toContain("bg-background")
  })

  it("applies secondary variant classes", () => {
    render(<Button variant="secondary">Secondary</Button>)
    const btn = screen.getByRole("button")
    expect(btn.className).toContain("bg-secondary")
    expect(btn.className).toContain("text-secondary-foreground")
  })

  it("applies ghost variant classes", () => {
    render(<Button variant="ghost">Ghost</Button>)
    const btn = screen.getByRole("button")
    expect(btn.className).toContain("hover:bg-accent")
  })

  it("applies default size classes", () => {
    render(<Button>Sized</Button>)
    const btn = screen.getByRole("button")
    expect(btn.className).toContain("h-9")
    expect(btn.className).toContain("px-4")
  })

  it("applies sm size classes", () => {
    render(<Button size="sm">Small</Button>)
    const btn = screen.getByRole("button")
    expect(btn.className).toContain("h-8")
    expect(btn.className).toContain("px-3")
    expect(btn.className).toContain("text-xs")
  })

  it("applies lg size classes", () => {
    render(<Button size="lg">Large</Button>)
    const btn = screen.getByRole("button")
    expect(btn.className).toContain("h-10")
    expect(btn.className).toContain("px-8")
  })

  it("applies icon size classes", () => {
    render(<Button size="icon">X</Button>)
    const btn = screen.getByRole("button")
    expect(btn.className).toContain("h-9")
    expect(btn.className).toContain("w-9")
  })

  it("handles disabled state", () => {
    render(<Button disabled>Disabled</Button>)
    const btn = screen.getByRole("button")
    expect(btn).toBeDisabled()
    expect(btn.className).toContain("disabled:opacity-50")
  })

  it("handles onClick", async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()
    render(<Button onClick={handleClick}>Press</Button>)
    await user.click(screen.getByRole("button"))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })
})
