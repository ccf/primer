import type { RecommendationNarrative } from "@/types/api"
import { cn } from "@/lib/utils"

interface RecommendationNarrativeBlockProps {
  narrative: RecommendationNarrative
  className?: string
}

export function RecommendationNarrativeBlock({
  narrative,
  className,
}: RecommendationNarrativeBlockProps) {
  return (
    <div className={cn("mt-3 border border-border/70 p-3 text-sm", className)}>
      <p className="font-medium text-foreground/90">Why this helps</p>
      <p className="mt-1 text-muted-foreground">{narrative.why_this_helps}</p>
      {narrative.evidence_summary && (
        <p className="mt-2 text-muted-foreground">
          <span className="font-medium text-foreground/90">Evidence:</span>{" "}
          {narrative.evidence_summary}
        </p>
      )}
      {narrative.expected_impact && (
        <p className="mt-1 text-muted-foreground">
          <span className="font-medium text-foreground/90">Likely impact:</span>{" "}
          {narrative.expected_impact}
        </p>
      )}
    </div>
  )
}
