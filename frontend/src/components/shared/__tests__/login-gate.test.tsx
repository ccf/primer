import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

const mockSetApiKey = vi.fn()
vi.mock("@/lib/api", () => ({
  setApiKey: (...args: unknown[]) => mockSetApiKey(...args),
}))

const mockFetch = vi.fn()
vi.stubGlobal("fetch", mockFetch)

const mockReload = vi.fn()
Object.defineProperty(window, "location", {
  value: { reload: mockReload },
  writable: true,
})

import { LoginGate } from "../login-gate"

beforeEach(() => {
  mockSetApiKey.mockReset()
  mockFetch.mockReset()
  mockReload.mockReset()
})

describe("LoginGate", () => {
  it('renders "Primer Dashboard" title', () => {
    render(<LoginGate />)
    expect(screen.getByText("Primer Dashboard")).toBeInTheDocument()
  })

  it('renders "Enter your admin API key to continue"', () => {
    render(<LoginGate />)
    expect(screen.getByText("Enter your admin API key to continue")).toBeInTheDocument()
  })

  it("renders Sign in button", () => {
    render(<LoginGate />)
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument()
  })

  it('shows error "Please enter an API key" when submitting empty', async () => {
    const user = userEvent.setup()
    render(<LoginGate />)

    await user.click(screen.getByRole("button", { name: "Sign in" }))

    expect(screen.getByText("Please enter an API key")).toBeInTheDocument()
  })

  it('shows error "Invalid API key" when server returns non-ok response', async () => {
    const user = userEvent.setup()
    mockFetch.mockResolvedValue({ ok: false, status: 403 })

    render(<LoginGate />)

    const input = screen.getByPlaceholderText("primer-admin-dev-key")
    await user.type(input, "bad-key")
    await user.click(screen.getByRole("button", { name: "Sign in" }))

    expect(await screen.findByText("Invalid API key")).toBeInTheDocument()
  })

  it('shows error "Cannot connect to server" when fetch throws', async () => {
    const user = userEvent.setup()
    mockFetch.mockRejectedValue(new Error("Network error"))

    render(<LoginGate />)

    const input = screen.getByPlaceholderText("primer-admin-dev-key")
    await user.type(input, "some-key")
    await user.click(screen.getByRole("button", { name: "Sign in" }))

    expect(await screen.findByText("Cannot connect to server")).toBeInTheDocument()
  })

  it("calls setApiKey and reloads on successful submission", async () => {
    const user = userEvent.setup()
    mockFetch.mockResolvedValue({ ok: true, status: 200 })

    render(<LoginGate />)

    const input = screen.getByPlaceholderText("primer-admin-dev-key")
    await user.type(input, "valid-key")
    await user.click(screen.getByRole("button", { name: "Sign in" }))

    await vi.waitFor(() => {
      expect(mockSetApiKey).toHaveBeenCalledWith("valid-key")
    })
    expect(mockReload).toHaveBeenCalled()
  })
})
