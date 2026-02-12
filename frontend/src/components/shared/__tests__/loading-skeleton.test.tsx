import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { CardSkeleton, ChartSkeleton, TableSkeleton } from "../loading-skeleton"

describe("CardSkeleton", () => {
  it("renders skeleton elements", () => {
    const { container } = render(<CardSkeleton />)
    const pulseElements = container.querySelectorAll(".animate-pulse")
    expect(pulseElements.length).toBeGreaterThanOrEqual(2)
  })
})

describe("ChartSkeleton", () => {
  it("renders skeleton elements", () => {
    const { container } = render(<ChartSkeleton />)
    const pulseElements = container.querySelectorAll(".animate-pulse")
    expect(pulseElements.length).toBeGreaterThanOrEqual(1)
  })
})

describe("TableSkeleton", () => {
  it("renders header skeleton plus 5 row skeletons by default", () => {
    const { container } = render(<TableSkeleton />)
    const pulseElements = container.querySelectorAll(".animate-pulse")
    // 1 header skeleton + 5 row skeletons = 6
    expect(pulseElements.length).toBe(6)
  })

  it("renders custom number of row skeletons", () => {
    const { container } = render(<TableSkeleton rows={3} />)
    const pulseElements = container.querySelectorAll(".animate-pulse")
    // 1 header skeleton + 3 row skeletons = 4
    expect(pulseElements.length).toBe(4)
  })
})
