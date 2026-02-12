import { describe, it, expect } from "vitest"
import { cn, formatTokens, formatDuration, formatNumber } from "../utils"

describe("cn", () => {
  it("merges multiple class names", () => {
    expect(cn("px-2", "py-1")).toBe("px-2 py-1")
  })

  it("handles conditional classes", () => {
    const isActive = true
    const isDisabled = false
    expect(cn("base", isActive && "active", isDisabled && "disabled")).toBe("base active")
  })

  it("deduplicates and merges tailwind classes", () => {
    expect(cn("px-2 py-1", "px-4")).toBe("py-1 px-4")
  })

  it("handles empty input", () => {
    expect(cn()).toBe("")
  })

  it("handles undefined and null values", () => {
    expect(cn("base", undefined, null, "extra")).toBe("base extra")
  })
})

describe("formatTokens", () => {
  it("returns 'M' suffix for values >= 1,000,000", () => {
    expect(formatTokens(1_500_000)).toBe("1.5M")
    expect(formatTokens(10_000_000)).toBe("10.0M")
  })

  it("returns 'K' suffix for values >= 1,000 and < 1,000,000", () => {
    expect(formatTokens(1_500)).toBe("1.5K")
    expect(formatTokens(999_999)).toBe("1000.0K")
  })

  it("returns raw number as string for values < 1,000", () => {
    expect(formatTokens(0)).toBe("0")
    expect(formatTokens(999)).toBe("999")
    expect(formatTokens(42)).toBe("42")
  })

  it("handles boundary at exactly 1,000", () => {
    expect(formatTokens(1_000)).toBe("1.0K")
  })

  it("handles boundary at exactly 1,000,000", () => {
    expect(formatTokens(1_000_000)).toBe("1.0M")
  })
})

describe("formatDuration", () => {
  it("returns '-' for null", () => {
    expect(formatDuration(null)).toBe("-")
  })

  it("returns '-' for undefined", () => {
    expect(formatDuration(undefined)).toBe("-")
  })

  it("returns seconds with 's' suffix for values < 60", () => {
    expect(formatDuration(0)).toBe("0s")
    expect(formatDuration(30)).toBe("30s")
    expect(formatDuration(59)).toBe("59s")
    expect(formatDuration(59.4)).toBe("59s")
  })

  it("rounds seconds to nearest integer", () => {
    expect(formatDuration(30.6)).toBe("31s")
    expect(formatDuration(0.4)).toBe("0s")
  })

  it("returns minutes with 'm' suffix for values >= 60 and < 3600", () => {
    expect(formatDuration(60)).toBe("1m")
    expect(formatDuration(120)).toBe("2m")
    expect(formatDuration(3599)).toBe("60m")
  })

  it("returns hours with 'h' suffix for values >= 3600", () => {
    expect(formatDuration(3600)).toBe("1.0h")
    expect(formatDuration(5400)).toBe("1.5h")
    expect(formatDuration(7200)).toBe("2.0h")
  })
})

describe("formatNumber", () => {
  it("formats numbers with locale separators", () => {
    // toLocaleString output is locale-dependent; verify it returns a string
    expect(formatNumber(1000)).toBe((1000).toLocaleString())
    expect(formatNumber(1234567)).toBe((1234567).toLocaleString())
  })

  it("returns plain number string for small values", () => {
    expect(formatNumber(0)).toBe("0")
    expect(formatNumber(42)).toBe("42")
  })
})
