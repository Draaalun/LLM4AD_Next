import { useCallback, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import type { TaskResponse } from "@/client"
import FullscreenToggle from "./FullscreenToggle"
import InsightsPanel from "./InsightsPanel"
import IslandGAVisualization from "./IslandGAVisualization"

interface InsightsSplitViewProps {
  task: TaskResponse
}

const MIN_PCT = 25
const MAX_PCT = 75

export default function InsightsSplitView({ task }: InsightsSplitViewProps) {
  const { t } = useTranslation()
  const containerRef = useRef<HTMLDivElement>(null)
  const [leftPct, setLeftPct] = useState(50)
  const [isResizing, setIsResizing] = useState(false)

  const startResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
    const onMove = (ev: MouseEvent) => {
      const rect = containerRef.current?.getBoundingClientRect()
      if (!rect || rect.width === 0) return
      const pct = ((ev.clientX - rect.left) / rect.width) * 100
      setLeftPct(Math.max(MIN_PCT, Math.min(MAX_PCT, pct)))
    }
    const onUp = () => {
      setIsResizing(false)
      document.removeEventListener("mousemove", onMove)
      document.removeEventListener("mouseup", onUp)
      document.body.style.userSelect = ""
      document.body.style.cursor = ""
    }
    document.addEventListener("mousemove", onMove)
    document.addEventListener("mouseup", onUp)
    document.body.style.userSelect = "none"
    document.body.style.cursor = "ew-resize"
  }, [])

  return (
    <div
      ref={containerRef}
      className="flex h-full w-full overflow-hidden rounded-lg border border-dashed bg-card/50"
    >
      {/* Left: D3 evolution visualization */}
      <div
        className={`min-w-0 overflow-hidden relative ${
          isResizing ? "" : "transition-[width] duration-150 ease-out"
        }`}
        style={{ width: `${leftPct}%` }}
      >
        <FullscreenToggle>
          <IslandGAVisualization />
        </FullscreenToggle>
      </div>

      {/* Drag handle */}
      <div
        role="slider"
        tabIndex={-1}
        aria-label={t("evolution.dragToResize", {
          defaultValue: "Drag to resize",
        })}
        aria-valuemin={MIN_PCT}
        aria-valuemax={MAX_PCT}
        aria-valuenow={Math.round(leftPct)}
        onMouseDown={startResize}
        className="w-1 shrink-0 cursor-ew-resize bg-border/40 hover:bg-primary/40 active:bg-primary/60 transition-colors"
      />

      {/* Right: Insights panel (analysis report inputs + content) */}
      <div className="flex-1 min-w-0 overflow-hidden">
        <FullscreenToggle>
          <InsightsPanel task={task} />
        </FullscreenToggle>
      </div>
    </div>
  )
}
