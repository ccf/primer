import { useState } from "react"
import { cn } from "@/lib/utils"
import { AdminEngineersTab } from "@/components/admin/admin-engineers-tab"
import { AdminTeamsTab } from "@/components/admin/admin-teams-tab"
import { AdminAuditTab } from "@/components/admin/admin-audit-tab"
import { AdminSystemTab } from "@/components/admin/admin-system-tab"

const tabs = [
  { id: "engineers", label: "Engineers" },
  { id: "teams", label: "Teams" },
  { id: "audit", label: "Audit Log" },
  { id: "system", label: "System" },
] as const

type TabId = (typeof tabs)[number]["id"]

export function AdminPage() {
  const [activeTab, setActiveTab] = useState<TabId>("engineers")

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Admin</h1>

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

      {activeTab === "engineers" && <AdminEngineersTab />}
      {activeTab === "teams" && <AdminTeamsTab />}
      {activeTab === "audit" && <AdminAuditTab />}
      {activeTab === "system" && <AdminSystemTab />}
    </div>
  )
}
