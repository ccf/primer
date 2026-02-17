import { SessionBrowser } from "@/components/sessions/session-browser"
import type { DateRange } from "@/components/layout/date-range-picker"

interface ProfileSessionsTabProps {
  engineerId: string
  teamId: string | null
  dateRange: DateRange | null
}

export function ProfileSessionsTab({ engineerId, teamId, dateRange }: ProfileSessionsTabProps) {
  return (
    <SessionBrowser
      teamId={teamId}
      engineerId={engineerId}
      dateRange={dateRange}
      showEngineerFilter={false}
    />
  )
}
