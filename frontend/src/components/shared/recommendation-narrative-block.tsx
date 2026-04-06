import { useState } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"
import type { RecommendationNarrative } from "@/types/api"
import { cn } from "@/lib/utils"

interface RecommendationNarrativeBlockProps {
  narrative: RecommendationNarrative
  className?: string
  defaultExpanded?: boolean
}

export function RecommendationNarrativeBlock({
  narrative,
  className,
  defaultExpanded = false,
}: RecommendationNarrativeBlockProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <div className={cn("mt-3 border border-border/70 p-3 text-sm", className)}>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-1.5 text-left font-medium text-foreground/90 hover:text-foreground transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-3.5 w-3.5 shrink-0" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 shrink-0" />
        )}
        Why this helps
      </button>
      {expanded && (
        <div className="mt-2 space-y-1.5 pl-5">
          <p className="text-muted-foreground">{narrative.why_this_helps}</p>
          {narrative.evidence_summary && (
            <p className="text-muted-foreground">
              <span className="font-medium text-foreground/90">Evidence:</span>{" "}
              {narrative.evidence_summary}
            </p>
          )}
          {narrative.expected_impact && (
            <p className="text-muted-foreground">
              <span className="font-medium text-foreground/90">Likely impact:</span>{" "}
              {narrative.expected_impact}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
