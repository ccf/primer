import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`
  return tokens.toString()
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return "-"
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${(seconds / 3600).toFixed(1)}h`
}

export function formatNumber(n: number): string {
  return n.toLocaleString()
}

export function formatCost(dollars: number): string {
  if (dollars >= 1_000) return `$${(dollars / 1_000).toFixed(1)}K`
  return `$${dollars.toFixed(2)}`
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return "-"
  return `${(value * 100).toFixed(0)}%`
}

export function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

const MODEL_PRICING: Record<string, { input: number; output: number; cacheRead: number; cacheCreate: number }> = {
  // Anthropic (Claude Code)
  "claude-opus-4-6": { input: 5 / 1e6, output: 25 / 1e6, cacheRead: 0.5 / 1e6, cacheCreate: 6.25 / 1e6 },
  "claude-opus-4-5": { input: 5 / 1e6, output: 25 / 1e6, cacheRead: 0.5 / 1e6, cacheCreate: 6.25 / 1e6 },
  "claude-opus-4": { input: 15 / 1e6, output: 75 / 1e6, cacheRead: 1.5 / 1e6, cacheCreate: 18.75 / 1e6 },
  "claude-sonnet-4": { input: 3 / 1e6, output: 15 / 1e6, cacheRead: 0.3 / 1e6, cacheCreate: 3.75 / 1e6 },
  "claude-sonnet-3.5": { input: 3 / 1e6, output: 15 / 1e6, cacheRead: 0.3 / 1e6, cacheCreate: 3.75 / 1e6 },
  "claude-haiku-4-5": { input: 1 / 1e6, output: 5 / 1e6, cacheRead: 0.1 / 1e6, cacheCreate: 1.25 / 1e6 },
  "claude-haiku-3.5": { input: 0.8 / 1e6, output: 4 / 1e6, cacheRead: 0.08 / 1e6, cacheCreate: 1 / 1e6 },
  // OpenAI (Codex CLI)
  "gpt-5.3-codex": { input: 1.75 / 1e6, output: 14 / 1e6, cacheRead: 0.4375 / 1e6, cacheCreate: 1.75 / 1e6 },
  "gpt-5.2": { input: 1.75 / 1e6, output: 14 / 1e6, cacheRead: 0.4375 / 1e6, cacheCreate: 1.75 / 1e6 },
  "gpt-5-mini": { input: 0.25 / 1e6, output: 2 / 1e6, cacheRead: 0.0625 / 1e6, cacheCreate: 0.25 / 1e6 },
  "gpt-5": { input: 1.25 / 1e6, output: 10 / 1e6, cacheRead: 0.3125 / 1e6, cacheCreate: 1.25 / 1e6 },
  "gpt-4o-mini": { input: 0.15 / 1e6, output: 0.6 / 1e6, cacheRead: 0.0375 / 1e6, cacheCreate: 0.15 / 1e6 },
  "gpt-4o": { input: 2.5 / 1e6, output: 10 / 1e6, cacheRead: 0.625 / 1e6, cacheCreate: 2.5 / 1e6 },
  "gpt-4.1": { input: 2 / 1e6, output: 8 / 1e6, cacheRead: 0.5 / 1e6, cacheCreate: 2 / 1e6 },
  "gpt-4.1-mini": { input: 0.4 / 1e6, output: 1.6 / 1e6, cacheRead: 0.1 / 1e6, cacheCreate: 0.4 / 1e6 },
  "gpt-4.1-nano": { input: 0.1 / 1e6, output: 0.4 / 1e6, cacheRead: 0.025 / 1e6, cacheCreate: 0.1 / 1e6 },
  "o3-mini": { input: 1.1 / 1e6, output: 4.4 / 1e6, cacheRead: 0.275 / 1e6, cacheCreate: 1.1 / 1e6 },
  "o3": { input: 2 / 1e6, output: 8 / 1e6, cacheRead: 0.5 / 1e6, cacheCreate: 2 / 1e6 },
  "o4-mini": { input: 1.1 / 1e6, output: 4.4 / 1e6, cacheRead: 0.275 / 1e6, cacheCreate: 1.1 / 1e6 },
  "o1-mini": { input: 1.1 / 1e6, output: 4.4 / 1e6, cacheRead: 0.275 / 1e6, cacheCreate: 1.1 / 1e6 },
  "o1": { input: 15 / 1e6, output: 60 / 1e6, cacheRead: 3.75 / 1e6, cacheCreate: 15 / 1e6 },
  "codex-mini": { input: 1.5 / 1e6, output: 6 / 1e6, cacheRead: 0.375 / 1e6, cacheCreate: 1.5 / 1e6 },
  // Google (Gemini CLI)
  "gemini-3.1-pro": { input: 2 / 1e6, output: 12 / 1e6, cacheRead: 0.5 / 1e6, cacheCreate: 2 / 1e6 },
  "gemini-3.0-pro": { input: 2 / 1e6, output: 12 / 1e6, cacheRead: 0.5 / 1e6, cacheCreate: 2 / 1e6 },
  "gemini-2.5-pro": { input: 1.25 / 1e6, output: 10 / 1e6, cacheRead: 0.3125 / 1e6, cacheCreate: 1.25 / 1e6 },
  "gemini-2.5-flash": { input: 0.3 / 1e6, output: 2.5 / 1e6, cacheRead: 0.075 / 1e6, cacheCreate: 0.3 / 1e6 },
  "gemini-2.0-flash": { input: 0.1 / 1e6, output: 0.4 / 1e6, cacheRead: 0.025 / 1e6, cacheCreate: 0.1 / 1e6 },
  "gemini-1.5-pro": { input: 1.25 / 1e6, output: 5 / 1e6, cacheRead: 0.3125 / 1e6, cacheCreate: 1.25 / 1e6 },
  "gemini-1.5-flash": { input: 0.075 / 1e6, output: 0.3 / 1e6, cacheRead: 0.01875 / 1e6, cacheCreate: 0.075 / 1e6 },
}

export function getModelPricing(modelName: string) {
  let bestKey = ""
  for (const prefix of Object.keys(MODEL_PRICING)) {
    if (modelName.startsWith(prefix) && prefix.length > bestKey.length) {
      bestKey = prefix
    }
  }
  return MODEL_PRICING[bestKey] || MODEL_PRICING["claude-sonnet-4"]
}

export function estimateModelCost(
  modelName: string,
  usage: { input_tokens: number; output_tokens: number; cache_read_tokens?: number; cache_creation_tokens?: number },
): number {
  const p = getModelPricing(modelName)
  return (
    usage.input_tokens * p.input +
    usage.output_tokens * p.output +
    (usage.cache_read_tokens ?? 0) * p.cacheRead +
    (usage.cache_creation_tokens ?? 0) * p.cacheCreate
  )
}
