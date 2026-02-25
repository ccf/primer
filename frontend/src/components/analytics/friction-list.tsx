import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { FrictionReport } from "@/types/api"
import { EmptyState } from "@/components/shared/empty-state"
import { useState } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"

interface FrictionListProps {
  data: FrictionReport[]
}

export function FrictionList({ data }: FrictionListProps) {
  const [expanded, setExpanded] = useState<string | null>(null)

  if (data.length === 0) {
    return <EmptyState message="No friction detected" />
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Friction Report</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {data.map((f) => (
            <div key={f.friction_type} className="rounded-xl border border-border/60">
              <div className="flex w-full items-center justify-between p-3 text-sm">
                <button
                  onClick={() => setExpanded(expanded === f.friction_type ? null : f.friction_type)}
                  className="flex items-center gap-3 text-left hover:text-foreground"
                >
                  {expanded === f.friction_type ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                  <span className="font-medium">{f.friction_type}</span>
                </button>
                <Badge variant="secondary">{f.count}</Badge>
              </div>
              {expanded === f.friction_type && f.details.length > 0 && (
                <div className="border-t border-border px-4 py-3">
                  <ul className="space-y-1">
                    {f.details.map((d, i) => (
                      <li key={i} className="text-sm text-muted-foreground">
                        {d}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
