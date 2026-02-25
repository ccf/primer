import { cn } from "@/lib/utils"

interface Tab<T extends string> {
  id: T
  label: string
  count?: number
}

interface PageTabsProps<T extends string> {
  tabs: readonly Tab<T>[]
  activeTab: T
  onChange: (tab: T) => void
}

export function PageTabs<T extends string>({ tabs, activeTab, onChange }: PageTabsProps<T>) {
  return (
    <div className="flex gap-1 border-b border-border/60">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={cn(
            "relative px-4 py-2.5 text-sm font-medium transition-colors",
            activeTab === tab.id
              ? "text-foreground after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:bg-primary"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {tab.label}
          {tab.count != null && (
            <span className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
              {tab.count.toLocaleString()}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}
