import { NavLink } from "react-router-dom"
import { BarChart3, Layout, MonitorDot, Users } from "lucide-react"
import { cn } from "@/lib/utils"

const links = [
  { to: "/", label: "Overview", icon: Layout },
  { to: "/sessions", label: "Sessions", icon: MonitorDot },
  { to: "/engineers", label: "Engineers", icon: Users },
]

export function Sidebar() {
  return (
    <aside className="flex h-full w-56 flex-col border-r border-border bg-card">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <BarChart3 className="h-5 w-5 text-primary" />
        <span className="text-lg font-semibold">Primer</span>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )
            }
          >
            <link.icon className="h-4 w-4" />
            {link.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
