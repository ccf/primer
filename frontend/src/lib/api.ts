const API_KEY_STORAGE = "primer_admin_key"

export function getApiKey(): string | null {
  return localStorage.getItem(API_KEY_STORAGE)
}

export function setApiKey(key: string) {
  localStorage.setItem(API_KEY_STORAGE, key)
}

export function clearApiKey() {
  localStorage.removeItem(API_KEY_STORAGE)
}

class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

export { ApiError }

let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  if (refreshPromise) return refreshPromise
  refreshPromise = fetch("/api/v1/auth/refresh", {
    method: "POST",
    credentials: "include",
  })
    .then((res) => res.ok)
    .catch(() => false)
    .finally(() => {
      refreshPromise = null
    })
  return refreshPromise
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const apiKey = getApiKey()
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(apiKey ? { "x-admin-key": apiKey } : {}),
    ...(init?.headers as Record<string, string> | undefined),
  }

  const doFetch = () =>
    fetch(path, { ...init, headers, credentials: "include" })

  let res = await doFetch()

  // On 401 with no API key (cookie auth), attempt silent refresh
  if (res.status === 401 && !apiKey) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      res = await doFetch()
    }
  }

  if (res.status === 403 && apiKey) {
    clearApiKey()
    window.location.reload()
    throw new ApiError(403, "Unauthorized")
  }

  if (!res.ok) {
    throw new ApiError(res.status, await res.text())
  }

  return res.json() as Promise<T>
}
