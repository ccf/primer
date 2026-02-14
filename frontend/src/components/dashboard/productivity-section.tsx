import { Clock, Target, TrendingUp, Zap, Users, BarChart3 } from "lucide-react"
import { StatCard } from "@/components/dashboard/stat-card"
import { formatCost, formatNumber } from "@/lib/utils"
import type { ProductivityMetrics } from "@/types/api"

interface ProductivitySectionProps {
  data: ProductivityMetrics
}

export function ProductivitySection({ data }: ProductivitySectionProps) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Productivity & ROI</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Time Saved"
          value={
            data.estimated_time_saved_hours != null
              ? `${data.estimated_time_saved_hours.toFixed(0)}h`
              : "-"
          }
          subtitle={
            data.estimated_value_created != null
              ? `${formatCost(data.estimated_value_created)} value`
              : undefined
          }
          icon={Clock}
        />
        <StatCard
          label="Value Created"
          value={
            data.estimated_value_created != null
              ? formatCost(data.estimated_value_created)
              : "-"
          }
          subtitle={
            data.roi_ratio != null ? `${data.roi_ratio.toFixed(1)}x ROI` : undefined
          }
          icon={TrendingUp}
        />
        <StatCard
          label="Cost per Task"
          value={
            data.cost_per_successful_outcome != null
              ? formatCost(data.cost_per_successful_outcome)
              : "-"
          }
          subtitle={
            data.avg_cost_per_session != null
              ? `${formatCost(data.avg_cost_per_session)}/session`
              : undefined
          }
          icon={Target}
        />
        <StatCard
          label="Adoption Rate"
          value={`${data.adoption_rate.toFixed(0)}%`}
          subtitle={`${data.power_users} power user${data.power_users !== 1 ? "s" : ""}`}
          icon={Zap}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="ROI Ratio"
          value={data.roi_ratio != null ? `${data.roi_ratio.toFixed(1)}x` : "-"}
          icon={BarChart3}
        />
        <StatCard
          label="Engineers in Scope"
          value={formatNumber(data.total_engineers_in_scope)}
          icon={Users}
        />
        <StatCard
          label="Sessions/Eng/Day"
          value={data.sessions_per_engineer_per_day.toFixed(2)}
          icon={BarChart3}
        />
      </div>
    </div>
  )
}
