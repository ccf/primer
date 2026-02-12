import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { Skeleton } from "../skeleton"

describe("Skeleton", () => {
  it("renders with default classes", () => {
    const { container } = render(<Skeleton />)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("animate-pulse")
    expect(el.className).toContain("rounded-md")
    expect(el.className).toContain("bg-muted")
  })

  it("merges custom className", () => {
    const { container } = render(<Skeleton className="h-4 w-24" />)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("animate-pulse")
    expect(el.className).toContain("h-4")
    expect(el.className).toContain("w-24")
  })
})
