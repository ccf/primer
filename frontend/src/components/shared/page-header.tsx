import type { LucideIcon } from "lucide-react"
import type { ReactNode } from "react"

interface PageHeaderProps {
  icon: LucideIcon
  title: string
  description?: string
  children?: ReactNode
}

export function PageHeader({ icon: Icon, title, description, children }: PageHeaderProps) {
  return (
    <div className="rounded-3xl border border-border/70 bg-gradient-to-br from-card via-card to-primary/[0.04] p-5 shadow-sm sm:p-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-primary/15 bg-primary/10 shadow-sm">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <div className="space-y-1">
            <h1 className="font-display text-3xl tracking-tight">{title}</h1>
            {description && (
              <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
                {description}
              </p>
            )}
          </div>
        </div>
        {children && <div className="flex items-center gap-2">{children}</div>}
      </div>
    </div>
  )
}
