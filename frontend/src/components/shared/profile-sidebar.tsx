import { Activity, Target, DollarSign, Clock, Zap } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { InlineStat } from "@/components/ui/inline-stat"
import { formatNumber, formatPercent, formatCost, formatDuration } from "@/lib/utils"

interface ProfileSidebarProps {
  profile: {
    display_name: string | null
    name: string
    email: string
    avatar_url: string | null
    github_username: string | null
    team_name: string | null
    leverage_score?: number | null
    projects?: string[]
    overview: {
      total_sessions: number
      success_rate: number | null
      estimated_cost: number | null
      avg_session_duration: number | null
    }
  }
}

export function ProfileSidebar({ profile }: ProfileSidebarProps) {
  const overview = profile.overview
  const displayName = profile.display_name ?? profile.name
  const projects = profile.projects ?? []

  const stats = [
    { label: "Sessions", value: formatNumber(overview.total_sessions), icon: Activity },
    { label: "Success Rate", value: formatPercent(overview.success_rate), icon: Target },
    {
      label: "Est. Cost",
      value: overview.estimated_cost != null ? formatCost(overview.estimated_cost) : "-",
      icon: DollarSign,
    },
    { label: "Avg Duration", value: formatDuration(overview.avg_session_duration), icon: Clock },
  ]

  if (profile.leverage_score != null) {
    stats.push({
      label: "Leverage",
      value: profile.leverage_score.toFixed(1),
      icon: Zap,
    })
  }

  return (
    <Card>
      <CardContent className="p-5">
        {/* Avatar */}
        <div className="flex justify-center lg:justify-start">
          {profile.avatar_url ? (
            <img
              src={profile.avatar_url}
              alt={displayName}
              className="h-24 w-24 rounded-full ring-2 ring-border/40"
            />
          ) : (
            <div className="flex h-24 w-24 items-center justify-center rounded-full bg-muted text-2xl font-medium ring-2 ring-border/40">
              {displayName.charAt(0).toUpperCase()}
            </div>
          )}
        </div>

        {/* Name */}
        <div className="mt-4 text-center lg:text-left">
          <h1 className="font-display text-2xl">{displayName}</h1>
          {profile.github_username && (
            <p className="text-sm text-muted-foreground">@{profile.github_username}</p>
          )}
          <p className="mt-1 text-sm text-muted-foreground">{profile.email}</p>
        </div>

        {/* Stats grid */}
        <div className="mt-5 grid grid-cols-2 gap-3">
          {stats.map((s, i) => (
            <div
              key={s.label}
              className="animate-stagger-in"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <InlineStat label={s.label} value={s.value} icon={s.icon} />
            </div>
          ))}
        </div>

        {/* Team badge */}
        {profile.team_name && (
          <div className="mt-5">
            <span className="inline-flex items-center rounded-full border border-primary/20 bg-primary/8 px-3 py-1 text-xs font-medium text-primary">
              {profile.team_name}
            </span>
          </div>
        )}

        {/* Projects */}
        {projects.length > 0 && (
          <div className="mt-4">
            <p className="mb-2 text-xs font-medium text-muted-foreground">Projects</p>
            <div className="flex flex-wrap gap-1.5">
              {projects.slice(0, 8).map((p, i) => (
                <span
                  key={p}
                  className={
                    i < 3
                      ? "inline-flex items-center rounded-full bg-primary/8 px-2.5 py-0.5 text-xs font-medium text-primary"
                      : "inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium"
                  }
                >
                  {p}
                </span>
              ))}
              {projects.length > 8 && (
                <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
                  +{projects.length - 8} more
                </span>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
