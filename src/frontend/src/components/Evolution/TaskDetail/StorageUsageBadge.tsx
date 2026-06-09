import { HardDrive } from "lucide-react"
import { useTranslation } from "react-i18next"

import type { StorageUsage } from "@/client"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

export default function StorageUsageBadge({
  storage,
}: {
  storage: StorageUsage
}) {
  const { t } = useTranslation()
  const pct =
    storage.limit_bytes > 0
      ? Math.min((storage.used_bytes / storage.limit_bytes) * 100, 100)
      : 0
  const isWarning = pct >= 80
  const isCritical = pct >= 95

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className={cn(
            "flex items-center gap-2 px-2.5 py-1 rounded-lg border text-[11px] font-medium tabular-nums transition-colors",
            isCritical
              ? "border-destructive/40 bg-destructive/5 text-destructive"
              : isWarning
                ? "border-amber-500/30 bg-amber-500/5 text-amber-600 dark:text-amber-400"
                : "border-border/50 bg-muted/40 text-muted-foreground",
          )}
        >
          <HardDrive className="size-3 shrink-0 opacity-60" />
          <div className="w-10 h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-[width] duration-300",
                isCritical
                  ? "bg-destructive"
                  : isWarning
                    ? "bg-amber-500"
                    : "bg-primary/60",
              )}
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="whitespace-nowrap">
            {storage.used_mb} / {storage.limit_mb} MB
          </span>
        </div>
      </TooltipTrigger>
      <TooltipContent side="bottom">
        {t("evolution.storageTooltip", { pct: pct.toFixed(1) })}
      </TooltipContent>
    </Tooltip>
  )
}
