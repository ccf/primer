import { render, screen } from "@testing-library/react"
import { DailyActivityChart } from "@/components/dashboard/daily-activity-chart"
import type { DailyStatsResponse } from "@/types/api"

const sampleData: DailyStatsResponse[] = [
  { date: "2025-01-15", session_count: 5, message_count: 20, tool_call_count: 10 },
]

describe("DailyActivityChart", () => {
  it("renders 'Daily Activity' title", () => {
    render(<DailyActivityChart data={sampleData} />)

    expect(screen.getByText("Daily Activity")).toBeInTheDocument()
  })

  it("renders with empty array", () => {
    render(<DailyActivityChart data={[]} />)

    expect(screen.getByText("Daily Activity")).toBeInTheDocument()
  })
})
