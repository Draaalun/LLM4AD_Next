import { useQuery } from "@tanstack/react-query"
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  MessageSquareText,
  XCircle,
} from "lucide-react"
import { useTranslation } from "react-i18next"

import { FeedbackService } from "@/client/sdk.gen"

const STAT_ITEMS = [
  { key: "total", icon: MessageSquareText, color: "text-foreground" },
  { key: "pending", icon: Clock, color: "text-amber-500" },
  { key: "in_progress", icon: Loader2, color: "text-blue-500" },
  { key: "resolved", icon: CheckCircle2, color: "text-emerald-500" },
  { key: "closed", icon: XCircle, color: "text-muted-foreground" },
  { key: "rejected", icon: AlertCircle, color: "text-red-500" },
] as const

const STAT_I18N_MAP: Record<string, string> = {
  total: "statistics.total",
  pending: "statistics.pending",
  in_progress: "statistics.inProgress",
  resolved: "statistics.resolved",
  closed: "statistics.closed",
  rejected: "statistics.rejected",
}

export function FeedbackStatistics() {
  const { t } = useTranslation()
  const { data: stats } = useQuery({
    queryKey: ["feedback-statistics"],
    queryFn: () => FeedbackService.getFeedbackStatistics(),
  })

  if (!stats) return null

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {STAT_ITEMS.map(({ key, icon: Icon, color }) => (
        <div
          key={key}
          className="flex items-center gap-3 rounded-lg border border-border/60 bg-card/60 px-4 py-3 transition-colors hover:bg-card"
        >
          <Icon className={`size-4 shrink-0 ${color}`} />
          <div className="min-w-0">
            <p className="text-lg font-semibold tabular-nums leading-tight">
              {stats[key as keyof typeof stats] as number}
            </p>
            <p className="text-[11px] text-muted-foreground truncate">
              {t(`feedback.${STAT_I18N_MAP[key]}`)}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
