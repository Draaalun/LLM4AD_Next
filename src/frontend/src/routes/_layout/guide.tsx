import { createFileRoute } from "@tanstack/react-router"
import { Maximize2, Minimize2, RotateCcw } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"

import { UserManualContent } from "@/components/Guide/UserManualContent"
import { resetAllTours } from "@/components/Onboarding/tourStorage"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/_layout/guide")({
  component: GuidePage,
  head: () => ({
    meta: [
      {
        title: "Guide - LLM4AD_Next",
      },
    ],
  }),
})

function GuidePage() {
  const { t } = useTranslation()
  const { showSuccessToast } = useCustomToast()
  const [fullscreen, setFullscreen] = useState(false)

  const handleReplayTour = () => {
    // Reset every tour back to the freshly-registered state. Each one will
    // re-trigger when the user lands on its host page.
    resetAllTours()
    showSuccessToast(
      t("guide.tourReplayReset", {
        defaultValue:
          "Walkthroughs reset — they'll show up again as you visit each page.",
      }),
    )
  }

  return (
    <div
      className={cn(
        "relative",
        fullscreen
          ? "fixed inset-0 z-50 bg-background h-screen"
          : "h-full overflow-hidden",
      )}
    >
      <div className="absolute top-2 right-2 z-10 flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={handleReplayTour}
          title={t("guide.replayTour", {
            defaultValue: "Replay the guided tour",
          })}
        >
          <RotateCcw className="size-3.5" />
          {t("guide.replayTour", { defaultValue: "Replay the guided tour" })}
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
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
      </div>
      <UserManualContent className="h-full" />
    </div>
  )
}
