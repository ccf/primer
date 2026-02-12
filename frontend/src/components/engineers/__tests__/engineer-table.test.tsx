import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { EngineerTable } from "../engineer-table"
import type { EngineerResponse, TeamResponse } from "@/types/api"

const engineers: EngineerResponse[] = [
  {
    id: "e1",
    name: "Alice",
    email: "a@t.com",
    team_id: "t1",
    role: "engineer",
    avatar_url: null,
    github_username: null,
    display_name: null,
    created_at: "2025-01-15T00:00:00",
  },
  {
    id: "e2",
    name: "Bob",
    email: "b@t.com",
    team_id: null,
    role: "engineer",
    avatar_url: null,
    github_username: null,
    display_name: null,
    created_at: "2025-02-01T00:00:00",
  },
]

const teams: TeamResponse[] = [
  {
    id: "t1",
    name: "Platform",
    created_at: "2025-01-01T00:00:00",
  },
]

describe("EngineerTable", () => {
  it("renders table headers", () => {
    render(<EngineerTable engineers={engineers} teams={teams} />)

    const headerRow = screen.getAllByRole("columnheader")
    const headerTexts = headerRow.map((th) => th.textContent)
    expect(headerTexts).toEqual(["Engineer", "Email", "Role", "Team", "Joined"])
  })

  it("renders engineer data", () => {
    render(<EngineerTable engineers={engineers} teams={teams} />)

    expect(screen.getByText("Alice")).toBeInTheDocument()
    expect(screen.getByText("a@t.com")).toBeInTheDocument()
    expect(screen.getByText("Bob")).toBeInTheDocument()
    expect(screen.getByText("b@t.com")).toBeInTheDocument()
  })

  it("maps team_id to team name", () => {
    render(<EngineerTable engineers={engineers} teams={teams} />)

    expect(screen.getByText("Platform")).toBeInTheDocument()
  })

  it("shows '-' when no team_id", () => {
    render(<EngineerTable engineers={engineers} teams={teams} />)

    const rows = screen.getAllByRole("row")
    // Row 0 is header, row 1 is Alice (has team), row 2 is Bob (no team)
    const bobRow = rows[2]
    const cells = bobRow.querySelectorAll("td")
    expect(cells[3]).toHaveTextContent("-")
  })
})
