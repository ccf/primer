import { useState } from "react"
import { useAuth } from "@/lib/auth-context"
import { getApiKey } from "@/lib/api"
import { EmptyState } from "@/components/shared/empty-state"
import { PageTabs } from "@/components/ui/page-tabs"
import { AdminEngineersTab } from "@/components/admin/admin-engineers-tab"
import { AdminTeamsTab } from "@/components/admin/admin-teams-tab"
import { AdminAlertsTab } from "@/components/admin/admin-alerts-tab"
import { AdminNotificationsTab } from "@/components/admin/admin-notifications-tab"
import { AdminAuditTab } from "@/components/admin/admin-audit-tab"
import { AdminSystemTab } from "@/components/admin/admin-system-tab"

const tabs = [
  { id: "engineers", label: "Engineers" },
  { id: "teams", label: "Teams" },
  { id: "alerts", label: "Alert Thresholds" },
  { id: "notifications", label: "Notifications" },
  { id: "audit", label: "Audit Log" },
  { id: "system", label: "System" },
] as const

type TabId = (typeof tabs)[number]["id"]

export function AdminPage() {
  const { user } = useAuth()
  const isApiKeyUser = !user && !!getApiKey()
  const role = user?.role ?? (isApiKeyUser ? "admin" : "engineer")
  const [activeTab, setActiveTab] = useState<TabId>("engineers")

  if (role !== "admin") {
    return <EmptyState message="You do not have permission to access this page" />
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Admin</h1>

      <PageTabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === "engineers" && <AdminEngineersTab />}
      {activeTab === "teams" && <AdminTeamsTab />}
      {activeTab === "alerts" && <AdminAlertsTab />}
      {activeTab === "notifications" && <AdminNotificationsTab />}
      {activeTab === "audit" && <AdminAuditTab />}
      {activeTab === "system" && <AdminSystemTab />}
    </div>
  )
}
