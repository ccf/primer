import { render, screen } from "@testing-library/react"
import { Activity } from "lucide-react"
import { StatCard } from "@/components/dashboard/stat-card"

describe("StatCard", () => {
  it("renders label and value", () => {
    render(<StatCard label="Total Sessions" value={42} icon={Activity} />)

    expect(screen.getByText("Total Sessions")).toBeInTheDocument()
    expect(screen.getByText("42")).toBeInTheDocument()
  })

  it("renders subtitle when provided", () => {
    render(
      <StatCard
        label="Total Sessions"
        value={42}
        subtitle="Last 7 days"
        icon={Activity}
      />,
    )

    expect(screen.getByText("Last 7 days")).toBeInTheDocument()
  })

  it("does not render subtitle when not provided", () => {
    render(<StatCard label="Total Sessions" value={42} icon={Activity} />)

    expect(screen.queryByText("Last 7 days")).not.toBeInTheDocument()
  })
})
