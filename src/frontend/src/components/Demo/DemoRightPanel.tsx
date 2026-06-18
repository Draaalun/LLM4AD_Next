import { useTranslation } from "react-i18next"

import { buildDemoTask } from "@/data/demoFixtures"
import type { DemoPhase } from "@/hooks/useDemoMode"
import { useDemoState } from "@/hooks/useDemoMode"

/**
 * Read-only right-side panel for the demo route.
 *
 * Mirrors the visual rhythm of the real `EvolutionRightPanel` (compact
 * status badge, key/value rows, parameter list) but exposes ZERO
 * interactive controls — no Run / Stop / Adjust params / View params /
 * AI Build History buttons. Per leadership feedback the demo's right
 * column should be informational only, so the user never gets stuck on
 * a button that would silently no-op.
 *
 * The component derives its task state from the live `demoState.phase`
 * via `buildDemoTask(phase)` so the panel reflects whatever step of the
 * walkthrough the user is on (uninitialized → configuring → … → done).
 */
export default function DemoRightPanel() {
  const { t } = useTranslation()
  const demoState = useDemoState()

  if (demoState.phase === "uninitialized") {
    return (
      <div className="flex flex-col h-full">
        <div className="px-4 py-3 border-b border-border/50">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">
            {t("demo.rightPanel.title", { defaultValue: "Task Info" })}
          </span>
        </div>
        <div className="flex-1 flex items-center justify-center text-center px-4">
          <p className="text-xs text-muted-foreground/70">
            {t("demo.rightPanel.empty", {
              defaultValue: "Create a task to see its status and parameters.",
            })}
          </p>
        </div>
      </div>
    )
  }

  const task = buildDemoTask(demoState.phase as DemoPhase)
  const statusInfo = getStatusInfo(t, task.status)
  const args = (task.input_args ?? {}) as Record<string, unknown>

  return (
    <div className="flex flex-col h-full">
      <div className="shrink-0 px-4 py-3 border-b border-border/50 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">
          {t("demo.rightPanel.title", { defaultValue: "Task Info" })}
        </span>
        <span
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-medium uppercase tracking-wider border"
          style={{
            color: statusInfo.color,
            borderColor: `${statusInfo.color}55`,
            backgroundColor: `${statusInfo.color}15`,
          }}
        >
          <span
            className="size-1.5 rounded-full"
            style={{ backgroundColor: statusInfo.color }}
          />
          {statusInfo.label}
        </span>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3 space-y-4">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground/60 mb-1">
            {t("demo.rightPanel.name", { defaultValue: "Name" })}
          </div>
          <div className="text-sm text-foreground break-words">{task.name}</div>
        </div>

        {task.description && (
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground/60 mb-1">
              {t("demo.rightPanel.description", {
                defaultValue: "Description",
              })}
            </div>
            <div className="text-xs text-muted-foreground break-words leading-relaxed">
              {task.description}
            </div>
          </div>
        )}

        <div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground/60 mb-1">
            {t("demo.rightPanel.parameters", {
              defaultValue: "Parameters",
            })}
          </div>
          <div className="space-y-1">
            {Object.entries(args).length === 0 ? (
              <span className="text-xs text-muted-foreground/60 italic">
                {t("demo.rightPanel.noParameters", { defaultValue: "—" })}
              </span>
            ) : (
              Object.entries(args).map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-center justify-between gap-2 text-xs"
                >
                  <span className="text-muted-foreground font-mono truncate">
                    {key}
                  </span>
                  <span className="text-foreground font-mono tabular-nums">
                    {String(value)}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        <div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground/60 mb-1">
            {t("demo.rightPanel.flags", { defaultValue: "Build Mode" })}
          </div>
          <div className="text-xs text-foreground">
            {task.ai_built
              ? t("demo.rightPanel.aiBuilt", { defaultValue: "AI Build" })
              : t("demo.rightPanel.manualBuilt", {
                  defaultValue: "Manual Build",
                })}
          </div>
        </div>
      </div>

      <div className="shrink-0 px-4 py-2.5 border-t border-border/50">
        <p className="text-[10px] text-muted-foreground/60 italic leading-relaxed">
          {t("demo.rightPanel.readOnlyHint", {
            defaultValue:
              "Read-only — interactive controls are disabled in the demo.",
          })}
        </p>
      </div>
    </div>
  )
}

function getStatusInfo(
  t: (key: string, opts?: { defaultValue?: string }) => string,
  status: string,
): { label: string; color: string } {
  switch (status) {
    case "uninitialized":
      return {
        label: t("evolution.taskStatus.uninitialized", {
          defaultValue: "Uninitialized",
        }),
        color: "#6b7280",
      }
    case "pending":
      return {
        label: t("evolution.taskStatus.pending", { defaultValue: "Pending" }),
        color: "#f59e0b",
      }
    case "running":
      return {
        label: t("evolution.taskStatus.running", { defaultValue: "Running" }),
        color: "#00d4ff",
      }
    case "completed":
      return {
        label: t("evolution.taskStatus.completed", {
          defaultValue: "Completed",
        }),
        color: "#10b981",
      }
    case "failed":
      return {
        label: t("evolution.taskStatus.failed", { defaultValue: "Failed" }),
        color: "#ef4444",
      }
    default:
      return { label: status, color: "#6b7280" }
  }
}
