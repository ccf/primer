import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { Separator } from "../separator"

describe("Separator", () => {
  it("renders horizontal by default", () => {
    const { container } = render(<Separator />)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("bg-border")
    expect(el.className).toContain("h-px")
    expect(el.className).toContain("w-full")
  })

  it("renders vertical orientation", () => {
    const { container } = render(<Separator orientation="vertical" />)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("bg-border")
    expect(el.className).toContain("h-full")
    expect(el.className).toContain("w-px")
  })

  it("does not have vertical classes when horizontal", () => {
    const { container } = render(<Separator orientation="horizontal" />)
    const el = container.firstChild as HTMLElement
    expect(el.className).not.toContain("h-full")
    expect(el.className).not.toContain("w-px")
  })

  it("merges custom className", () => {
    const { container } = render(<Separator className="my-4" />)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("my-4")
    expect(el.className).toContain("bg-border")
  })
})
