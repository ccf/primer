import { Navigate, useSearchParams } from "react-router-dom"
import { useAuth } from "@/lib/auth-context"
import { getApiKey } from "@/lib/api"
import { useEngineerChooser } from "@/hooks/use-engineer-chooser"
import { EngineerChooserCard } from "@/components/shared/engineer-chooser-card"
import { CardSkeleton } from "@/components/shared/loading-skeleton"

/**
 * Profile page redirects to the unified engineer profile at /engineers/:id.
 *
 * For OAuth users, the redirect is immediate using the authenticated engineer ID.
 * For API-key users (no identity), a chooser is shown first.
 */
export function ProfilePage() {
  const { user } = useAuth()
  const isApiKeyUser = !user && !!getApiKey()
  const [searchParams, setSearchParams] = useSearchParams()
  const rawEngineerId = searchParams.get("engineer_id")

  const {
    engineerId,
    selectableEngineers,
    loadingEngineers,
    selectEngineer,
  } = useEngineerChooser({
    rawEngineerId,
    createSearchParams: (nextEngineerId) => {
      const nextParams = new URLSearchParams()
      if (nextEngineerId) nextParams.set("engineer_id", nextEngineerId)
      return nextParams
    },
    setSearchParams,
  })

  // OAuth user — redirect immediately
  if (user?.engineer_id) {
    return <Navigate to={`/engineers/${user.engineer_id}`} replace />
  }

  // API key user with a selected engineer — redirect
  if (isApiKeyUser && engineerId) {
    return <Navigate to={`/engineers/${engineerId}`} replace />
  }

  // API key user — show chooser
  if (isApiKeyUser && !engineerId) {
    if (loadingEngineers) {
      return (
        <div className="space-y-6">
          <CardSkeleton />
        </div>
      )
    }
    return (
      <div className="space-y-6">
        <EngineerChooserCard
          title="Choose a profile"
          description="Pick an engineer to view their profile, sessions, growth, and workflow insights."
          engineers={selectableEngineers}
          onSelect={selectEngineer}
        />
      </div>
    )
  }

  // Fallback — shouldn't normally happen
  return <Navigate to="/dashboard" replace />
}
