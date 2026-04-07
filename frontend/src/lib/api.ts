const API_KEY_STORAGE = "primer_admin_key"
const DEMO_MODE_STORAGE = "primer_demo_mode"

export function getApiKey(): string | null {
  return localStorage.getItem(API_KEY_STORAGE)
}

export function setApiKey(key: string) {
  localStorage.setItem(API_KEY_STORAGE, key)
}

export function clearApiKey() {
  localStorage.removeItem(API_KEY_STORAGE)
}

export function isDemoMode(): boolean {
  return localStorage.getItem(DEMO_MODE_STORAGE) === "true"
}

/**
 * Check the server's demo config on startup. If the server is running in
 * demo mode, auto-inject the admin key so visitors skip the login page.
 * This key only grants read access — the server blocks all mutations.
 */
export async function initDemoMode(): Promise<boolean> {
  try {
    const res = await fetch("/api/v1/demo-config")
    if (res.ok) {
      const data = await res.json()
      if (data.demo_mode && data.admin_key) {
        setApiKey(data.admin_key)
        localStorage.setItem(DEMO_MODE_STORAGE, "true")
        return true
      }
    }
  } catch {
    // Server not reachable or not in demo mode — fall through to cleanup
  }
  // Not in demo mode (or server unreachable): clear any stale flag so that
  // apiFetch's 403 handling can clear the API key if it becomes invalid.
  localStorage.removeItem(DEMO_MODE_STORAGE)
  return false
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

  // In demo mode, 403 on mutations is expected — don't clear the key
  if (res.status === 403 && apiKey && !isDemoMode()) {
    clearApiKey()
    window.location.reload()
    throw new ApiError(403, "Unauthorized")
  }

  if (!res.ok) {
    throw new ApiError(res.status, await res.text())
  }

  return res.json() as Promise<T>
}
