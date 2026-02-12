import { describe, it, expect, vi, beforeEach } from "vitest"

// Create a proper localStorage mock before importing the module under test
const storageMap = new Map<string, string>()
const localStorageMock = {
  getItem: vi.fn((key: string) => storageMap.get(key) ?? null),
  setItem: vi.fn((key: string, value: string) => {
    storageMap.set(key, value)
  }),
  removeItem: vi.fn((key: string) => {
    storageMap.delete(key)
  }),
  clear: vi.fn(() => {
    storageMap.clear()
  }),
  get length() {
    return storageMap.size
  },
  key: vi.fn((index: number) => {
    return Array.from(storageMap.keys())[index] ?? null
  }),
}
vi.stubGlobal("localStorage", localStorageMock)

const mockFetch = vi.fn()
vi.stubGlobal("fetch", mockFetch)

const mockReload = vi.fn()
Object.defineProperty(window, "location", {
  value: { reload: mockReload },
  writable: true,
})

import { getApiKey, setApiKey, clearApiKey, ApiError, apiFetch } from "../api"

beforeEach(() => {
  storageMap.clear()
  localStorageMock.getItem.mockClear()
  localStorageMock.setItem.mockClear()
  localStorageMock.removeItem.mockClear()
  mockFetch.mockReset()
  mockReload.mockReset()
})

describe("getApiKey", () => {
  it("returns null when no key is stored", () => {
    expect(getApiKey()).toBeNull()
  })

  it("returns the stored key", () => {
    storageMap.set("primer_admin_key", "test-key-123")
    expect(getApiKey()).toBe("test-key-123")
  })
})

describe("setApiKey", () => {
  it("stores the key in localStorage", () => {
    setApiKey("my-secret-key")
    expect(localStorageMock.setItem).toHaveBeenCalledWith("primer_admin_key", "my-secret-key")
    expect(storageMap.get("primer_admin_key")).toBe("my-secret-key")
  })
})

describe("clearApiKey", () => {
  it("removes the key from localStorage", () => {
    storageMap.set("primer_admin_key", "to-be-removed")
    clearApiKey()
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("primer_admin_key")
    expect(storageMap.has("primer_admin_key")).toBe(false)
  })
})

describe("ApiError", () => {
  it("has the correct name, status, and message", () => {
    const error = new ApiError(404, "Not Found")
    expect(error).toBeInstanceOf(Error)
    expect(error.name).toBe("ApiError")
    expect(error.status).toBe(404)
    expect(error.message).toBe("Not Found")
  })
})

describe("apiFetch", () => {
  function mockResponse(status: number, body: unknown, ok?: boolean) {
    return {
      status,
      ok: ok !== undefined ? ok : status >= 200 && status < 300,
      json: () => Promise.resolve(body),
      text: () => Promise.resolve(typeof body === "string" ? body : JSON.stringify(body)),
    }
  }

  it("sends Content-Type application/json header", async () => {
    mockFetch.mockResolvedValue(mockResponse(200, { data: "ok" }))

    await apiFetch("/api/v1/test")

    expect(mockFetch).toHaveBeenCalledWith("/api/v1/test", {
      credentials: "include",
      headers: expect.objectContaining({
        "Content-Type": "application/json",
      }),
    })
  })

  it("sends x-admin-key header when API key exists", async () => {
    storageMap.set("primer_admin_key", "admin-key-456")
    mockFetch.mockResolvedValue(mockResponse(200, { data: "ok" }))

    await apiFetch("/api/v1/test")

    expect(mockFetch).toHaveBeenCalledWith("/api/v1/test", {
      credentials: "include",
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "x-admin-key": "admin-key-456",
      }),
    })
  })

  it("does not send x-admin-key header when no key exists", async () => {
    mockFetch.mockResolvedValue(mockResponse(200, { data: "ok" }))

    await apiFetch("/api/v1/test")

    const callHeaders = mockFetch.mock.calls[0][1].headers
    expect(callHeaders).not.toHaveProperty("x-admin-key")
  })

  it("returns parsed JSON on success", async () => {
    const responseBody = { id: 1, name: "test" }
    mockFetch.mockResolvedValue(mockResponse(200, responseBody))

    const result = await apiFetch("/api/v1/test")

    expect(result).toEqual(responseBody)
  })

  it("on 403 clears the API key and reloads the page", async () => {
    storageMap.set("primer_admin_key", "expired-key")
    mockFetch.mockResolvedValue(mockResponse(403, "Forbidden"))

    await expect(apiFetch("/api/v1/test")).rejects.toThrow(ApiError)
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("primer_admin_key")
    expect(storageMap.has("primer_admin_key")).toBe(false)
    expect(mockReload).toHaveBeenCalled()
  })

  it("on 403 throws ApiError with status 403 and 'Unauthorized' message", async () => {
    storageMap.set("primer_admin_key", "some-key")
    mockFetch.mockResolvedValue(mockResponse(403, "Forbidden"))

    await expect(apiFetch("/api/v1/test")).rejects.toThrow(
      expect.objectContaining({
        name: "ApiError",
        status: 403,
        message: "Unauthorized",
      })
    )
  })

  it("on non-ok response throws ApiError with status and body text", async () => {
    mockFetch.mockResolvedValue(mockResponse(500, "Internal Server Error"))

    await expect(apiFetch("/api/v1/test")).rejects.toThrow(
      expect.objectContaining({
        name: "ApiError",
        status: 500,
        message: "Internal Server Error",
      })
    )
  })

  it("on 404 throws ApiError with correct status", async () => {
    mockFetch.mockResolvedValue(mockResponse(404, "Not Found"))

    await expect(apiFetch("/api/v1/missing")).rejects.toThrow(
      expect.objectContaining({
        name: "ApiError",
        status: 404,
        message: "Not Found",
      })
    )
  })

  it("merges additional headers from init", async () => {
    mockFetch.mockResolvedValue(mockResponse(200, {}))

    await apiFetch("/api/v1/test", {
      headers: { "X-Custom-Header": "custom-value" },
    })

    expect(mockFetch).toHaveBeenCalledWith("/api/v1/test", {
      credentials: "include",
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "X-Custom-Header": "custom-value",
      }),
    })
  })

  it("passes through init options like method and body", async () => {
    mockFetch.mockResolvedValue(mockResponse(201, { id: "new" }))

    await apiFetch("/api/v1/test", {
      method: "POST",
      body: JSON.stringify({ name: "new item" }),
    })

    expect(mockFetch).toHaveBeenCalledWith("/api/v1/test", {
      method: "POST",
      body: JSON.stringify({ name: "new item" }),
      credentials: "include",
      headers: expect.objectContaining({
        "Content-Type": "application/json",
      }),
    })
  })
})
