import { SessionBrowser } from "@/components/sessions/session-browser"
import type { DateRange } from "@/components/layout/date-range-picker"

interface SessionsTabProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function SessionsTab({ teamId, dateRange }: SessionsTabProps) {
  return <SessionBrowser teamId={teamId} dateRange={dateRange} showEngineerFilter />
}
