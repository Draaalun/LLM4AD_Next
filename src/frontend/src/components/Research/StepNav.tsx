import {
  BookOpen,
  Code2,
  Dna,
  FileText,
  List,
  Loader2,
  Plus,
} from "lucide-react"
import { useTranslation } from "react-i18next"

import type { StepState } from "./mock-data"

const STEP_ICONS = [BookOpen, Code2, Dna, FileText]

function getLastCompletedIndex(steps: StepState[]): number {
  for (let i = steps.length - 1; i >= 0; i--) {
    if (steps[i].status === "completed") return i
  }
  return -1
}

export default function StepNav({
  activeStep,
  steps,
  onStepChange,
  onNewResearch,
  onToggleHistory,
}: {
  activeStep: number
  steps: StepState[]
  onStepChange: (step: number) => void
  onNewResearch: () => void
  onToggleHistory: () => void
}) {
  const { t } = useTranslation()
  const stepLabels = [
    t("research.steps.backgroundResearch"),
    t("research.steps.algorithmDesign"),
    t("research.steps.algorithmEvolve"),
    t("research.steps.paperCompilation"),
  ]
  const lastCompleted = getLastCompletedIndex(steps)

  return (
    <nav className="shrink-0 relative border-b border-border/20 bg-background">
      <div className="absolute inset-0 bg-gradient-to-r from-primary/[0.02] via-transparent to-blue-600/[0.01]" />

      <div className="relative z-10 flex items-center px-4 py-3">
        {/* Left: session list + new research */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={onToggleHistory}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg hover:bg-muted/60 border border-border/30 hover:border-primary/25 transition-colors"
          >
            <List className="size-3.5 text-muted-foreground" />
            <span className="text-[11px] font-medium text-muted-foreground">
              {t("research.sidebar.researchList")}
            </span>
          </button>
          <button
            type="button"
            onClick={onNewResearch}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-primary/8 hover:bg-primary/15 border border-primary/20 transition-colors"
          >
            <Plus className="size-3.5 text-primary" />
            <span className="text-[11px] font-medium text-primary">
              {t("research.sidebar.newResearch")}
            </span>
          </button>
        </div>

        {/* Center: steps */}
        <div className="flex-1 flex items-center justify-center">
          <div className="flex items-center gap-0">
            {stepLabels.map((label, i) => {
              const Icon = STEP_ICONS[i]
              const state = steps[i]
              const isActive = activeStep === i
              const isCompleted = state?.status === "completed"
              const isRunning = state?.status === "running"
              const connectorFilled = lastCompleted >= i

              return (
                <div key={i} className="flex items-center">
                  <button
                    type="button"
                    onClick={() => onStepChange(i)}
                    className={`relative group flex items-center gap-2.5 px-4 py-2 rounded-xl transition-all duration-300 ${
                      isActive
                        ? "bg-primary/12 shadow-md shadow-primary/10"
                        : "hover:bg-muted/50"
                    }`}
                  >
                    {isActive && (
                      <div className="absolute inset-0 rounded-xl border-2 border-primary/40 pointer-events-none" />
                    )}

                    <div className="relative">
                      <div
                        className={`size-9 rounded-lg flex items-center justify-center transition-all duration-300 ${
                          isActive
                            ? "bg-gradient-to-br from-primary to-blue-500 text-white shadow-lg shadow-primary/40"
                            : isCompleted
                              ? "bg-gradient-to-br from-emerald-500 to-teal-500 text-white shadow-md shadow-emerald-500/25"
                              : isRunning
                                ? "bg-primary/10 text-primary border border-primary/25"
                                : "bg-muted/70 text-muted-foreground/55 border border-border/50 group-hover:border-primary/25 group-hover:text-muted-foreground/75 group-hover:bg-muted"
                        }`}
                      >
                        {isRunning ? (
                          <Loader2
                            className="size-3.5 animate-spin"
                            strokeWidth={2.5}
                          />
                        ) : isCompleted ? (
                          <svg
                            className="size-4"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={3}
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                        ) : (
                          <span className="text-sm font-bold">{i + 1}</span>
                        )}
                      </div>

                      {isRunning && (
                        <div className="absolute inset-0 rounded-lg border-2 border-primary/20 animate-pulse" />
                      )}
                    </div>

                    <div className="flex items-center gap-1.5">
                      <Icon
                        className={`size-3 shrink-0 ${
                          isActive
                            ? "text-primary"
                            : isCompleted
                              ? "text-emerald-500/70"
                              : "text-muted-foreground/40"
                        }`}
                        strokeWidth={2}
                      />
                      <span
                        className={`font-medium whitespace-nowrap transition-colors ${
                          isActive
                            ? "text-xs text-primary font-bold"
                            : isCompleted
                              ? "text-[11px] text-foreground/75"
                              : "text-[11px] text-foreground/60 group-hover:text-foreground/80"
                        }`}
                      >
                        {label}
                      </span>
                    </div>
                  </button>

                  {i < 3 && (
                    <div className="flex items-center px-1">
                      <div
                        className={`w-8 h-0.5 rounded-full transition-all duration-500 ${
                          connectorFilled ? "bg-emerald-500/50" : "bg-border/30"
                        }`}
                      />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Right spacer to balance layout */}
        <div className="shrink-0 w-[180px]" />
      </div>
    </nav>
  )
}
