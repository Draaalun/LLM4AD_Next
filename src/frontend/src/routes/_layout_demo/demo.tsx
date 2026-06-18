import { createFileRoute } from "@tanstack/react-router"
import { Plus } from "lucide-react"
import { useTranslation } from "react-i18next"

import DemoBuildShell from "@/components/Demo/DemoBuildShell"
import DemoResultShell from "@/components/Demo/DemoResultShell"
import { useDemoState } from "@/hooks/useDemoMode"

/**
 * Center pane for `/demo`. Phase-driven switch:
 *
 *   uninitialized          → Empty CTA prompt
 *   configuring / building → DemoBuildShell (chat + preview + run footer)
 *   running / completed    → DemoResultShell (real InitializedView)
 *
 * The empty state intentionally tells the user where to look (left panel)
 * rather than offering its own CTA — the only New-Task button lives in the
 * task list per the walkthrough's flow, and surfacing a duplicate here
 * would give the user a target the tour overlay isn't aware of.
 */
export const Route = createFileRoute("/_layout_demo/demo")({
  component: DemoIndex,
  head: () => ({
    meta: [
      {
        title: "Demo · LLM4AD_Next",
      },
    ],
  }),
})

function DemoIndex() {
  const { t } = useTranslation()
  const demoState = useDemoState()

  if (
    demoState.phase === "configuring" ||
    demoState.phase === "building"
  ) {
    return <DemoBuildShell />
  }

  if (demoState.phase === "running" || demoState.phase === "completed") {
    return <DemoResultShell />
  }

  // uninitialized — point the user at the left panel.
  return (
    <div className="h-full w-full flex flex-col items-center justify-center text-center px-6 gap-4">
      <div className="size-16 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
        <Plus className="size-7 text-primary" />
      </div>
      <p className="text-base font-medium text-foreground">
        {t("demo.center.emptyTitle", {
          defaultValue: "No task selected",
        })}
      </p>
      <p className="text-sm text-muted-foreground max-w-md leading-relaxed">
        {t("demo.center.emptyHint", {
          defaultValue:
            "Click the New task button on the left to start the walkthrough. The tour will guide you through every step.",
        })}
      </p>
    </div>
  )
}
