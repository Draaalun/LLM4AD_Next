import { ExternalLink, Github, Maximize2, Minimize2, X } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"

import { UserManualContent } from "@/components/Guide/UserManualContent"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { isLoggedIn } from "@/hooks/useAuth"
import { cn } from "@/lib/utils"

interface UserManualDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function UserManualDialog({
  open,
  onOpenChange,
}: UserManualDialogProps) {
  const { t } = useTranslation()
  const [fullscreen, setFullscreen] = useState(false)
  const logged = isLoggedIn()

  const handleOpenInNewWindow = () => {
    window.open("/guide", "_blank")
    onOpenChange(false)
  }

  const handleOpenOnGithub = () => {
    window.open(
      "https://github.com/Optima-CityU/LLM4AD_Next/blob/main/docs/index.md",
      "_blank",
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn(
          "flex flex-col p-0 gap-0 transition-[width,height,max-width,top,left,translate,border-radius,border-width] duration-300 ease-in-out",
          fullscreen
            ? "w-screen h-screen max-w-none sm:max-w-none rounded-none border-0 top-0 left-0 translate-x-0 translate-y-0"
            : "w-[calc(100vw-64px)] max-w-400 sm:max-w-400 h-[calc(100vh-64px)]",
        )}
        showCloseButton={false}
      >
        {/* Custom header with proper button spacing */}
        <div className="shrink-0 flex items-center justify-between px-6 pt-5 pb-4 border-b border-border">
          <DialogTitle className="text-lg font-semibold">
            {t("userManual.title")}
          </DialogTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={handleOpenOnGithub}
            >
              <Github className="size-3.5" />
              {t("userManual.openOnGithub")}
            </Button>
            {logged && (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={handleOpenInNewWindow}
              >
                <ExternalLink className="size-3.5" />
                {t("userManual.openInNewWindow")}
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => setFullscreen((v) => !v)}
              aria-label={
                fullscreen
                  ? t("userManual.exitFullscreen")
                  : t("userManual.enterFullscreen")
              }
              title={
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
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            >
              <X className="size-4" />
              <span className="sr-only">Close</span>
            </button>
          </div>
        </div>
        <UserManualContent className="flex-1 min-h-0" />
      </DialogContent>
    </Dialog>
  )
}
