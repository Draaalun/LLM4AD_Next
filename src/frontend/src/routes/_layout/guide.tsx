import { createFileRoute } from "@tanstack/react-router"
import { Maximize2, Minimize2 } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"

import { UserManualContent } from "@/components/Guide/UserManualContent"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/_layout/guide")({
  component: GuidePage,
  head: () => ({
    meta: [
      {
        title: "Guide - LLM4AD",
      },
    ],
  }),
})

function GuidePage() {
  const { t } = useTranslation()
  const [fullscreen, setFullscreen] = useState(false)

  return (
    <div
      className={cn(
        "relative",
        fullscreen
          ? "fixed inset-0 z-50 bg-background h-screen"
          : "h-full overflow-hidden",
      )}
    >
      <Button
        variant="outline"
        size="sm"
        className="absolute top-2 right-2 z-10 gap-1.5"
        onClick={() => setFullscreen((v) => !v)}
        title={
          fullscreen
            ? t("userManual.exitFullscreen")
            : t("userManual.enterFullscreen")
        }
        aria-label={
          fullscreen
            ? t("userManual.exitFullscreen")
            : t("userManual.enterFullscreen")
        }
      >
        {fullscreen ? (
          <Minimize2 className="size-3.5" />
        ) : (
          <Maximize2 className="size-3.5" />
        )}
        {fullscreen
          ? t("userManual.exitFullscreen")
          : t("userManual.enterFullscreen")}
      </Button>
      <UserManualContent className="h-full" />
    </div>
  )
}
