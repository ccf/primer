import { useState } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { FrictionCluster } from "@/types/api"

interface Props {
  data: FrictionCluster[]
}

export function FrictionClusterList({ data }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const toggle = (label: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(label)) next.delete(label)
      else next.add(label)
      return next
    })
  }

  if (data.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Friction Clusters</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {data.map((cluster) => (
          <div key={cluster.cluster_label} className="rounded-lg border border-border">
            <button
              onClick={() => toggle(cluster.cluster_label)}
              className="flex w-full items-center justify-between px-4 py-3 text-left text-sm hover:bg-accent/50"
            >
              <div className="flex items-center gap-3">
                {expanded.has(cluster.cluster_label) ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
                <span className="font-medium">{cluster.cluster_label}</span>
              </div>
              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                {cluster.occurrence_count}
              </span>
            </button>
            {expanded.has(cluster.cluster_label) && cluster.sample_details.length > 0 && (
              <div className="border-t border-border px-4 py-3">
                <ul className="space-y-1.5 text-xs text-muted-foreground">
                  {cluster.sample_details.map((detail, i) => (
                    <li key={i} className="truncate">
                      {detail}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
