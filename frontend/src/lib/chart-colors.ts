export const CHART_COLORS = {
  primary: "var(--color-chart-primary)",
  secondary: "var(--color-chart-secondary)",
  tertiary: "var(--color-chart-tertiary)",
  quaternary: "var(--color-chart-quaternary)",
  quinary: "var(--color-chart-quinary)",
} as const

export const CHART_PALETTE = [
  CHART_COLORS.primary,
  CHART_COLORS.secondary,
  CHART_COLORS.tertiary,
  CHART_COLORS.quaternary,
  CHART_COLORS.quinary,
]

export const AXIS_TICK_STYLE = {
  fontSize: 11,
  fill: "var(--color-muted-foreground)",
} as const
