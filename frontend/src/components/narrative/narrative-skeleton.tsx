import { Lightbulb } from "lucide-react"

export function NarrativeSkeleton() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="mb-4 animate-pulse text-primary">
        <Lightbulb className="h-12 w-12" />
      </div>
      <h3 className="text-lg font-semibold">Generating insights...</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        This may take 10-15 seconds
      </p>
    </div>
  )
}
