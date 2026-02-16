import { useState } from "react"
import { HeartPulse, Smile, Zap, Target } from "lucide-react"
import { cn, formatNumber, formatPercent, formatCost, formatTokens } from "@/lib/utils"
import { useSessionInsights } from "@/hooks/use-api-queries"
import { StatCard } from "@/components/dashboard/stat-card"
import { HealthDistributionChart } from "@/components/session-insights/health-distribution-chart"
import { DailyHealthTrendChart } from "@/components/session-insights/daily-health-trend-chart"
import { EndReasonTable } from "@/components/session-insights/end-reason-table"
import { PermissionModeTable } from "@/components/session-insights/permission-mode-table"
import { SatisfactionTrendChart } from "@/components/session-insights/satisfaction-trend-chart"
import { FrictionClusterList } from "@/components/session-insights/friction-cluster-list"
import { DailyCacheTrendChart } from "@/components/session-insights/daily-cache-trend-chart"
import { GoalTypeTable } from "@/components/session-insights/goal-type-table"
import { GoalCategoryChart } from "@/components/session-insights/goal-category-chart"
import { PrimarySuccessChart } from "@/components/session-insights/primary-success-chart"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import type { DateRange } from "@/components/layout/date-range-picker"

const tabs = [
  { id: "health", label: "Health & Outcomes" },
  { id: "satisfaction", label: "Satisfaction & Friction" },
  { id: "cache", label: "Cache & Efficiency" },
  { id: "goals", label: "Goals & Success" },
] as const

type TabId = (typeof tabs)[number]["id"]

interface SessionInsightsPageProps {
  teamId: string | null
  dateRange: DateRange | null
}

export function SessionInsightsPage({ teamId, dateRange }: SessionInsightsPageProps) {
  const [activeTab, setActiveTab] = useState<TabId>("health")
  const startDate = dateRange?.startDate
  const endDate = dateRange?.endDate
  const { data, isLoading } = useSessionInsights(teamId, startDate, endDate)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Session Insights</h1>

      <div className="flex gap-1 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors",
              activeTab === tab.id
                ? "border-b-2 border-primary text-primary"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
          <CardSkeleton />
        </div>
      )}

      {!isLoading && data && (
        <>
          {activeTab === "health" && (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-3">
                <StatCard
                  label="Avg Health Score"
                  value={data.health_distribution.avg_score.toFixed(1)}
                  icon={HeartPulse}
                />
                <StatCard
                  label="Median Health Score"
                  value={data.health_distribution.median_score.toFixed(1)}
                  icon={HeartPulse}
                />
                <StatCard
                  label="Sessions Analyzed"
                  value={formatNumber(data.sessions_analyzed)}
                  icon={Target}
                />
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                <HealthDistributionChart data={data.health_distribution} />
                <DailyHealthTrendChart data={data.health_distribution.daily_trend} />
              </div>
              <EndReasonTable data={data.end_reasons} />
              <PermissionModeTable data={data.permission_modes} />
            </div>
          )}

          {activeTab === "satisfaction" && (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-3">
                <StatCard
                  label="Satisfaction Rate"
                  value={formatPercent(data.satisfaction.satisfaction_rate)}
                  icon={Smile}
                />
                <StatCard
                  label="Dissatisfied"
                  value={formatNumber(data.satisfaction.dissatisfied_count)}
                  icon={Smile}
                />
                <StatCard
                  label="Friction Types"
                  value={formatNumber(data.friction_clusters.length)}
                  icon={Target}
                />
              </div>
              <SatisfactionTrendChart data={data.satisfaction.trend} />
              <FrictionClusterList data={data.friction_clusters} />
            </div>
          )}

          {activeTab === "cache" && (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-3">
                <StatCard
                  label="Cache Hit Rate"
                  value={formatPercent(data.cache_efficiency.cache_hit_rate)}
                  icon={Zap}
                />
                <StatCard
                  label="Cache Savings"
                  value={data.cache_efficiency.cache_savings_estimate != null ? formatCost(data.cache_efficiency.cache_savings_estimate) : "-"}
                  icon={Zap}
                />
                <StatCard
                  label="Cache Read Tokens"
                  value={formatTokens(data.cache_efficiency.total_cache_read_tokens)}
                  icon={Zap}
                />
              </div>
              <DailyCacheTrendChart data={data.cache_efficiency.daily_cache_trend} />
            </div>
          )}

          {activeTab === "goals" && (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-3">
                <StatCard
                  label="Primary Success Rate"
                  value={formatPercent(data.primary_success.full_rate)}
                  icon={Target}
                />
                <StatCard
                  label="Top Session Type"
                  value={data.goals.session_type_breakdown[0]?.session_type ?? "-"}
                  icon={Target}
                />
                <StatCard
                  label="Top Goal Category"
                  value={data.goals.goal_category_breakdown[0]?.category ?? "-"}
                  icon={Target}
                />
              </div>
              <GoalTypeTable data={data.goals.session_type_breakdown} />
              <div className="grid gap-4 lg:grid-cols-2">
                <GoalCategoryChart data={data.goals.goal_category_breakdown} />
                <PrimarySuccessChart data={data.primary_success} />
              </div>
            </div>
          )}

          {data.sessions_analyzed === 0 && (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No session data available for insights analysis.
            </div>
          )}
        </>
      )}
    </div>
  )
}
