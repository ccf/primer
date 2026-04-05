import { Activity, AlertTriangle, BarChart3 } from "lucide-react"
import { StatCard } from "@/components/dashboard/stat-card"
import { formatDuration, formatNumber, formatPercent } from "@/lib/utils"
import type { BottleneckAnalytics } from "@/types/api"

interface BottleneckSummaryProps {
  data: BottleneckAnalytics
}

export function BottleneckSummary({ data }: BottleneckSummaryProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard
        label="Sessions Analyzed"
        value={formatNumber(data.total_sessions_analyzed)}
        icon={Activity}
      />
      <StatCard
        label="Sessions with Friction"
        value={formatNumber(data.sessions_with_any_friction)}
        icon={AlertTriangle}
      />
      <StatCard
        label="Friction Rate"
        value={formatPercent(data.overall_friction_rate)}
        icon={BarChart3}
      />
      <StatCard
        label="Estimated Time Lost"
        value={formatDuration(data.total_estimated_minutes_lost * 60)}
        icon={AlertTriangle}
      />
    </div>
  )
}
