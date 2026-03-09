import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { ArrowUpDown, Download, FileText } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { formatTokens, formatCost } from "@/lib/utils"
import { exportToCsv } from "@/lib/csv-export"
import { exportToPdf } from "@/lib/pdf-export"
import type { ProjectStats } from "@/types/api"

interface ProjectTableProps {
  projects: ProjectStats[]
  onSortChange: (sortBy: string) => void
  sortBy: string
}

const OUTCOME_COLORS: Record<string, string> = {
  success: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  partial: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  failure: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  abandoned: "bg-gray-100 text-gray-700 dark:bg-gray-800/50 dark:text-gray-400",
}

export function ProjectTable({ projects, onSortChange, sortBy }: ProjectTableProps) {
  const navigate = useNavigate()
  const [hoveredName, setHoveredName] = useState<string | null>(null)

  const columns = [
    { key: "project_name", label: "Project" },
    { key: "total_sessions", label: "Sessions" },
    { key: "unique_engineers", label: "Engineers" },
    { key: "total_tokens", label: "Tokens" },
  ] as const

  const projExportHeaders = ["Project", "Sessions", "Engineers", "Tokens", "Cost", "Success", "Partial", "Failure", "Abandoned", "Top Tools"]
  const projExportRows = () =>
    projects.map((p) => [
      p.project_name,
      p.total_sessions,
      p.unique_engineers,
      p.total_tokens,
      p.estimated_cost.toFixed(2),
      p.outcome_distribution.success ?? 0,
      p.outcome_distribution.partial ?? 0,
      p.outcome_distribution.failure ?? 0,
      p.outcome_distribution.abandoned ?? 0,
      p.top_tools.join(", "),
    ])

  const handleExport = () => {
    exportToCsv("projects.csv", projExportHeaders, projExportRows())
  }

  const handleExportPdf = () => {
    exportToPdf("projects.pdf", "Projects Report", projExportHeaders, projExportRows())
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-medium">Projects</CardTitle>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="mr-1 h-4 w-4" />
            Export CSV
          </Button>
          <Button variant="outline" size="sm" onClick={handleExportPdf}>
            <FileText className="mr-1 h-4 w-4" />
            Export PDF
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className="cursor-pointer pb-2 text-left font-medium text-muted-foreground hover:text-foreground"
                    onClick={() => onSortChange(col.key)}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {sortBy === col.key && <ArrowUpDown className="h-3 w-3" />}
                    </span>
                  </th>
                ))}
                <th className="pb-2 text-left font-medium text-muted-foreground">Cost</th>
                <th className="pb-2 text-left font-medium text-muted-foreground">Outcomes</th>
                <th className="pb-2 text-left font-medium text-muted-foreground">Top Tools</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((proj) => (
                <tr
                  key={proj.project_name}
                  className="cursor-pointer border-b border-border last:border-0 hover:bg-muted/50"
                  onMouseEnter={() => setHoveredName(proj.project_name)}
                  onMouseLeave={() => setHoveredName(null)}
                  onClick={() => navigate(`/projects/${encodeURIComponent(proj.project_name)}`)}
                >
                  <td className="py-2.5">
                    <span className={hoveredName === proj.project_name ? "underline" : ""}>
                      {proj.project_name}
                    </span>
                  </td>
                  <td className="py-2.5">{proj.total_sessions}</td>
                  <td className="py-2.5">{proj.unique_engineers}</td>
                  <td className="py-2.5">{formatTokens(proj.total_tokens)}</td>
                  <td className="py-2.5">{formatCost(proj.estimated_cost)}</td>
                  <td className="py-2.5">
                    <div className="flex gap-1">
                      {Object.entries(proj.outcome_distribution).map(([outcome, count]) => (
                        <span
                          key={outcome}
                          className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium ${OUTCOME_COLORS[outcome] ?? ""}`}
                        >
                          {outcome}: {count}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {proj.top_tools.slice(0, 3).map((tool) => (
                        <Badge key={tool} variant="secondary" className="text-[10px]">
                          {tool}
                        </Badge>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
