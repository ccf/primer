import { useEffect, useMemo } from "react"
import { getApiKey } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { useEngineers } from "@/hooks/use-api-queries"
import type { EngineerResponse } from "@/types/api"

export const DEFAULT_ENGINEER_STORAGE_KEY = "primer_profile_engineer_id"

interface UseEngineerChooserOptions {
  rawEngineerId: string | null
  createSearchParams: (engineerId: string | null) => URLSearchParams
  setSearchParams: (params: URLSearchParams) => void
  storageKey?: string
}

interface UseEngineerChooserResult {
  isApiKeyUser: boolean
  engineerId: string
  selectableEngineers: EngineerResponse[]
  loadingEngineers: boolean
  selectEngineer: (engineerId: string) => void
  resetEngineer: () => void
}

export function useEngineerChooser({
  rawEngineerId,
  createSearchParams,
  setSearchParams,
  storageKey = DEFAULT_ENGINEER_STORAGE_KEY,
}: UseEngineerChooserOptions): UseEngineerChooserResult {
  const { user } = useAuth()
  const isApiKeyUser = !user && !!getApiKey()
  const rememberedEngineerId =
    isApiKeyUser && typeof window !== "undefined"
      ? window.localStorage.getItem(storageKey) ?? ""
      : ""
  const engineerId = user?.engineer_id ?? rawEngineerId ?? rememberedEngineerId ?? ""

  const { data: engineers, isLoading: loadingEngineers } = useEngineers(false, isApiKeyUser)

  useEffect(() => {
    if (!isApiKeyUser || !rawEngineerId || typeof window === "undefined") return
    window.localStorage.setItem(storageKey, rawEngineerId)
  }, [isApiKeyUser, rawEngineerId, storageKey])

  const selectableEngineers = useMemo(
    () =>
      (engineers ?? [])
        .filter((engineer) => engineer.is_active)
        .sort((a, b) =>
          (a.display_name ?? a.name).localeCompare(b.display_name ?? b.name),
        ),
    [engineers],
  )

  const selectEngineer = (nextEngineerId: string) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(storageKey, nextEngineerId)
    }
    setSearchParams(createSearchParams(nextEngineerId))
  }

  const resetEngineer = () => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(storageKey)
    }
    setSearchParams(createSearchParams(null))
  }

  return {
    isApiKeyUser,
    engineerId,
    selectableEngineers,
    loadingEngineers,
    selectEngineer,
    resetEngineer,
  }
}
