import { useTranslation } from "react-i18next"

import InitializedView from "@/components/Evolution/TaskDetail/InitializedView"
import { buildDemoTask } from "@/data/demoFixtures"
import type { DemoPhase } from "@/hooks/useDemoMode"
import { useDemoState } from "@/hooks/useDemoMode"

/**
 * Center pane during the result phases (running → completed).
 *
 * Reuses the production `InitializedView` directly. That component reads
 * everything it needs from `EvolutionContext` — node graph, log entries,
 * active tab, selected nodes — and the demo route's layout already feeds
 * those slots with fixture-driven values via the existing demo
 * short-circuits in `useEvolutionNodes` and `useTaskLogs`.
 *
 * The IDE tab inside `InitializedView` already detects demo task ids and
 * swaps its iframe for a static code block, so no extra branching is
 * needed here.
 */
export default function DemoResultShell() {
  const { t } = useTranslation()
  const demoState = useDemoState()

  if (demoState.phase === "uninitialized") {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center text-muted-foreground">
        <p className="text-sm">
          {t("demo.result.notReady", {
            defaultValue: "Waiting for the build to start...",
          })}
        </p>
      </div>
    )
  }

  const task = buildDemoTask(demoState.phase as DemoPhase)
  return <InitializedView task={task} />
}
