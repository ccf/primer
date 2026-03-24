import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

interface SectionHeaderProps {
  title: string
  description?: string
  children?: ReactNode
  className?: string
}

export function SectionHeader({
  title,
  description,
  children,
  className,
}: SectionHeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between",
        className,
      )}
    >
      <div className="space-y-1">
        <h2 className="font-display text-xl tracking-tight text-foreground">{title}</h2>
        {description ? (
          <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
            {description}
          </p>
        ) : null}
      </div>
      {children ? <div className="flex items-center gap-2">{children}</div> : null}
    </div>
  )
}
