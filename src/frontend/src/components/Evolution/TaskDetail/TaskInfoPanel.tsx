import { ChevronDown, ChevronRight } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"

import type { TaskResponse } from "@/client"
import { Badge } from "@/components/ui/badge"
import { cn, formatDateTime } from "@/lib/utils"

interface TaskInfoPanelProps {
  task: TaskResponse
  className?: string
}

export default function TaskInfoPanel({ task, className }: TaskInfoPanelProps) {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(true)

  const statusMap: Record<
    string,
    {
      label: string
      variant: "default" | "secondary" | "destructive" | "outline"
    }
  > = {
    uninitialized: {
      label: t("evolution.taskStatus.uninitialized"),
      variant: "secondary",
    },
    pending: { label: t("evolution.taskStatus.pending"), variant: "outline" },
    running: { label: t("evolution.taskStatus.running"), variant: "default" },
    completed: {
      label: t("evolution.taskStatus.completed"),
      variant: "default",
    },
    failed: { label: t("evolution.taskStatus.failed"), variant: "destructive" },
  }

  const statusInfo = statusMap[task.status] ?? {
    label: task.status,
    variant: "secondary" as const,
  }

  return (
    <div className={cn("w-64 shrink-0 rounded-lg border bg-card", className)}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center gap-2 p-3 text-left"
      >
        {isOpen ? (
          <ChevronDown className="size-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-4 text-muted-foreground" />
        )}
        <span className="text-sm font-medium">{t("evolution.taskInfo")}</span>
      </button>
      {isOpen && (
        <div className="space-y-3 border-t px-3 pb-3 pt-2">
          <InfoRow
            label={t("evolution.taskInfoLabel.taskName")}
            value={task.name}
          />
          <InfoRow label={t("evolution.taskInfoLabel.status")}>
            <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
          </InfoRow>
          <InfoRow
            label={t("evolution.taskInfoLabel.createdTime")}
            value={formatDateTime(task.created_time)}
          />
          <InfoRow
            label={t("evolution.taskInfoLabel.updatedTime")}
            value={formatDateTime(task.updated_time)}
          />
          {task.description && (
            <InfoRow
              label={t("evolution.taskInfoLabel.description")}
              value={task.description}
            />
          )}
        </div>
      )}
    </div>
  )
}

function InfoRow({
  label,
  value,
  children,
}: {
  label: string
  value?: string
  children?: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      {children ?? <span className="text-sm break-all">{value}</span>}
    </div>
  )
}
