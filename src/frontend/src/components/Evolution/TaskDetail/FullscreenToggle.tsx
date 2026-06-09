import { Maximize2, Minimize2 } from "lucide-react"
import { type ReactNode, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"

interface FullscreenToggleProps {
  children: ReactNode
  className?: string
}

export default function FullscreenToggle({
  children,
  className = "",
}: FullscreenToggleProps) {
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

  const toggleBtn = (
    <button
      type="button"
      onClick={() => setFullscreen((v) => !v)}
      className="absolute top-2 right-2 z-10 p-1 rounded text-muted-foreground hover:text-primary hover:bg-accent/60 transition-all duration-200"
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
  )

  if (fullscreen) {
    return (
      <>
        <div className={`h-full w-full bg-background ${className}`} />
        <div className="fixed inset-0 z-50 bg-background flex flex-col">
          {toggleBtn}
          <div className="h-full w-full pt-8">{children}</div>
        </div>
      </>
    )
  }

  return (
    <div className={`relative h-full w-full overflow-hidden ${className}`}>
      {toggleBtn}
      {children}
    </div>
  )
}
