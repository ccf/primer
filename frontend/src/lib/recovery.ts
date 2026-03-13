import type { RecoveryStrategy } from "@/types/api"

export const RECOVERY_STRATEGY_LABELS: Record<RecoveryStrategy, string> = {
  inspect_context: "Inspect Context",
  edit_fix: "Edit Fix",
  revert_or_reset: "Revert or Reset",
  rerun_verification: "Rerun Verification",
  delegate_or_parallelize: "Delegate or Parallelize",
}
