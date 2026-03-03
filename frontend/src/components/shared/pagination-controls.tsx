import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight } from "lucide-react"

interface PaginationControlsProps {
  offset: number
  pageSize: number
  totalCount: number
  onPrev: () => void
  onNext: () => void
}

export function PaginationControls({ offset, pageSize, totalCount, onPrev, onNext }: PaginationControlsProps) {
  const start = totalCount === 0 ? 0 : offset + 1
  const end = Math.min(offset + pageSize, totalCount)
  const hasPrev = offset > 0
  const hasNext = offset + pageSize < totalCount

  return (
    <div className="flex items-center justify-between pt-4">
      <span className="text-sm text-muted-foreground">
        Showing {start}–{end} of {totalCount}
      </span>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={onPrev} disabled={!hasPrev}>
          <ChevronLeft className="h-4 w-4" />
          Prev
        </Button>
        <Button variant="outline" size="sm" onClick={onNext} disabled={!hasNext}>
          Next
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
