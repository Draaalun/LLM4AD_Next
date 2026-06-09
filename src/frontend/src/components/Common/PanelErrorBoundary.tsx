import { AlertTriangle, RefreshCw } from "lucide-react"
import type { ReactNode } from "react"
import { ErrorBoundary, type FallbackProps } from "react-error-boundary"
import { useTranslation } from "react-i18next"

function PanelErrorFallback({ resetErrorBoundary }: FallbackProps) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 p-6 text-center">
      <div
        className="p-3 rounded-full"
        style={{
          background:
            "radial-gradient(circle, rgba(239,68,68,0.12) 0%, transparent 70%)",
        }}
      >
        <AlertTriangle className="size-8 text-red-400/70" />
      </div>
      <div className="space-y-0.5">
        <p className="text-sm font-medium text-foreground">
          {t("evolution.panel.errorTitle", {
            defaultValue: "面板加载失败",
          })}
        </p>
        <p className="text-[11px] text-muted-foreground/70">
          {t("evolution.panel.errorHint", {
            defaultValue: "其它面板不受影响，可点击重试",
          })}
        </p>
      </div>
      <button
        type="button"
        onClick={resetErrorBoundary}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium
          border border-border/60 text-muted-foreground hover:text-primary
          hover:bg-accent/40 hover:border-primary/40 transition-colors"
      >
        <RefreshCw className="size-3.5" />
        {t("common.retry", { defaultValue: "重试" })}
      </button>
    </div>
  )
}

interface PanelErrorBoundaryProps {
  children: ReactNode
  /** Stable key to reset the boundary when the underlying data identity changes */
  resetKey?: string | number
}

/**
 * Boundary intended for individual panel contents (D3 viz, virtualized logs,
 * charts) so a render error doesn't take down the whole right column or
 * MultiPanelLayout grid.
 */
export default function PanelErrorBoundary({
  children,
  resetKey,
}: PanelErrorBoundaryProps) {
  return (
    <ErrorBoundary
      FallbackComponent={PanelErrorFallback}
      resetKeys={resetKey != null ? [resetKey] : undefined}
    >
      {children}
    </ErrorBoundary>
  )
}
