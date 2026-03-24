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
    <div className="overflow-x-auto">
      <div className="inline-flex min-w-full gap-1 rounded-2xl border border-border/60 bg-muted/30 p-1 sm:min-w-0">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={cn(
              "flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-medium transition-all",
              activeTab === tab.id
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:bg-background/60 hover:text-foreground",
            )}
          >
            {tab.label}
            {tab.count != null && (
              <span
                className={cn(
                  "ml-1.5 rounded-full px-1.5 py-0.5 text-[11px]",
                  activeTab === tab.id
                    ? "bg-primary/10 text-primary"
                    : "bg-background/80 text-muted-foreground",
                )}
              >
                {tab.count.toLocaleString()}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
