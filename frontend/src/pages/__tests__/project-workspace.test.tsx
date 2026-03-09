import { beforeEach, describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom")
  return { ...actual, useParams: () => ({ projectName: "build%25output" }) }
})

vi.mock("@/hooks/use-api-queries", () => ({
  useProjectWorkspace: vi.fn(),
}))

import { useProjectWorkspace } from "@/hooks/use-api-queries"
import { ProjectWorkspacePage } from "../project-workspace"

const mockUseProjectWorkspace = vi.mocked(useProjectWorkspace)

describe("ProjectWorkspacePage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("passes the already-decoded route param through without double decoding", () => {
    mockUseProjectWorkspace.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("missing"),
    } as ReturnType<typeof useProjectWorkspace>)

    render(
      <MemoryRouter>
        <ProjectWorkspacePage teamId={null} dateRange={null} />
      </MemoryRouter>,
    )

    expect(mockUseProjectWorkspace).toHaveBeenCalledWith(
      "build%25output",
      null,
      undefined,
      undefined,
    )
    expect(screen.getByText("build%25output")).toBeInTheDocument()
  })
})
