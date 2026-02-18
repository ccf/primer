import { useState } from "react"
import ReactMarkdown from "react-markdown"
import { ChevronDown, ChevronRight, Clock, RefreshCw, Sparkles } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { NarrativeResponse } from "@/types/api"

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

interface NarrativeReportProps {
  data: NarrativeResponse
  onRefresh: () => void
  isRefreshing: boolean
}

export function NarrativeReport({ data, onRefresh, isRefreshing }: NarrativeReportProps) {
  const [showSummary, setShowSummary] = useState(false)

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Sparkles className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold">{data.scope_label}</h2>
          {data.cached && (
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              cached
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            {timeAgo(data.generated_at)}
          </span>
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
          >
            <RefreshCw className={`h-3 w-3 ${isRefreshing ? "animate-spin" : ""}`} />
            Regenerate
          </button>
        </div>
      </div>

      {/* Sections */}
      {data.sections.map((section, i) => (
        <Card key={i}>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{section.title}</CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown>{section.content}</ReactMarkdown>
          </CardContent>
        </Card>
      ))}

      {/* Data summary footer */}
      <div className="border-t border-border pt-3">
        <button
          onClick={() => setShowSummary(!showSummary)}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          {showSummary ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          Data used for generation
        </button>
        {showSummary && (
          <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {Object.entries(data.data_summary)
              .filter(([, v]) => v != null)
              .map(([key, value]) => (
                <div key={key} className="rounded-lg bg-muted px-3 py-2">
                  <div className="text-xs text-muted-foreground">{key.replace(/_/g, " ")}</div>
                  <div className="text-sm font-medium">
                    {typeof value === "number" ? value.toLocaleString() : String(value)}
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  )
}
