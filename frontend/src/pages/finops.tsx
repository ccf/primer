import { useState } from "react"
import { DollarSign } from "lucide-react"
import { PageTabs } from "@/components/ui/page-tabs"
import { PageHeader } from "@/components/shared/page-header"
import { OverviewTab } from "@/components/finops/overview-tab"
import { CacheTab } from "@/components/finops/cache-tab"
import { ModelingTab } from "@/components/finops/modeling-tab"
import { ForecastTab } from "@/components/finops/forecast-tab"
import { BudgetsTab } from "@/components/finops/budgets-tab"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "cache", label: "Cache" },
  { id: "modeling", label: "Cost Modeling" },
  { id: "forecasting", label: "Forecasting" },
  { id: "budgets", label: "Budgets" },
] as const

type TabId = (typeof tabs)[number]["id"]

interface FinOpsPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function FinOpsPage({ teamId, dateRange }: FinOpsPageProps) {
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate

  return (
    <div className="space-y-6">
      <PageHeader
        icon={DollarSign}
        title="FinOps"
        description="Cost analytics, forecasting, and budget management"
      />

      <PageTabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === "overview" && (
        <OverviewTab teamId={teamId} startDate={startDate} endDate={endDate} />
      )}

      {activeTab === "cache" && (
        <CacheTab teamId={teamId} startDate={startDate} endDate={endDate} />
      )}

      {activeTab === "modeling" && (
        <ModelingTab teamId={teamId} startDate={startDate} endDate={endDate} />
      )}

      {activeTab === "forecasting" && (
        <ForecastTab teamId={teamId} startDate={startDate} endDate={endDate} />
      )}

      {activeTab === "budgets" && (
        <BudgetsTab teamId={teamId} startDate={startDate} endDate={endDate} />
      )}
    </div>
  )
}
