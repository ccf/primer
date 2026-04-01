import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/hooks/use-api-queries", () => ({
  useDeviceTokens: vi.fn(),
}))

vi.mock("@/hooks/use-api-mutations", () => ({
  useCreateDeviceToken: vi.fn(),
  useCreateDeviceTokenSetupCode: vi.fn(),
  useRevokeDeviceToken: vi.fn(),
}))

import {
  useCreateDeviceToken,
  useCreateDeviceTokenSetupCode,
  useRevokeDeviceToken,
} from "@/hooks/use-api-mutations"
import { useDeviceTokens } from "@/hooks/use-api-queries"
import { DeviceTokenCard } from "@/components/profile/device-token-card"
import { parseApiUtcDate } from "@/lib/datetime"

const mockUseDeviceTokens = vi.mocked(useDeviceTokens)
const mockUseCreateDeviceToken = vi.mocked(useCreateDeviceToken)
const mockUseCreateDeviceTokenSetupCode = vi.mocked(useCreateDeviceTokenSetupCode)
const mockUseRevokeDeviceToken = vi.mocked(useRevokeDeviceToken)

describe("DeviceTokenCard", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseDeviceTokens.mockReturnValue({
      data: [
        {
          id: "dt-1",
          engineer_id: "eng-1",
          name: "Laptop",
          token_last_four: "1234",
          revoked: false,
          created_at: "2026-03-31T00:00:00Z",
        },
      ],
      isLoading: false,
    } as ReturnType<typeof useDeviceTokens>)
    mockUseCreateDeviceToken.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useCreateDeviceToken>)
    mockUseCreateDeviceTokenSetupCode.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useCreateDeviceTokenSetupCode>)
    mockUseRevokeDeviceToken.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useRevokeDeviceToken>)
  })

  it("renders existing tokens", () => {
    render(<DeviceTokenCard />)

    expect(screen.getByText("Local Device Tokens")).toBeInTheDocument()
    expect(screen.getByText("Laptop")).toBeInTheDocument()
    expect(screen.getByText(/Ends with 1234/)).toBeInTheDocument()
  })

  it("creates a token when requested", () => {
    const mutate = vi.fn()
    mockUseCreateDeviceToken.mockReturnValue({
      mutate,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateDeviceToken>)

    render(<DeviceTokenCard />)
    fireEvent.click(screen.getByText("Create device token"))

    expect(mutate).toHaveBeenCalled()
  })

  it("creates a setup code when requested", () => {
    const mutate = vi.fn()
    mockUseCreateDeviceTokenSetupCode.mockReturnValue({
      mutate,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateDeviceTokenSetupCode>)

    render(<DeviceTokenCard />)
    fireEvent.click(screen.getByText("Create setup code"))

    expect(mutate).toHaveBeenCalled()
  })

  it("treats naive API timestamps as UTC", () => {
    expect(parseApiUtcDate("2026-03-31T12:15:00").toISOString()).toBe("2026-03-31T12:15:00.000Z")
    expect(parseApiUtcDate("2026-03-31T12:15:00Z").toISOString()).toBe("2026-03-31T12:15:00.000Z")
  })
})
