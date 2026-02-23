import ReactMarkdown from "react-markdown"
import { Clock, RefreshCw, Sparkles } from "lucide-react"
import { cn, timeAgo } from "@/lib/utils"
import { useNarrative, useNarrativeStatus } from "@/hooks/use-api-queries"
import { useRefreshNarrative } from "@/hooks/use-api-mutations"
import { InsightsBarChart } from "./insights-bar-chart"
import {
  AtAGlanceCard,
  NarrativeCardSkeleton,
  NarrativeItemCards,
} from "./insights-narrative-card"
import { proseStyles, variantStyles } from "./insights-utils"
import type { EngineerProfileResponse } from "@/types/api"

interface InsightsReportProps {
  profile: EngineerProfileResponse
  engineerId: string
  startDate?: string
  endDate?: string
}

export function InsightsReport({
  profile,
  engineerId,
  startDate,
  endDate,
}: InsightsReportProps) {
  const { data: status } = useNarrativeStatus()
  const {
    data: narrative,
    isLoading: narrativeLoading,
    error: narrativeError,
  } = useNarrative(
    "engineer",
    undefined,
    startDate,
    endDate,
    status?.available === true,
    engineerId,
  )

  const refreshMutation = useRefreshNarrative()
  const narrativeData = refreshMutation.data ?? narrative
  const isNarrativeReady = !!narrativeData && !narrativeLoading && !refreshMutation.isPending
  const showNarrativeSkeletons = narrativeLoading || refreshMutation.isPending

  const handleRefresh = () => {
    refreshMutation.mutate({ scope: "engineer", startDate, endDate, engineerId })
  }

  // Extract narrative sections by index (matching ENGINEER_SECTIONS order)
  const getSection = (index: number) => narrativeData?.sections?.[index]

  // Build bar chart data from profile
  const sessionTypeItems = Object.entries(profile.overview.session_type_counts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 6)
    .map(([label, value]) => ({ label, value }))

  const toolItems = profile.tool_rankings.slice(0, 6).map((t) => ({
    label: t.tool_name,
    value: t.total_calls,
  }))

  const outcomeItems = Object.entries(profile.overview.outcome_counts)
    .sort(([, a], [, b]) => b - a)
    .map(([label, value]) => ({ label, value }))

  const frictionItems = profile.friction.slice(0, 6).map((f) => ({
    label: f.friction_type,
    value: f.count,
  }))

  // Insufficient narrative data message
  const isInsufficientData =
    narrativeError &&
    (String(narrativeError).includes("422") || String(narrativeError).includes("Insufficient"))

  return (
    <div className="space-y-6">
      {/* Header with regenerate */}
      {(isNarrativeReady || showNarrativeSkeletons) && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Sparkles className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Insights Report</h2>
            {narrativeData?.cached && (
              <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                cached
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {narrativeData?.generated_at && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                {timeAgo(narrativeData.generated_at)}
              </span>
            )}
            <button
              onClick={handleRefresh}
              disabled={refreshMutation.isPending}
              className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
            >
              <RefreshCw className={`h-3 w-3 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
              Regenerate
            </button>
          </div>
        </div>
      )}

      {/* 1. At a Glance — gold card with 4 bold-labeled paragraphs */}
      {isNarrativeReady && getSection(0) ? (
        <AtAGlanceCard content={getSection(0)!.content} />
      ) : showNarrativeSkeletons ? (
        <NarrativeCardSkeleton variant="gold" />
      ) : null}

      {/* 2. Session Types + Top Tools */}
      {(sessionTypeItems.length > 0 || toolItems.length > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          <InsightsBarChart
            title="Session Types"
            items={sessionTypeItems}
            color="#2563eb"
          />
          <InsightsBarChart
            title="Top Tools"
            items={toolItems}
            color="#0891b2"
          />
        </div>
      )}

      {/* 3. How You Use CC — white narrative card with key-insight callout */}
      {isNarrativeReady && getSection(1) ? (
        <HowYouUseCCCard content={getSection(1)!.content} />
      ) : showNarrativeSkeletons ? (
        <NarrativeCardSkeleton variant="white" />
      ) : null}

      {/* 4. Impressive Things — each item as a separate green card */}
      {isNarrativeReady && getSection(2) ? (
        <NarrativeItemCards
          sectionTitle={getSection(2)!.title}
          content={getSection(2)!.content}
          variant="green"
        />
      ) : showNarrativeSkeletons ? (
        <div className="space-y-3">
          <NarrativeCardSkeleton variant="green" />
          <NarrativeCardSkeleton variant="green" />
        </div>
      ) : null}

      {/* 5. Outcomes */}
      {outcomeItems.length > 0 && (
        <InsightsBarChart title="Outcomes" items={outcomeItems} color="#10b981" />
      )}

      {/* 6. Where Things Go Wrong — each category as a separate red card */}
      {isNarrativeReady && getSection(3) ? (
        <NarrativeItemCards
          sectionTitle={getSection(3)!.title}
          content={getSection(3)!.content}
          variant="red"
        />
      ) : showNarrativeSkeletons ? (
        <div className="space-y-3">
          <NarrativeCardSkeleton variant="red" />
          <NarrativeCardSkeleton variant="red" />
        </div>
      ) : null}

      {frictionItems.length > 0 && (
        <InsightsBarChart title="Friction Breakdown" items={frictionItems} color="#ef4444" />
      )}

      {/* 7. CLAUDE.md Suggestions */}
      {profile.config_suggestions.length > 0 && (
        <div className="rounded-xl border border-blue-300 bg-blue-50 p-5 dark:border-blue-700 dark:bg-blue-950/30">
          <h3 className="mb-3 text-base font-semibold text-blue-900 dark:text-blue-200">
            CLAUDE.md Suggestions
          </h3>
          <div className="space-y-3">
            {profile.config_suggestions.slice(0, 5).map((s, i) => (
              <div key={i}>
                <div className="text-sm font-medium text-blue-900 dark:text-blue-200">
                  {s.title}
                </div>
                <p className="mt-0.5 text-sm text-blue-950/70 dark:text-blue-100/70">
                  {s.description}
                </p>
                {s.suggested_config && (
                  <pre className="mt-1.5 overflow-x-auto rounded-md border border-blue-200 bg-white/80 px-3 py-2 text-xs text-blue-900 dark:border-blue-600 dark:bg-blue-900/30 dark:text-blue-100">
                    <code>{s.suggested_config}</code>
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 8. New Usage Patterns — each pattern as a separate blue card */}
      {isNarrativeReady && getSection(4) ? (
        <NarrativeItemCards
          sectionTitle={getSection(4)!.title}
          content={getSection(4)!.content}
          variant="blue"
        />
      ) : showNarrativeSkeletons ? (
        <div className="space-y-3">
          <NarrativeCardSkeleton variant="blue" />
          <NarrativeCardSkeleton variant="blue" />
        </div>
      ) : null}

      {/* 9. On the Horizon — each idea as a separate purple card */}
      {isNarrativeReady && getSection(5) ? (
        <NarrativeItemCards
          sectionTitle={getSection(5)!.title}
          content={getSection(5)!.content}
          variant="purple"
        />
      ) : showNarrativeSkeletons ? (
        <div className="space-y-3">
          <NarrativeCardSkeleton variant="purple" />
          <NarrativeCardSkeleton variant="purple" />
        </div>
      ) : null}

      {/* 10. Memorable Moment — centered gold card */}
      {isNarrativeReady && getSection(6) ? (
        <div
          className={cn(
            "rounded-xl border p-6 text-center",
            variantStyles.gold,
          )}
        >
          <div className={cn("text-lg font-semibold mb-2", "text-amber-900 dark:text-amber-200")}>
            {getSection(6)!.title}
          </div>
          <div
            className={cn(
              "prose prose-sm mx-auto max-w-none",
              "[&_p]:leading-relaxed",
              proseStyles.gold,
            )}
          >
            <ReactMarkdown>{getSection(6)!.content}</ReactMarkdown>
          </div>
        </div>
      ) : showNarrativeSkeletons ? (
        <NarrativeCardSkeleton variant="gold" />
      ) : null}

      {/* Insufficient data message */}
      {isInsufficientData && (
        <p className="py-4 text-center text-sm text-muted-foreground">
          Not enough session data for narrative synthesis yet.
        </p>
      )}
    </div>
  )
}

/**
 * "How You Use CC" card — white card with markdown body,
 * plus a green key-insight callout extracted from `**Key pattern:**` lines.
 */
function HowYouUseCCCard({ content }: { content: string }) {
  // Extract **Key pattern:** or **Key insight:** line as a callout
  const keyPatternRegex = /\*\*Key (?:pattern|insight):\*\*\s*(.*)/i
  const match = content.match(keyPatternRegex)
  const mainContent = match ? content.replace(keyPatternRegex, "").trim() : content
  const keyInsight = match?.[1]?.trim()

  return (
    <div className={cn("rounded-xl border p-5", variantStyles.white)}>
      <h3 className="mb-3 text-base font-semibold text-foreground">
        How You Use Claude Code
      </h3>
      <div
        className={cn(
          "prose prose-sm max-w-none",
          "[&_p]:mb-3 [&_p]:leading-relaxed [&_p:last-child]:mb-0",
          proseStyles.white,
        )}
      >
        <ReactMarkdown>{mainContent}</ReactMarkdown>
      </div>
      {keyInsight && (
        <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200">
          <strong>Key pattern:</strong> {keyInsight}
        </div>
      )}
    </div>
  )
}
