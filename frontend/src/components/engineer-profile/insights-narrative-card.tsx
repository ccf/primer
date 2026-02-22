import ReactMarkdown from "react-markdown"
import { cn } from "@/lib/utils"
import {
  type CardVariant,
  variantStyles,
  titleStyles,
  proseStyles,
  splitByHeadings,
  parseGlanceSections,
} from "./insights-utils"

interface InsightsNarrativeCardProps {
  title: string
  content: string
  variant?: CardVariant
  className?: string
}

export function InsightsNarrativeCard({
  title,
  content,
  variant = "white",
  className,
}: InsightsNarrativeCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border p-5",
        variantStyles[variant],
        className,
      )}
    >
      <h3 className={cn("mb-3 text-base font-semibold", titleStyles[variant])}>
        {title}
      </h3>
      <div
        className={cn(
          "prose prose-sm max-w-none",
          "[&_p]:mb-3 [&_p]:leading-relaxed [&_p:last-child]:mb-0",
          "[&_h3]:mb-2 [&_h3]:mt-4 [&_h3]:text-sm [&_h3]:font-semibold first:[&_h3]:mt-0",
          "[&_ul]:mt-1 [&_ul]:list-disc [&_ul]:pl-5 [&_li]:my-0.5 [&_li]:text-sm",
          proseStyles[variant],
        )}
      >
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  )
}

/**
 * At a Glance card with paragraphs rendered as separate styled divs
 * matching the report.html `.glance-section` layout.
 */
export function AtAGlanceCard({ content }: { content: string }) {
  const sections = parseGlanceSections(content)

  return (
    <div
      className={cn(
        "rounded-xl border p-5",
        variantStyles.gold,
      )}
    >
      <h3 className={cn("mb-4 text-base font-bold", "text-amber-900 dark:text-amber-200")}>
        At a Glance
      </h3>
      <div className="flex flex-col gap-3">
        {sections.map((section, i) => (
          <div
            key={i}
            className={cn(
              "text-sm leading-relaxed",
              proseStyles.gold,
            )}
          >
            {section.label && (
              <strong className="text-amber-900 dark:text-amber-200">
                {section.label}:{" "}
              </strong>
            )}
            <ReactMarkdown
              components={{
                // Render inline — strip wrapping <p> so text flows after the bold label
                p: ({ children }) => <span>{children}</span>,
              }}
            >
              {section.text}
            </ReactMarkdown>
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * Renders a list of split-by-heading items as individual colored cards.
 */
export function NarrativeItemCards({
  sectionTitle,
  content,
  variant,
}: {
  sectionTitle: string
  content: string
  variant: CardVariant
}) {
  const items = splitByHeadings(content)

  // If there's only one item with no heading, render as a single card
  if (items.length === 1 && !items[0].title) {
    return (
      <InsightsNarrativeCard
        title={sectionTitle}
        content={items[0].body}
        variant={variant}
      />
    )
  }

  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <div
          key={i}
          className={cn("rounded-xl border p-4", variantStyles[variant])}
        >
          {item.title && (
            <div
              className={cn(
                "mb-2 text-[15px] font-semibold",
                variant === "green"
                  ? "text-emerald-800 dark:text-emerald-200"
                  : variant === "red"
                    ? "text-red-900 dark:text-red-200"
                    : variant === "blue"
                      ? "text-blue-900 dark:text-blue-200"
                      : variant === "purple"
                        ? "text-violet-800 dark:text-violet-200"
                        : "text-foreground",
              )}
            >
              {item.title}
            </div>
          )}
          <div
            className={cn(
              "prose prose-sm max-w-none",
              "[&_p]:mb-2 [&_p]:leading-relaxed [&_p:last-child]:mb-0",
              "[&_ul]:mt-1 [&_ul]:list-disc [&_ul]:pl-5 [&_li]:my-0.5 [&_li]:text-sm",
              proseStyles[variant],
            )}
          >
            <ReactMarkdown>{item.body}</ReactMarkdown>
          </div>
        </div>
      ))}
    </div>
  )
}

export function NarrativeCardSkeleton({ variant = "white" }: { variant?: CardVariant }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-xl border p-5",
        variantStyles[variant],
      )}
    >
      <div className="mb-3 h-5 w-1/3 rounded bg-current opacity-10" />
      <div className="space-y-2">
        <div className="h-3 w-full rounded bg-current opacity-10" />
        <div className="h-3 w-5/6 rounded bg-current opacity-10" />
        <div className="h-3 w-4/6 rounded bg-current opacity-10" />
      </div>
    </div>
  )
}
