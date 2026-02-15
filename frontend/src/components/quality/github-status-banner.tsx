interface Props {
  connected: boolean
}

export function GitHubStatusBanner({ connected }: Props) {
  if (connected) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
        <span className="h-2 w-2 rounded-full bg-emerald-500" />
        GitHub App connected &mdash; PR data and code review metrics are available.
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-4 py-2 text-sm text-muted-foreground">
      <span className="h-2 w-2 rounded-full bg-muted-foreground" />
      Connect a GitHub App for PR insights, merge rates, and code review metrics.
    </div>
  )
}
