import { useNavigate } from "@tanstack/react-router"
import { ArrowRight, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"

import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { DEMO_PROJECT } from "@/data/demoFixtures"
import { getProjectIcon } from "./ProjectIcons"

export default function DemoProjectCard() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const Icon = getProjectIcon(DEMO_PROJECT.icon)

  const handleEnter = () => {
    // The dedicated /demo route owns the demo session lifecycle now —
    // _layout_demo calls enterDemo on mount.
    navigate({ to: "/demo" })
  }

  return (
    <Card
      data-tour="demo-project-card"
      onClick={handleEnter}
      className="group relative overflow-hidden cursor-pointer transition-all duration-200
        border-primary/40 bg-gradient-to-br from-primary/[0.06] via-primary/[0.02] to-transparent
        hover:border-primary/70 hover:shadow-lg hover:shadow-primary/15 hover:-translate-y-0.5"
    >
      <div
        className="pointer-events-none absolute -top-12 -right-12 size-32 rounded-full bg-primary/15 blur-2xl opacity-60 group-hover:opacity-100 transition-opacity duration-500"
        aria-hidden="true"
      />

      <span
        className="absolute top-2.5 right-2.5 z-10 inline-flex items-center gap-1
          rounded-full bg-primary/15 text-primary border border-primary/30
          px-2 py-0.5 text-[10px] font-semibold tracking-wider uppercase"
      >
        <Sparkles className="size-3" />
        {t("demo.badge", { defaultValue: "DEMO" })}
      </span>

      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-1.5 pt-4 px-4">
        <div className="flex items-center gap-2.5 min-w-0 pr-2">
          <div className="shrink-0 size-8 rounded-md bg-primary/10 text-primary flex items-center justify-center transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3">
            <Icon className="size-4.5" />
          </div>
          <CardTitle className="text-sm font-semibold leading-tight truncate">
            {t("demo.projectName", {
              defaultValue: "✨ Example · TSP Heuristic",
            })}
          </CardTitle>
        </div>
      </CardHeader>

      <CardContent className="pb-3 px-4">
        <p className="text-sm text-muted-foreground line-clamp-2 min-h-[2.5rem]">
          {t("demo.projectDescription", {
            defaultValue:
              "Read-only example. Walk through it to see how LLM4AD designs an algorithm end-to-end.",
          })}
        </p>
      </CardContent>

      <CardFooter className="pt-0 pb-3 px-4 flex items-center justify-between gap-2">
        <span className="text-xs text-muted-foreground/80">
          {t("demo.readOnly", { defaultValue: "Read-only · No LLM calls" })}
        </span>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            handleEnter()
          }}
          className="relative shrink-0 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium text-primary border border-primary/40 bg-primary/5 transition-all duration-300 group-hover:bg-primary group-hover:text-primary-foreground group-hover:border-primary hover:opacity-90 active:scale-95"
        >
          <span>
            {t("demo.startTour", { defaultValue: "Start guided tour" })}
          </span>
          <ArrowRight className="size-3.5 transition-transform duration-300 group-hover:translate-x-0.5" />
        </button>
      </CardFooter>
    </Card>
  )
}
