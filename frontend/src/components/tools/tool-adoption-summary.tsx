import { Users, Wrench, BarChart3 } from "lucide-react"
import { StatCard } from "@/components/dashboard/stat-card"
import { formatNumber } from "@/lib/utils"
import type { ToolAdoptionAnalytics } from "@/types/api"

interface ToolAdoptionSummaryProps {
  data: ToolAdoptionAnalytics
}

export function ToolAdoptionSummary({ data }: ToolAdoptionSummaryProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <StatCard
        label="Tools Discovered"
        value={formatNumber(data.total_tools_discovered)}
        icon={Wrench}
      />
      <StatCard
        label="Avg Tools per Engineer"
        value={data.avg_tools_per_engineer.toFixed(1)}
        icon={BarChart3}
      />
      <StatCard
        label="Engineers"
        value={formatNumber(data.total_engineers)}
        icon={Users}
      />
    </div>
  )
}
