import { AlertTriangle, Check } from "lucide-react"

import { cn } from "@/lib/utils"

interface Step {
  label: string
  completed?: boolean
  warning?: boolean
}

interface StepperProps {
  steps: Step[]
  currentStep: number
  onStepClick?: (index: number) => void
}

export default function Stepper({
  steps,
  currentStep,
  onStepClick,
}: StepperProps) {
  return (
    <div className="flex items-center gap-1 overflow-x-auto">
      {steps.map((step, index) => {
        const isPast = index < currentStep
        const isActive = index === currentStep

        const isCompleted =
          step.completed !== undefined ? step.completed : isPast
        const showWarning = isPast && step.completed === false

        return (
          <div key={step.label} className="flex items-center gap-1 shrink-0">
            {index > 0 && (
              <div
                className={cn(
                  "h-px w-6",
                  isCompleted || isActive ? "bg-primary" : "bg-border",
                )}
              />
            )}
            <button
              type="button"
              onClick={() => onStepClick?.(index)}
              className={cn(
                "flex items-center gap-1.5 rounded-full px-1 py-0.5 text-sm transition-colors",
                onStepClick && "cursor-pointer hover:opacity-80",
                !onStepClick && "cursor-default",
              )}
            >
              <span
                className={cn(
                  "flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-medium",
                  isCompleted &&
                    !showWarning &&
                    "bg-primary text-primary-foreground",
                  showWarning && "bg-amber-500 text-white",
                  isActive &&
                    !isCompleted &&
                    "bg-primary text-primary-foreground",
                  !isCompleted &&
                    !isActive &&
                    !showWarning &&
                    "bg-muted text-muted-foreground",
                )}
              >
                {showWarning ? (
                  <AlertTriangle className="size-3.5" />
                ) : isCompleted ? (
                  <Check className="size-3.5" />
                ) : (
                  index + 1
                )}
              </span>
              <span
                className={cn(
                  "whitespace-nowrap text-xs font-medium",
                  isActive && "text-foreground",
                  showWarning &&
                    !isActive &&
                    "text-amber-600 dark:text-amber-400",
                  !isActive && !showWarning && "text-muted-foreground",
                )}
              >
                {step.label}
              </span>
            </button>
          </div>
        )
      })}
    </div>
  )
}
