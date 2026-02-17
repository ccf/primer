export type EffectiveRole = "engineer" | "leadership"

export function getEffectiveRole(role: string): EffectiveRole {
  if (role === "admin" || role === "team_lead") return "leadership"
  return "engineer"
}

export function getDefaultRoute(role: string): "/profile" | "/dashboard" {
  return getEffectiveRole(role) === "leadership" ? "/dashboard" : "/profile"
}
