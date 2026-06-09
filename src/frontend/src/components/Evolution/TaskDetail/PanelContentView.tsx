import { Maximize2, Minimize2 } from "lucide-react"
import { lazy, Suspense, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import type { TaskResponse } from "@/client"
import PanelErrorBoundary from "@/components/Common/PanelErrorBoundary"
import { cn } from "@/lib/utils"
import {
  PANEL_CONTENT_TYPES,
  type PanelContentType,
} from "./panel-layout-types"

// Heavy panel contents — pulled in only when their content type is selected.
const IslandGAVisualization = lazy(() => import("./IslandGAVisualization"))
const LogsPanel = lazy(() => import("./LogsPanel"))
const TrendPanel = lazy(() => import("./TrendPanel"))

interface PanelContentViewProps {
  task: TaskResponse
  contentType: PanelContentType
  onContentChange: (type: PanelContentType) => void
}

export default function PanelContentView({
  task,
  contentType,
  onContentChange,
}: PanelContentViewProps) {
  const { t } = useTranslation()
  const [fullscreen, setFullscreen] = useState(false)

  // ESC closes fullscreen
  useEffect(() => {
    if (!fullscreen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setFullscreen(false)
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [fullscreen])

  const content = (
    <PanelErrorBoundary resetKey={contentType}>
      <Suspense
        fallback={
          <div className="flex items-center justify-center h-full text-xs text-muted-foreground/60">
            {t("common.loading", { defaultValue: "Loading…" })}
          </div>
        }
      >
        {contentType === "visualization" && <IslandGAVisualization />}
        {contentType === "logs" && <LogsPanel task={task} />}
        {contentType === "trend" && <TrendPanel />}
      </Suspense>
    </PanelErrorBoundary>
  )

  const toolbar = (
    <div className="shrink-0 flex items-center justify-between px-1 py-1 border-b border-border/30 bg-background/80 backdrop-blur-sm">
      {/* Content type text buttons */}
      <div className="flex items-center gap-0.5">
        {PANEL_CONTENT_TYPES.map((type) => {
          const isActive = contentType === type
          return (
            <button
              key={type}
              type="button"
              onClick={() => onContentChange(type)}
              className={cn(
                "px-2 py-0.5 text-xs rounded transition-all duration-200",
                isActive
                  ? "text-primary bg-primary/10"
                  : "text-muted-foreground/50 hover:text-muted-foreground hover:bg-accent/30",
              )}
            >
              {t(`evolution.panelContent.${type}`)}
            </button>
          )
        })}
      </div>

      {/* Per-panel fullscreen toggle */}
      <button
        type="button"
        onClick={() => setFullscreen(!fullscreen)}
        className="p-1 rounded text-muted-foreground hover:text-primary hover:bg-accent/60 transition-all duration-200"
        title={
          fullscreen
            ? `${t("evolution.panel.exitFullscreen")} (Esc)`
            : t("evolution.panel.fullscreen")
        }
      >
        {fullscreen ? (
          <Minimize2 className="size-3.5" />
        ) : (
          <Maximize2 className="size-3.5" />
        )}
      </button>
    </div>
  )

  if (fullscreen) {
    return (
      <>
        {/* Placeholder to keep panel size */}
        <div className="h-full w-full bg-background" />
        {/* Fullscreen overlay */}
        <div className="fixed inset-0 z-50 bg-background flex flex-col">
          {toolbar}
          <div className="flex-1 min-h-0">{content}</div>
        </div>
      </>
    )
  }

  return (
    <div className="relative h-full w-full overflow-hidden bg-background flex flex-col">
      {toolbar}
      <div className="flex-1 min-h-0">{content}</div>
    </div>
  )
}
