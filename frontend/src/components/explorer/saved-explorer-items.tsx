import { Bookmark, FileText, Play, Trash2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ExplorerSavedItemResponse } from "@/types/api"

interface SavedExplorerItemsProps {
  items: ExplorerSavedItemResponse[]
  onRun: (item: ExplorerSavedItemResponse) => void
  onDelete: (itemId: string) => void
  deletingId?: string | null
}

function scopeLabel(item: ExplorerSavedItemResponse): string {
  const parts: string[] = []
  if (item.scope_team_id) parts.push("Team scope")
  if (item.scope_start_date || item.scope_end_date) parts.push("Saved date range")
  return parts.join(" · ") || "Current scope"
}

export function SavedExplorerItems({
  items,
  onRun,
  onDelete,
  deletingId,
}: SavedExplorerItemsProps) {
  const prompts = items.filter((item) => item.item_type === "prompt")
  const reportCards = items.filter((item) => item.item_type === "report_card")

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Saved Prompts</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {prompts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No saved prompts yet.</p>
          ) : (
            prompts.map((item) => (
              <div
                key={item.id}
                className="rounded-xl border border-border/60 bg-muted/20 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 space-y-1">
                    <div className="flex items-center gap-2">
                      <Bookmark className="h-4 w-4 text-primary" />
                      <p className="truncate font-medium">{item.title}</p>
                    </div>
                    <p className="line-clamp-2 text-sm text-muted-foreground">
                      {item.prompt_text}
                    </p>
                    <p className="text-xs text-muted-foreground">{scopeLabel(item)}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button size="icon" variant="ghost" onClick={() => onRun(item)}>
                      <Play className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      disabled={deletingId === item.id}
                      onClick={() => onDelete(item.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Report Cards</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {reportCards.length === 0 ? (
            <p className="text-sm text-muted-foreground">No saved report cards yet.</p>
          ) : (
            reportCards.map((item) => (
              <div
                key={item.id}
                className="rounded-xl border border-border/60 bg-muted/20 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 space-y-2">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-primary" />
                      <p className="truncate font-medium">{item.title}</p>
                      <Badge variant="secondary">Report</Badge>
                    </div>
                    <p className="line-clamp-2 text-sm text-muted-foreground">
                      {item.prompt_text}
                    </p>
                    {item.result_preview ? (
                      <p className="line-clamp-3 text-xs text-muted-foreground">
                        {item.result_preview}
                      </p>
                    ) : null}
                    <p className="text-xs text-muted-foreground">{scopeLabel(item)}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button size="icon" variant="ghost" onClick={() => onRun(item)}>
                      <Play className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      disabled={deletingId === item.id}
                      onClick={() => onDelete(item.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  )
}
