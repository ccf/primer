import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../card"

describe("Card", () => {
  it("renders children", () => {
    render(<Card>Card content</Card>)
    expect(screen.getByText("Card content")).toBeInTheDocument()
  })

  it("applies default classes", () => {
    const { container } = render(<Card>Test</Card>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("rounded-2xl")
    expect(el.className).toContain("border")
    expect(el.className).toContain("bg-card")
    expect(el.className).toContain("shadow-sm")
  })

  it("merges custom className", () => {
    const { container } = render(<Card className="my-custom">Test</Card>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("my-custom")
    expect(el.className).toContain("rounded-2xl")
  })
})

describe("CardHeader", () => {
  it("renders children", () => {
    render(<CardHeader>Header text</CardHeader>)
    expect(screen.getByText("Header text")).toBeInTheDocument()
  })

  it("applies default classes", () => {
    const { container } = render(<CardHeader>Test</CardHeader>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("flex")
    expect(el.className).toContain("flex-col")
    expect(el.className).toContain("p-6")
  })

  it("merges custom className", () => {
    const { container } = render(<CardHeader className="extra">Test</CardHeader>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("extra")
  })
})

describe("CardTitle", () => {
  it("renders children", () => {
    render(<CardTitle>My Title</CardTitle>)
    expect(screen.getByText("My Title")).toBeInTheDocument()
  })

  it("applies default classes", () => {
    const { container } = render(<CardTitle>Test</CardTitle>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("font-semibold")
    expect(el.className).toContain("leading-none")
    expect(el.className).toContain("tracking-tight")
  })

  it("merges custom className", () => {
    const { container } = render(<CardTitle className="text-xl">Test</CardTitle>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("text-xl")
  })
})

describe("CardDescription", () => {
  it("renders children", () => {
    render(<CardDescription>Some description</CardDescription>)
    expect(screen.getByText("Some description")).toBeInTheDocument()
  })

  it("applies default classes", () => {
    const { container } = render(<CardDescription>Test</CardDescription>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("text-sm")
    expect(el.className).toContain("text-muted-foreground")
  })

  it("merges custom className", () => {
    const { container } = render(<CardDescription className="italic">Test</CardDescription>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("italic")
  })
})

describe("CardContent", () => {
  it("renders children", () => {
    render(<CardContent>Content here</CardContent>)
    expect(screen.getByText("Content here")).toBeInTheDocument()
  })

  it("applies default classes", () => {
    const { container } = render(<CardContent>Test</CardContent>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("p-6")
    expect(el.className).toContain("pt-0")
  })

  it("merges custom className", () => {
    const { container } = render(<CardContent className="gap-4">Test</CardContent>)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("gap-4")
  })
})
