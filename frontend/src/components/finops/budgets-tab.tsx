import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useBudgets } from "@/hooks/use-api-queries"
import { useCreateBudget, useUpdateBudget, useDeleteBudget } from "@/hooks/use-api-mutations"
import { CardSkeleton } from "@/components/shared/loading-skeleton"
import { formatCost, cn } from "@/lib/utils"
import { Plus, Pencil, Trash2, X } from "lucide-react"
import type { BudgetStatus } from "@/types/api"

interface BudgetsTabProps {
  teamId: string | null
  startDate?: string
  endDate?: string
}

interface BudgetFormData {
  name: string
  amount: number
  period: string
  alert_threshold_pct: number
  team_id?: string | null
}

const EMPTY_FORM: BudgetFormData = {
  name: "",
  amount: 0,
  period: "monthly",
  alert_threshold_pct: 80,
}

export function BudgetsTab({ teamId }: BudgetsTabProps) {
  const { data, isLoading } = useBudgets(teamId)
  const createBudget = useCreateBudget()
  const updateBudget = useUpdateBudget()
  const deleteBudget = useDeleteBudget()

  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<BudgetFormData>(EMPTY_FORM)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    )
  }

  if (!data) return null

  function openCreate() {
    setEditingId(null)
    setForm({ ...EMPTY_FORM, team_id: teamId })
    setShowModal(true)
  }

  function openEdit(budget: BudgetStatus) {
    setEditingId(budget.id)
    setForm({
      name: budget.name,
      amount: budget.amount,
      period: budget.period,
      alert_threshold_pct: budget.alert_threshold_pct,
      team_id: budget.team_id,
    })
    setShowModal(true)
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (editingId) {
      updateBudget.mutate(
        { id: editingId, ...form },
        { onSuccess: () => setShowModal(false) },
      )
    } else {
      createBudget.mutate(form, { onSuccess: () => setShowModal(false) })
    }
  }

  function handleDelete(id: string) {
    deleteBudget.mutate(id)
  }

  function statusColor(status: string) {
    switch (status) {
      case "on_track":
        return "bg-emerald-500"
      case "warning":
        return "bg-amber-500"
      case "over_budget":
        return "bg-red-500"
      default:
        return "bg-muted-foreground"
    }
  }

  function statusBadgeClasses(status: string) {
    switch (status) {
      case "on_track":
        return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
      case "warning":
        return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
      case "over_budget":
        return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
      default:
        return "bg-muted text-muted-foreground"
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Budgets</h2>
        <button
          onClick={openCreate}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Create Budget
        </button>
      </div>

      {data.length === 0 && (
        <div className="rounded-lg border border-border/60 bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No budgets configured. Create one to start tracking spend.
          </p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data.map((budget) => {
          const pctUsed = Math.min(budget.pct_used, 100)
          const pctDisplay = budget.pct_used.toFixed(0)
          return (
            <Card key={budget.id}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-sm font-medium">{budget.name}</CardTitle>
                    <div className="mt-1 flex items-center gap-2">
                      <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                        {budget.period}
                      </span>
                      <span
                        className={cn(
                          "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                          statusBadgeClasses(budget.status),
                        )}
                      >
                        {budget.status.replace("_", " ")}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={() => openEdit(budget)}
                      className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                      title="Edit budget"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => handleDelete(budget.id)}
                      className="rounded-md p-1 text-muted-foreground hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400 transition-colors"
                      title="Delete budget"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>
                        {formatCost(budget.current_spend)} / {formatCost(budget.amount)}
                      </span>
                      <span>{pctDisplay}%</span>
                    </div>
                    <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className={cn("h-full rounded-full transition-all", statusColor(budget.status))}
                        style={{ width: `${pctUsed}%` }}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-muted-foreground">Burn Rate</p>
                      <p className="font-medium">{formatCost(budget.burn_rate_daily)}/day</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Projected EoP</p>
                      <p className="font-medium">
                        {formatCost(budget.projected_end_of_period)}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setShowModal(false)}
          />
          <div className="relative w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">
                {editingId ? "Edit Budget" : "Create Budget"}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-foreground">
                  Name
                </label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="e.g. Engineering Q1"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-foreground">
                  Amount ($)
                </label>
                <input
                  type="number"
                  required
                  min={0}
                  step={0.01}
                  value={form.amount}
                  onChange={(e) => setForm({ ...form, amount: Number(e.target.value) })}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-foreground">
                  Period
                </label>
                <select
                  value={form.period}
                  onChange={(e) => setForm({ ...form, period: e.target.value })}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="monthly">Monthly</option>
                  <option value="quarterly">Quarterly</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-foreground">
                  Alert Threshold (%)
                </label>
                <input
                  type="number"
                  required
                  min={0}
                  max={100}
                  value={form.alert_threshold_pct}
                  onChange={(e) =>
                    setForm({ ...form, alert_threshold_pct: Number(e.target.value) })
                  }
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-muted-foreground hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createBudget.isPending || updateBudget.isPending}
                  className="rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  {editingId ? "Update" : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
