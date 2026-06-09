import { format } from "date-fns"
import { useTranslation } from "react-i18next"
import type { FeedbackAdmin } from "@/client/types.gen"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

import { PRIORITY_STYLES, STATUS_STYLES, TYPE_STYLES } from "./feedbackStyles"

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  if (!children) return null
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <div className="text-sm">{children}</div>
    </div>
  )
}

interface FeedbackDetailDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  feedback: FeedbackAdmin | null
  isAdmin?: boolean
}

export function FeedbackDetailDialog({
  open,
  onOpenChange,
  feedback,
  isAdmin,
}: FeedbackDetailDialogProps) {
  const { t } = useTranslation()

  if (!feedback) return null

  const fmt = (d: string | null) =>
    d ? format(new Date(d), "yyyy-MM-dd HH:mm:ss") : "-"

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t("feedback.list.detailTitle")}</DialogTitle>
        </DialogHeader>

        <div className="space-y-5">
          {/* Header badges */}
          <div className="flex flex-wrap gap-2">
            <Badge
              variant="outline"
              className={TYPE_STYLES[feedback.type ?? "other"]}
            >
              {t(`feedback.submit.typeOptions.${feedback.type ?? "other"}`)}
            </Badge>
            <Badge variant="outline" className={STATUS_STYLES[feedback.status]}>
              {t(`feedback.list.status.${feedback.status}`)}
            </Badge>
            <Badge
              variant="outline"
              className={PRIORITY_STYLES[feedback.priority]}
            >
              {t(`feedback.list.priority.${feedback.priority}`)}
            </Badge>
          </div>

          {/* Title & Content */}
          <Field label={t("feedback.list.columns.title")}>
            <p className="font-medium">{feedback.title}</p>
          </Field>
          <Field label={t("feedback.list.content")}>
            <p className="whitespace-pre-wrap text-muted-foreground">
              {feedback.content}
            </p>
          </Field>

          {/* Contact info */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label={t("feedback.list.columns.contactEmail")}>
              {feedback.contact_email || "-"}
            </Field>
            <Field label={t("feedback.list.columns.contactPhone")}>
              {feedback.contact_phone || "-"}
            </Field>
          </div>

          {/* Admin reply */}
          {feedback.admin_reply && (
            <Field label={t("feedback.list.columns.adminReply")}>
              <div className="rounded-md bg-muted/50 p-3 text-sm whitespace-pre-wrap">
                {feedback.admin_reply}
              </div>
            </Field>
          )}

          {/* Admin-only fields */}
          {isAdmin && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label={t("feedback.list.columns.userEmail")}>
                {feedback.user_email || "-"}
              </Field>
              <Field label={t("feedback.list.columns.userName")}>
                {feedback.user_full_name || "-"}
              </Field>
              {feedback.tags && (
                <Field label={t("feedback.list.columns.tags")}>
                  <div className="flex flex-wrap gap-1">
                    {feedback.tags.split(",").map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">
                        {tag.trim()}
                      </Badge>
                    ))}
                  </div>
                </Field>
              )}
              {feedback.internal_notes && (
                <Field label={t("feedback.list.internalNotesLabel")}>
                  <div className="rounded-md bg-muted/50 p-3 text-sm whitespace-pre-wrap">
                    {feedback.internal_notes}
                  </div>
                </Field>
              )}
            </div>
          )}

          {/* Technical info */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t">
            <Field label={t("feedback.list.columns.pageUrl")}>
              <p className="break-all text-xs text-muted-foreground">
                {feedback.page_url || "-"}
              </p>
            </Field>
            <Field label={t("feedback.list.browserInfo")}>
              <p className="break-all text-xs text-muted-foreground">
                {feedback.browser_info || "-"}
              </p>
            </Field>
          </div>

          {/* Timestamps */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t text-xs text-muted-foreground">
            <div>
              <p className="font-medium">
                {t("feedback.list.columns.createdTime")}
              </p>
              <p>{fmt(feedback.created_time)}</p>
            </div>
            <div>
              <p className="font-medium">{t("feedback.list.resolvedTime")}</p>
              <p>{fmt(feedback.resolved_time)}</p>
            </div>
            <div>
              <p className="font-medium">
                {t("common.updatedTime") || "Updated"}
              </p>
              <p>{fmt(feedback.updated_time)}</p>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
