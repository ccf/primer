import { Users, Layers, Wrench } from "lucide-react"
import { StatCard } from "@/components/dashboard/stat-card"
import { formatNumber } from "@/lib/utils"
import type { SkillInventoryResponse } from "@/types/api"

interface SkillInventorySummaryProps {
  data: SkillInventoryResponse
}

export function SkillInventorySummary({ data }: SkillInventorySummaryProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <StatCard
        label="Total Engineers"
        value={formatNumber(data.total_engineers)}
        icon={Users}
      />
      <StatCard
        label="Session Types"
        value={formatNumber(data.total_session_types)}
        icon={Layers}
      />
      <StatCard
        label="Tools Used"
        value={formatNumber(data.total_tools_used)}
        icon={Wrench}
      />
    </div>
  )
}
